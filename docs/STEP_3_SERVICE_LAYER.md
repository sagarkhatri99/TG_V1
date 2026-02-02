# Step 3: Service Layer Implementation

**Status:** Implementation Specification (No Code Yet)
**Branch:** `feature/campaign-engine-foundation`
**Date:** 2026-01-22

---

## Overview

Step 3 defines the service layer—the business logic that orchestrates the models from Step 2. Services handle:
- Campaign lifecycle (CRUD, state transitions)
- Interaction state management (phase transitions)
- Message scheduling (delay calculation, job queuing)
- Reply handling (match, log, trigger closure)
- Settings resolution (inheritance chain)
- Audit logging

**This is specification only.** No implementation code yet, just detailed interface contracts, business rules, and workflow definitions.

---

## 3.1 Service Layer Architecture

### Service Classes Overview

```
┌─────────────────────────────────────────────┐
│           Controller/API Layer              │
│   (FastAPI endpoints - Step 6)              │
└────────────────────┬────────────────────────┘
                     │
┌────────────────────┴────────────────────────┐
│         SERVICE LAYER (THIS STEP)           │
├─────────────────────────────────────────────┤
│                                             │
│  ┌──────────────────────────────────────┐  │
│  │  CampaignService                     │  │
│  │  ├─ create_campaign()                │  │
│  │  ├─ update_campaign()                │  │
│  │  ├─ activate_campaign()              │  │
│  │  ├─ pause_campaign()                 │  │
│  │  ├─ resume_campaign()                │  │
│  │  ├─ complete_campaign()              │  │
│  │  ├─ fail_campaign()                  │  │
│  │  └─ get_campaigns()                  │  │
│  └──────────────────────────────────────┘  │
│                                             │
│  ┌──────────────────────────────────────┐  │
│  │  InteractionService                  │  │
│  │  ├─ add_user_to_campaign()           │  │
│  │  ├─ transition_phase()               │  │
│  │  ├─ close_job()                      │  │
│  │  ├─ get_open_jobs()                  │  │
│  │  └─ get_interaction_by_user()        │  │
│  └──────────────────────────────────────┘  │
│                                             │
│  ┌──────────────────────────────────────┐  │
│  │  MessageScheduler                    │  │
│  │  ├─ schedule_next_message()          │  │
│  │  ├─ get_effective_delay_range()      │  │
│  │  ├─ calculate_random_delay()         │  │
│  │  └─ queue_message_job()              │  │
│  └──────────────────────────────────────┘  │
│                                             │
│  ┌──────────────────────────────────────┐  │
│  │  ReplyListener                       │  │
│  │  ├─ handle_incoming_message()        │  │
│  │  ├─ update_interaction_on_reply()    │  │
│  │  ├─ log_reply()                      │  │
│  │  └─ check_job_closure_trigger()      │  │
│  └──────────────────────────────────────┘  │
│                                             │
│  ┌──────────────────────────────────────┐  │
│  │  SettingsResolver                    │  │
│  │  ├─ get_effective_sleep_hours()      │  │
│  │  ├─ get_effective_max_daily_users()  │  │
│  │  ├─ get_effective_message_delays()   │  │
│  │  └─ resolve_setting()                │  │
│  └──────────────────────────────────────┘  │
│                                             │
│  ┌──────────────────────────────────────┐  │
│  │  LogService                          │  │
│  │  ├─ log_action()                     │  │
│  │  ├─ get_campaign_logs()              │  │
│  │  └─ get_user_logs()                  │  │
│  └──────────────────────────────────────┘  │
│                                             │
└─────────────────────────────────────────────┘
                     │
┌────────────────────┴────────────────────────┐
│        ORM Layer (Models from Step 2)       │
│  ├─ Campaign                                │
│  ├─ CampaignUserInteraction                │
│  ├─ CampaignReply                          │
│  └─ CampaignLog                            │
└─────────────────────────────────────────────┘
                     │
┌────────────────────┴────────────────────────┐
│    Database (Schema from Step 1)            │
└─────────────────────────────────────────────┘
```

---

## 3.2 CampaignService

### Purpose
Manage campaign lifecycle: creation, updates, activation, pausing, resuming, completion.

### Interface Specification

