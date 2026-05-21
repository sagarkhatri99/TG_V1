from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, Float, ForeignKey, JSON, UniqueConstraint
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
    account_trust_tier = Column(String(20), default="warming")  # new, warming, trusted, custom
    warmup_started_at = Column(DateTime, nullable=True)
    warmup_completed_at = Column(DateTime, nullable=True)
    daily_message_limit = Column(Integer, default=5)  # Increases per stage
    assigned_ip = Column(String(50), nullable=True)  # Static IP from proxy
    ip_last_verified = Column(DateTime, nullable=True)
    
    # Operating Hours
    sleep_hour_start = Column(Integer, nullable=True, default=23)
    sleep_hour_end = Column(Integer, nullable=True, default=7)
    
    user = relationship("User", back_populates="telegram_accounts")
    proxy = relationship("Proxy", foreign_keys=[proxy_id], back_populates="accounts")
    interactions = relationship("UserInteraction", back_populates="telegram_account")
    action_logs = relationship("ActionLog", back_populates="account")
    health = relationship("AccountHealth", back_populates="account", uselist=False)


class Proxy(Base):
    __tablename__ = "proxies"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=True)  # Optional human-readable label
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
    status = Column(String(20), default="pending")  # pending, running, paused, completed, failed, scheduled
    scheduled_at = Column(DateTime, nullable=True)  # If set, job waits until this time before dispatching
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
    celery_task_id = Column(String(255), nullable=True)  # Celery task tracking ID
    # Batch distribution fields
    parent_job_id = Column(Integer, ForeignKey("jobs.id"), nullable=True)  # Link to parent distribution job
    batch_number = Column(Integer, nullable=True)  # Which batch this is (1-indexed)
    total_batches = Column(Integer, nullable=True)  # Total number of batches for this distribution
    batch_user_ids = Column(Text, nullable=True)  # JSON array of user IDs for this batch
    telegram_account = relationship("TelegramAccount", foreign_keys=[telegram_account_id])

class MessageLog(Base):
    __tablename__ = "message_logs"
    __table_args__ = (
        UniqueConstraint("job_id", "target_user_id", name="uq_job_target"),
    )
    
    id = Column(Integer, primary_key=True, index=True)
    telegram_account_id = Column(Integer, ForeignKey("telegram_accounts.id"), index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=True, index=True)
    target_user_id = Column(String(50), index=True)
    target_username = Column(String(100))
    message_content = Column(Text)
    ai_relevance_score = Column(Float)
    delivery_status = Column(String(20), index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

class ActionLog(Base):
    __tablename__ = "action_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("telegram_accounts.id"), nullable=False, index=True)
    action_type = Column(String(50), nullable=False)  # join_group, send_message, react, voice, etc.
    action_data = Column(Text, nullable=True)  # JSON data with action details
    action_details = Column(Text, nullable=True)  # Additional human-readable details
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
