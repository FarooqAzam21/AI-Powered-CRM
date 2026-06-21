"""
Email Tasks - Async processing for email operations
Runs in Celery worker queue
"""
from tasks.celery_app import celery_app
from database import SessionLocal
from auth.models import User, Email, Contact, Activity
from services.ai_service import ai_service
import logging
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)

# =================== EMAIL TASKS ===================

@celery_app.task(bind=True, name="tasks.email_tasks.sync_gmail_emails")
def sync_gmail_emails(self, user_id: int = None):
    """
    Sync Gmail emails for user(s)
    Can run for specific user or all users
    Returns: {synced_count, classified_count, drafted_count}
    """
    try:
        db = SessionLocal()
        
        # Get users to sync
        if user_id:
            users = db.query(User).filter(User.id == user_id).all()
        else:
            users = db.query(User).filter(User.gmail_connected == True).all()
        
        total_synced = 0
        total_classified = 0
        total_drafted = 0
        
        for user in users:
            logger.info(f"📧 Syncing emails for {user.email}")
            from crm_email.incremental_sync import sync_metadata_page
            from config.settings import get_settings

            result = sync_metadata_page(db, user, page_size=get_settings().gmail_page_size)
            total_synced += result.get("synced", 0)
        
        db.close()
        
        logger.info(f"✅ Email sync complete: {total_synced} synced, {total_classified} classified")
        return {
            "synced_count": total_synced,
            "classified_count": total_classified,
            "drafted_count": total_drafted,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Email sync failed: {e}")
        raise

@celery_app.task(bind=True, name="tasks.email_tasks.classify_email")
def classify_email(self, email_id: int):
    """
    Classify a single email using AI
    Updates email record with category, confidence, action
    """
    try:
        db = SessionLocal()
        email = db.query(Email).filter(Email.id == email_id).first()
        
        if not email:
            logger.warning(f"⚠️  Email {email_id} not found")
            return {"error": "Email not found"}
        
        logger.info(f"🤖 Classifying email: {email.subject[:50]}")
        
        # Run async AI classification
        loop = asyncio.get_event_loop()
        classification = loop.run_until_complete(
            ai_service.classify_email(email.subject, email.body)
        )
        
        # Update email with classification
        email.category = classification.get("category", "general")
        email.confidence = classification.get("confidence", 0.5)
        email.action = classification.get("action", "draft_response")
        
        db.commit()
        
        logger.info(f"✅ Email classified: {email.category}")
        return {
            "email_id": email_id,
            "category": email.category,
            "confidence": email.confidence,
            "action": email.action
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Classification failed: {e}")
        raise
    finally:
        db.close()

@celery_app.task(bind=True, name="tasks.email_tasks.generate_reply")
def generate_reply(self, email_id: int, tone: str = "professional"):
    """
    Generate AI draft reply for email
    Creates draft without sending
    """
    try:
        db = SessionLocal()
        email = db.query(Email).filter(Email.id == email_id).first()
        
        if not email:
            return {"error": "Email not found"}
        
        logger.info(f"✍️  Generating reply for: {email.subject[:50]}")
        
        # Generate reply
        loop = asyncio.get_event_loop()
        draft_reply = loop.run_until_complete(
            ai_service.generate_reply(
                email_body=email.body,
                category=email.category or "general",
                tone=tone
            )
        )
        
        # Store draft
        email.draft_reply = draft_reply
        db.commit()
        
        logger.info(f"✅ Draft reply generated ({len(draft_reply)} chars)")
        return {
            "email_id": email_id,
            "draft_length": len(draft_reply),
            "preview": draft_reply[:100] + "..."
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Reply generation failed: {e}")
        raise
    finally:
        db.close()

@celery_app.task(bind=True, name="tasks.email_tasks.link_email_to_contact")
def link_email_to_contact(self, email_id: int):
    """
    Link email to existing contact or create new contact
    """
    try:
        db = SessionLocal()
        email = db.query(Email).filter(Email.id == email_id).first()
        
        if not email or email.contact_id:
            return {"already_linked": True}
        
        logger.info(f"🔗 Linking email to contact: {email.sender}")
        
        # Extract sender info
        sender_email = email.sender.split('<')[-1].rstrip('>')
        sender_name = email.sender.split('<')[0].strip() if '<' in email.sender else sender_email.split('@')[0]
        
        # Get or create contact
        contact = db.query(Contact).filter(
            Contact.user_id == email.user_id,
            Contact.email == sender_email.lower()
        ).first()
        
        if not contact:
            contact = Contact(
                user_id=email.user_id,
                email=sender_email.lower(),
                name=sender_name,
                is_active=True
            )
            db.add(contact)
            db.flush()
        
        # Link email to contact
        email.contact_id = contact.id
        
        # Create activity record
        activity = Activity(
            user_id=email.user_id,
            contact_id=contact.id,
            type="email_received",
            subject=email.subject,
            direction="inbound"
        )
        db.add(activity)
        
        # Update contact interaction count
        contact.last_interaction_at = email.received_at
        contact.interaction_count = (contact.interaction_count or 0) + 1
        
        db.commit()
        
        logger.info(f"✅ Email linked to contact: {contact.email}")
        return {
            "email_id": email_id,
            "contact_id": contact.id,
            "contact_email": contact.email
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Contact linking failed: {e}")
        raise
    finally:
        db.close()
