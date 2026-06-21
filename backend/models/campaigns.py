"""
Campaign Models - Phase 9
Bulk email campaigns with tracking and analytics
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, JSON, ForeignKey, Enum
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime
import enum

class CampaignStatus(str, enum.Enum):
    """Campaign status"""
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"

class EmailStatus(str, enum.Enum):
    """Individual email status"""
    PENDING = "pending"
    SENT = "sent"
    OPENED = "opened"
    CLICKED = "clicked"
    BOUNCED = "bounced"
    FAILED = "failed"
    RETRYING = "retrying"

class Campaign(Base):
    """Email campaign"""
    __tablename__ = "campaigns"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user = relationship("User", back_populates="campaigns")
    
    # Campaign details
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text)
    subject = Column(String(255), nullable=False)
    template = Column(Text, nullable=False)  # HTML template
    from_name = Column(String(255), nullable=True)
    reply_to = Column(String(255), nullable=True)
    
    # Personalization
    variables = Column(JSON, default=dict)  # {"first_name": "Contact.first_name", ...}
    
    # Status and scheduling
    status = Column(Enum(CampaignStatus), default=CampaignStatus.DRAFT)  # index managed by crm.Campaign
    scheduled_at = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Throttling (emails per minute)
    throttle_per_minute = Column(Integer, default=2)
    
    # Recipients
    recipient_count = Column(Integer, default=0)
    contact_group_ids = Column(JSON, default=list)  # Filter: specific contacts
    segment_criteria = Column(JSON, default=dict)  # Filter: by attributes
    
    # Tracking
    open_tracking_enabled = Column(Boolean, default=True)
    click_tracking_enabled = Column(Boolean, default=True)
    
    # Performance
    sent_count = Column(Integer, default=0, index=True)
    opened_count = Column(Integer, default=0)
    clicked_count = Column(Integer, default=0)
    bounced_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    
    # Analytics
    open_rate = Column(Float, default=0.0)
    click_rate = Column(Float, default=0.0)
    bounce_rate = Column(Float, default=0.0)
    unsubscribe_count = Column(Integer, default=0)
    
    # Relationships
    sends = relationship("CampaignSend", back_populates="campaign", cascade="all, delete-orphan")
    tracks = relationship("CampaignTrack", back_populates="campaign", cascade="all, delete-orphan")
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def calculate_metrics(self):
        """Calculate campaign metrics"""
        if self.sent_count == 0:
            return
        
        self.open_rate = (self.opened_count / self.sent_count) * 100
        self.click_rate = (self.clicked_count / self.sent_count) * 100
        self.bounce_rate = (self.bounced_count / self.sent_count) * 100

class CampaignSend(Base):
    """Individual email send record"""
    __tablename__ = "campaign_sends"
    
    id = Column(Integer, primary_key=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=False, index=True)
    campaign = relationship("models.campaigns.Campaign", back_populates="sends")
    
    contact_id = Column(Integer, ForeignKey("crm_contacts.id"), nullable=False, index=True)
    contact = relationship("models.crm.Contact")
    
    # Send details
    recipient_email = Column(String(255), nullable=False, index=True)
    personalized_subject = Column(String(255))
    personalized_body = Column(Text)
    tracking_id = Column(String(64), unique=True, index=True)  # UUID for tracking
    
    # Status
    status = Column(Enum(EmailStatus), default=EmailStatus.PENDING, index=True)
    
    # Events
    sent_at = Column(DateTime, nullable=True)
    opened_at = Column(DateTime, nullable=True)
    opened_count = Column(Integer, default=0)
    clicked_at = Column(DateTime, nullable=True)
    clicked_count = Column(Integer, default=0)
    bounced_at = Column(DateTime, nullable=True)
    
    # Retry logic
    attempt_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    next_retry_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class CampaignTrack(Base):
    """Campaign open/click tracking"""
    __tablename__ = "campaign_tracks"
    
    id = Column(Integer, primary_key=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=False, index=True)
    campaign = relationship("models.campaigns.Campaign", back_populates="tracks")
    
    send_id = Column(Integer, ForeignKey("campaign_sends.id"), nullable=False, index=True)
    send = relationship("CampaignSend")
    
    # Track details
    tracking_id = Column(String(64), nullable=False, index=True)
    event_type = Column(String(20), nullable=False)  # open, click, bounce
    
    # Event details
    user_agent = Column(String(512))
    ip_address = Column(String(45))
    referer = Column(String(512))
    link_url = Column(String(512))  # For clicks
    
    # Timestamp
    tracked_at = Column(DateTime, default=datetime.utcnow, index=True)
