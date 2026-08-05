import secrets
import hashlib
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import or_

from database import get_db
from auth.dependencies import require_workspace_admin, AuthContext
from auth.models import APIKey, WebhookSubscription, WebhookDelivery, AuditLog, User

router = APIRouter(prefix="/api/v1/developer", tags=["Developer Platform"])

# --- Pydantic Models ---
class APIKeyCreate(BaseModel):
    name: str
    permissions: List[str]
    rate_limit: int = 60
    daily_limit: int = 1000
    expires_in_days: Optional[int] = 30
    description: Optional[str] = None
    is_live: bool = True

class APIKeyUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None
    rate_limit: Optional[int] = None
    daily_limit: Optional[int] = None
    permissions: Optional[List[str]] = None
    description: Optional[str] = None

class APIKeyResponse(BaseModel):
    id: int
    name: str
    key_prefix: str
    status: str
    created_at: datetime
    expires_at: Optional[datetime]
    last_used_at: Optional[datetime]
    last_ip: Optional[str]
    permissions: List[str]
    rate_limit: int
    daily_limit: int
    description: Optional[str]

    class Config:
        from_attributes = True

class APIKeyCreateResponse(APIKeyResponse):
    plaintext_key: str

class WebhookSubscriptionCreate(BaseModel):
    url: str
    events: List[str]
    is_active: bool = True

class WebhookSubscriptionUpdate(BaseModel):
    url: Optional[str] = None
    events: Optional[List[str]] = None
    is_active: Optional[bool] = None

class WebhookSubscriptionResponse(BaseModel):
    id: int
    url: str
    events: List[str]
    is_active: bool
    created_at: datetime
    secret_key: str

    class Config:
        from_attributes = True

# --- API Keys Routes ---

@router.post("/keys", response_model=APIKeyCreateResponse)
def create_key(data: APIKeyCreate, auth: AuthContext = Depends(require_workspace_admin), db: Session = Depends(get_db)):
    prefix = "crm_live_" if data.is_live else "crm_test_"
    random_part = secrets.token_urlsafe(24)
    raw_key = f"{prefix}{random_part}"
    
    hashed = hashlib.sha256(raw_key.encode('utf-8')).hexdigest()
    key_prefix = raw_key[:12]
    
    expires_at = None
    if data.expires_in_days:
        expires_at = datetime.utcnow() + timedelta(days=data.expires_in_days)
        
    api_key = APIKey(
        workspace_id=auth.workspace_id,
        owner_id=auth.user.id if auth.user else None,
        key=None,
        hashed_key=hashed,
        key_prefix=key_prefix,
        name=data.name,
        is_active=True,
        status="active",
        expires_at=expires_at,
        permissions=data.permissions,
        rate_limit=data.rate_limit,
        daily_limit=data.daily_limit,
        description=data.description
    )
    
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    
    response = APIKeyCreateResponse.from_orm(api_key)
    response.plaintext_key = raw_key
    return response

@router.get("/keys", response_model=List[APIKeyResponse])
def list_keys(auth: AuthContext = Depends(require_workspace_admin), db: Session = Depends(get_db)):
    return db.query(APIKey).filter(APIKey.workspace_id == auth.workspace_id).order_by(APIKey.created_at.desc()).all()

@router.patch("/keys/{key_id}", response_model=APIKeyResponse)
def update_key(key_id: int, data: APIKeyUpdate, auth: AuthContext = Depends(require_workspace_admin), db: Session = Depends(get_db)):
    key = db.query(APIKey).filter(APIKey.id == key_id, APIKey.workspace_id == auth.workspace_id).first()
    if not key:
        raise HTTPException(404, "API Key not found")
        
    if data.name is not None:
        key.name = data.name
    if data.status is not None:
        if data.status in ["active", "revoked"]:
            key.status = data.status
            key.is_active = (data.status == "active")
    if data.rate_limit is not None:
        key.rate_limit = data.rate_limit
    if data.daily_limit is not None:
        key.daily_limit = data.daily_limit
    if data.permissions is not None:
        key.permissions = data.permissions
    if data.description is not None:
        key.description = data.description
        
    db.commit()
    db.refresh(key)
    return key

@router.post("/keys/{key_id}/rotate", response_model=APIKeyCreateResponse)
def rotate_key(key_id: int, auth: AuthContext = Depends(require_workspace_admin), db: Session = Depends(get_db)):
    key = db.query(APIKey).filter(APIKey.id == key_id, APIKey.workspace_id == auth.workspace_id).first()
    if not key:
        raise HTTPException(404, "API Key not found")
        
    key.status = "revoked"
    key.is_active = False
    
    prefix = "crm_live_" if key.key_prefix.startswith("crm_live") else "crm_test_"
    random_part = secrets.token_urlsafe(24)
    raw_key = f"{prefix}{random_part}"
    
    hashed = hashlib.sha256(raw_key.encode('utf-8')).hexdigest()
    key_prefix = raw_key[:12]
    
    expires_at = key.expires_at
    if expires_at and expires_at < datetime.utcnow():
        expires_at = datetime.utcnow() + timedelta(days=30)
        
    new_key = APIKey(
        workspace_id=auth.workspace_id,
        owner_id=auth.user.id if auth.user else None,
        key=None,
        hashed_key=hashed,
        key_prefix=key_prefix,
        name=f"{key.name} (Rotated)",
        is_active=True,
        status="active",
        expires_at=expires_at,
        permissions=key.permissions,
        rate_limit=key.rate_limit,
        daily_limit=key.daily_limit,
        description=key.description
    )
    
    db.add(new_key)
    db.commit()
    db.refresh(new_key)
    
    response = APIKeyCreateResponse.from_orm(new_key)
    response.plaintext_key = raw_key
    return response

