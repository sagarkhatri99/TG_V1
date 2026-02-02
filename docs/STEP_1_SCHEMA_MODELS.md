# Step 1: Schema & Models Design

**Status:** Design Phase (No Code Yet)
**Branch:** `feature/campaign-engine-foundation`
**Date:** 2026-01-22

---

## Overview

Step 1 establishes the database schema and model structure for the Campaign Engine. This is **design only**—no implementation code yet. We define tables, relationships, constraints, and field purposes.

---

## 1.1 New Tables & Fields

### Table 1: `campaigns`

**Purpose:** Core campaign record. Stores campaign metadata, configuration, and aggregated stats.

| Field | Type | Constraint | Notes |
|-------|------|-----------|-------|
| `id` | UUID/BIGINT | PK | Unique campaign ID |
| `user_id` | UUID | FK → `users.id` | Campaign owner |
| `telegram_account_id` | UUID | FK → `telegram_accounts.id` | Associated Telegram account |
| `name` | VARCHAR(255) | NOT NULL | Campaign name (e.g., "Q1 Hiring Push") |
| `description` | TEXT | NULL | Optional campaign description |
| `target_group_id` | VARCHAR(255) | **NULL** | Telegram group ID (e.g., "-100123456789") - **OPTIONAL** |
| `target_group_name` | VARCHAR(255) | NULL | Cached group name for easy reference |
| `message_1_text` | TEXT | NOT NULL | Text of first message |
| `message_2_text` | TEXT | NOT NULL | Text of second message |
| `message_3_text` | TEXT | NOT NULL | Text of third message |
| `close_job_at_message` | SMALLINT | NOT NULL, CHECK (IN 2, 3) | Close job after message 2 or 3 |
| `message_1_delay_min` | INT | NOT NULL | Min delay before msg 1 (seconds) |
| `message_1_delay_max` | INT | NOT NULL | Max delay before msg 1 (seconds) |
| `message_2_delay_min` | INT | NOT NULL | Min delay before msg 2 (seconds) |
| `message_2_delay_max` | INT | NOT NULL | Max delay before msg 2 (seconds) |
| `message_3_delay_min` | INT | NULL | Min delay before msg 3 (NULL if close_job_at_message=2) |
| `message_3_delay_max` | INT | NULL | Max delay before msg 3 (NULL if close_job_at_message=2) |
| `status` | ENUM | NOT NULL, DEFAULT 'draft' | `draft`, `active`, `paused`, `completed`, `failed` |
| `priority` | ENUM | NOT NULL, DEFAULT 'medium' | `low`, `medium`, `high` |
| `max_daily_users` | INT | NULL | Daily cap (NULL = no limit) |
| `total_users_contacted` | INT | DEFAULT 0 | Running count of unique users sent msg 1 to |
| `total_messages_sent` | INT | DEFAULT 0 | Aggregate count of all messages (msg1 + msg2 + msg3) |
| `total_replies_received` | INT | DEFAULT 0 | Total replies received from all users |
| `total_jobs_closed` | INT | DEFAULT 0 | Total jobs closed (either after msg2 or msg3) |
| `created_at` | DATETIME | NOT NULL | Timestamp |
| `started_at` | DATETIME | NULL | When campaign transitioned to `active` |
| `completed_at` | DATETIME | NULL | When campaign ended |
| `last_activity_at` | DATETIME | NULL | Last message sent or reply received |

**Constraints:**
- PK: `id`
- FK: `user_id` → `users.id` (cascade delete)
- FK: `telegram_account_id` → `telegram_accounts.id` (cascade delete)
- UNIQUE: `(user_id, name)` – One campaign name per user
- CHECK: `message_1_delay_min <= message_1_delay_max` (and same for msg2, msg3)
- CHECK: `close_job_at_message IN (2, 3)`
- INDEX: `(user_id, status)` – For querying user's active campaigns
- INDEX: `(telegram_account_id, status)` – For processing by account
- INDEX: `created_at` – For historical queries

**Notes on `target_group_id` being OPTIONAL:**
- User can create campaign without specifying target group initially (Draft state)
- Group MUST be set before activation (validated at status transition)
- Validation: `target_group_id` required before `status` transitions to `active`
- Populated: Can be updated anytime campaign is not `active`

---

### Table 2: `campaign_user_interactions`

**Purpose:** Track interaction state per campaign per user. One row = one user in one campaign.

