"""
Contacts API Routes
CRUD operations for contacts + contact intelligence
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from sqlalchemy.orm import Session
from datetime import datetime
import logging
from services.webhook_service import trigger_webhook_event

from database import SessionLocal
from auth.dependencies import (
    require_viewer,
    require_security_analyst,
    require_workspace_admin,
    AuthContext
)
from auth.models import User
from models.crm import Contact, Lead, Activity, Interaction, EmailMetadata, CustomerProfile
from services.contact_service import ContactService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/contacts", tags=["Contacts"])

# =================== PYDANTIC MODELS ===================
class ContactCreate(BaseModel):
    email: EmailStr
    name: Optional[str] = None
    company: Optional[str] = None
    title: Optional[str] = None
    phone: Optional[str] = None

class ContactUpdate(BaseModel):
    name: Optional[str] = None
    company: Optional[str] = None
    title: Optional[str] = None
    phone: Optional[str] = None
    tags: Optional[List[str]] = None

class ContactResponse(BaseModel):
    id: int
    email: str
    name: Optional[str]
    company: Optional[str] = None
    score: float = 0.0
    last_interaction_at: Optional[datetime] = None
    interaction_count: int

class ContactDetailResponse(ContactResponse):
    title: Optional[str]
    phone: Optional[str]
    is_prospect: bool
    tags: List[str]
    created_at: datetime
    updated_at: datetime

# =================== ROUTES ===================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("", response_model=List[ContactResponse])
async def list_contacts(
    current_user: AuthContext = Depends(require_viewer),
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = None
):
    """List all contacts for user"""
    try:
        user = current_user.user
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        contacts = ContactService.list_contacts(
            db=db,
            user_id=user.id,
            workspace_id=current_user.workspace_id,
            skip=skip,
            limit=limit,
            search=search
        )
        return contacts
    except Exception as e:
        logger.error(f"❌ Error listing contacts: {e}")
        raise HTTPException(status_code=500, detail="Error listing contacts")

@router.get("/{contact_id}", response_model=ContactDetailResponse)
async def get_contact(
    contact_id: int,
    current_user: AuthContext = Depends(require_viewer),
    db: Session = Depends(get_db)
):
    """Get specific contact details"""
    try:
        user = current_user.user
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        contact = db.query(Contact).filter(
            Contact.id == contact_id,
            Contact.user_id == user.id,
            Contact.workspace_id == current_user.workspace_id
        ).first()
        
        if not contact:
            raise HTTPException(status_code=404, detail="Contact not found")
        
        return ContactDetailResponse(
            id=contact.id,
            email=contact.email,
            name=contact.name,
            company=contact.company,
            score=getattr(contact, "score", 0.0),
            last_interaction_at=contact.last_interaction_at,
            interaction_count=contact.interaction_count or 0,
            title=contact.title,
            phone=contact.phone,
            is_prospect=contact.is_prospect,
            tags=contact.tags or [],
            created_at=contact.created_at,
            updated_at=contact.updated_at
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting contact: {e}")
        raise HTTPException(status_code=500, detail="Error fetching contact")

@router.post("", response_model=ContactResponse)
async def create_contact(
    data: ContactCreate,
    current_user: AuthContext = Depends(require_security_analyst),
    db: Session = Depends(get_db)
):
    """Create new contact"""
    try:
        user = current_user.user
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        result = ContactService.get_or_create_contact(
            db=db,
            user_id=user.id,
            email=data.email,
            name=data.name,
            company=data.company,
            workspace_id=current_user.workspace_id
        )
        
        if not result["is_new"]:
            raise HTTPException(status_code=409, detail="Contact already exists")
        
        contact = db.query(Contact).filter(Contact.id == result["id"]).first()
        response = ContactResponse(
            id=contact.id,
            email=contact.email,
            name=contact.name,
            company=contact.company,
            score=getattr(contact, "score", 0.0),
            last_interaction_at=contact.last_interaction_at,
            interaction_count=contact.interaction_count or 0
        )
        # Fire webhook event for external integrations
        if user.workspace_id:
            trigger_webhook_event(db, user.workspace_id, "contact.created", {
                "id": contact.id, "email": contact.email,
                "name": contact.name, "company": contact.company
            })
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error creating contact: {e}")
        raise HTTPException(status_code=500, detail="Error creating contact")

@router.put("/{contact_id}", response_model=ContactResponse)
async def update_contact(
    contact_id: int,
    data: ContactUpdate,
    current_user: AuthContext = Depends(require_security_analyst),
    db: Session = Depends(get_db)
):
    """Update contact"""
    try:
        user = current_user.user
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        contact = db.query(Contact).filter(
            Contact.id == contact_id,
            Contact.user_id == user.id,
            Contact.workspace_id == current_user.workspace_id
        ).first()
        
        if not contact:
            raise HTTPException(status_code=404, detail="Contact not found")
        
        # Update fields
        if data.name:
            contact.name = data.name
        if data.company:
            contact.company = data.company
        if data.title:
            contact.title = data.title
        if data.phone:
            contact.phone = data.phone
        if data.tags is not None:
            contact.tags = data.tags
        
        contact.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(contact)
        
        # Fire webhook event for external integrations
        if user.workspace_id:
            trigger_webhook_event(db, user.workspace_id, "contact.updated", {
                "id": contact.id, "email": contact.email,
                "name": contact.name, "company": contact.company
            })
        logger.info(f"✅ Contact updated: {contact.email}")
        
        return ContactResponse(
            id=contact.id,
            email=contact.email,
            name=contact.name,
            company=contact.company,
            score=getattr(contact, "score", 0.0),
            last_interaction_at=contact.last_interaction_at,
            interaction_count=contact.interaction_count or 0
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error updating contact: {e}")
        raise HTTPException(status_code=500, detail="Error updating contact")

@router.delete("/{contact_id}")
async def delete_contact(
    contact_id: int,
    current_user: AuthContext = Depends(require_workspace_admin),
    db: Session = Depends(get_db)
):
    """Delete contact"""
    try:
        user = current_user.user
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        contact = db.query(Contact).filter(
            Contact.id == contact_id,
            Contact.user_id == user.id,
            Contact.workspace_id == current_user.workspace_id
        ).first()
        
        if not contact:
            raise HTTPException(status_code=404, detail="Contact not found")
        
        db.delete(contact)
        db.commit()
        
        logger.info(f"✅ Contact deleted: {contact.email}")
        
        return {"message": "Contact deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error deleting contact: {e}")
        raise HTTPException(status_code=500, detail="Error deleting contact")

@router.get("/{contact_id}/interactions")
async def get_contact_interactions(
    contact_id: int,
    current_user: AuthContext = Depends(require_viewer),
    db: Session = Depends(get_db),
    skip: int = Query(0),
    limit: int = Query(10)
):
    """Get interaction history for contact"""
    try:
        user = current_user.user
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        contact = db.query(Contact).filter(
            Contact.id == contact_id,
            Contact.user_id == user.id,
            Contact.workspace_id == current_user.workspace_id
        ).first()
        
        if not contact:
            raise HTTPException(status_code=404, detail="Contact not found")
        
        from models.crm import Activity
        activities = db.query(Activity).filter(
            Activity.contact_id == contact_id
        ).order_by(Activity.created_at.desc()).offset(skip).limit(limit).all()
        
        return [
            {
                "id": a.id,
                "type": a.type,
                "subject": a.subject,
                "description": a.description,
                "created_at": a.created_at
            }
            for a in activities
        ]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting interactions: {e}")
        raise HTTPException(status_code=500, detail="Error fetching interactions")