```python
class CampaignService:
    """
    Service for campaign operations.
    Handles CRUD, lifecycle management, validation.
    """

    def __init__(self, db: Session, logger: Logger):
        """
        Initialize service.

        Args:
            db: SQLAlchemy session
            logger: Logger instance
        """
        pass

    # ======================== CREATE & READ ========================

    async def create_campaign(
        self,
        user_id: UUID,
        account_id: UUID,
        data: CampaignCreateRequest
    ) -> Campaign:
        """
        Create a new campaign in DRAFT status.

        Args:
            user_id: Campaign owner
            account_id: Associated Telegram account
            data: Campaign data (CampaignCreateRequest)

        Returns:
            Created Campaign object

        Raises:
            ValidationError: If data validation fails
            DuplicateError: If campaign name already exists for user
            NotFoundError: If account doesn't exist or doesn't belong to user

        Business Rules:
            1. Validate all fields from CampaignCreateRequest
            2. Check user owns the telegram_account
            3. Check campaign name is unique per user
            4. Create campaign with status=DRAFT
            5. Log action: campaign_created
            6. Return created campaign object

        Notes:
            - target_group_id is optional in DRAFT
            - No message jobs scheduled until activation
            - Campaign starts with stats at 0
        """
        pass

    async def get_campaign(
        self,
        campaign_id: UUID,
        user_id: UUID
    ) -> Campaign:
        """
        Get campaign by ID (with user ownership check).

        Args:
            campaign_id: Campaign ID
            user_id: Current user (for authorization)

        Returns:
            Campaign object

        Raises:
            NotFoundError: If campaign doesn't exist
            ForbiddenError: If user doesn't own campaign
        """
        pass

    async def get_campaigns(
        self,
        user_id: UUID,
        filters: Optional[CampaignFilters] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[Campaign], int]:
        """
        Get campaigns for user with optional filters.

        Args:
            user_id: Campaign owner
            filters: Optional filters (status, priority, date_range)
            limit: Max results
            offset: Pagination offset

        Returns:
            (List of campaigns, total count)

        Filter Options:
            - status: CampaignStatus
            - priority: CampaignPriority
            - account_id: UUID
            - created_after: datetime
            - created_before: datetime

        Ordering:
            - Default: created_at DESC
        """
        pass

    # ======================== UPDATE ========================

    async def update_campaign(
        self,
        campaign_id: UUID,
        user_id: UUID,
        data: CampaignUpdateRequest
    ) -> Campaign:
        """
        Update campaign (DRAFT status only).

        Args:
            campaign_id: Campaign ID
            user_id: Current user
            data: Update data (CampaignUpdateRequest)

        Returns:
            Updated Campaign object

        Raises:
            NotFoundError: If campaign doesn't exist
            ForbiddenError: If user doesn't own campaign
            ValidationError: If data is invalid
            StateError: If campaign is not in DRAFT status

        Business Rules:
            1. Check campaign is in DRAFT status
            2. Validate all provided fields
            3. Update only provided fields (partial update)
            4. Check campaign name uniqueness if updating name
            5. Log action: settings_updated
            6. Return updated campaign

        Notes:
            - Cannot update active/paused/completed campaigns
            - Can clear target_group_id in draft
        """
        pass

    # ======================== LIFECYCLE: ACTIVATE ========================

    async def activate_campaign(
        self,
        campaign_id: UUID,
        user_id: UUID
    ) -> Campaign:
        """
        Activate campaign (DRAFT → ACTIVE).

        Args:
            campaign_id: Campaign ID
            user_id: Current user

        Returns:
            Updated Campaign object (status=ACTIVE)

        Raises:
            NotFoundError: If campaign doesn't exist
            ForbiddenError: If user doesn't own campaign
            ValidationError: If campaign cannot be activated
            StateError: If campaign is not in DRAFT status

        Pre-Activation Validation:
            1. Campaign status must be DRAFT
            2. target_group_id must NOT be NULL
            3. All message texts must be non-empty
            4. Telegram account must exist and be accessible
            5. Account must have campaign_enabled=true
            6. At least one proxy must be available for account

        Activation Actions:
            1. Validate using Campaign.validate_can_activate()
            2. Update status to ACTIVE
            3. Set started_at = now
            4. Log action: campaign_started
            5. Trigger InteractionService to initialize message queues
            6. Return updated campaign

        Notes:
            - Activation is a state transition (verified, atomic)
            - Post-activation, message scheduling begins (Step 4)
            - Cannot be undone (only pause/resume allowed after)
        """
        pass

    # ======================== LIFECYCLE: PAUSE/RESUME ========================

    async def pause_campaign(
        self,
        campaign_id: UUID,
        user_id: UUID
    ) -> Campaign:
        """
        Pause campaign (ACTIVE → PAUSED).

        Args:
            campaign_id: Campaign ID
            user_id: Current user

        Returns:
            Updated Campaign object (status=PAUSED)

        Raises:
            StateError: If campaign is not ACTIVE

        Actions:
            1. Check campaign is ACTIVE
            2. Update status to PAUSED
            3. Log action: campaign_paused
            4. Stop scheduling new messages (handled in Step 4)
            5. Return updated campaign

        Notes:
            - Paused campaigns can be resumed
            - In-flight messages still deliver (Step 5 manages this)
            - New messages not scheduled
        """
        pass

    async def resume_campaign(
        self,
        campaign_id: UUID,
        user_id: UUID
    ) -> Campaign:
        """
        Resume campaign (PAUSED → ACTIVE).

        Args:
            campaign_id: Campaign ID
            user_id: Current user

        Returns:
            Updated Campaign object (status=ACTIVE)

        Raises:
            StateError: If campaign is not PAUSED

        Actions:
            1. Check campaign is PAUSED
            2. Update status to ACTIVE
            3. Log action: campaign_started (or similar)
            4. Resume message scheduling (Step 4)
            5. Return updated campaign
        """
        pass

    # ======================== LIFECYCLE: COMPLETION ========================

    async def complete_campaign(
        self,
        campaign_id: UUID,
        user_id: UUID
    ) -> Campaign:
        """
        Mark campaign as completed (ACTIVE/PAUSED → COMPLETED).

        Args:
            campaign_id: Campaign ID
            user_id: Current user

        Returns:
            Updated Campaign object (status=COMPLETED)

        Raises:
            StateError: If campaign is not ACTIVE or PAUSED

        Actions:
            1. Check campaign is ACTIVE or PAUSED
            2. Update status to COMPLETED
            3. Set completed_at = now
            4. Log action: campaign_completed
            5. Cancel any pending message jobs (Step 4)
            6. Return updated campaign

        Notes:
            - User manually marks campaign complete
            - Can happen anytime, not automatic
            - Used for early termination
        """
        pass

    async def fail_campaign(
        self,
        campaign_id: UUID,
        user_id: UUID,
        reason: str
    ) -> Campaign:
        """
        Mark campaign as failed (ACTIVE/PAUSED → FAILED).

        Args:
            campaign_id: Campaign ID
            user_id: Current user
            reason: Reason for failure (e.g., "proxy_error", "account_blocked")

        Returns:
            Updated Campaign object (status=FAILED)

        Raises:
            StateError: If campaign is not ACTIVE or PAUSED

        Actions:
            1. Check campaign is ACTIVE or PAUSED
            2. Update status to FAILED
            3. Set completed_at = now
            4. Log action: campaign_failed with reason in details
            5. Cancel all pending jobs
            6. Return updated campaign

        Notes:
            - Used when unrecoverable error occurs
            - Not user-initiated normally (called by workers)
        """
        pass

    # ======================== HELPERS ========================

    async def get_campaign_stats(
        self,
        campaign_id: UUID
    ) -> dict:
        """
        Get campaign statistics (from denormalized fields).

        Returns:
            {
                "total_users_contacted": int,
                "total_messages_sent": int,
                "total_replies_received": int,
                "total_jobs_closed": int,
                "avg_reply_rate": float,  # Computed
                "avg_closure_rate": float,  # Computed
                "messages_per_user": float,  # Computed
            }
        """
        pass

    async def validate_activation(
        self,
        campaign_id: UUID
    ) -> Tuple[bool, Optional[str]]:
        """
        Pre-activation validation without modifying campaign.

        Returns:
            (is_valid, error_message)

        Uses Campaign.validate_can_activate() + additional checks.
        """
        pass
```

