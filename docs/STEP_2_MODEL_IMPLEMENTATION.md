# Step 2: Model Implementation

**Status:** Design Phase (Model Definitions & Validation Logic)
**Branch:** `feature/campaign-engine-foundation`
**Date:** 2026-01-22

---

## Overview

Step 2 defines the Python models (Pydantic for API, ORM for database) with validation logic, helper methods, and relationships. This **does not include implementation code** yet—just the specifications and structure.

---

## 2.1 Enum Definitions

### CampaignStatus
```python
class CampaignStatus(str, Enum):
    """Campaign lifecycle states."""
    DRAFT = "draft"           # Not yet started
    ACTIVE = "active"         # Running
    PAUSED = "paused"         # Temporarily halted
    COMPLETED = "completed"   # Finished normally
    FAILED = "failed"         # Error or user aborted
```

### CampaignPriority
```python
class CampaignPriority(str, Enum):
    """Campaign priority levels (affects scheduling)."""
    LOW = "low"               # Process after high/medium
    MEDIUM = "medium"         # Standard priority
    HIGH = "high"             # Process first
```

### InteractionPhase
```python
class InteractionPhase(str, Enum):
    """User interaction state in campaign."""
    A = "A"        # New user, no messages sent
    B = "B"        # Message 1 sent
    C = "C"        # Message 2 sent
    D = "D"        # Message 3 sent (only if close_job_at_message=3)
    E = "E"        # All messages sent, awaiting final reply
    CLOSED = "closed"  # Job complete
```

### CampaignLogAction
```python
class CampaignLogAction(str, Enum):
    """Action types for audit log."""
    CAMPAIGN_CREATED = "campaign_created"
    CAMPAIGN_STARTED = "campaign_started"
    CAMPAIGN_PAUSED = "campaign_paused"
    CAMPAIGN_COMPLETED = "campaign_completed"
    CAMPAIGN_FAILED = "campaign_failed"
    USER_ADDED = "user_added"
    MESSAGE_SCHEDULED = "message_scheduled"
    MESSAGE_SENT = "message_sent"
    MESSAGE_FAILED = "message_failed"
    REPLY_RECEIVED = "reply_received"
    JOB_CLOSED = "job_closed"
    PHASE_UPDATED = "phase_updated"
    SETTINGS_UPDATED = "settings_updated"
```

---

## 2.2 Pydantic Models (API Layer)

