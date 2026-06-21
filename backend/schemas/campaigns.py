"""
Campaign Schemas - Phase 9
Pydantic models for campaign API
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class CampaignStatus(str, Enum):
    """Campaign status"""
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"

class EmailStatus(str, Enum):
    """Email status"""
    PENDING = "pending"
    SENT = "sent"
    OPENED = "opened"
    CLICKED = "clicked"
    BOUNCED = "bounced"
    FAILED = "failed"
    RETRYING = "retrying"

# =================== CREATE / UPDATE ===================

class CampaignCreate(BaseModel):
    """Create campaign"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    subject: str = Field(..., min_length=5, max_length=255)
    template: str = Field(..., min_length=10)
    from_name: Optional[str] = None
    reply_to: Optional[str] = None
    variables: Dict[str, str] = Field(default_factory=dict)  # {"first_name": "Contact.first_name"}
    throttle_per_minute: int = Field(default=2, ge=1, le=60)
    contact_group_ids: List[int] = Field(default_factory=list)
    segment_criteria: Dict[str, Any] = Field(default_factory=dict)
    open_tracking_enabled: bool = True
    click_tracking_enabled: bool = True
    scheduled_at: Optional[datetime] = None
    
    @validator('template')
    def validate_template(cls, v):
        """Validate template has variables or content"""
        if '{{' not in v and len(v) < 50:
            raise ValueError('Template must have variables or sufficient content')
        return v

class CampaignUpdate(BaseModel):
    """Update campaign"""
    name: Optional[str] = None
    description: Optional[str] = None
    subject: Optional[str] = None
    template: Optional[str] = None
    from_name: Optional[str] = None
    reply_to: Optional[str] = None
    variables: Optional[Dict[str, str]] = None
    throttle_per_minute: Optional[int] = None
    contact_group_ids: Optional[List[int]] = None
    segment_criteria: Optional[Dict[str, Any]] = None
    scheduled_at: Optional[datetime] = None

class CampaignStart(BaseModel):
    """Start campaign sending"""
    scheduled_at: Optional[datetime] = None

# =================== RESPONSES ===================

class CampaignAnalytics(BaseModel):
    """Campaign analytics snapshot"""
    sent_count: int
    opened_count: int
    clicked_count: int
    bounced_count: int
    failed_count: int
    open_rate: float
    click_rate: float
    bounce_rate: float
    unsubscribe_count: int
    
    class Config:
        from_attributes = True

class CampaignResponse(BaseModel):
    """Campaign response"""
    id: int
    user_id: int
    name: str
    description: Optional[str]
    subject: str
    status: CampaignStatus
    scheduled_at: Optional[datetime]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    throttle_per_minute: int
    recipient_count: int
    open_tracking_enabled: bool
    click_tracking_enabled: bool
    analytics: CampaignAnalytics
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class CampaignListResponse(BaseModel):
    """Campaign list response"""
    id: int
    name: str
    subject: str
    status: CampaignStatus
    recipient_count: int
    sent_count: int
    open_rate: float
    click_rate: float
    created_at: datetime
    
    class Config:
        from_attributes = True

# =================== SEND TRACKING ===================

class CampaignSendResponse(BaseModel):
    """Individual send response"""
    id: int
    campaign_id: int
    contact_id: int
    recipient_email: str
    status: EmailStatus
    sent_at: Optional[datetime]
    opened_at: Optional[datetime]
    opened_count: int
    clicked_at: Optional[datetime]
    clicked_count: int
    attempt_count: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class CampaignSendBatch(BaseModel):
    """Send batch results"""
    total: int
    sent: int
    pending: int
    failed: int
    failed_emails: List[Dict[str, Any]]

# =================== BULK OPERATIONS ===================

class BulkSendRequest(BaseModel):
    """Bulk send request"""
    campaign_id: int
    contact_ids: Optional[List[int]] = None  # Specific contacts
    segment_criteria: Optional[Dict[str, Any]] = None  # Or by segment
    start_immediately: bool = True
    scheduled_at: Optional[datetime] = None

class BulkRetryRequest(BaseModel):
    """Retry failed sends"""
    campaign_id: int
    max_retries: int = Field(default=3, le=5)
    retry_interval_minutes: int = Field(default=30, ge=5)