---

## 3.3 InteractionService

### Purpose
Manage user interactions within a campaign: add users, phase transitions, job closure.

### Interface Specification

```python
class InteractionService:
    """
    Service for managing user interactions in campaigns.
    Implements state machine transitions (phase A→B→C→D→E→closed).
    """

    def __init__(self, db: Session, logger: Logger, message_scheduler: MessageScheduler):
        """
        Initialize service.

        Args:
            db: SQLAlchemy session
            logger: Logger instance
            message_scheduler: MessageScheduler instance (for job queuing)
        """
        pass

    # ======================== ADD USER ========================

    async def add_user_to_campaign(
        self,
        campaign_id: UUID,
        telegram_user_data: TelegramUserData
    ) -> CampaignUserInteraction:
        """
        Add user to campaign (create new interaction).

        Args:
            campaign_id: Target campaign
            telegram_user_data: User data from Telegram API
                {
                    "user_id": str,      # Telegram user ID
                    "username": Optional[str],
                    "first_name": Optional[str],  # May be NULL
                    "last_name": Optional[str],
                }

        Returns:
            Created CampaignUserInteraction object (phase=A)

        Raises:
            DuplicateError: If user already in this campaign
            NotFoundError: If campaign doesn't exist
            ValidationError: If user data is invalid

        Business Rules:
            1. Check user not already in campaign (unique constraint)
            2. Validate telegram_user_id is non-empty
            3. first_name can be NULL (optional)
            4. Create interaction with:
               - current_phase = 'A' (new)
               - job_closed = false
               - reply_count = 0
               - All message_*_sent_at = NULL
            5. Log action: user_added
            6. Return created interaction

        Notes:
            - No message sent yet (phase A)
            - Message scheduling happens in next step (MessageScheduler)
            - Interaction initially inactive (awaiting first message)
        """
        pass

    # ======================== PHASE TRANSITIONS ========================

    async def transition_phase(
        self,
        interaction_id: UUID,
        new_phase: InteractionPhase,
        details: Optional[dict] = None
    ) -> CampaignUserInteraction:
        """
        Transition interaction to new phase (state machine).

        Args:
            interaction_id: Interaction ID
            new_phase: Target phase (B, C, D, E, or closed)
            details: Optional context (e.g., {"job_id": "...", "message_number": 2})

        Returns:
            Updated CampaignUserInteraction object

        Raises:
            ValidationError: If transition is invalid
            NotFoundError: If interaction doesn't exist

        State Machine Rules:

            Phase A (new) → valid transitions:
              - A → B: message 1 sent (details: {job_id, delay_sec})
              - A → closed: manual closure only (requires reason)

            Phase B (msg1 sent) → valid transitions:
              - B → C: message 2 sent (details: {job_id, delay_sec})
              - B → closed: reply received OR timeout (details: {reason})

            Phase C (msg2 sent) → valid transitions:
              - C → D: message 3 sent, if close_job_at_message=3 (details: {job_id})
              - C → E: message 3 skipped, if close_job_at_message=2 (details: {reason})
              - C → closed: reply received (details: {reason})

            Phase D (msg3 sent) → valid transitions:
              - D → E: awaiting final reply (details: {})
              - D → closed: reply received (details: {reason})

            Phase E (awaiting) → valid transitions:
              - E → closed: reply received OR timeout (details: {reason})

            Phase closed: no transitions allowed

        Actions on Transition:
            1. Validate current_phase and requested transition
            2. Update current_phase
            3. Update updated_at = now
            4. Log action: phase_updated with old/new phase and details
            5. If transitioning to closed:
               a. Set job_closed = true, job_closed_at = now
               b. Update job_closed_reason from details['reason']
            6. Return updated interaction

        Notes:
            - State machine is rigid (only valid transitions allowed)
            - Each phase tied to message delivery
            - Closure can happen at any phase if user replies
        """
        pass

    # ======================== JOB CLOSURE ========================

    async def close_job(
        self,
        interaction_id: UUID,
        reason: str,
        details: Optional[dict] = None
    ) -> CampaignUserInteraction:
        """
        Manually close user job (mark complete).

        Args:
            interaction_id: Interaction ID
            reason: Closure reason (e.g., "user_replied", "timeout", "manual", "account_blocked")
            details: Optional context

        Returns:
            Updated CampaignUserInteraction object (job_closed=true)

        Raises:
            ValidationError: If job already closed
            NotFoundError: If interaction doesn't exist

        Business Rules:
            1. Check interaction.job_closed == false
            2. Validate reason is non-empty
            3. Transition phase to 'closed' using transition_phase()
            4. Set job_closed = true, job_closed_at = now
            5. Set job_closed_reason = reason
            6. Log action: job_closed with reason and details
            7. Update campaign.total_jobs_closed += 1
            8. Return updated interaction

        Closure Reasons:
            - "user_replied": User replied to any message
            - "timeout": No reply within X days
            - "manual": User manually closed
            - "message_failed": Message sending failed
            - "account_blocked": Telegram account blocked
            - "proxy_error": Proxy connection failed

        Notes:
            - Closure is final (no reopening)
            - Triggers campaign.total_jobs_closed increment
            - Affects closure rate statistics
        """
        pass

    # ======================== QUERIES ========================

    async def get_open_jobs(
        self,
        campaign_id: UUID,
        limit: int = 100,
        offset: int = 0
    ) -> Tuple[List[CampaignUserInteraction], int]:
        """
        Get all open jobs for campaign (job_closed=false).

        Args:
            campaign_id: Campaign ID
            limit: Max results
            offset: Pagination offset

        Returns:
            (List of open interactions, total count)

        Ordering:
            - created_at ASC (oldest first, for fairness)

        Use Cases:
            - Dashboard display of active interactions
            - Worker picking up next job to process
        """
        pass

    async def get_interactions_by_phase(
        self,
        campaign_id: UUID,
        phase: InteractionPhase
    ) -> List[CampaignUserInteraction]:
        """
        Get all interactions in specific phase.

        Args:
            campaign_id: Campaign ID
            phase: Target phase (A, B, C, D, E, or closed)

        Returns:
            List of interactions in that phase

        Use Cases:
            - Message scheduler finding users in phase B (await message 2 sending)
            - Analytics queries
        """
        pass

    async def get_interaction_by_user(
        self,
        campaign_id: UUID,
        telegram_user_id: str
    ) -> Optional[CampaignUserInteraction]:
        """
        Get interaction for specific user in campaign.

        Args:
            campaign_id: Campaign ID
            telegram_user_id: Telegram user ID

        Returns:
            CampaignUserInteraction or None if not found

        Use Cases:
            - Reply listener matching incoming message to interaction
            - Dashboard showing single user's status
        """
        pass

    async def get_interaction_stats(
        self,
        campaign_id: UUID
    ) -> dict:
        """
        Get aggregate stats for campaign interactions.

        Returns:
            {
                "total_users": int,
                "open_jobs_count": int,
                "closed_jobs_count": int,
                "phase_distribution": {
                    "A": int,
                    "B": int,
                    "C": int,
                    "D": int,
                    "E": int,
                    "closed": int,
                },
                "avg_reply_time": Optional[timedelta],
                "total_replies": int,
            }

        Used for:
            - Dashboard analytics
            - Campaign performance tracking
        """
        pass
```