### Base Schema
```python
# For input validation
class CampaignCreateRequest(BaseModel):
    """API request to create campaign."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=1000)
    target_group_id: Optional[str] = Field(default=None)  # Optional for draft
    target_group_name: Optional[str] = Field(default=None)
    message_1_text: str = Field(..., min_length=1)
    message_2_text: str = Field(..., min_length=1)
    message_3_text: str = Field(..., min_length=1)
    close_job_at_message: int = Field(..., ge=2, le=3)
    message_1_delay_min: int = Field(default=60, ge=0)
    message_1_delay_max: int = Field(default=300, ge=0)
    message_2_delay_min: int = Field(default=60, ge=0)
    message_2_delay_max: int = Field(default=300, ge=0)
    message_3_delay_min: Optional[int] = Field(default=60, ge=0)
    message_3_delay_max: Optional[int] = Field(default=300, ge=0)
    priority: CampaignPriority = Field(default=CampaignPriority.MEDIUM)
    max_daily_users: Optional[int] = Field(default=None, ge=1)

    # Validation: delays must be in order
    @field_validator('message_1_delay_min', 'message_2_delay_min', 'message_3_delay_min')
    def validate_delays(cls, v, info):
        field_name = info.field_name
        max_field = field_name.replace('_min', '_max')
        # This will be validated in model-level validator
        return v

    # Model-level validation
    @model_validator(mode='after')
    def validate_delay_ranges(self):
        """
        Ensure:
        - min <= max for each message
        - message_3_* is NULL if close_job_at_message=2
        """
        if self.message_1_delay_min > self.message_1_delay_max:
            raise ValueError("message_1_delay_min must be <= message_1_delay_max")
        if self.message_2_delay_min > self.message_2_delay_max:
            raise ValueError("message_2_delay_min must be <= message_2_delay_max")

        if self.close_job_at_message == 2:
            if self.message_3_delay_min is not None or self.message_3_delay_max is not None:
                raise ValueError("message_3_delay_* must be NULL when close_job_at_message=2")
        elif self.close_job_at_message == 3:
            if self.message_3_delay_min is None or self.message_3_delay_max is None:
                raise ValueError("message_3_delay_* must be provided when close_job_at_message=3")
            if self.message_3_delay_min > self.message_3_delay_max:
                raise ValueError("message_3_delay_min must be <= message_3_delay_max")

        return self


class CampaignUpdateRequest(BaseModel):
    """API request to update campaign (only draft)."""
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=1000)
    target_group_id: Optional[str] = Field(default=None)
    target_group_name: Optional[str] = Field(default=None)
    message_1_text: Optional[str] = Field(default=None, min_length=1)
    message_2_text: Optional[str] = Field(default=None, min_length=1)
    message_3_text: Optional[str] = Field(default=None, min_length=1)
    close_job_at_message: Optional[int] = Field(default=None, ge=2, le=3)
    message_1_delay_min: Optional[int] = Field(default=None, ge=0)
    message_1_delay_max: Optional[int] = Field(default=None, ge=0)
    message_2_delay_min: Optional[int] = Field(default=None, ge=0)
    message_2_delay_max: Optional[int] = Field(default=None, ge=0)
    message_3_delay_min: Optional[int] = Field(default=None, ge=0)
    message_3_delay_max: Optional[int] = Field(default=None, ge=0)
    priority: Optional[CampaignPriority] = Field(default=None)
    max_daily_users: Optional[int] = Field(default=None, ge=1)


class CampaignResponse(BaseModel):
    """API response for campaign (read)."""
    id: UUID
    user_id: UUID
    telegram_account_id: UUID
    name: str
    description: Optional[str]
    target_group_id: Optional[str]  # Can be NULL
    target_group_name: Optional[str]
    message_1_text: str
    message_2_text: str
    message_3_text: str
    close_job_at_message: int
    message_1_delay_min: int
    message_1_delay_max: int
    message_2_delay_min: int
    message_2_delay_max: int
    message_3_delay_min: Optional[int]
    message_3_delay_max: Optional[int]
    status: CampaignStatus
    priority: CampaignPriority
    max_daily_users: Optional[int]
    total_users_contacted: int
    total_messages_sent: int
    total_replies_received: int
    total_jobs_closed: int
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    last_activity_at: Optional[datetime]

    class Config:
        from_attributes = True


class CampaignUserInteractionResponse(BaseModel):
    """API response for user interaction in campaign."""
    id: UUID
    campaign_id: UUID
    telegram_user_id: str
    telegram_username: Optional[str]
    telegram_first_name: Optional[str]  # Can be NULL
    telegram_last_name: Optional[str]
    message_1_sent_at: Optional[datetime]
    message_1_job_id: Optional[str]
    message_2_sent_at: Optional[datetime]
    message_2_job_id: Optional[str]
    message_3_sent_at: Optional[datetime]
    message_3_job_id: Optional[str]
    last_reply_at: Optional[datetime]
    reply_count: int
    current_phase: InteractionPhase
    job_closed: bool
    job_closed_at: Optional[datetime]
    job_closed_reason: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

    def get_display_name(self) -> str:
        """
        Return user's display name with fallback logic.
        Priority: first_name > username > user_id
        """
        if self.telegram_first_name:
            return self.telegram_first_name
        elif self.telegram_username:
            return self.telegram_username
        else:
            return str(self.telegram_user_id)


class CampaignReplyResponse(BaseModel):
    """API response for reply."""
    id: UUID
    interaction_id: UUID
    telegram_message_id: str
    message_text: str
    received_at: datetime

    class Config:
        from_attributes = True


class CampaignLogResponse(BaseModel):
    """API response for log entry."""
    id: UUID
    campaign_id: UUID
    telegram_user_id: Optional[str]
    action: CampaignLogAction
    phase: Optional[InteractionPhase]
    message_number: Optional[int]
    details: Optional[dict]
    created_at: datetime

    class Config:
        from_attributes = True
```

