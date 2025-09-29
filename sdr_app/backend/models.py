from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, Float, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True)
    password_hash = Column(String(255))
    subscription_plan = Column(String(50), default="free")
    created_at = Column(DateTime, default=datetime.utcnow)

class LeadProfile(Base):
    __tablename__ = "lead_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=False)
    keywords = Column(Text, nullable=True, index=True)
    industry = Column(String(100), nullable=True)
    interests = Column(Text, nullable=True)
    regions = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    target_groups = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    lead_profile_id = Column(Integer, ForeignKey("lead_profiles.id"), nullable=False)
    telegram_user_id = Column(String(50), nullable=True, index=True)
    telegram_username = Column(String(100), nullable=True)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    bio = Column(Text, nullable=True)
    profile_match_keywords = Column(Text, nullable=True)
    relevance_score = Column(Float, default=0.0, index=True)
    conversation_score = Column(Float, default=0.0)
    status = Column(String(20), default='discovered', index=True)
    last_contacted_at = Column(DateTime, nullable=True)
    last_reply_at = Column(DateTime, nullable=True)
    source_group = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class LeadConversation(Base):
    __tablename__ = "lead_conversations"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False)
    message_id = Column(String(50), nullable=True)
    direction = Column(String(10), nullable=False)  # 'outbound' or 'inbound'
    message_content = Column(Text, nullable=True)
    ai_generated = Column(Boolean, default=False)
    sentiment_score = Column(Float, nullable=True)
    intent_detected = Column(String(100), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