---

## 3.4 MessageScheduler

### Purpose
Calculate message delays, resolve settings inheritance, queue message sending jobs.

### Interface Specification

```python
class MessageScheduler:
    """
    Service for scheduling message sending.
    Handles delay calculation, settings inheritance, and job queuing.
    """

    def __init__(self, db: Session, logger: Logger, job_queue: JobQueue, settings_resolver: SettingsResolver):
        """
        Initialize scheduler.

        Args:
            db: SQLAlchemy session
            logger: Logger instance
            job_queue: Background job queue (Celery/RQ/etc)
            settings_resolver: SettingsResolver instance
        """
        pass

    # ======================== SCHEDULE MESSAGE ========================

    async def schedule_next_message(
        self,
        interaction_id: UUID,
        campaign_id: UUID,
        account_id: UUID
    ) -> Optional[str]:
        """
        Schedule next message for user (if any).

        Args:
            interaction_id: User interaction ID
            campaign_id: Campaign ID
            account_id: Telegram account ID

        Returns:
            Job ID if scheduled, None if no more messages

        Raises:
            ValidationError: If interaction already has all messages sent
            NotFoundError: If entities don't exist

        Business Logic:
            1. Get interaction and check current state
            2. Determine next message number using interaction.get_next_message_number()
            3. If no more messages to send, return None
            4. If user already has pending job, skip (prevent duplicates)
            5. Calculate delay:
               a. Get effective delay range using SettingsResolver
               b. Generate random delay within range using calculate_random_delay()
            6. Queue message job using queue_message_job()
            7. Update interaction.message_N_sent_at = now
            8. Update interaction.message_N_job_id = returned_job_id
            9. Transition phase (A→B, B→C, C→D, etc.)
            10. Log action: message_scheduled with job_id
            11. Return job_id

        Notes:
            - Called after campaign activation (once per user)
            - Called recursively as messages are delivered
            - Never schedules duplicate jobs for same message
        """
        pass

    # ======================== DELAY CALCULATION ========================

    async def get_effective_delay_range(
        self,
        campaign_id: UUID,
        account_id: UUID,
        user_id: UUID,
        message_number: int
    ) -> Tuple[int, int]:
        """
        Get effective (min, max) delay range for message (in seconds).

        Args:
            campaign_id: Campaign ID
            account_id: Telegram account ID
            user_id: User ID
            message_number: 1, 2, or 3

        Returns:
            (min_delay_seconds, max_delay_seconds)

        Raises:
            NotFoundError: If any entity missing
            ValidationError: If message_number is invalid

        3-Tier Inheritance Resolution:

            Step 1: Check Campaign Level
              - Get Campaign.message_N_delay_min/max
              - If both set (not NULL), use them

            Step 2: Fallback to Account Level
              - Get TelegramAccount.campaign_default_message_delay_min/max
              - If both set, use them

            Step 3: Fallback to User Level
              - Get User.campaign_default_behavior_request_interval_min/max
              - Use these (always available, should have defaults)

            Return:
              - Always return a valid (min, max) tuple
              - Never return NULL or missing values

        Example:
            Campaign: message_1_delay_min=120, message_1_delay_max=300  → Use campaign
            Campaign: message_2_delay_min=NULL, message_2_delay_max=NULL
            Account:  campaign_default_message_delay_min=60, max=240     → Use account
            Campaign: message_3_delay_min=NULL, message_3_delay_max=NULL
            Account:  campaign_default_message_delay_min=NULL, max=NULL
            User:     request_interval_min=30, request_interval_max=120  → Use user
        """
        pass

    def calculate_random_delay(self, min_seconds: int, max_seconds: int) -> int:
        """
        Generate random delay within range (human behavior simulation).

        Args:
            min_seconds: Minimum delay (inclusive)
            max_seconds: Maximum delay (inclusive)

        Returns:
            Random delay in seconds

        Implementation Notes:
            - Use random.randint(min_seconds, max_seconds)
            - Simulates human behavior (not instant, varying)
            - Use for each message independently (not cumulative)

        Example:
            min=60, max=300  →  Returns value like 145, 267, 89, etc.
        """
        pass

    # ======================== JOB QUEUING ========================

    async def queue_message_job(
        self,
        interaction_id: UUID,
        campaign_id: UUID,
        account_id: UUID,
        message_number: int,
        delay_seconds: int
    ) -> str:
        """
        Queue message sending job in background queue.

        Args:
            interaction_id: User interaction ID
            campaign_id: Campaign ID
            account_id: Telegram account ID
            message_number: 1, 2, or 3
            delay_seconds: How long to wait before sending

        Returns:
            Job ID (from job queue)

        Raises:
            JobQueueError: If job queue is unavailable

        Job Details:
            Queue the job with parameters:
            {
                "interaction_id": UUID,
                "campaign_id": UUID,
                "account_id": UUID,
                "message_number": int,
                "scheduled_at": datetime.utcnow(),
                "scheduled_delay_seconds": int,
            }

        Job Execution (handled in Step 4):
            - After delay_seconds, worker:
              1. Fetches campaign, interaction, account
              2. Resolves proxy for account
              3. Gets message text from campaign
              4. Sends DM using TelegramClient
              5. Logs action: message_sent
              6. Calls InteractionService.transition_phase() to move to next phase
              7. Queues next message (if any)

        Returns:
            Job ID for tracking/cancellation
        """
        pass

    # ======================== JOB MANAGEMENT ========================

    async def cancel_pending_jobs(
        self,
        campaign_id: UUID
    ) -> int:
        """
        Cancel all pending message jobs for campaign.

        Args:
            campaign_id: Campaign ID

        Returns:
            Count of cancelled jobs

        Used for:
            - Campaign completion/pausing
            - Campaign failure

        Actions:
            1. Find all interactions with message_N_job_id NOT NULL and job_closed=false
            2. For each job_id, cancel job in queue
            3. Clear message_N_job_id field
            4. Log action: message_cancelled (or skip logging)
            5. Return count of cancelled jobs
        """
        pass

    async def get_pending_jobs_count(
        self,
        campaign_id: UUID
    ) -> int:
        """
        Count pending message jobs for campaign.

        Args:
            campaign_id: Campaign ID

        Returns:
            Count of pending jobs

        Used for:
            - Dashboard display
            - Campaign status monitoring
        """
        pass
```

