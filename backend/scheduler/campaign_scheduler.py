"""
Campaign Scheduler Engine - Phase 9
Throttled bulk email scheduling (2 emails/minute)
"""
import logging
from datetime import datetime, timedelta
from typing import List, Dict
from sqlalchemy.orm import Session
from database import SessionLocal

from models.campaigns import Campaign, CampaignSend, CampaignStatus, EmailStatus
from services.campaign_service import CampaignService

logger = logging.getLogger(__name__)

class CampaignScheduler:
    """
    Campaign email scheduler with throttling.
    Respects per-campaign throttle settings (default 2 emails/minute).
    """
    
    def __init__(self):
        self.throttle_per_minute = 2  # Global default
        self.min_interval_ms = (60 / self.throttle_per_minute) * 1000  # 30 seconds between emails
        self.active_campaigns = {}  # Track last send per campaign

    def get_emails_per_interval(self, campaign_id: int) -> int:
        """
        Calculate how many emails should be sent in current interval.
        Default: 2 per minute = 1 every 30 seconds.
        """
        db = SessionLocal()
        try:
            campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
            if not campaign:
                return 1
            
            # Calculate based on campaign throttle setting
            return max(1, campaign.throttle_per_minute // 2)  # Conservative: send in 30-sec batches
        finally:
            db.close()

    def schedule_next_batch(self, campaign_id: int, batch_size: int = 2):
        """
        Schedule next batch of emails for sending.
        Uses Celery task with scheduled time based on throttle.
        """
        db = SessionLocal()
        try:
            campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
            if not campaign:
                logger.warning(f"⚠️ Campaign {campaign_id} not found")
                return 0
            
            # Get pending emails
            pending_sends = db.query(CampaignSend).filter(
                CampaignSend.campaign_id == campaign_id,
                CampaignSend.status == EmailStatus.PENDING
            ).order_by(CampaignSend.created_at).limit(batch_size).all()
            
            if not pending_sends:
                logger.info(f"ℹ️ No pending sends for campaign {campaign_id}")
                
                # Check if all sends are complete
                pending_count = db.query(CampaignSend).filter(
                    CampaignSend.campaign_id == campaign_id,
                    CampaignSend.status == EmailStatus.PENDING
                ).count()
                
                if pending_count == 0:
                    campaign.status = CampaignStatus.COMPLETED
                    campaign.completed_at = datetime.utcnow()
                    db.commit()
                    logger.info(f"✅ Campaign {campaign.name} completed")
                
                return 0
            
            logger.info(f"📧 Scheduling {len(pending_sends)} emails for campaign {campaign.name}")
            
            # Schedule each send with staggered timing
            for idx, send in enumerate(pending_sends):
                # Calculate delay: space out sends by 30 seconds (2 per minute)
                delay_seconds = idx * 30
                scheduled_time = datetime.utcnow() + timedelta(seconds=delay_seconds)
                
                # Queue the email send task
                from tasks.campaign_tasks import send_campaign_email

                send_campaign_email.apply_async(
                    args=[send.id],
                    countdown=delay_seconds,
                    expires=3600  # Expire if not sent within 1 hour
                )
                
                logger.debug(f"⏱️ Email {send.id} scheduled in {delay_seconds}s")
            
            # Update campaign status if just starting
            if campaign.status == CampaignStatus.SCHEDULED and campaign.started_at is None:
                campaign.status = CampaignStatus.RUNNING
                campaign.started_at = datetime.utcnow()
                db.commit()
                logger.info(f"🚀 Campaign {campaign.name} started")
            
            return len(pending_sends)
        except Exception as e:
            logger.error(f"❌ Scheduling failed: {e}")
            return 0
        finally:
            db.close()

    def handle_retry_sends(self, campaign_id: int = None):
        """
        Handle retrying failed sends with exponential backoff.
        """
        db = SessionLocal()
        try:
            query = db.query(CampaignSend).filter(
                CampaignSend.status == EmailStatus.RETRYING,
                CampaignSend.next_retry_at <= datetime.utcnow()
            )
            
            if campaign_id:
                query = query.filter(CampaignSend.campaign_id == campaign_id)
            
            retry_sends = query.all()
            
            if not retry_sends:
                logger.debug("ℹ️ No sends pending retry")
                return 0
            
            logger.info(f"🔄 Retrying {len(retry_sends)} sends")
            
            for idx, send in enumerate(retry_sends):
                delay_seconds = idx * 30  # Space out retries
                
                from tasks.campaign_tasks import send_campaign_email

                send_campaign_email.apply_async(
                    args=[send.id],
                    countdown=delay_seconds,
                    expires=3600
                )
            
            return len(retry_sends)
        except Exception as e:
            logger.error(f"❌ Retry handling failed: {e}")
            return 0
        finally:
            db.close()

    def get_campaign_progress(self, campaign_id: int) -> Dict:
        """Get campaign sending progress"""
        db = SessionLocal()
        try:
            stats = CampaignService.get_send_stats(db, campaign_id)
            campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
            
            if not campaign:
                return {}
            
            total = stats.get("total", 1)
            sent = stats.get("sent", 0)
            opened = stats.get("opened", 0)
            clicked = stats.get("clicked", 0)
            failed = stats.get("failed", 0)
            
            progress = {
                "campaign_id": campaign_id,
                "campaign_name": campaign.name,
                "status": campaign.status.value,
                "total": total,
                "sent": sent,
                "pending": stats.get("pending", 0),
                "opened": opened,
                "clicked": clicked,
                "bounced": stats.get("bounced", 0),
                "failed": failed,
                "progress_percent": round((sent / total * 100) if total > 0 else 0, 1),
                "open_rate": round((opened / sent * 100) if sent > 0 else 0, 1),
                "click_rate": round((clicked / sent * 100) if sent > 0 else 0, 1),
                "started_at": campaign.started_at,
                "completed_at": campaign.completed_at
            }
            
            return progress
        except Exception as e:
            logger.error(f"❌ Progress retrieval failed: {e}")
            return {}
        finally:
            db.close()

    def pause_campaign(self, campaign_id: int) -> bool:
        """Pause campaign sending"""
        db = SessionLocal()
        try:
            campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
            if not campaign:
                return False
            
            campaign.status = CampaignStatus.PAUSED
            db.commit()
            logger.info(f"⏸️ Campaign {campaign.name} paused")
            return True
        except Exception as e:
            logger.error(f"❌ Pause failed: {e}")
            return False
        finally:
            db.close()

    def resume_campaign(self, campaign_id: int) -> bool:
        """Resume campaign sending"""
        db = SessionLocal()
        try:
            campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
            if not campaign:
                return False
            
            campaign.status = CampaignStatus.RUNNING
            db.commit()
            
            # Reschedule remaining sends
            self.schedule_next_batch(campaign_id)
            
            logger.info(f"▶️ Campaign {campaign.name} resumed")
            return True
        except Exception as e:
            logger.error(f"❌ Resume failed: {e}")
            return False
        finally:
            db.close()

# Global scheduler instance
scheduler = CampaignScheduler()
