# Step 4: Background Jobs & Scheduling

**Status:** Implementation Specification (No Code Yet)
**Branch:** `feature/campaign-engine-foundation`
**Date:** 2026-01-22

---

## Overview

Step 4 defines how background jobs are structured and orchestrated:
- How message send jobs are queued and executed
- How replies are ingested (worker side, paired with ReplyListener from Step 3)
- How timeout/cleanup jobs work (close stale jobs, auto-complete campaigns)
- How rate limiting and scheduling policies are enforced

This step **does not implement** a specific queue (Celery/RQ/APScheduler), but defines abstract interfaces and behaviors so you can plug in your chosen backend.

---

## 4.1 Components

### Workers & Job Types

We define three main worker categories:

1. **Message Sender Worker**
   - Executes `send_message_job`
   - Sends DM to user, updates interaction, queues next message

2. **Reply Ingestion Worker**
   - Executes `process_incoming_message_job`
   - Consumes messages from TG (via polling/webhook), calls `ReplyListener`

3. **Maintenance Worker**
   - Executes periodic jobs:
     - `close_stale_jobs_job` – timeout non-responding users
     - `auto_complete_campaigns_job` – mark campaigns as completed when fully done
     - `reset_daily_counters_job` – reset per-day usage counters

---

## 4.2 Abstract Job Queue Interface

We assume a generic job queue with this minimal interface:

```python
class JobQueue(Protocol):
    """Abstract job queue interface (Celery/RQ/other)."""

    async def enqueue(
        self,
        job_name: str,
        payload: dict,
        delay_seconds: int = 0,
    ) -> str:
        """Enqueue a job.

        Args:
            job_name: Logical job identifier (e.g., "send_message")
            payload: JSON-serializable payload
            delay_seconds: Delay before execution

        Returns:
            job_id: Queue-specific identifier
        """
        ...

    async def cancel(self, job_id: str) -> bool:
        """Cancel a scheduled/pending job.

        Returns True if existed and was cancelled, False otherwise.
        """
        ...
```

The concrete implementation (Celery task, RQ job, etc.) will just adapt to this contract.

---

## 4.3 Message Send Job: `send_message_job`

### Purpose
Send one campaign message to a specific user and advance the interaction state.

### Job Payload

```json
{
  "job_type": "send_message",
  "campaign_id": "<uuid>",
  "interaction_id": "<uuid>",
  "account_id": "<uuid>",
  "message_number": 1,
  "scheduled_at": "2026-01-22T02:30:00Z",
  "scheduled_delay_seconds": 180
}
```

### Execution Flow

```python
async def send_message_job(payload: dict):
    """Background job entrypoint for sending a message."""
    # 1. Extract payload
    campaign_id = UUID(payload["campaign_id"])
    interaction_id = UUID(payload["interaction_id"])
    account_id = UUID(payload["account_id"])
    message_number = payload["message_number"]

    # 2. Load entities
    campaign = db.get(Campaign, campaign_id)
    interaction = db.get(CampaignUserInteraction, interaction_id)
    account = db.get(TelegramAccount, account_id)

    # 3. Guard checks
    #   - Campaign exists and is ACTIVE
    #   - Interaction exists and not closed
    #   - Message_number is still valid (not already sent)

    # 4. Resolve proxy & client (Step 5 will detail this)

    # 5. Get message text
    message_text = campaign.get_message_by_number(message_number)

    # 6. Send DM via Telegram client

    # 7. On success:
    #   - Update interaction.message_N_sent_at = now
    #   - Clear interaction.message_N_job_id (job consumed)
    #   - Update interaction.current_phase (via InteractionService.transition_phase)
    #   - Increment campaign.total_messages_sent
    #   - Log action: message_sent

    # 8. On failure:
    #   - Log action: message_failed with error details
    #   - Depending on error type:
    #       * Retry with backoff (network/proxy issue)
    #       * Close job with reason (account_blocked, user_blocked)

    # 9. Queue next message if applicable (via MessageScheduler.schedule_next_message)
```

### Guard Conditions

1. **Campaign status must be ACTIVE.**
2. **Interaction must not be closed.**
3. **Message must not have been sent already** (check `message_N_sent_at`).
4. **Respect close_job_at_message:**
   - If `close_job_at_message = 2` and message_number > 2 → do not send.

### Retry Policy (Conceptual)

- **Network errors / proxy issues:**
  - Retry up to N times (e.g., 3) with exponential backoff.