| Field | Type | Constraint | Notes |
|-------|------|-----------|-------|
| `id` | UUID/BIGINT | PK | Unique interaction record |
| `campaign_id` | UUID | FK → `campaigns.id` | Which campaign |
| `telegram_user_id` | VARCHAR(255) | NOT NULL | TG user ID (e.g., "123456789") |
| `telegram_username` | VARCHAR(255) | NULL | @username (if available) |
| `telegram_first_name` | VARCHAR(255) | **NULL** | First name from TG profile - **OPTIONAL** |
| `telegram_last_name` | VARCHAR(255) | NULL | Last name (optional) |
| `message_1_sent_at` | DATETIME | NULL | When msg 1 was sent |
| `message_1_job_id` | VARCHAR(255) | NULL | Background job ID (for tracking) |
| `message_2_sent_at` | DATETIME | NULL | When msg 2 was sent |
| `message_2_job_id` | VARCHAR(255) | NULL | Background job ID |
| `message_3_sent_at` | DATETIME | NULL | When msg 3 was sent (if close_job_at=3) |
| `message_3_job_id` | VARCHAR(255) | NULL | Background job ID |
| `last_reply_at` | DATETIME | NULL | Last reply received from this user |
| `reply_count` | INT | DEFAULT 0 | Number of replies received |
| `current_phase` | ENUM | DEFAULT 'A' | `A` (new), `B` (msg1 sent), `C` (msg2 sent), `D` (msg3 sent), `E` (awaiting), `closed` |
| `job_closed` | BOOLEAN | DEFAULT false | Has job been marked complete? |
| `job_closed_at` | DATETIME | NULL | When job was closed |
| `job_closed_reason` | VARCHAR(255) | NULL | Reason for closure (e.g., "user_replied", "timeout", "manual") |
| `created_at` | DATETIME | NOT NULL | When user was added to campaign |
| `updated_at` | DATETIME | NOT NULL | Last state change |

**Constraints:**
- PK: `id`
- FK: `campaign_id` → `campaigns.id` (cascade delete)
- UNIQUE: `(campaign_id, telegram_user_id)` – One interaction per user per campaign
- INDEX: `(campaign_id, current_phase)` – For state machine queries
- INDEX: `(telegram_user_id, campaign_id)` – For reverse lookup
- INDEX: `(job_closed, campaign_id)` – For finding open jobs
- INDEX: `created_at` – For pagination

**Notes on `telegram_first_name` being OPTIONAL:**
- Some Telegram accounts may not have first_name set
- Validation: Allow NULL, populate if available from TG API
- **Impact on dashboard:** Use fallback display logic:
  - If `telegram_first_name` NOT NULL → Use it
  - Else if `telegram_username` NOT NULL → Use username
  - Else → Use `telegram_user_id` as fallback
- **Impact on logging:** User always identified by `telegram_user_id` (no issues)
- **Impact on message personalization:** Can use `telegram_username` if first_name missing

---

### Table 3: `campaign_replies`

**Purpose:** Log each reply received from a user.

| Field | Type | Constraint | Notes |
|-------|------|-----------|-------|
| `id` | UUID/BIGINT | PK | Unique reply record |
| `interaction_id` | UUID | FK → `campaign_user_interactions.id` | Which interaction |
| `telegram_message_id` | VARCHAR(255) | NOT NULL | TG message ID (for dedup) |
| `message_text` | TEXT | NOT NULL | Full reply text |
| `received_at` | DATETIME | NOT NULL | When received |

**Constraints:**
- PK: `id`
- FK: `interaction_id` → `campaign_user_interactions.id` (cascade delete)
- UNIQUE: `telegram_message_id` – Prevent duplicate ingestion
- INDEX: `(interaction_id, received_at)` – For chronological queries

---

### Table 4: `campaign_logs`

**Purpose:** Audit trail of all campaign actions. For debugging, analytics, and compliance.

| Field | Type | Constraint | Notes |
|-------|------|-----------|-------|
| `id` | UUID/BIGINT | PK | Unique log entry |
| `campaign_id` | UUID | FK → `campaigns.id` | Which campaign |
| `telegram_user_id` | VARCHAR(255) | NULL | Affected user (may be null for campaign-level events) |
| `action` | VARCHAR(255) | NOT NULL | Action type (see below) |
| `phase` | ENUM | NULL | Phase at time of action (`A`, `B`, `C`, `D`, `E`, `closed`) |
| `message_number` | SMALLINT | NULL | 1, 2, or 3 (NULL for non-message actions) |
| `details` | JSON | NULL | Additional context (flexible structure) |
| `created_at` | DATETIME | NOT NULL | Event timestamp |

