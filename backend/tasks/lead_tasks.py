"""
Lead Tasks - Async lead scoring and follow-up automation
"""
from tasks.celery_app import celery_app
from database import SessionLocal
from auth.models import Lead, Contact, Activity
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

@celery_app.task(bind=True, name="tasks.lead_tasks.score_lead")
def score_lead(self, lead_id: int):
    """
    Calculate lead quality score based on:
    - Interaction frequency
    - Email response time
    - AI-detected intent
    - Company info
    """
    try:
        db = SessionLocal()
        lead = db.query(Lead).filter(Lead.id == lead_id).first()
        
        if not lead:
            return {"error": "Lead not found"}
        
        logger.info(f"📊 Scoring lead: {lead.contact.email if lead.contact else 'unknown'}")
        
        score = 0.0
        
        # Base score for being a lead
        score += 10
        
        # Interaction frequency (max 30 points)
        if lead.contact:
            interaction_count = lead.contact.interaction_count or 0
            score += min(interaction_count * 5, 30)
        
        # Intent detection (max 30 points)
        if lead.intent_detected == "buying":
            score += 30
        elif lead.intent_detected == "hiring":
            score += 25
        elif lead.intent_detected == "support":
            score += 15
        
        # Response time (max 20 points)
        if lead.last_contacted_at:
            hours_since = (datetime.utcnow() - lead.last_contacted_at).total_seconds() / 3600
            if hours_since < 24:
                score += 20
            elif hours_since < 72:
                score += 15
            elif hours_since < 168:
                score += 10
        
        # Lead status (max 10 points)
        if lead.status == "qualified":
            score += 10
        elif lead.status == "nurturing":
            score += 5
        
        # Determine temperature
        if score >= 70:
            lead.temperature = "hot"
        elif score >= 40:
            lead.temperature = "warm"
        else:
            lead.temperature = "cold"
        
        lead.score = score
        db.commit()
        
        logger.info(f"✅ Lead scored: {score:.1f} ({lead.temperature})")
        return {
            "lead_id": lead_id,
            "score": score,
            "temperature": lead.temperature
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Lead scoring failed: {e}")
        raise
    finally:
        db.close()

@celery_app.task(bind=True, name="tasks.lead_tasks.check_follow_ups")
def check_follow_ups(self):
    """
    Check for leads that need follow-up
    Scheduled to run every hour
    """
    try:
        db = SessionLocal()
        
        # Find leads with overdue follow-ups
        now = datetime.utcnow()
        overdue_leads = db.query(Lead).filter(
            Lead.next_follow_up_at <= now,
            Lead.status.in_(["new", "nurturing"])
        ).all()
        
        logger.info(f"⏰ Found {len(overdue_leads)} leads needing follow-up")
        
        follow_up_tasks = []
        
        for lead in overdue_leads:
            logger.info(f"📧 Scheduling follow-up for: {lead.contact.email if lead.contact else 'unknown'}")
            
            # Schedule follow-up email task
            from tasks.campaign_tasks import send_follow_up_email
            task = send_follow_up_email.delay(lead.id)
            follow_up_tasks.append(task.id)
            
            # Update next follow-up date (3 days from now)
            lead.next_follow_up_at = now + timedelta(days=3)
            lead.follow_up_count = (lead.follow_up_count or 0) + 1
        
        db.commit()
        db.close()
        
        logger.info(f"✅ Scheduled {len(follow_up_tasks)} follow-up tasks")
        return {
            "checked_count": len(overdue_leads),
            "scheduled_tasks": follow_up_tasks
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Follow-up check failed: {e}")
        raise

@celery_app.task(bind=True, name="tasks.lead_tasks.convert_lead")
def convert_lead(self, lead_id: int):
    """
    Mark lead as converted (customer)
    """
    try:
        db = SessionLocal()
        lead = db.query(Lead).filter(Lead.id == lead_id).first()
        
        if not lead:
            return {"error": "Lead not found"}
        
        logger.info(f"🎉 Converting lead: {lead.contact.email if lead.contact else 'unknown'}")
        
        lead.status = "converted"
        lead.temperature = "hot"
        
        # Create activity record
        activity = Activity(
            user_id=lead.user_id,
            contact_id=lead.contact_id,
            type="lead_converted",
            subject="Lead converted to customer",
            status="completed"
        )
        db.add(activity)
        
        db.commit()
        
        logger.info(f"✅ Lead converted successfully")
        return {
            "lead_id": lead_id,
            "status": "converted"
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Lead conversion failed: {e}")
        raise
    finally:
        db.close()

@celery_app.task(bind=True, name="tasks.lead_tasks.mark_lost")
def mark_lost(self, lead_id: int, reason: str = ""):
    """
    Mark lead as lost with optional reason
    """
    try:
        db = SessionLocal()
        lead = db.query(Lead).filter(Lead.id == lead_id).first()
        
        if not lead:
            return {"error": "Lead not found"}
        
        logger.info(f"❌ Marking lead as lost: {lead.contact.email if lead.contact else 'unknown'}")
        
        lead.status = "lost"
        lead.temperature = "cold"
        
        # Create activity record
        activity = Activity(
            user_id=lead.user_id,
            contact_id=lead.contact_id,
            type="lead_lost",
            description=reason or "Lead marked as lost",
            status="completed"
        )
        db.add(activity)
        
        db.commit()
        
        logger.info(f"✅ Lead marked as lost")
        return {
            "lead_id": lead_id,
            "status": "lost",
            "reason": reason
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Failed to mark lead as lost: {e}")
        raise
    finally:
        db.close()
