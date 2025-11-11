# Telegram Account Protection System Documentation

## Overview

This system prevents Telegram accounts from being banned through intelligent rate limiting, flood detection, and automatic job suspension. It's based on Telegram's official API rate limits and best practices from large-scale messaging platforms.

---

## Why This System Exists

**The Problem:**
- Telegram enforces strict rate limits to prevent spam and abuse
- Accounts can be **temporarily restricted** (hours/days) or **permanently banned** if limits are exceeded
- Mass messaging without proper spacing triggers immediate FloodWait responses
- Multiple FloodWait incidents → account suspension
- Users often don't know when their account is at risk until it's too late

**The Solution:**
- Intelligent rate limiting with per-account tracking
- Progressive flood detection with 4 severity levels
- Automatic job suspension to prevent ban
- Real-time account health monitoring
- Clear logging of all protection actions

---

## Telegram Official Limits

Based on Telegram's API documentation and reverse-engineered behavior:

```
SEND RATE LIMITS:
- Per-user: ~3-5 messages/second (different users)
- Per-chat: ~1 message/second
- Global: ~50 messages/second (all clients combined)

TIME-BASED LIMITS:
- Normal account: ~1000-2000 messages/hour
- Business account: ~5000 messages/hour
- Hourly resets at UTC 00:00

FloodWait Response:
- First violation: 5-10 second wait
- Repeated violations: 30-300 second wait (escalating)
- Continued abuse: Hours-long restrictions
- Patterns detected: Permanent ban

OUR SAFE THRESHOLDS:
- Max: 300 messages/hour (30% of normal limit)
- Max: 5000 messages/day
- Delay between messages: 30-120 seconds (user-configurable)
```

---

## Architecture

### Core Components

#### 1. `TelegramRateLimiter` Class (`core/account_protection.py`)
Main intelligent rate limiter with:
- Per-account message tracking (hour/day buckets)
- Flood severity categorization
- Progressive backoff strategies
- Account health status management

#### 2. Flood Severity Levels

```
LOW (1-10s wait):
  - 1st occurrence: Allow retry after full wait
  - 2nd occurrence: Add 50% delay increase
  - 3rd+ occurrence: Continue with 50% more delay
  
MEDIUM (11-60s wait):
  - 1st occurrence: Allow retry after 2x wait
  - 2nd occurrence: PAUSE JOB + alert
  - 3rd+ occurrence: SUSPEND ACCOUNT
  
HIGH (61-300s wait):
  - 1st occurrence: Allow retry after 4x wait
  - 2nd+ occurrence: SUSPEND ACCOUNT
  
CRITICAL (300+ seconds):
  - Any occurrence: IMMEDIATE SUSPEND
  - Account marked as critical risk
```

#### 3. Account Health States

```
HEALTHY
└─ Normal operation, no incidents
   
WARNED  
└─ 1 flood incident detected
└─ Job continues with monitoring
   
THROTTLED
└─ 2+ flood incidents
└─ Delays increased 2-4x
└─ Rate limits enforced strictly
   
SUSPENDED
└─ Too many incidents or critical flood
└─ Job auto-paused to prevent ban
└─ Manual intervention required
   
RESTRICTED
└─ Telegram-level API restriction active
└─ Cannot use account until restriction lifts
```

---

## How It Works

### Delay Spacing (Solves Your Original Issue)

**Your config:** min_delay=30s, max_delay=120s

**Before (PROBLEM):**
```
21:51:01 → Message 1
21:51:01 → Message 2  (same time!)
21:51:01 → Message 3  (same time!)
```

**After (FIXED):**
```
21:51:01 → Message 1 (waits 45s)
21:51:46 → Message 2 (waits 73s)  ← Different times!
21:52:59 → Message 3 (waits 35s)
```

**Implementation:**
- Each message applies random delay BEFORE sending
- Delays are applied inside the async pool (15 concurrent slots)
- Result: 15 concurrent tasks, each with independent wait timers
- Messages naturally space out while respecting concurrency limits

---

### Flood Detection & Auto-Stop