- **Telegram 429 (rate limit):**
  - Backoff based on `retry_after` header if present.
  - Optionally move message to "deferred" queue to be retried later.
- **User-blocked / account-blocked / invalid user:**
  - Do not retry.
  - Close job with appropriate reason.

---

## 4.4 Reply Ingestion Job: `process_incoming_message_job`

### Purpose
Ingest a message received from Telegram and route it to `ReplyListener` (Step 3).

### Triggering
- Depends on how you integrate with Telegram:
  - **Webhook:** HTTP handler receives updates and enqueues this job.
  - **Polling:** Poller reads updates from TG and enqueues this job.

### Job Payload

```json
{
  "job_type": "process_incoming_message",
  "account_id": "<uuid>",
  "group_id": "-100123456789",
  "telegram_user_id": "123456789",
  "message_id": "12345",
  "message_text": "Hi, I'm interested.",
  "received_at": "2026-01-22T02:45:00Z"
}
```

### Execution Flow

```python
async def process_incoming_message_job(payload: dict):
    account_id = UUID(payload["account_id"])
    group_id = payload["group_id"]
    telegram_user_id = payload["telegram_user_id"]
    message_id = payload["message_id"]
    message_text = payload["message_text"]
    received_at = parse_datetime(payload["received_at"])

    # Use ReplyListener from Step 3
    processed = await reply_listener.handle_incoming_message(
        telegram_user_id=telegram_user_id,
        message_text=message_text,
        message_id=message_id,
        received_at=received_at,
        group_id=group_id,
        account_id=account_id,
    )

    # Optionally log if not matched (for debugging)
```

### Deduplication
- Handled in `ReplyListener.log_reply()` using `telegram_message_id` unique constraint.

---

## 4.5 Maintenance Jobs

### 4.5.1 `close_stale_jobs_job`

**Purpose:** Close interactions that have not received a reply after X days.

```python
async def close_stale_jobs_job(now: datetime, stale_days: int = 3):
    """Close jobs where last activity is older than stale_days and no reply."""

    cutoff = now - timedelta(days=stale_days)

    # Query interactions:
    # - job_closed = false
    # - current_phase in (B, C, D, E)
    # - last_reply_at IS NULL
    # - last message sent_at < cutoff

    interactions = (
        db.query(CampaignUserInteraction)
        .join(Campaign)
        .filter(
            CampaignUserInteraction.job_closed.is_(False),
            CampaignUserInteraction.current_phase.in_([
                InteractionPhase.B,
                InteractionPhase.C,
                InteractionPhase.D,
                InteractionPhase.E,
            ]),
            CampaignUserInteraction.last_reply_at.is_(None),
            # last message time < cutoff
        )
    )

    # For each, call InteractionService.close_job(reason="timeout")
```

**Notes:**
- "last message time" = max of non-null `message_N_sent_at` fields.
- Reason stored in `job_closed_reason` = "timeout".
- This job can run daily.

---

### 4.5.2 `auto_complete_campaigns_job`

**Purpose:** Mark campaigns as `completed` when all jobs are closed.

```python
async def auto_complete_campaigns_job(now: datetime):
    """Mark campaigns as COMPLETED when all interactions closed."""

    # Query campaigns where:
    # - status in (ACTIVE, PAUSED)
    # - no open interactions (job_closed=false)

    campaigns = (
        db.query(Campaign)
        .filter(Campaign.status.in_([CampaignStatus.ACTIVE, CampaignStatus.PAUSED]))
    )

    for campaign in campaigns:
        open_jobs_count = (
            db.query(CampaignUserInteraction)
            .filter_by(campaign_id=campaign.id, job_closed=False)
            .count()
        )
        if open_jobs_count == 0:
            # All jobs done → auto-complete
            campaign.status = CampaignStatus.COMPLETED
            campaign.completed_at = now
            log_service.log_action(
                campaign_id=campaign.id,
                action=CampaignLogAction.CAMPAIGN_COMPLETED,
                details={"auto_completed": True},
            )
```

**Notes:**
- This job can run every N minutes/hours.
- Only campaigns with no open interactions are auto-completed.

---

### 4.5.3 `reset_daily_counters_job`

**Purpose:** Reset daily counters for rate limiting.

Pre-requisite (Step 1/2):
- You may add fields like `daily_users_contacted`, `daily_reset_at` on `Campaign` or `TelegramAccount`.