---

## 2.3 ORM Models (Database Layer)

We assume using **SQLAlchemy** (or similar ORM).

### Campaign ORM Model
```python
class Campaign(Base):
    """Campaign database model."""
    __tablename__ = "campaigns"

    # Primary & Foreign Keys
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    telegram_account_id: Mapped[UUID] = mapped_column(ForeignKey("telegram_accounts.id", ondelete="CASCADE"))

    # Basic Info
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    target_group_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # OPTIONAL
    target_group_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Messages
    message_1_text: Mapped[str] = mapped_column(Text, nullable=False)
    message_2_text: Mapped[str] = mapped_column(Text, nullable=False)
    message_3_text: Mapped[str] = mapped_column(Text, nullable=False)
    close_job_at_message: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    # Delays (in seconds)
    message_1_delay_min: Mapped[int] = mapped_column(Integer, nullable=False)
    message_1_delay_max: Mapped[int] = mapped_column(Integer, nullable=False)
    message_2_delay_min: Mapped[int] = mapped_column(Integer, nullable=False)
    message_2_delay_max: Mapped[int] = mapped_column(Integer, nullable=False)
    message_3_delay_min: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    message_3_delay_max: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Configuration
    status: Mapped[CampaignStatus] = mapped_column(Enum(CampaignStatus), default=CampaignStatus.DRAFT, nullable=False)
    priority: Mapped[CampaignPriority] = mapped_column(Enum(CampaignPriority), default=CampaignPriority.MEDIUM, nullable=False)
    max_daily_users: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Statistics (denormalized for performance)
    total_users_contacted: Mapped[int] = mapped_column(Integer, default=0)
    total_messages_sent: Mapped[int] = mapped_column(Integer, default=0)
    total_replies_received: Mapped[int] = mapped_column(Integer, default=0)
    total_jobs_closed: Mapped[int] = mapped_column(Integer, default=0)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_activity_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="campaigns")
    account: Mapped[TelegramAccount] = relationship("TelegramAccount", back_populates="campaigns")
    interactions: Mapped[List[CampaignUserInteraction]] = relationship("CampaignUserInteraction", back_populates="campaign", cascade="all, delete-orphan")
    logs: Mapped[List[CampaignLog]] = relationship("CampaignLog", back_populates="campaign", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index('idx_campaigns_user_status', 'user_id', 'status'),
        Index('idx_campaigns_account_status', 'telegram_account_id', 'status'),
        Index('idx_campaigns_created_at', 'created_at'),
        UniqueConstraint('user_id', 'name', name='uq_user_campaign_name'),
        CheckConstraint('message_1_delay_min <= message_1_delay_max'),
        CheckConstraint('message_2_delay_min <= message_2_delay_max'),
        CheckConstraint('close_job_at_message IN (2, 3)'),
    )

    # Helper Methods
    def can_activate(self) -> bool:
        """
        Check if campaign can transition to active state.
        Requirements:
        - status is DRAFT
        - target_group_id is NOT NULL
        - all message texts are non-empty
        """
        if self.status != CampaignStatus.DRAFT:
            return False
        if self.target_group_id is None:
            return False
        if not all([self.message_1_text, self.message_2_text, self.message_3_text]):
            return False
        return True

    def validate_can_activate(self) -> tuple[bool, Optional[str]]:
        """
        Detailed validation with error message.
        Returns: (is_valid, error_message)
        """
        if self.status != CampaignStatus.DRAFT:
            return (False, f"Campaign must be in DRAFT status to activate, currently {self.status}")
        if self.target_group_id is None:
            return (False, "Target group ID must be set before activation")
        if not self.message_1_text:
            return (False, "Message 1 text is required")
        if not self.message_2_text:
            return (False, "Message 2 text is required")
        if not self.message_3_text:
            return (False, "Message 3 text is required")
        return (True, None)

    def get_message_by_number(self, number: int) -> str:
        """Get message text by number (1, 2, or 3)."""
        messages = {
            1: self.message_1_text,
            2: self.message_2_text,
            3: self.message_3_text,
        }
        return messages.get(number)

    def get_delay_range(self, message_number: int) -> tuple[int, int]:
        """Get (min, max) delay in seconds for a message."""
        ranges = {
            1: (self.message_1_delay_min, self.message_1_delay_max),
            2: (self.message_2_delay_min, self.message_2_delay_max),
            3: (self.message_3_delay_min, self.message_3_delay_max),
        }
        return ranges.get(message_number, (0, 0))
```

