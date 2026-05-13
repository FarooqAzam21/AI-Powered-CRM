from sqlalchemy import Column, Integer, String, Boolean, Text, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True)
    password = Column(String, nullable=False)
    role = Column(String, default="user")
    
    is_verified = Column(Boolean, default=False)
    verification_token = Column(String, nullable=True)

    # Google OAuth
    google_access_token = Column(String, nullable=True)
    google_refresh_token = Column(String, nullable=True)
    gmail_connected = Column(Boolean, default=False)

    # Relationships
    emails = relationship("Email", back_populates="user", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")

class Email(Base):
    __tablename__ = "emails"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    gmail_message_id = Column(String, unique=True, index=True)
    sender = Column(String, nullable=False)
    subject = Column(String)
    body = Column(Text)
    
    # AI Analysis fields
    category = Column(String)
    confidence = Column(Float)
    action = Column(String)
    reason = Column(Text)
    draft_reply = Column(Text, nullable=True)
    
    status = Column(String, default="PENDING")  # PENDING, SENT, ARCHIVED, ESCALATED
    received_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="emails")

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    type = Column(String)  # INFO, URGENT, SUCCESS
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="notifications")
