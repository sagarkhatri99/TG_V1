# Campaign Engine Foundation: Phase Roadmap

**Branch:** `feature/campaign-engine-foundation`  
**Last Updated:** 2026-01-22  
**Status:** Design Phases Complete (Steps 1-2). Ready for Implementation (Step 3+)

---

## Phase Overview

This is a **phased, step-by-step approach** to building the Campaign Engine. Each step is isolated, documented, and ready for implementation.

### Core Principles
1. **Proxies:** Strictly per-user, no cross-user sharing
2. **Settings:** Hierarchical (User → Account → Campaign)
3. **Mass DM = Campaigns:** Conceptual equivalence, gradual migration
4. **State Machine:** Clear phase transitions for user interactions

---

## Step 1: Schema & Models ✅ COMPLETE

**File:** `docs/STEP_1_SCHEMA_MODELS.md`

### Deliverables
- [x] 4 new tables defined (campaigns, campaign_user_interactions, campaign_replies, campaign_logs)
- [x] 3 existing tables updated with new columns (users, telegram_accounts, proxies)
- [x] Full field specifications, constraints, indexes
- [x] State machine phases clarified (A → B → C → D → E → closed)
- [x] Settings hierarchy defined
- [x] Optional fields handled with detailed validation rules
  - `campaigns.target_group_id` (OPTIONAL for draft, REQUIRED for activation)
  - `campaign_user_interactions.telegram_first_name` (OPTIONAL, with fallback display logic)
- [x] Impact analysis: NO functionality harm from optional fields

### Key Tables
```
campaigns
  ├─ campaign_user_interactions (1:N)
  │  └─ campaign_replies (1:N)
  └─ campaign_logs (1:N)
```

---

## Step 2: Model Implementation ✅ COMPLETE

**File:** `docs/STEP_2_MODEL_IMPLEMENTATION.md`

### Deliverables
- [x] Enum definitions
  - `CampaignStatus` (draft, active, paused, completed, failed)
  - `CampaignPriority` (low, medium, high)
  - `InteractionPhase` (A, B, C, D, E, closed)
  - `CampaignLogAction` (13 action types)
- [x] Pydantic models for API validation
  - `CampaignCreateRequest`, `CampaignUpdateRequest`, `CampaignResponse`
  - `CampaignUserInteractionResponse`, `CampaignReplyResponse`, `CampaignLogResponse`
- [x] SQLAlchemy ORM models
  - `Campaign` with helper methods (`can_activate()`, `get_message_by_number()`, etc.)
  - `CampaignUserInteraction` with state machine logic (`get_next_message_number()`, `can_close_job()`, etc.)
  - `CampaignReply`, `CampaignLog`
- [x] Validation rules documented
- [x] Settings inheritance chain defined
- [x] Relationships mapped

### Helper Methods
- `Campaign.can_activate()` / `validate_can_activate()` – Check activation readiness
- `Campaign.get_message_by_number(n)` – Retrieve message text
- `Campaign.get_delay_range(n)` – Get (min, max) delay for message
- `CampaignUserInteraction.get_display_name()` – Fallback: first_name → username → user_id
- `CampaignUserInteraction.get_next_message_number()` – State machine navigation
- `CampaignUserInteraction.can_close_job()` – Job closure validation

---

## Step 3: Service Layer (NEXT) 🔄 IN PROGRESS

**File:** `docs/STEP_3_SERVICE_LAYER.md` (To be created)

### Expected Deliverables
- [ ] `CampaignService` (CRUD, lifecycle management)
  - `create_campaign(user, account, data)`
  - `update_campaign(campaign, data)`
  - `activate_campaign(campaign)` – With validation
  - `pause_campaign(campaign)`, `resume_campaign(campaign)`, `complete_campaign(campaign)`
  - `get_campaigns(user, filters)`

- [ ] `InteractionService` (State machine, user management)
  - `add_user_to_campaign(campaign, telegram_user_data)`
  - `transition_phase(interaction, new_phase)` – With validation
  - `close_job(interaction, reason)`
  - `get_open_jobs(campaign)`