**Scenario: Account gets FloodWaitError(seconds=120)**

```python
1. Message send → FloodWaitError(120s)
   ↓
2. Rate limiter categorizes: MEDIUM severity
   ↓
3. Check consecutive floods: This is flood #2
   ↓
4. MEDIUM + 2 consecutive = OVER LIMIT
   ↓
5. Action: PAUSE_JOB (auto-stop job)
   ↓
6. Log: "ACCOUNT SUSPENDED: Job 42 paused. Too many flood incidents"
   ↓
7. Job status → 'paused'
   ↓
8. Account marked THROTTLED (next job will use longer delays)
```

**What the user sees in logs:**
```
[CRITICAL] FLOOD INCIDENT DETAILS: Job 42, Account 2, Action: PAUSE_JOB
Messages this hour: 127/300
Messages today: 1,245/5,000
Severity: medium

[ERROR] ACCOUNT SUSPENDED: Job 42 paused. Too many flood incidents.
Account protection triggered to prevent ban.
```

---

## Usage Guide

### 1. Create a Mass DM Job with Protection

```json
{
  "telegram_account_id": 2,
  "message": "Hello!",
  "csv_file_path": "/uploads/users.csv",
  "delay_seconds": null,
  "min_delay_seconds": 30,      // ← Minimum 30s between messages
  "max_delay_seconds": 120,     // ← Maximum 120s between messages
  "rate_limit_per_hour": 300    // ← Max 300 messages/hour
}
```

### 2. Monitor Job Execution

**Watch for these log patterns:**

```bash
# ✅ GOOD: Normal operation
Job 50: Sent message to user_123
Job 50: Sent message to user_456 (random delay applied)

# ⚠️  WARNING: Flood warning (1st incident)
[WARNING] FLOOD WARNING: Account 2 got low flood (8s wait)
[WARNING] Account 2 received flood warning. Job will continue with caution.

# 🚨 CRITICAL: Auto-pause (2+ incidents)
[ERROR] ACCOUNT SUSPENDED: Account 2 job 50 paused. Too many flood incidents.
[CRITICAL] ACCOUNT AT RISK: Job 50 - Account 2 has 2 consecutive flood incidents

# 💥 CRITICAL: Account protection triggered
[CRITICAL] ACCOUNT AT CRITICAL RISK: Account 2 suspended to prevent ban.
Flood wait: 600s (10 minutes!)
```

### 3. Check Account Health

In logs, you'll see:
```
Job 50 final status: completed
Account health: healthy
Hour messages: 145/300
Day messages: 2,890/5,000
```

### 4. After Flood Incidents

If an account has consecutive flood incidents:
- Delays are automatically increased 2-4x
- Next job using this account will get: `90-240s` instead of `30-120s`
- This reduces send rate to prevent future floods

---

## Protection Strategies

### Strategy 1: Rate Limit Enforcement

```python
# Before EACH message, check:
if account_messages_this_hour >= 300:
    job.status = 'paused'
    job.error_message = "Rate limit reached: 145/300"
    break  # Stop job gracefully
```

**Result:** Accounts never exceed 300/hour, staying far below Telegram's limit.

### Strategy 2: Progressive Backoff

```
1st flood (5s)    → Wait 5s + retry
2nd flood (15s)   → Increase delays by 2x (30-120 → 60-240)
                    + Wait 15s + retry
3rd flood (45s)   → Suspend account
```

**Result:** Each flood gets progressively more aggressive, protecting the account.

### Strategy 3: Severity-Based Actions

```
Severity = seconds_to_wait / categorization_threshold

LOW (≤10s)      → Can tolerate 3 incidents
MEDIUM (11-60s) → Can tolerate 2 incidents  
HIGH (61-300s)  → Can tolerate 1 incident
CRITICAL (>300) → STOP IMMEDIATELY
```

**Result:** Heavy flood responses = immediate job pause.

### Strategy 4: Per-Account Memory