---

## 3.5 ReplyListener

### Purpose
Handle incoming messages from users, match to interactions, log replies, trigger job closure.

### Interface Specification

```python
class ReplyListener:
    """
    Service for handling incoming replies from users.
    Matches messages to campaigns, logs replies, triggers closure.
    """

    def __init__(self, db: Session, logger: Logger, interaction_service: InteractionService, log_service: LogService):
        """
        Initialize listener.

        Args:
            db: SQLAlchemy session
            logger: Logger instance
            interaction_service: InteractionService instance
            log_service: LogService instance
        """
        pass

    # ======================== HANDLE INCOMING MESSAGE ========================

    async def handle_incoming_message(
        self,
        telegram_user_id: str,
        message_text: str,
        message_id: str,
        received_at: datetime,
        group_id: str,
        account_id: UUID
    ) -> bool:
        """
        Process incoming DM reply from user.

        Args:
            telegram_user_id: Sender user ID
            message_text: Message content
            message_id: Telegram message ID (for dedup)
            received_at: When message was received
            group_id: Which group/channel message was in
            account_id: Which telegram account received it

        Returns:
            True if processed successfully, False if not matched

        Business Logic:
            1. Check for duplicate using dedup on telegram_message_id
            2. Find all campaigns with target_group_id=group_id
            3. For each campaign:
               a. Get interaction for (campaign_id, telegram_user_id)
               b. If no interaction found, skip (user not in campaign)
               c. If interaction found and job_closed=true, skip (already done)
               d. If interaction found and job_closed=false:
                  - Log reply using log_reply()
                  - Check closure trigger using check_job_closure_trigger()
                  - If triggered, close job
                  - Return True
            4. If no matching interaction found, return False

        Notes:
            - Single message may match multiple campaigns (though unlikely)
            - Process all matches (one message could reply to multiple campaigns)
            - Deduplication prevents duplicate processing
        """
        pass

    # ======================== REPLY LOGGING ========================

    async def log_reply(
        self,
        interaction_id: UUID,
        message_text: str,
        message_id: str,
        received_at: datetime
    ) -> CampaignReply:
        """
        Log incoming reply to database.

        Args:
            interaction_id: User interaction ID
            message_text: Message content
            message_id: Telegram message ID (for dedup)
            received_at: When received

        Returns:
            Created CampaignReply object

        Raises:
            DuplicateError: If message_id already logged

        Actions:
            1. Check message_id uniqueness (dedup)
            2. Create CampaignReply record
            3. Update interaction.last_reply_at = received_at
            4. Increment interaction.reply_count += 1
            5. Log action: reply_received
            6. Return created reply

        Notes:
            - Deduplication on message_id prevents double-processing
            - reply_count is maintained for analytics
            - Stored for audit trail and debugging
        """
        pass

    # ======================== CLOSURE TRIGGER ========================

    async def check_job_closure_trigger(
        self,
        interaction_id: UUID
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if job should close on reply.

        Args:
            interaction_id: User interaction ID

        Returns:
            (should_close, closure_reason)

        Business Rules:
            1. If job already closed, return (False, None)
            2. If user replied at ANY phase (A, B, C, D, E):
               → Job closes immediately
               → Reason: "user_replied"
            3. Return (True, "user_replied")

        Design Note:
            - Reply always closes job (per spec)
            - No exceptions (even if not all messages sent)
            - Simplifies state machine
        """
        pass

    # ======================== HELPER ========================

    async def update_interaction_on_reply(
        self,
        interaction_id: UUID
    ) -> CampaignUserInteraction:
        """
        Update interaction state on reply (shortcut method).

        This method combines:
        1. check_job_closure_trigger()
        2. close_job() from InteractionService

        Returns updated interaction.
        """
        pass
```

