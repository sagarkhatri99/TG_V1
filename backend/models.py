from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, Float, ForeignKey, JSON, SmallInteger, BigInteger, UniqueConstraint
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True)
    password_hash = Column(String(255))
    subscription_plan = Column(String(50), default="free")
    billing_cycle = Column(String(10), nullable=True)  # 'monthly' or 'annual'
    trial_end_date = Column(DateTime, nullable=True)
    jobs_created_this_month = Column(Integer, default=0)
    job_counter_last_reset = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    telegram_accounts = relationship("TelegramAccount", back_populates="user")
    jobs = relationship("Job", back_populates="user")
    campaigns = relationship("Campaign", back_populates="user")
    message_templates = relationship("MessageTemplate", back_populates="user")

class TelegramAccount(Base):
    __tablename__ = "telegram_accounts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    nickname = Column(String(100))
    phone_number = Column(String(20), unique=True)
    api_id = Column(String(50))
    api_hash = Column(String(255))
    session_string = Column(Text)
    proxy_id = Column(Integer, ForeignKey("proxies.id"), nullable=True)
    status = Column(String(20), default="pending")
    trust_score = Column(Float, default=50.0)  # Changed from Integer to Float
    last_activity = Column(DateTime)
    daily_message_count = Column(Integer, default=0)
    ban_risk_score = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Warmup fields
    warmup_stage = Column(String(50), default="pending")  # pending, stage1, stage2, stage3, ready
    warmup_started_at = Column(DateTime, nullable=True)
    warmup_completed_at = Column(DateTime, nullable=True)
    daily_message_limit = Column(Integer, default=5)  # Increases per stage
    assigned_ip = Column(String(50), nullable=True)  # Static IP from proxy
    ip_last_verified = Column(DateTime, nullable=True)
    
    user = relationship("User", back_populates="telegram_accounts")
    proxy = relationship("Proxy", foreign_keys=[proxy_id], back_populates="accounts")
    interactions = relationship("UserInteraction", back_populates="telegram_account")
    action_logs = relationship("ActionLog", back_populates="account")
    health = relationship("AccountHealth", back_populates="account", uselist=False)
    campaigns = relationship("Campaign", back_populates="account")
    
    # Campaign-specific settings
    sleep_hour_start = Column(Integer, default=23)  # 11 PM
    sleep_hour_end = Column(Integer, default=7)    # 7 AM
    # campaign_enabled = Column(Boolean, default=False)  # DEPRECATED v1.2 - Removed unnecessary toggle

class Proxy(Base):
    __tablename__ = "proxies"
    
    id = Column(Integer, primary_key=True, index=True)
    proxy_url = Column(String(500))  # Increased length for long parameterized URLs
    proxy_type = Column(String(10))
    country_code = Column(String(2))
    status = Column(String(20), default="active")
    response_time = Column(Integer, nullable=True)  # Only set after testing
    last_check = Column(DateTime, nullable=True)  # Only set after testing
    ip_address = Column(String(45), nullable=True)  # Store detected IP (supports IPv6)
    
    # Proxy provider tracking (static residential proxies)
    provider = Column(String(50), nullable=True)  # webshare, iproyal, proxycheap
    assigned_account_id = Column(Integer, ForeignKey("telegram_accounts.id"), nullable=True, unique=True)  # 1 proxy per account
    
    # Relationships
    accounts = relationship("TelegramAccount", foreign_keys="TelegramAccount.proxy_id", back_populates="proxy")

class UserInteraction(Base):
    __tablename__ = "user_interactions"
    
    id = Column(Integer, primary_key=True, index=True)
    telegram_account_id = Column(Integer, ForeignKey("telegram_accounts.id"))
    target_user_id = Column(String(50))
    target_username = Column(String(100))
    last_interaction = Column(DateTime)
    interaction_count = Column(Integer, default=1)
    
    telegram_account = relationship("TelegramAccount", back_populates="interactions")