### CampaignUserInteraction ORM Model
```python
class CampaignUserInteraction(Base):
    """User interaction in campaign."""
    __tablename__ = "campaign_user_interactions"

    # Primary & Foreign Keys
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    campaign_id: Mapped[UUID] = mapped_column(ForeignKey("campaigns.id", ondelete="CASCADE"))

    # Telegram User Info
    telegram_user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    telegram_username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    telegram_first_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # OPTIONAL
    telegram_last_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Message Tracking
    message_1_sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    message_1_job_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    message_2_sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    message_2_job_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    message_3_sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    message_3_job_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Reply Tracking
    last_reply_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    reply_count: Mapped[int] = mapped_column(Integer, default=0)

    # State
    current_phase: Mapped[InteractionPhase] = mapped_column(Enum(InteractionPhase), default=InteractionPhase.A, nullable=False)
    job_closed: Mapped[bool] = mapped_column(Boolean, default=False)
    job_closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    job_closed_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    campaign: Mapped[Campaign] = relationship("Campaign", back_populates="interactions")
    replies: Mapped[List[CampaignReply]] = relationship("CampaignReply", back_populates="interaction", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        UniqueConstraint('campaign_id', 'telegram_user_id', name='uq_campaign_user'),
        Index('idx_interaction_phase', 'campaign_id', 'current_phase'),
        Index('idx_interaction_tg_user', 'telegram_user_id', 'campaign_id'),
        Index('idx_interaction_job_open', 'job_closed', 'campaign_id'),
        Index('idx_interaction_created_at', 'created_at'),
    )

    # Helper Methods
    def get_display_name(self) -> str:
        """
        Return user's display name with fallback logic.
        Priority: first_name > username > user_id
        """
        if self.telegram_first_name:
            return self.telegram_first_name
        elif self.telegram_username:
            return self.telegram_username
        else:
            return self.telegram_user_id

    def can_close_job(self, reason: str) -> bool:
        """
        Check if job can be closed.
        - Must not already be closed
        - Reason must be provided
        """
        if self.job_closed:
            return False
        if not reason:
            return False
        return True

    def get_next_message_number(self) -> Optional[int]:
        """
        Determine which message to send next.
        Returns: 1, 2, 3, or None if no more messages to send.
        """
        if not self.message_1_sent_at:
            return 1
        elif not self.message_2_sent_at:
            return 2
        elif not self.message_3_sent_at:
            return 3
        else:
            return None  # All messages sent

    def get_messages_sent_count(self) -> int:
        """Count how many messages have been sent to this user."""
        count = 0
        if self.message_1_sent_at:
            count += 1
        if self.message_2_sent_at:
            count += 1
        if self.message_3_sent_at:
            count += 1
        return count
```

### CampaignReply ORM Model
```python
class CampaignReply(Base):
    """Reply received from user in campaign."""
    __tablename__ = "campaign_replies"

    # Primary & Foreign Keys
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    interaction_id: Mapped[UUID] = mapped_column(ForeignKey("campaign_user_interactions.id", ondelete="CASCADE"))

    # Content
    telegram_message_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    message_text: Mapped[str] = mapped_column(Text, nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # Relationships
    interaction: Mapped[CampaignUserInteraction] = relationship("CampaignUserInteraction", back_populates="replies")

    # Indexes
    __table_args__ = (
        Index('idx_reply_interaction', 'interaction_id', 'received_at'),
    )
```