```python
rate_limiter.account_stats[account_id] = {
    'messages_sent_hour': [time1, time2, ...],  # Track all sends
    'messages_sent_day': [time1, time2, ...],
    'flood_incidents': [
        {timestamp, wait_seconds, severity, job_id},
        ...
    ],
    'consecutive_floods': 2,
    'health_status': 'THROTTLED',
    'min_delay_current': 60,   # ← Dynamically increased
    'max_delay_current': 240,  # ← Dynamically increased
}
```

**Result:** Account delays adapt based on history.

---

## Real-World Examples

### Example 1: User Sends 50 Messages in 1 Hour (✅ Safe)

```
Config: min=30s, max=120s
User starts: 10:00 AM
Sends ~50 messages (one every ~60-90s)

Timeline:
10:01 → Message 1 (waited 45s)
10:02:30 → Message 2 (waited 90s)
10:03:45 → Message 3 (waited 75s)
...
10:51:00 → Message 50 (waited 60s)

Result:
✅ 50 messages sent
✅ Spaced over 51 minutes (NOT in 1 minute!)
✅ No flood warnings
✅ Account health: HEALTHY
```

### Example 2: User Tries to Send 500 Messages (⛔ Protected)

```
Config: min=30s, max=120s
Goal: Send 500 messages
Per-hour limit: 300 messages

Timeline:
Message 300 sent → 10:45 AM
[Rate Limiter] Hour limit reached: 300/300
Job paused with message: "Rate limit reached"

Result:
✅ Job stops gracefully
✅ Only 300 messages sent (safe limit)
⛔ 200 messages NOT sent (prevented abuse)
✅ Account remains healthy
```

### Example 3: Account Gets Flood Warning (⚠️ Smart Backoff)

```
Config: min=30s, max=120s
Telegram rate limit: 100 messages/10 minutes

Timeline:
Messages 1-50: Sent successfully (delays working)
Message 51: FloodWaitError(15 seconds)
   ↓
[Rate Limiter] MEDIUM flood severity, 1st incident
Action: CONTINUE_WITH_BACKOFF

New delays: 60-240s (2x multiplier)
[WARNING] Account 2 delays increased: 60-240s

Message 52-100: Sent with longer delays (safer)

Result:
✅ Flood detected early
✅ Delays adjusted automatically
✅ Job completes without account suspension
✅ Account health: WARNED (but not suspended)
```

### Example 4: Account Gets Critical Flood (🚨 Auto-Stop)

```
Timeline:
Message 50: FloodWaitError(8s) → Count: 1 (allowed)
Message 75: FloodWaitError(25s) → Count: 2 (allowed, delays increased)
Message 100: FloodWaitError(180s) → HIGH severity, Count: 3

[Rate Limiter] HIGH + 3 consecutive > tolerance
Action: CRITICAL_STOP

[CRITICAL] ACCOUNT AT CRITICAL RISK: Account 2 suspended
Flood wait: 180s (3 minutes!)
Job 42 auto-paused

Result:
🚨 Account suspended after 100 messages sent
✅ Prevented ban (would have been banned if continued)
⛔ Remaining 150 messages NOT sent (saved the account!)
```

---

## Monitoring & Alerts

### Key Metrics to Watch

1. **Messages/Hour Percentage**
   ```
   If > 60% of safe limit: ⚠️ WARNING
   If > 80% of safe limit: 🚨 CRITICAL
   ```

2. **Consecutive Floods**
   ```
   = 1: ⚠️  Watch closely
   = 2: 🚨 Increase delays
   ≥ 3: 🛑 STOP
   ```

3. **Account Health**
   ```
   HEALTHY     → No action
   WARNED      → Monitor
   THROTTLED   → Delays increased, continue
   SUSPENDED   → Manual review required
   RESTRICTED  → Account needs recovery
   ```

### Log Examples

✅ **All Good:**
```
[INFO] Job 50: Account health check - Status: healthy, Messages this hour: 45, Messages today: 312
```

⚠️ **Warning:**
```
[WARNING] FLOOD WARNING: Account 2 got low flood (8s wait). Job 50. Consecutive floods: 1
```