class Job(Base):
    __tablename__ = "jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    user = relationship("User", back_populates="jobs")
    telegram_account_id = Column(Integer, ForeignKey("telegram_accounts.id"), nullable=True)
    job_type = Column(String(50))
    config = Column(Text)
    status = Column(String(20), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    progress = Column(Integer, default=0)
    total_tasks = Column(Integer)
    error_message = Column(Text)
    # New fields for enhanced job tracking
    user_description = Column(Text, nullable=True)  # What user mentioned when creating the job
    messages_sent = Column(Integer, default=0)  # Actual messages sent
    messages_planned = Column(Integer, default=0)  # Total messages supposed to send
    completion_percentage = Column(Float, default=0.0)  # Calculated percentage
    # Batch distribution fields
    parent_job_id = Column(Integer, ForeignKey("jobs.id"), nullable=True)  # Link to parent distribution job
    batch_number = Column(Integer, nullable=True)  # Which batch this is (1-indexed)
    total_batches = Column(Integer, nullable=True)  # Total number of batches for this distribution
    batch_user_ids = Column(Text, nullable=True)  # JSON array of user IDs for this batch

class MessageLog(Base):
    __tablename__ = "message_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    telegram_account_id = Column(Integer, ForeignKey("telegram_accounts.id"))
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=True)
    target_user_id = Column(String(50))
    target_username = Column(String(100))
    message_content = Column(Text)
    ai_relevance_score = Column(Float)
    delivery_status = Column(String(20))
    timestamp = Column(DateTime, default=datetime.utcnow)

class ActionLog(Base):
    __tablename__ = "action_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("telegram_accounts.id"), nullable=False, index=True)
    action_type = Column(String(50), nullable=False)  # join_group, send_message, react, voice, etc.
    action_data = Column(Text, nullable=True)  # JSON data with action details
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    success = Column(Boolean, default=True, nullable=False)
    error_message = Column(Text, nullable=True)
    ban_risk_delta = Column(Float, nullable=True)  # Change in ban risk after this action
    
    account = relationship("TelegramAccount", back_populates="action_logs")

class AccountHealth(Base):
    """
    Track health and safety metrics for each Telegram account.
    Used for per-account rate limiting and ban prevention.
    """
    __tablename__ = "account_health"
    
    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("telegram_accounts.id"), unique=True, nullable=False, index=True)
    
    # Overall health
    health_score = Column(Float, default=100.0)  # 0-100
    status = Column(String(20), default="healthy", index=True)  # healthy, warning, restricted, banned
    
    # Daily counters (reset daily)
    messages_sent_today = Column(Integer, default=0)
    groups_joined_today = Column(Integer, default=0)
    api_calls_today = Column(Integer, default=0)
    last_reset_date = Column(DateTime, default=datetime.utcnow)
    
    # Error tracking
    flood_wait_count = Column(Integer, default=0)
    spam_error_count = Column(Integer, default=0)
    auth_error_count = Column(Integer, default=0)
    generic_error_count = Column(Integer, default=0)
    
    # Restriction info
    is_restricted = Column(Boolean, default=False)
    restriction_reason = Column(String(255))
    restriction_until = Column(DateTime)
    
    # Activity metadata
    last_activity = Column(DateTime, default=datetime.utcnow, index=True)
    last_error_time = Column(DateTime)
    
    # Error history (JSON array of last 50 errors)
    error_history = Column(JSON, default=list)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    account = relationship("TelegramAccount", back_populates="health")

# --- NEW CAMPAIGN SYSTEM MODELS ---