- [ ] `MessageScheduler` (Delay calculation, job queuing)
  - `schedule_next_message(interaction)` – Calculate delay, queue job
  - `get_effective_delay_range(campaign, account, user)` – Settings inheritance
  - `calculate_random_delay(min, max)` – Human behavior simulation

- [ ] `ReplyListener` (Message handling)
  - `handle_incoming_message(telegram_user_id, message_text)` – Match to interaction
  - `update_interaction_on_reply(interaction)`
  - `log_reply(interaction, message_data)`
  - `check_job_closure_trigger(interaction)` – Reply received = close job?

- [ ] `SettingsResolver` (Inheritance chain)
  - `get_effective_sleep_hours(user, account, campaign)` → Returns int
  - `get_effective_max_daily_users(campaign, account, user)` → Returns int
  - `get_effective_message_delays(campaign, account, user)` → Returns (min, max)

- [ ] `LogService` (Audit trail)
  - `log_action(campaign, action, telegram_user_id, details)`

### Service Layer Architecture
```
CampaignService
├─ uses InteractionService
├─ uses MessageScheduler
├─ uses LogService
└─ uses SettingsResolver

ReplyListener
├─ uses InteractionService
├─ uses LogService
└─ triggers job closure
```

---

## Step 4: Background Jobs & Scheduling 🔄 NOT STARTED

**File:** `docs/STEP_4_BACKGROUND_JOBS.md` (To be created)

### Expected Scope
- [ ] Job queue setup (Celery/RQ/APScheduler)
- [ ] Message sending job (`send_message_job`)
  - Fetch interaction
  - Get effective settings
  - Schedule next message with delay
  - Update interaction state
  - Log action

- [ ] Reply listener worker
  - Poll for new messages in target group
  - Match to campaigns
  - Call `ReplyListener.handle_incoming_message()`

- [ ] Cleanup jobs
  - Close stale jobs (timeout after X days)
  - Mark campaigns as completed when all users done
  - Archive logs

---

## Step 5: Telegram Integration 🔄 NOT STARTED

**File:** `docs/STEP_5_TELEGRAM_INTEGRATION.md` (To be created)

### Expected Scope
- [ ] TelegramClient wrapper for campaigns
  - `send_dm(user_id, message, account, proxy)` – With proxy selection
  - `listen_for_replies(group_id, account, proxy)` – With proxy rotation
  - `validate_group_access(group_id, account, proxy)` – Check before campaign activation

- [ ] Error handling
  - Rate limiting (429 Telegram error)
  - Account blocked
  - User privacy settings
  - Proxy failures

- [ ] Retry logic
  - Exponential backoff for messages
  - Proxy rotation on failure

---

## Step 6: API Endpoints 🔄 NOT STARTED

**File:** `docs/STEP_6_API_ENDPOINTS.md` (To be created)

### Expected Scope
- [ ] Campaign Management Endpoints
  - `POST /campaigns` – Create campaign
  - `GET /campaigns` – List campaigns
  - `GET /campaigns/{id}` – Get campaign
  - `PATCH /campaigns/{id}` – Update (draft only)
  - `POST /campaigns/{id}/activate` – Activate campaign
  - `POST /campaigns/{id}/pause` – Pause campaign
  - `POST /campaigns/{id}/resume` – Resume campaign
  - `POST /campaigns/{id}/complete` – Mark completed

- [ ] Interaction Endpoints
  - `GET /campaigns/{id}/interactions` – List user interactions
  - `GET /campaigns/{id}/interactions/{user_id}` – Get specific interaction
  - `GET /campaigns/{id}/interactions/{user_id}/replies` – Get replies from user
  - `POST /campaigns/{id}/interactions/{user_id}/close` – Close job manually

- [ ] Analytics Endpoints
  - `GET /campaigns/{id}/stats` – Aggregated stats
  - `GET /campaigns/{id}/logs` – Audit trail with filtering

- [ ] Settings Endpoints
  - `GET /user/campaign-settings` – Get user defaults
  - `PATCH /user/campaign-settings` – Update user defaults
  - `GET /accounts/{id}/campaign-settings` – Get account defaults
  - `PATCH /accounts/{id}/campaign-settings` – Update account defaults