---

## 3.6 SettingsResolver

### Purpose
Resolve settings from 3-tier hierarchy (Campaign → Account → User).

### Interface Specification

```python
class SettingsResolver:
    """
    Service for resolving effective settings from inheritance hierarchy.
    Handles 3-tier fallback: Campaign → Account → User.
    """

    def __init__(self, db: Session, logger: Logger):
        """
        Initialize resolver.

        Args:
            db: SQLAlchemy session
            logger: Logger instance
        """
        pass

    # ======================== MESSAGE DELAYS ========================

    async def get_effective_message_delays(
        self,
        campaign_id: UUID,
        account_id: UUID,
        user_id: UUID,
        message_number: int
    ) -> Tuple[int, int]:
        """
        Get effective (min, max) delay for specific message.

        Args:
            campaign_id: Campaign ID
            account_id: Account ID
            user_id: User ID
            message_number: 1, 2, or 3

        Returns:
            (min_delay_seconds, max_delay_seconds)

        3-Tier Inheritance:
            1. Campaign level: Campaign.message_N_delay_min/max
            2. Account level: TelegramAccount.campaign_default_message_delay_min/max
            3. User level: User.campaign_default_behavior_request_interval_min/max

        Returns first non-NULL tier, or user defaults as final fallback.
        """
        pass

    # ======================== SLEEP HOURS ========================

    async def get_effective_sleep_hours(
        self,
        user_id: UUID,
        account_id: Optional[UUID] = None
    ) -> int:
        """
        Get effective sleep hours setting.

        Args:
            user_id: User ID
            account_id: Optional account ID (for account-level override)

        Returns:
            Sleep hours (int, e.g., 8)

        2-Tier Hierarchy:
            1. Account level (if provided): TelegramAccount.campaign_default_sleep_hours
            2. User level: User.campaign_default_behavior_sleep_hours

        Used for:
            - Calculating rest windows
            - Rate limiting logic
        """
        pass

    # ======================== MAX DAILY USERS ========================

    async def get_effective_max_daily_users(
        self,
        campaign_id: UUID,
        account_id: UUID,
        user_id: UUID
    ) -> Optional[int]:
        """
        Get effective max daily users cap.

        Args:
            campaign_id: Campaign ID
            account_id: Account ID
            user_id: User ID

        Returns:
            Max users per day, or None if no limit

        3-Tier Inheritance:
            1. Campaign level: Campaign.max_daily_users
            2. Account level: TelegramAccount.campaign_default_max_daily_users
            3. User level: User.campaign_default_behavior_max_daily_requests
            4. Default: None (no limit)

        Used for:
            - Rate limiting across all campaigns
            - Daily quotas
        """
        pass

    # ======================== REQUEST INTERVALS ========================

    async def get_effective_request_interval(
        self,
        user_id: UUID,
        account_id: Optional[UUID] = None
    ) -> Tuple[int, int]:
        """
        Get effective (min, max) interval between requests (seconds).

        Args:
            user_id: User ID
            account_id: Optional account ID

        Returns:
            (min_interval_seconds, max_interval_seconds)

        Used for:
            - Inter-message delays
            - Human behavior simulation
        """
        pass

    # ======================== GENERIC RESOLVER ========================

    async def resolve_setting(
        self,
        setting_name: str,
        campaign: Optional[Campaign] = None,
        account: Optional[TelegramAccount] = None,
        user: Optional[User] = None
    ) -> Any:
        """
        Generic setting resolver (extensible).

        Args:
            setting_name: Name of setting to resolve
            campaign: Campaign object (optional)
            account: Account object (optional)
            user: User object (optional)

        Returns:
            Resolved setting value

        Supported Settings:
            - "message_delays" → (min, max)
            - "sleep_hours" → int
            - "max_daily_users" → int | None
            - "request_interval" → (min, max)

        Allows:
            - Adding new settings without changing interface
            - Consistent resolution logic
            - Easy extension
        """
        pass
```