@router.delete("/keys/{key_id}")
def delete_key(key_id: int, auth: AuthContext = Depends(require_workspace_admin), db: Session = Depends(get_db)):
    key = db.query(APIKey).filter(APIKey.id == key_id, APIKey.workspace_id == auth.workspace_id).first()
    if not key:
        raise HTTPException(404, "API Key not found")
    db.delete(key)
    db.commit()
    return {"status": "success", "message": "API Key revoked and deleted"}

# --- Webhook Subscription Routes ---

@router.post("/webhooks", response_model=WebhookSubscriptionResponse)
def create_webhook(data: WebhookSubscriptionCreate, auth: AuthContext = Depends(require_workspace_admin), db: Session = Depends(get_db)):
    secret = f"whsec_{secrets.token_hex(16)}"
    sub = WebhookSubscription(
        workspace_id=auth.workspace_id,
        url=str(data.url),
        secret_key=secret,
        events=data.events,
        is_active=data.is_active
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return sub

@router.get("/webhooks", response_model=List[WebhookSubscriptionResponse])
def list_webhooks(auth: AuthContext = Depends(require_workspace_admin), db: Session = Depends(get_db)):
    return db.query(WebhookSubscription).filter(WebhookSubscription.workspace_id == auth.workspace_id).all()

@router.patch("/webhooks/{webhook_id}", response_model=WebhookSubscriptionResponse)
def update_webhook(webhook_id: int, data: WebhookSubscriptionUpdate, auth: AuthContext = Depends(require_workspace_admin), db: Session = Depends(get_db)):
    sub = db.query(WebhookSubscription).filter(WebhookSubscription.id == webhook_id, WebhookSubscription.workspace_id == auth.workspace_id).first()
    if not sub:
        raise HTTPException(404, "Webhook subscription not found")
        
    if data.url is not None:
        sub.url = str(data.url)
    if data.events is not None:
        sub.events = data.events
    if data.is_active is not None:
        sub.is_active = data.is_active
        
    db.commit()
    db.refresh(sub)
    return sub

@router.delete("/webhooks/{webhook_id}")
def delete_webhook(webhook_id: int, auth: AuthContext = Depends(require_workspace_admin), db: Session = Depends(get_db)):
    sub = db.query(WebhookSubscription).filter(WebhookSubscription.id == webhook_id, WebhookSubscription.workspace_id == auth.workspace_id).first()
    if not sub:
        raise HTTPException(404, "Webhook subscription not found")
    
    # Delete child deliveries to avoid FK blockages
    db.query(WebhookDelivery).filter(WebhookDelivery.subscription_id == webhook_id).delete()
    db.delete(sub)
    db.commit()
    return {"status": "success", "message": "Webhook subscription deleted"}

@router.get("/webhooks/deliveries")
def list_deliveries(auth: AuthContext = Depends(require_workspace_admin), db: Session = Depends(get_db), limit: int = 50):
    return db.query(WebhookDelivery).filter(WebhookDelivery.workspace_id == auth.workspace_id).order_by(WebhookDelivery.created_at.desc()).limit(limit).all()

# --- Developer Logs & Usage Analytics ---

@router.get("/logs")
def list_developer_logs(auth: AuthContext = Depends(require_workspace_admin), db: Session = Depends(get_db), limit: int = 100):
    return db.query(AuditLog).filter(
        AuditLog.workspace_id == auth.workspace_id,
        AuditLog.action == "API_REQUEST"
    ).order_by(AuditLog.created_at.desc()).limit(limit).all()

@router.get("/usage")
def get_usage_analytics(auth: AuthContext = Depends(require_workspace_admin), db: Session = Depends(get_db)):
    keys_count = db.query(APIKey).filter(APIKey.workspace_id == auth.workspace_id).count()
    active_keys = db.query(APIKey).filter(APIKey.workspace_id == auth.workspace_id, APIKey.status == "active").count()
    
    requests = db.query(AuditLog).filter(
        AuditLog.workspace_id == auth.workspace_id,
        AuditLog.action == "API_REQUEST"
    ).all()
    
    total_requests = len(requests)
    success_requests = len([r for r in requests if r.status == "ALLOWED"])
    failed_requests = total_requests - success_requests
    
    paths = {}
    for r in requests:
        paths[r.resource] = paths.get(r.resource, 0) + 1
        
    return {
        "keys_count": keys_count,
        "active_keys": active_keys,
        "total_requests": total_requests,
        "success_requests": success_requests,
        "failed_requests": failed_requests,
        "endpoints_breakdown": paths,
    }
