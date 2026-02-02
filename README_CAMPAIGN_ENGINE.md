# Campaign Engine Foundation

## 🎯 Quick Reference

**Branch:** `feature/campaign-engine-foundation`
**Status:** Design Complete (Steps 1-2) | Ready for Implementation (Step 3+)
**Last Updated:** 2026-01-22, 02:50 AM IST

---

## 📋 What's Included?

This branch contains complete **design documentation** for the Campaign Engine foundation, covering:

### ✅ Documentation Files

1. **[STEP_1_SCHEMA_MODELS.md](./docs/STEP_1_SCHEMA_MODELS.md)** (Design)
   - Complete database schema for campaigns, interactions, replies, logs
   - Table definitions with 4 new tables, 3 existing tables updated
   - Constraints, indexes, relationships
   - Optional field handling (`target_group_id`, `telegram_first_name`)
   - **Status:** Complete ✅

2. **[STEP_2_MODEL_IMPLEMENTATION.md](./docs/STEP_2_MODEL_IMPLEMENTATION.md)** (Design)
   - Pydantic models for API validation
   - SQLAlchemy ORM models with helper methods
   - Enum definitions (Status, Priority, Phase, Action)
   - Validation rules and relationships
   - Settings inheritance chain
   - **Status:** Complete ✅

3. **[PHASE_ROADMAP.md](./docs/PHASE_ROADMAP.md)** (Guide)
   - Complete 7-step implementation roadmap
   - Clear scope for each step
   - Dependencies and architecture overview
   - Key decisions documented
   - **Status:** Complete ✅

---

## 🚀 Key Features Designed

### Campaigns
- ✅ Create, read, update, delete campaigns
- ✅ Campaign lifecycle (draft → active → paused/completed/failed)
- ✅ Message configuration (up to 3 messages with delays)
- ✅ Campaign stats (users contacted, messages sent, replies received, jobs closed)
- ✅ Audit logging (every action tracked)

### User Interactions
- ✅ State machine for each user (phases A → B → C → D → E → closed)
- ✅ Message tracking (when each message was sent)
- ✅ Reply tracking (count, timestamp, content)
- ✅ Job lifecycle (open → closed with reason)

### Settings & Defaults
- ✅ User-level defaults (sleep hours, max daily requests, message interval)
- ✅ Account-level overrides (per-telegram-account settings)
- ✅ Campaign-level specifics (per-campaign message delays)
- ✅ 3-tier inheritance: User → Account → Campaign

### Proxies
- ✅ **Strictly per-user** (no cross-user sharing)
- ✅ Campaign-enabled flag
- ✅ Usage tracking for daily resets

---

## 📊 Schema Overview

### New Tables

```
campaigns
  |
  +-- campaign_user_interactions (1:N)
  |     |
  |     +-- campaign_replies (1:N)
  |
  +-- campaign_logs (1:N)
```

### Core Fields

**campaigns table:**
- `id`, `user_id`, `telegram_account_id` (IDs)
- `name`, `description` (metadata)
- `target_group_id` (OPTIONAL for draft, required for activation)
- `message_1/2/3_text` (message templates)
- `close_job_at_message` (2 or 3)
- `message_1/2/3_delay_min/max` (in seconds)
- `status` (draft/active/paused/completed/failed)
- `priority` (low/medium/high)
- `max_daily_users` (optional daily cap)
- Stats: `total_users_contacted`, `total_messages_sent`, `total_replies_received`, `total_jobs_closed`

**campaign_user_interactions table:**
- `campaign_id`, `telegram_user_id` (unique pair)
- `telegram_username`, `telegram_first_name` (OPTIONAL), `telegram_last_name`
- `message_1/2/3_sent_at`, `message_1/2/3_job_id` (message tracking)
- `last_reply_at`, `reply_count` (reply tracking)
- `current_phase` (A/B/C/D/E/closed)
- `job_closed`, `job_closed_at`, `job_closed_reason`