```python
async def reset_daily_counters_job(now: datetime):
    """Reset per-day usage counters at midnight (or configured time)."""

    # Example for account-level counters:
    accounts = db.query(TelegramAccount).all()

    for account in accounts:
        if should_reset(account, now):
            account.daily_users_contacted = 0
            account.daily_reset_at = now
```

**Note:** This is optional and depends on how you implement rate limiting.

---

## 4.6 Rate Limiting & Scheduling Strategy

### Goals
- Avoid Telegram bans / rate limits
- Simulate human behavior
- Obey per-account and per-campaign limits

### Types of Limits

1. **Per-account message rate (hard):**
   - Max N messages per second/minute per Telegram account.

2. **Per-campaign daily cap:**
   - `Campaign.max_daily_users` (campaign-level)

3. **Per-user global daily cap:**
   - `User.campaign_default_behavior_max_daily_requests`

### Enforcement Points

1. **When scheduling next message (`MessageScheduler.schedule_next_message`):**
   - Check effective max_daily_users via `SettingsResolver.get_effective_max_daily_users()`.
   - Check current counters (messages/users contacted today).
   - If limit reached, do not schedule more jobs for that day.

2. **In `send_message_job` before sending:**
   - Check per-account rate (e.g., token bucket in memory/redis).
   - If account is "cooling down" due to 429 errors, skip/delay sending.

### Backoff Strategy for 429

- On 429:
  - Read `retry_after` if provided.
  - Delay next jobs for that account by `retry_after` seconds.
  - Optionally mark account in a `cooldown_until` timestamp.

---

## 4.7 Wiring to Step 3 Services

### From `MessageScheduler` (Step 3)
- Uses `JobQueue.enqueue` to queue `send_message` jobs.
- Uses `cancel` to cancel when pausing/completing campaigns.

### From `ReplyListener` (Step 3)
- It is **invoked by** the `process_incoming_message_job` worker.

### From `InteractionService` (Step 3)
- `close_stale_jobs_job` calls `InteractionService.close_job` for timeouts.

### From `CampaignService` (Step 3)
- `complete_campaign` / `fail_campaign` call `MessageScheduler.cancel_pending_jobs`.

---

## 4.8 Configuration & Environment

### Recommended Config Values

```yaml
campaigns:
  stale_days: 3          # Days without reply before timeout
  auto_complete_interval_minutes: 30

rate_limits:
  per_account_per_second: 1      # 1 DM / second
  per_account_per_minute: 30     # 30 DMs / minute

jobs:
  queue_name_send_message: "campaign_send_message"
  queue_name_process_reply: "campaign_process_reply"
  queue_name_maintenance: "campaign_maintenance"
```

### Environment Variables

- `CAMPAIGN_STALE_DAYS`
- `CAMPAIGN_RATE_LIMIT_PER_ACCOUNT_PER_SECOND`
- `CAMPAIGN_RATE_LIMIT_PER_ACCOUNT_PER_MINUTE`
- `CAMPAIGN_AUTO_COMPLETE_INTERVAL_MINUTES`

---

## 4.9 Testing Strategy

### Unit Tests

- `test_send_message_job_skips_if_campaign_not_active`
- `test_send_message_job_updates_interaction_on_success`
- `test_send_message_job_handles_telegram_errors`
- `test_process_incoming_message_job_calls_reply_listener`
- `test_close_stale_jobs_closes_old_interactions`
- `test_auto_complete_campaigns_marks_done_when_no_open_jobs`
- `test_rate_limit_blocks_scheduling_when_limit_reached`

### Integration Tests

- `test_end_to_end_message_delivery_and_reply_closure`
- `test_scheduling_respects_daily_caps`
- `test_429_backoff_logic`

---

## 4.10 Summary

**Step 4 Deliverables:**
- ✅ Abstract job queue interface defined
- ✅ `send_message_job` semantics defined
- ✅ `process_incoming_message_job` semantics defined
- ✅ Maintenance jobs (stale closure, auto completion, daily reset)
- ✅ Rate limiting & scheduling strategy
- ✅ Wiring to Step 3 services clarified
- ✅ Configuration points & testing strategy

**Status:** Specification Complete. Ready for Step 5 (Telegram Integration).

---

## Next: Step 5 → Telegram Integration

Step 5 will define:
- Telegram client wrapper interface
- Proxy handling for per-user accounts
- Error handling for Telegram-specific failure modes
- Mapping between internal models and Telegram entities