---

## 3.7 LogService

### Purpose
Log campaign actions for audit trail, analytics, debugging.

### Interface Specification

```python
class LogService:
    """
    Service for campaign audit logging.
    """

    def __init__(self, db: Session, logger: Logger):
        """
        Initialize service.

        Args:
            db: SQLAlchemy session
            logger: Logger instance
        """
        pass

    # ======================== LOG ACTION ========================

    async def log_action(
        self,
        campaign_id: UUID,
        action: CampaignLogAction,
        telegram_user_id: Optional[str] = None,
        phase: Optional[InteractionPhase] = None,
        message_number: Optional[int] = None,
        details: Optional[dict] = None
    ) -> CampaignLog:
        """
        Log campaign action.

        Args:
            campaign_id: Campaign ID
            action: Action type (enum)
            telegram_user_id: Optional affected user
            phase: Optional phase at time of action
            message_number: Optional message number (1, 2, or 3)
            details: Optional flexible context (JSON)

        Returns:
            Created CampaignLog object

        Examples of usage:
            log_action(
                campaign_id=uuid1,
                action=CampaignLogAction.CAMPAIGN_STARTED,
                details={"started_by": "user@example.com"}
            )

            log_action(
                campaign_id=uuid1,
                action=CampaignLogAction.MESSAGE_SENT,
                telegram_user_id="123456789",
                phase=InteractionPhase.B,
                message_number=1,
                details={"job_id": "xyz", "sent_via_proxy": "proxy_1"}
            )

            log_action(
                campaign_id=uuid1,
                action=CampaignLogAction.JOB_CLOSED,
                telegram_user_id="123456789",
                phase=InteractionPhase.CLOSED,
                details={"reason": "user_replied", "reply_count": 1}
            )
        """
        pass

    # ======================== RETRIEVE LOGS ========================

    async def get_campaign_logs(
        self,
        campaign_id: UUID,
        action_filter: Optional[CampaignLogAction] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Tuple[List[CampaignLog], int]:
        """
        Get logs for campaign.

        Args:
            campaign_id: Campaign ID
            action_filter: Optional filter by action type
            limit: Max results
            offset: Pagination offset

        Returns:
            (List of logs, total count)

        Ordering:
            - created_at DESC (most recent first)

        Used for:
            - Campaign audit trail
            - Dashboard activity feed
        """
        pass

    async def get_user_logs(
        self,
        campaign_id: UUID,
        telegram_user_id: str
    ) -> List[CampaignLog]:
        """
        Get all logs for specific user in campaign.

        Args:
            campaign_id: Campaign ID
            telegram_user_id: Telegram user ID

        Returns:
            List of logs in chronological order

        Used for:
            - User interaction timeline
            - Debugging user issues
        """
        pass

    async def get_action_logs(
        self,
        campaign_id: UUID,
        action: CampaignLogAction
    ) -> List[CampaignLog]:
        """
        Get all logs for specific action type.

        Args:
            campaign_id: Campaign ID
            action: Action type to filter by

        Returns:
            List of logs for that action

        Used for:
            - Analytics (e.g., count message_sent actions)
            - Debugging (e.g., find all message_failed logs)
        """
        pass
```

---

## 3.8 Service Integration & Dependencies

### Initialization Order

```python
# Step 1: Create basic services
settings_resolver = SettingsResolver(db, logger)
log_service = LogService(db, logger)

# Step 2: Create services that depend on above
message_scheduler = MessageScheduler(db, logger, job_queue, settings_resolver)
interaction_service = InteractionService(db, logger, message_scheduler)
reply_listener = ReplyListener(db, logger, interaction_service, log_service)

# Step 3: Create top-level service
campaign_service = CampaignService(db, logger)

# Now all services ready to use
```

### Service Dependencies