**campaign_replies table:**
- `interaction_id` (FK)
- `telegram_message_id` (unique, for dedup)
- `message_text`, `received_at`

**campaign_logs table:**
- `campaign_id`, `telegram_user_id`
- `action` (13 action types)
- `phase`, `message_number`, `details` (JSON)
- `created_at`

---

## 🔄 State Machine: Interaction Phases

```
A (new)
  ↓ message 1 sent
B (msg1 sent, waiting)
  ↓ message 2 sent OR reply received → closed
C (msg2 sent, waiting)
  ↓ message 3 sent (if close_job_at=3) OR reply received → closed
D (msg3 sent, waiting) [only if close_job_at=3]
  ↓ all messages sent
E (all sent, awaiting final reply)
  ↓ reply received OR timeout
closed (job complete)
```

---

## 🛠 Key Implementation Decisions

### 1. Optional `target_group_id`
- **Why:** Allow campaign creation in draft without immediately selecting target
- **Validation:** Required before activation (checked in `Campaign.validate_can_activate()`)
- **Impact:** ✅ No functionality harm (just deferred requirement)

### 2. Optional `telegram_first_name`
- **Why:** Not all Telegram accounts have first_name set
- **Fallback:** `get_display_name()` uses first_name → username → user_id
- **Impact:** ✅ No functionality harm (all queries use telegram_user_id as PK)

### 3. Proxies: Strictly Per-User
- **Decision:** Each proxy belongs to exactly one user
- **Constraint:** `proxies.user_id` is NOT NULL
- **No Sharing:** Even if proxy is capable, cannot be reused across users

### 4. Settings Inheritance (3-Tier)
```
Campaign Level (highest priority)
  ↓ if not set
Account Level (telegra_accounts)
  ↓ if not set
User Level (lowest priority)
```

### 5. Message Closing Logic
- **`close_job_at_message=2`:** Close after message 2 (discard message 3)
- **`close_job_at_message=3`:** Close after message 3 (all 3 messages sent)
- **Reply triggers closure:** If user replies at any phase, job closes immediately

---

## 📖 Model Highlights

### Helper Methods

**Campaign:**
- `can_activate()` → bool
- `validate_can_activate()` → (bool, error_msg)
- `get_message_by_number(n)` → str
- `get_delay_range(n)` → (int, int)

**CampaignUserInteraction:**
- `get_display_name()` → str (with fallback)
- `get_next_message_number()` → int | None
- `can_close_job(reason)` → bool
- `get_messages_sent_count()` → int

**Service Layer (coming in Step 3):**
- `CampaignService` → CRUD, lifecycle
- `InteractionService` → State machine, phase transitions
- `MessageScheduler` → Delay calculation, job queuing
- `ReplyListener` → Handle incoming messages
- `SettingsResolver` → Inheritance chain

---

## 📋 Implementation Roadmap

### ✅ Completed (Design Phases)
1. [x] **Step 1:** Schema & Models Design
2. [x] **Step 2:** Model Implementation (Pydantic/ORM)

### 🔄 Next (Implementation Phases)
3. [ ] **Step 3:** Service Layer (CampaignService, InteractionService, etc.)
4. [ ] **Step 4:** Background Jobs & Scheduling (message sending, reply listening)
5. [ ] **Step 5:** Telegram Integration (send_dm, listen_for_replies)
6. [ ] **Step 6:** API Endpoints (REST endpoints for campaigns, interactions, settings)
7. [ ] **Step 7:** Dashboard & UI (campaign management, analytics, settings)

### Estimated Timeline
- **Step 3:** 2-3 days (service layer architecture)
- **Step 4:** 2-3 days (job scheduling, workers)
- **Step 5:** 2-3 days (Telegram integration, error handling)
- **Step 6:** 3-4 days (API endpoints, validation)
- **Step 7:** 3-5 days (UI, dashboard, forms)
- **Total:** ~2-3 weeks for full implementation