**Action Types:**
- `campaign_created` – Campaign record created
- `campaign_started` – Status changed to `active`
- `campaign_paused` – Status changed to `paused`
- `campaign_completed` – Status changed to `completed`
- `campaign_failed` – Status changed to `failed`
- `user_added` – User added to campaign targets
- `message_scheduled` – Message job scheduled
- `message_sent` – Message successfully sent
- `message_failed` – Message send failed
- `reply_received` – Reply received from user
- `job_closed` – Job closed (user interaction complete)
- `phase_updated` – Current phase changed
- `settings_updated` – Campaign settings modified

**Constraints:**
- PK: `id`
- FK: `campaign_id` → `campaigns.id` (cascade delete)
- INDEX: `(campaign_id, created_at DESC)` – For audit trail
- INDEX: `(telegram_user_id, created_at DESC)` – For user activity
- INDEX: `action` – For filtering by event type

---

## 1.2 Existing Tables: Updates & Additions

### `telegram_accounts` (Existing)

**Add/Verify:**
- Has `user_id` (FK → `users.id`) ✓
- Has `proxy_id` (FK → `proxies.id`) ✓
- Add field: `campaign_enabled` (BOOLEAN, DEFAULT false) – Feature flag for this account
- Add field: `campaign_default_sleep_hours` (INT, DEFAULT 8) – Default sleep hours for campaigns
- Add field: `campaign_default_max_daily_users` (INT, DEFAULT NULL) – Default daily cap
- Add field: `campaign_default_message_delay_min` (INT, DEFAULT 60) – Default min delay (seconds)
- Add field: `campaign_default_message_delay_max` (INT, DEFAULT 300) – Default max delay

---

### `proxies` (Existing)

**Verify:**
- Has `user_id` (FK → `users.id`) ✓ – **Strictly per-user, no cross-user sharing**
- Add field (if not present): `campaign_enabled` (BOOLEAN, DEFAULT true) – Can this proxy be used for campaigns?
- Add field (if not present): `usage_last_reset_at` (DATETIME) – For daily reset tracking

---

### `users` (Existing)

**Verify:**
- Has `id` (PK) ✓
- Add field: `campaign_feature_enabled` (BOOLEAN, DEFAULT false) – Global feature flag
- Add field: `campaign_default_behavior_sleep_hours` (INT, DEFAULT 8) – Sleep window per user
- Add field: `campaign_default_behavior_max_daily_requests` (INT, DEFAULT NULL) – Max DMs per day
- Add field: `campaign_default_behavior_request_interval_min` (INT, DEFAULT 30) – Min seconds between msgs
- Add field: `campaign_default_behavior_request_interval_max` (INT, DEFAULT 120) – Max seconds

---

## 1.3 Key Design Decisions & Impact Analysis

### A. Optional `target_group_id`

**Rationale:**
- Allow campaign creation in draft mode without selecting a group immediately
- User can build campaign template first, select target later

**Validation Flow:**
```
Draft state     → target_group_id can be NULL
Active request  → target_group_id MUST be NOT NULL (validation check)
Paused/Resume   → target_group_id must remain NOT NULL
Complete/Failed → target_group_id can be any value
```

**Implementation Points:**
1. **In model validation:** Add method `validate_can_activate()` that checks `target_group_id IS NOT NULL`
2. **In API:** Before updating status to `active`, call validation
3. **In dashboard:** Show warning/error "Group not selected" if `target_group_id` is NULL and status is `draft`
4. **In queries:** Filter by status to handle NULLs correctly (GROUP BY should work fine)

**Does NOT harm functionality:**
- ✓ Indexes unaffected (no index on NULL-heavy column)
- ✓ Queries use `status` column primarily, not `target_group_id`
- ✓ Validation enforces non-NULL before activation
- ✓ No cascading impacts

### B. Optional `telegram_first_name`

**Rationale:**
- Not all Telegram users have `first_name` set in their profile
- Some accounts only have username

**Validation Flow:**
```
When fetching user profile from TG API:
  - If first_name present → store it
  - If first_name missing → store NULL

When displaying (dashboard/logs):
  - If first_name NOT NULL → use it
  - Else if username NOT NULL → use username
  - Else → use telegram_user_id as final fallback
```

**Implementation Points:**
1. **In model:** Add helper method `get_display_name()`:
   ```python
   def get_display_name(self) -> str:
       if self.telegram_first_name:
           return self.telegram_first_name
       elif self.telegram_username:
           return self.telegram_username
       else:
           return str(self.telegram_user_id)
   ```

