"""
Contact Management Service — uses canonical crm_contacts table.
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from datetime import datetime
from typing import List, Optional, Dict, Any
import logging

from models.crm import Contact, Interaction

logger = logging.getLogger(__name__)


class ContactService:
    """Service layer for contact management"""

    @staticmethod
    def get_or_create_contact(
        db: Session,
        user_id: int,
        email: str,
        name: Optional[str] = None,
        company: Optional[str] = None,
        workspace_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        try:
            existing = (
                db.query(Contact)
                .filter(
                    and_(
                        Contact.user_id == user_id,
                        Contact.workspace_id == workspace_id,
                        Contact.email == email.lower(),
                    )
                )
                .first()
            )
            if existing:
                return {
                    "id": existing.id,
                    "email": existing.email,
                    "name": existing.name,
                    "company": existing.company,
                    "is_new": False,
                }
            new_contact = Contact(
                user_id=user_id,
                workspace_id=workspace_id,
                email=email.lower(),
                name=name or email.split("@")[0],
                company=company or "",
                source="manual",
            )
            db.add(new_contact)
            db.commit()
            db.refresh(new_contact)
            return {
                "id": new_contact.id,
                "email": new_contact.email,
                "name": new_contact.name,
                "company": new_contact.company,
                "is_new": True,
            }
        except Exception as e:
            db.rollback()
            logger.error("Error creating contact: %s", e)
            raise

    @staticmethod
    def get_contact_by_email(db: Session, user_id: int, email: str, workspace_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        try:
            contact = (
                db.query(Contact)
                .filter(and_(Contact.user_id == user_id, Contact.workspace_id == workspace_id, Contact.email == email.lower()))
                .first()
            )
            if not contact:
                return None
            interaction_count = db.query(Interaction).filter(Interaction.contact_id == contact.id).count()
            return {
                "id": contact.id,
                "email": contact.email,
                "name": contact.name,
                "company": contact.company,
                "last_interaction": contact.last_interaction_at,
                "interaction_count": interaction_count,
                "score": contact.relationship_score,
            }
        except Exception as e:
            logger.error("Error fetching contact: %s", e)
            return None

    @staticmethod
    def update_contact_interaction(db: Session, contact_id: int, interaction_type: str = "email", workspace_id: Optional[int] = None) -> bool:
        try:
            contact = db.query(Contact).filter(Contact.id == contact_id, Contact.workspace_id == workspace_id).first()
            if not contact:
                return False
            contact.last_interaction_at = datetime.utcnow()
            db.add(
                Interaction(
                    user_id=contact.user_id,
                    contact_id=contact.id,
                    channel=interaction_type,
                    direction="inbound",
                    occurred_at=datetime.utcnow(),
                )
            )
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            logger.error("Error updating interaction: %s", e)
            return False

    @staticmethod
    def list_contacts(
        db: Session,
        user_id: int,
        workspace_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 20,
        search: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        try:
            query = db.query(Contact).filter(Contact.user_id == user_id, Contact.workspace_id == workspace_id)
            if search:
                query = query.filter(
                    or_(
                        Contact.email.ilike(f"%{search}%"),
                        Contact.name.ilike(f"%{search}%"),
                        Contact.company.ilike(f"%{search}%"),
                    )
                )
            contacts = query.order_by(Contact.last_interaction_at.desc().nullslast()).offset(skip).limit(limit).all()
            results = []
            for c in contacts:
                interaction_count = db.query(Interaction).filter(Interaction.contact_id == c.id).count()
                results.append(
                    {
                        "id": c.id,
                        "email": c.email,
                        "name": c.name,
                        "company": c.company,
                        "score": c.relationship_score,
                        "last_interaction": c.last_interaction_at,
                        "interaction_count": interaction_count,
                    }
                )
            return results
        except Exception as e:
            logger.error("Error listing contacts: %s", e)
            return []