---

## Step 7: Dashboard & UI 🔄 NOT STARTED

**File:** `docs/STEP_7_DASHBOARD.md` (To be created)

### Expected Scope
- [ ] Campaign List View
  - Filter by status, priority, date
  - Quick actions (activate, pause, view details)
  - Bulk operations (pause all, etc.)

- [ ] Campaign Detail View
  - Configuration review
  - Message templates
  - Target group info
  - Real-time stats (users contacted, messages sent, replies received, jobs closed)

- [ ] User Interactions View
  - Per-campaign user list
  - Current phase, message status
  - Reply timeline
  - Filter/search by username, status

- [ ] Settings UI
  - User-level campaign defaults
  - Account-level overrides
  - Campaign-level custom settings
  - Preview of effective settings after inheritance

- [ ] Analytics Dashboard
  - Campaign performance trends
  - Reply rate statistics
  - Job closure reasons breakdown
  - Logs viewer with filtering

---

## Implementation Checklist

### Design Phases ✅
- [x] Step 1: Schema & Models
- [x] Step 2: Model Implementation

### Implementation Phases (To Begin)
- [ ] Step 3: Service Layer
- [ ] Step 4: Background Jobs & Scheduling
- [ ] Step 5: Telegram Integration
- [ ] Step 6: API Endpoints
- [ ] Step 7: Dashboard & UI

### Integration & Testing
- [ ] Unit tests for service layer
- [ ] Integration tests for background jobs
- [ ] E2E tests for full campaign workflow
- [ ] Load testing for message scheduling
- [ ] Proxy failure resilience tests

---

## Key Decisions & Constraints

### Proxy Model
- **Strict per-user:** Each proxy belongs to exactly one user
- **No sharing:** Even if proxy is capable, cannot be shared across users
- **Location:** Config in `users.campaign_default_*` and `telegram_accounts.campaign_default_*`

### Settings Hierarchy
- **3-tier override:** User defaults → Account overrides → Campaign specifics
- **Inheritance:** Services use `SettingsResolver` to compute effective values
- **Database:** No computed columns; inheritance done in application code

### Optional Fields
- `campaigns.target_group_id`: Optional for draft, required for activation
- `campaign_user_interactions.telegram_first_name`: Optional, with fallback logic
- **No impact:** Validation enforces requirements at appropriate points

### State Machine
- **Phases:** A → B → C → D/E → closed
- **Transitions:** Driven by message sending and reply reception
- **Closure triggers:** Reply received OR timeout (handled in job scheduler)

---

## Progress Tracking

**Last Update:** 2026-01-22, 02:45 AM IST

### Current Status
✅ **Steps 1-2: Design Complete**

### Next Milestone
🔄 **Step 3: Service Layer Implementation** (Ready to start)

---

## Notes for Implementation Team

1. **Gradual Migration:** Don't rush to convert all Mass DM features. Campaigns are the new model; migrate existing features incrementally.

2. **Testing First:** For Step 3+ (service layer), start with comprehensive unit tests. Models are well-defined; services should be tested thoroughly.

3. **Proxy Rotation:** In Step 5, implement intelligent proxy rotation for `send_dm()` calls to balance load.

4. **Rate Limiting:** TG has strict rate limits (around 1-2 DMs per second per account). Job scheduler must respect this. Consider account-level queuing.

5. **Settings Defaults:** When creating user/account, initialize campaign defaults from constants (see STEP_2 model defaults).

6. **Logging:** Every action logged to `campaign_logs`. This is crucial for debugging and compliance.

---

## Document References

- [Step 1: Schema & Models](./STEP_1_SCHEMA_MODELS.md)
- [Step 2: Model Implementation](./STEP_2_MODEL_IMPLEMENTATION.md)
- Step 3: Service Layer (To be created)
- Step 4: Background Jobs (To be created)
- Step 5: Telegram Integration (To be created)
- Step 6: API Endpoints (To be created)
- Step 7: Dashboard & UI (To be created)