---

## 🎓 How to Use This Documentation

### For Developers Implementing Step 3+

1. **Read in order:**
   - `STEP_1_SCHEMA_MODELS.md` → Understand the data model
   - `STEP_2_MODEL_IMPLEMENTATION.md` → Understand the code models
   - `PHASE_ROADMAP.md` → Understand the full plan

2. **Implement following the steps:**
   - Create database migrations for Step 1 schema
   - Implement models from Step 2 (Pydantic + ORM)
   - Build service layer from Step 3 spec (coming)
   - Continue with remaining steps

3. **Use provided specifications:**
   - All field names, types, constraints are specified
   - All validation rules are documented
   - All relationships are mapped
   - Helper methods are listed (implement them)

### For Code Reviewers

1. **Schema Phase (Step 1):**
   - Verify migrations match the schema spec
   - Check indexes are created
   - Validate constraints are enforced

2. **Model Phase (Step 2):**
   - Verify Pydantic models match specs
   - Verify ORM models have all helper methods
   - Check validation logic is comprehensive

3. **Service Phase (Step 3+):**
   - Verify business logic matches specs
   - Check error handling for optional fields
   - Validate settings inheritance is correct

---

## 🔐 Security & Compliance Considerations

1. **Audit Logging:** Every action logged to `campaign_logs`
2. **User Isolation:** Campaigns are per-user (via `user_id` FK)
3. **Proxy Ownership:** Proxies strictly per-user, no sharing
4. **Data Privacy:** No cross-user data access by design
5. **Rate Limiting:** Designed for Telegram's rate limits (future Step 5)

---

## 🐛 Known Limitations (By Design)

1. **No Campaign Templates Yet:** Each campaign is unique (can be added later)
2. **No A/B Testing:** Single message set per campaign
3. **No Conditional Routing:** All users get same messages (can be added)
4. **No Dynamic Fields:** Message templates are static (future feature)
5. **No Scheduled Campaigns:** Must manually activate (can be automated)

---

## 📞 Questions & Next Steps

### If you want to...

- **Review the schema:** See `STEP_1_SCHEMA_MODELS.md`
- **Review the models:** See `STEP_2_MODEL_IMPLEMENTATION.md`
- **Understand the full plan:** See `PHASE_ROADMAP.md`
- **Start implementing:** Begin with Step 3 (service layer spec coming next)
- **Ask questions:** Check the existing docs for answers, then create an issue

---

## 📍 Branch Information

**Branch Name:** `feature/campaign-engine-foundation`
**Base:** Main development branch
**Purpose:** Campaign Engine Foundation (Design & Specification)
**Status:** Ready for PR review & Step 3 implementation

**To work on this branch:**
```bash
git checkout feature/campaign-engine-foundation
git pull origin feature/campaign-engine-foundation
```

---

## 📚 Document Map

```
README_CAMPAIGN_ENGINE.md (this file)
  |
  +-- docs/STEP_1_SCHEMA_MODELS.md ................... Database schema
  +-- docs/STEP_2_MODEL_IMPLEMENTATION.md ........... Python models
  +-- docs/PHASE_ROADMAP.md .......................... Full roadmap
  |
  +-- Implementation specs (TBD)
      +-- docs/STEP_3_SERVICE_LAYER.md .............. (To be created)
      +-- docs/STEP_4_BACKGROUND_JOBS.md ........... (To be created)
      +-- docs/STEP_5_TELEGRAM_INTEGRATION.md ...... (To be created)
      +-- docs/STEP_6_API_ENDPOINTS.md ............. (To be created)
      +-- docs/STEP_7_DASHBOARD.md ................. (To be created)
```

---

**Created:** 2026-01-22
**Updated:** 2026-01-22 at 02:50 AM IST
**Status:** Complete & Ready for Implementation