2. **In TG API handler:** Safely extract first_name (may be missing in response):
   ```python
   first_name = user_data.get('first_name')  # Can be None
   ```

3. **In dashboard queries:** No changes needed; use `get_display_name()` in serialization

4. **In message templates:** Use username if first_name is missing:
   ```
   name_for_greeting = telegram_first_name or telegram_username or "User"
   ```

**Does NOT harm functionality:**
- ✓ No queries depend on `first_name` being non-NULL
- ✓ All queries identify users by `telegram_user_id` (PK)
- ✓ Display logic is defensive (fallbacks in place)
- ✓ Logging uses `telegram_user_id` only
- ✓ No unique/foreign key constraints on first_name

---

## 1.4 Indexing Strategy

### `campaigns` table:
```sql
CREATE INDEX idx_campaigns_user_status ON campaigns(user_id, status);
CREATE INDEX idx_campaigns_account_status ON campaigns(telegram_account_id, status);
CREATE INDEX idx_campaigns_created_at ON campaigns(created_at DESC);
```

### `campaign_user_interactions` table:
```sql
CREATE UNIQUE INDEX idx_interaction_unique ON campaign_user_interactions(campaign_id, telegram_user_id);
CREATE INDEX idx_interaction_phase ON campaign_user_interactions(campaign_id, current_phase);
CREATE INDEX idx_interaction_tg_user ON campaign_user_interactions(telegram_user_id, campaign_id);
CREATE INDEX idx_interaction_job_open ON campaign_user_interactions(job_closed, campaign_id);
CREATE INDEX idx_interaction_created_at ON campaign_user_interactions(created_at DESC);
```

### `campaign_replies` table:
```sql
CREATE UNIQUE INDEX idx_reply_dedup ON campaign_replies(telegram_message_id);
CREATE INDEX idx_reply_interaction ON campaign_replies(interaction_id, received_at);
```

### `campaign_logs` table:
```sql
CREATE INDEX idx_logs_campaign_time ON campaign_logs(campaign_id, created_at DESC);
CREATE INDEX idx_logs_tg_user_time ON campaign_logs(telegram_user_id, created_at DESC);
CREATE INDEX idx_logs_action ON campaign_logs(action);
```

---

## 1.5 Data Validation Rules

### `campaigns` validation:
```
- message_1_delay_min <= message_1_delay_max
- message_2_delay_min <= message_2_delay_max
- If close_job_at_message = 2: message_3_* fields MUST be NULL
- If close_job_at_message = 3: message_3_* fields MUST be NOT NULL
- close_job_at_message IN (2, 3)
- status must be valid enum value
- BEFORE activation: target_group_id MUST be NOT NULL (NEW)
- All message text fields must be non-empty strings
```

### `campaign_user_interactions` validation:
```
- current_phase must match logical state:
  * If message_2_sent_at IS NOT NULL → phase must be >= 'C'
  * If message_3_sent_at IS NOT NULL → phase must be >= 'D'
- reply_count == COUNT(*) of campaign_replies for this interaction
- If job_closed = true: job_closed_at MUST be NOT NULL
- telegram_user_id is always required
- telegram_first_name CAN be NULL (optional) (NEW)
- If first_name is NULL: username or user_id will be used for display
```

---

## 1.6 Migration & Implementation Order

**When we implement (deferred to migration step):**
1. Create 4 new tables (campaigns, campaign_user_interactions, campaign_replies, campaign_logs)
2. Add columns to existing tables (users, telegram_accounts, proxies)
3. Create foreign key constraints
4. Create all indexes
5. Set default values for new columns on existing tables
6. Run validation on existing data (if any)

---

## 1.7 Summary

**Step 1 Deliverables:**
- ✓ 4 new tables with full field specs
- ✓ 3 existing tables updated with new columns
- ✓ Constraints, indexes, and relationships defined
- ✓ State machine phases clarified
- ✓ Settings hierarchy documented
- ✓ Optional fields (`target_group_id`, `telegram_first_name`) handled with detailed validation rules
- ✓ Impact analysis: NO functionality harm from optional fields
- ✓ Implementation points for handling NULLs defined

**Status:** ✓ Design Complete. Ready for Step 2.

---

## Next: Step 2 → Model Implementation

See `STEP_2_MODEL_IMPLEMENTATION.md` for:
- Pydantic/ORM model definitions
- Field validation logic
- Helper methods (e.g., `get_display_name()`, `validate_can_activate()`)
- Enum definitions (Status, Priority, Phase, Action)
- Relationship loaders