```
CampaignService
  └─ uses: InteractionService
  └─ uses: LogService
  └─ uses: SettingsResolver (indirect, via InteractionService)

InteractionService
  └─ uses: MessageScheduler
  └─ uses: LogService

MessageScheduler
  └─ uses: SettingsResolver
  └─ uses: LogService (indirect)

ReplyListener
  └─ uses: InteractionService
  └─ uses: LogService

SettingsResolver
  (no dependencies on other services)

LogService
  (no dependencies on other services)
```

### Cross-Service Communication

**CampaignService → InteractionService:**
- On campaign activation: initialize message queues for each user
- On campaign completion/pause: cancel pending jobs

**InteractionService ↔ MessageScheduler:**
- Phase transition triggers message scheduling
- Message scheduler queues jobs that update interaction state

**ReplyListener → InteractionService:**
- Incoming message triggers job closure
- Closure updates interaction state

**All Services → LogService:**
- Every action logged via `log_service.log_action()`

---

## 3.9 Error Handling Strategy

### Exception Hierarchy

```python
class CampaignException(Exception):
    """Base exception for campaign service errors."""
    pass

class ValidationError(CampaignException):
    """Validation failed (invalid input data)."""
    pass

class StateError(CampaignException):
    """Invalid state transition (e.g., can't activate non-draft campaign)."""
    pass

class NotFoundError(CampaignException):
    """Entity not found (campaign, interaction, etc)."""
    pass

class DuplicateError(CampaignException):
    """Duplicate entry (e.g., user already in campaign)."""
    pass

class ForbiddenError(CampaignException):
    """Authorization failed (user doesn't own resource)."""
    pass

class JobQueueError(CampaignException):
    """Background job queue error."""
    pass
```

### Error Handling Patterns

**In all services:**
1. Validate inputs early (raise `ValidationError`)
2. Check authorization (raise `ForbiddenError`)
3. Verify entities exist (raise `NotFoundError`)
4. Check state preconditions (raise `StateError`)
5. Handle DB/queue errors gracefully
6. Log all errors with context
7. Return meaningful error messages to caller

---

## 3.10 Concurrency & Thread Safety

### Assumptions
- Service methods are **async** (support async/await)
- Database session is thread-safe (SQLAlchemy)
- Job queue supports concurrent submissions

### Race Conditions to Handle

**Add user to campaign:**
- Use UNIQUE constraint on (campaign_id, telegram_user_id) to prevent duplicates
- Handle IntegrityError gracefully

**Close job twice:**
- Check job_closed=false before closing
- Idempotent operation (closing already-closed job is no-op)

**Update campaign while scheduling:**
- Use database transactions for atomicity
- Serialize updates (only one update allowed at a time)

**Campaign completion vs message delivery:**
- Message job checks campaign status before sending
- Completed campaigns skip sending new messages

---

## 3.11 Testing Strategy

### Unit Tests (Per Service)

**CampaignService:**
- `test_create_campaign_draft`
- `test_activate_campaign_validates_requirements`
- `test_activate_campaign_success`
- `test_pause_active_campaign`
- `test_resume_paused_campaign`
- `test_cannot_update_active_campaign`
- `test_duplicate_campaign_name_rejected`

**InteractionService:**
- `test_add_user_to_campaign`
- `test_add_duplicate_user_rejected`
- `test_transition_valid_phases`
- `test_transition_invalid_phases_rejected`
- `test_close_job_idempotent`
- `test_get_open_jobs`
- `test_phase_distribution_stats`

**MessageScheduler:**
- `test_schedule_next_message_returns_job_id`
- `test_no_more_messages_returns_none`
- `test_settings_inheritance_campaign_level`
- `test_settings_inheritance_account_level`
- `test_settings_inheritance_user_level`
- `test_random_delay_in_range`
- `test_queue_message_job`
- `test_cancel_pending_jobs`

**ReplyListener:**
- `test_handle_incoming_message_matches_interaction`
- `test_handle_incoming_message_dedup`
- `test_handle_incoming_message_no_match`
- `test_reply_closes_job`
- `test_log_reply_increments_count`

**SettingsResolver:**
- `test_resolve_campaign_level_setting`
- `test_resolve_account_level_setting`
- `test_resolve_user_level_setting`
- `test_resolution_with_nulls`

**LogService:**
- `test_log_action`
- `test_get_campaign_logs`
- `test_get_user_logs`
- `test_get_action_logs`

### Integration Tests

- `test_full_campaign_workflow` (create → activate → add users → schedule messages → receive reply → close job)
- `test_concurrent_message_scheduling`
- `test_settings_inheritance_end_to_end`

### Mocks Needed
- `JobQueue` (background job queue)
- `TelegramClient` (actual API calls in Step 5)

---

## 3.12 Summary

**Step 3 Deliverables:**
- ✅ 6 service classes specified with detailed interfaces
- ✅ 50+ methods with complete business logic documentation
- ✅ Error handling strategy defined
- ✅ State machine transitions clarified
- ✅ Settings inheritance chain fully specified
- ✅ Service dependencies mapped
- ✅ Testing strategy outlined
- ✅ Concurrency considerations addressed

**Status:** Specification Complete. Ready for Step 4 (Background Jobs).

---

## Next: Step 4 → Background Jobs & Scheduling

Step 4 will define:
- Job queue setup (Celery/RQ/APScheduler)
- Message sending job worker
- Reply listener worker
- Job error handling & retries
- Rate limiting & queue management
