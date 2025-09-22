from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, Float, ForeignKey
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
    trust_score = Column(Integer, default=50)
    last_activity = Column(DateTime)
    daily_message_count = Column(Integer, default=0)
    ban_risk_score = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="telegram_accounts")
    proxy = relationship("Proxy")
    interactions = relationship("UserInteraction", back_populates="telegram_account")

class Proxy(Base):
    __tablename__ = "proxies"
    
    id = Column(Integer, primary_key=True, index=True)
    proxy_url = Column(String(255))
    proxy_type = Column(String(10))
    country_code = Column(String(2))
    status = Column(String(20), default="active")
    response_time = Column(Integer)
    last_check = Column(DateTime)

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