🚨 **Critical:**
```
[CRITICAL] ⚠️  ACCOUNT AT RISK: Job 50 - Account 2 has 2 consecutive flood incidents. Status: throttled
```

---

## Best Practices

### 1. Start Conservative
```
First jobs: min=60s, max=120s (slower is safer)
After 10+ safe jobs: min=30s, max=90s (adjust based on experience)
Never go below: min=15s, max=60s (too aggressive)
```

### 2. Monitor Account Health
```
After EACH job, check:
- Was there any flood incident? (look for [WARNING] FLOOD)
- What's the account health status?
- How many messages/hour did we send?
```

### 3. Space Out Large Campaigns
```
Goal: Send 5,000 messages/day
Don't: 1 job with 5,000 messages
Do: 5 jobs of 1,000 messages each, 2 hours apart
```

### 4. Use Rate Limit Config
```json
{
  "delay_seconds": null,          // Use random range instead
  "min_delay_seconds": 45,        // Conservative minimum
  "max_delay_seconds": 150,       // Conservative maximum
  "rate_limit_per_hour": 250      // Stay below 300 limit
}
```

### 5. After Incidents
```
Account got suspended? 
→ Wait 2-3 hours before retrying
→ Start with longer delays (min=120s, max=300s)
→ Monitor first 20 messages carefully
```

---

## Technical Implementation

### Flood Detection Integration

```python
# In mass_dm_account/tasks.py

# 1. On FloodWaitError:
except FloodWaitError as e:
    should_continue, action, details = rate_limiter.handle_flood_incident(
        account.id, flood_seconds, job_id
    )
    
    if not should_continue:
        result_dict['should_stop'] = True  # ← Triggers auto-stop
        return False  # ← Stop retrying

# 2. Check before each message:
is_safe, reason = rate_limiter.check_rate_limits(account.id)
if not is_safe:
    job.status = 'paused'  # ← Graceful stop
    break  # ← Exit loop

# 3. On job completion:
if result_dict['sent'] >= len(ids):
    rate_limiter.record_flood_recovery(account.id)  # ← Reset flood counter
```

### Account Health Check

```python
health = rate_limiter.get_account_health(account.id)
{
    "health_status": "healthy",
    "consecutive_floods": 0,
    "hour_messages": 145,
    "day_messages": 2890,
    "current_min_delay": 30,
    "current_max_delay": 120,
    "recent_incidents": []
}
```

---

## Troubleshooting

### Q: Why did my job pause?
**A:** Check logs for one of these:
- `[WARNING] FLOOD WARNING` - Account got flood alert
- `Rate limit reached: 145/300` - Hourly limit hit
- `AUTO-STOPPING due to flood protection` - Multiple floods detected

### Q: Delays got longer. Why?
**A:** Account had multiple flood incidents. Delays increase automatically:
```
1st flood: Delays stay 30-120s
2nd flood: Delays increase to 60-240s (2x)
3rd flood: Account suspended (job pauses)
```

### Q: Is my account banned?
**A:** Look for status in logs:
- `health_status: healthy` → Not banned ✅
- `health_status: restricted` → API restriction active ⛔
- If restricted, wait 2-6 hours and retry

### Q: Can I send more messages if I increase delays?
**A:** Delays don't affect hourly limits. You're still limited to ~300/hour.
Use multiple accounts or split campaigns across hours.

---

## Summary

This system provides **enterprise-grade account protection** by:

1. ✅ **Tracking** messages per account per hour/day
2. ✅ **Detecting** flood warnings in real-time
3. ✅ **Responding** with progressive backoff strategies
4. ✅ **Protecting** accounts by auto-stopping dangerous jobs
5. ✅ **Logging** all incidents for transparency
6. ✅ **Recovering** gracefully when incidents occur

**Result:** Your accounts stay safe and compliant with Telegram's policies.

---

## Version History

- **v1.0** (2025-11-08): Initial implementation
  - Flood detection with 4 severity levels
  - Progressive backoff strategies
  - Per-account rate limiting
  - Auto-stop on critical incidents
  - Account health monitoring