### CampaignLog ORM Model
```python
class CampaignLog(Base):
    """Audit log for campaign actions."""
    __tablename__ = "campaign_logs"

    # Primary & Foreign Keys
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    campaign_id: Mapped[UUID] = mapped_column(ForeignKey("campaigns.id", ondelete="CASCADE"))

    # Content
    telegram_user_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    action: Mapped[CampaignLogAction] = mapped_column(Enum(CampaignLogAction), nullable=False)
    phase: Mapped[Optional[InteractionPhase]] = mapped_column(Enum(InteractionPhase), nullable=True)
    message_number: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    details: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    campaign: Mapped[Campaign] = relationship("Campaign", back_populates="logs")

    # Indexes
    __table_args__ = (
        Index('idx_logs_campaign_time', 'campaign_id', 'created_at'),
        Index('idx_logs_tg_user_time', 'telegram_user_id', 'created_at'),
        Index('idx_logs_action', 'action'),
    )
```

---

## 2.4 Validation Rules Summary

### Create/Update Campaign
1. `name`: 1-255 characters, required, unique per user
2. `target_group_id`: Optional for draft, **required before activation**
3. Messages: All text required, non-empty
4. Delays: `min <= max` for each message
5. `close_job_at_message`: Must be 2 or 3
6. If `close_job_at_message=2`: `message_3_*` fields must be NULL
7. If `close_job_at_message=3`: `message_3_*` fields must be provided

### Create/Update Interaction
1. `telegram_user_id`: Required, unique per campaign
2. `telegram_first_name`: Optional, can be NULL
3. `current_phase`: Must match logical state of message delivery
4. `job_closed`: If true, `job_closed_at` and `job_closed_reason` required

### Activation Flow
```
Draft campaign  → Call validate_can_activate()  → If valid: transition to ACTIVE
```

---

## 2.5 Settings Inheritance

### Default Resolution Order

**For message delays:**
```python
def get_effective_delay_range(campaign: Campaign, telegram_account: TelegramAccount, user: User) -> tuple[int, int]:
    """
    Resolve delay range with 3-tier override:
    1. Campaign level (if explicitly set in campaign)
    2. Account level (telegram_account.campaign_default_*)
    3. User level (user.campaign_default_*)
    """
    # If campaign has explicit delay, use it
    if campaign.message_1_delay_min is not None:
        return (campaign.message_1_delay_min, campaign.message_1_delay_max)

    # Fallback to account defaults
    if telegram_account.campaign_default_message_delay_min is not None:
        return (telegram_account.campaign_default_message_delay_min,
                telegram_account.campaign_default_message_delay_max)

    # Final fallback to user defaults
    return (user.campaign_default_behavior_request_interval_min,
            user.campaign_default_behavior_request_interval_max)
```

---

## 2.6 Summary

**Step 2 Deliverables:**
- ✓ Enum definitions (CampaignStatus, CampaignPriority, InteractionPhase, CampaignLogAction)
- ✓ Pydantic models (API validation, request/response schemas)
- ✓ ORM models (SQLAlchemy, database mapping)
- ✓ Helper methods (validation, display, state transitions)
- ✓ Validation rules documented
- ✓ Settings inheritance chain defined
- ✓ Relationships mapped
- ✓ Indexes specified

**Status:** Design Complete. Ready for Step 3.

---

## Next: Step 3 → Service Layer

Step 3 will define:
- **CampaignService** (CRUD operations)
- **InteractionService** (State machine, phase transitions)
- **MessageScheduler** (Delay calculation, job queuing)
- **ReplyListener** (Handle incoming messages)
- **SettingsResolver** (Inheritance chain)
