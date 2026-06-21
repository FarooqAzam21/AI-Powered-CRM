"""
Campaign Tasks - Phase 9
Bulk email sending with throttling, personalization, and tracking
"""
import logging
from celery import shared_task
from sqlalchemy.orm import Session
from database import SessionLocal
from datetime import datetime, timedelta

from models.campaigns import CampaignSend, EmailStatus, Campaign
from services.campaign_service import CampaignService

logger = logging.getLogger(__name__)


def _scheduler():
    from scheduler.campaign_scheduler import scheduler
    return scheduler

# =================== SEND TASKS ===================

@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def send_campaign_email(self, send_id: int):
    """
    Send individual campaign email with retry logic.
    Retries up to 3 times with 5-minute delay.
    """
    db = SessionLocal()
    try:
        send = db.query(CampaignSend).filter(CampaignSend.id == send_id).first()
        if not send:
            logger.warning(f"⚠️ Send {send_id} not found")
            return {"status": "error", "message": "Send not found"}
        
        campaign = send.campaign
        
        # Check campaign is still running
        if campaign.status.value not in ["running", "scheduled"]:
            logger.warning(f"⚠️ Campaign {campaign.id} not running, skipping send {send_id}")
            return {"status": "error", "message": "Campaign not running"}
        
        logger.info(f"📧 Sending email to {send.recipient_email}")
        
        # Simulate email send (in production, use Gmail API)
        # from services.email_service import EmailService
        # email_service = EmailService()
        # result = email_service.send_email(...)
        
        # For now, mark as sent
        CampaignService.mark_sent(db, send_id)
        logger.info(f"✅ Email sent: {send_id} to {send.recipient_email}")
        
        # Schedule next batch
        _scheduler().schedule_next_batch(campaign.id)
        
        return {"status": "success", "message": f"Email sent to {send.recipient_email}"}
    
    except Exception as e:
        logger.error(f"❌ Send task failed: {e}")
        
        # Mark as failed with retry
        try:
            send = db.query(CampaignSend).filter(CampaignSend.id == send_id).first()
            if send:
                CampaignService.mark_failed(db, send_id, str(e), retry=True)
        except:
            pass
        
        # Retry the task
        try:
            raise self.retry(exc=e)
        except self.MaxRetriesExceededError:
            logger.error(f"❌ Max retries exceeded for send {send_id}")
            return {"status": "failed", "message": "Max retries exceeded"}
    finally:
        db.close()

@shared_task
def bulk_send_campaign(campaign_id: int):
    """
    Start bulk sending for campaign.
    Entry point for starting a campaign.
    """
    db = SessionLocal()
    try:
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if not campaign:
            logger.warning(f"⚠️ Campaign {campaign_id} not found")
            return
        
        logger.info(f"🚀 Starting bulk send for campaign: {campaign.name}")
        
        # Prepare all emails
        CampaignService.prepare_bulk_send(db, campaign_id)
        
        # Start scheduling sends
        _scheduler().schedule_next_batch(campaign_id, batch_size=5)
        
        return {"status": "started", "campaign_id": campaign_id}
    except Exception as e:
        logger.error(f"❌ Bulk send failed: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        db.close()

# =================== RETRY TASKS ===================

@shared_task
def retry_failed_sends(campaign_id: int = None, max_age_hours: int = 24):
    """
    Retry sends that failed recently and are still within retry window.
    """
    db = SessionLocal()
    try:
        logger.info("🔄 Processing retry sends")
        
        count = _scheduler().handle_retry_sends(campaign_id)
        
        logger.info(f"✅ Scheduled {count} retries")
        return {"status": "success", "retried_count": count}
    except Exception as e:
        logger.error(f"❌ Retry processing failed: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        db.close()

# =================== TRACKING TASKS ===================

@shared_task
def process_open_tracking(tracking_id: str, user_agent: str = None, ip_address: str = None):
    """Process email open event"""
    db = SessionLocal()
    try:
        CampaignService.track_open(db, tracking_id, user_agent, ip_address)
        return {"status": "success", "event": "open"}
    except Exception as e:
        logger.error(f"❌ Open tracking failed: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        db.close()

@shared_task
def process_click_tracking(tracking_id: str, link_url: str = None, 
                          user_agent: str = None, ip_address: str = None):
    """Process email click event"""
    db = SessionLocal()
    try:
        CampaignService.track_click(db, tracking_id, link_url, user_agent, ip_address)
        return {"status": "success", "event": "click"}
    except Exception as e:
        logger.error(f"❌ Click tracking failed: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        db.close()

# =================== ANALYTICS TASKS ===================

@shared_task
def update_campaign_analytics(campaign_id: int):
    """Update campaign analytics"""
    db = SessionLocal()
    try:
        analytics = CampaignService.get_campaign_analytics(db, campaign_id)
        logger.info(f"📊 Analytics updated for campaign {campaign_id}")
        return {"status": "success", "analytics": analytics}
    except Exception as e:
        logger.error(f"❌ Analytics update failed: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        db.close()

@shared_task
def periodic_campaign_monitor():
    """
    Periodic task to monitor campaign progress.
    Runs every 5 minutes to check for stuck campaigns or needed retries.
    """
    db = SessionLocal()
    try:
        from models.campaigns import CampaignStatus
        
        # Get running campaigns
        running = db.query(Campaign).filter(
            Campaign.status == CampaignStatus.RUNNING
        ).all()
        
        for campaign in running:
            progress = _scheduler().get_campaign_progress(campaign.id)
            
            # Check if all sends are complete
            if progress.get("pending", 0) == 0:
                campaign.status = CampaignStatus.COMPLETED
                campaign.completed_at = datetime.utcnow()
                logger.info(f"✅ Campaign {campaign.name} marked complete")
            
            db.commit()
        
        # Process any pending retries
        retry_count = _scheduler().handle_retry_sends()
        
        logger.info(f"📊 Campaign monitor: {len(running)} running, {retry_count} retries processed")
        return {"status": "success", "running_campaigns": len(running), "retries": retry_count}
    except Exception as e:
        logger.error(f"❌ Campaign monitor failed: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        db.close()