class Campaign(Base):
    __tablename__ = "campaigns"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    telegram_account_id = Column(Integer, ForeignKey("telegram_accounts.id"), nullable=False, index=True)
    parent_job_id = Column(Integer, ForeignKey("jobs.id"), nullable=True)
    
    name = Column(String(255), nullable=False)
    status = Column(String(20), default="draft", index=True)
    
    message_templates = Column(JSON, nullable=False)
    target_group_id = Column(String(100), nullable=True)
    
    start_at = Column(DateTime, nullable=True)
    end_at = Column(DateTime, nullable=True)
    
    min_delay = Column(Integer, default=30)
    max_delay = Column(Integer, default=120)
    daily_limit = Column(Integer, nullable=True)
    
    total_targets = Column(Integer, default=0)
    sent_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    reply_count = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="campaigns")
    account = relationship("TelegramAccount", back_populates="campaigns")
    parent_job = relationship("Job", foreign_keys=[parent_job_id])
    interactions = relationship("CampaignUserInteraction", back_populates="campaign")
    logs = relationship("CampaignLog", back_populates="campaign")

class CampaignUserInteraction(Base):
    __tablename__ = "campaign_user_interactions"
    
    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=False, index=True)
    target_user_id = Column(String(50), nullable=False)
    target_username = Column(String(100), nullable=True)
    telegram_first_name = Column(String(100), nullable=True)
    
    current_phase = Column(String(10), default="A")
    status = Column(String(20), default="pending")
    
    last_interaction_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('campaign_id', 'target_user_id', name='uq_campaign_target_user'),
    )

    # Relationships
    campaign = relationship("Campaign", back_populates="interactions")
    pending_tasks = relationship("CampaignPendingTask", back_populates="interaction")
    messages = relationship("CampaignMessageTracking", back_populates="interaction")
    replies = relationship("CampaignReply", back_populates="interaction")
    logs = relationship("CampaignLog", back_populates="interaction")

class CampaignPendingTask(Base):
    __tablename__ = "campaign_pending_tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    campaign_user_interaction_id = Column(Integer, ForeignKey("campaign_user_interactions.id"), nullable=False, index=True)
    celery_task_id = Column(String(255), nullable=True, unique=True)
    
    task_type = Column(String(50), nullable=False)
    scheduled_for = Column(DateTime, nullable=False, index=True)
    
    status = Column(String(20), default="pending", index=True)
    reason_paused = Column(String(255), nullable=True)
    retry_count = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    interaction = relationship("CampaignUserInteraction", back_populates="pending_tasks")

class CampaignMessageTracking(Base):
    __tablename__ = "campaign_message_tracking"
    
    id = Column(Integer, primary_key=True, index=True)
    campaign_user_interaction_id = Column(Integer, ForeignKey("campaign_user_interactions.id"), nullable=False, index=True)
    
    message_number = Column(SmallInteger, nullable=False)
    telegram_message_id = Column(BigInteger, nullable=True)
    idempotency_key = Column(String(36), unique=True, nullable=False, index=True)
    
    status = Column(String(20), default="sent")
    sent_at = Column(DateTime, default=datetime.utcnow)
    error_message = Column(Text, nullable=True)

    # Relationships
    interaction = relationship("CampaignUserInteraction", back_populates="messages")

class CampaignReply(Base):
    __tablename__ = "campaign_replies"
    
    id = Column(Integer, primary_key=True, index=True)
    campaign_user_interaction_id = Column(Integer, ForeignKey("campaign_user_interactions.id"), nullable=False, index=True)
    
    telegram_message_id = Column(BigInteger, nullable=False)
    message_text = Column(Text, nullable=True)
    received_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    interaction = relationship("CampaignUserInteraction", back_populates="replies")

class CampaignLog(Base):
    __tablename__ = "campaign_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=False, index=True)
    campaign_user_interaction_id = Column(Integer, ForeignKey("campaign_user_interactions.id"), nullable=True, index=True)
    
    action = Column(String(50), nullable=False)
    phase = Column(String(10), nullable=True)
    message_number = Column(SmallInteger, nullable=True)
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    campaign = relationship("Campaign", back_populates="logs")
    interaction = relationship("CampaignUserInteraction", back_populates="logs")

class MessageTemplate(Base):
    __tablename__ = "message_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    category = Column(String(50), default="Custom")
    spam_risk_score = Column(Float, default=0.0)
    variables = Column(JSON, default=list)  # List of strings: ["name", "username"]
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", back_populates="message_templates")
