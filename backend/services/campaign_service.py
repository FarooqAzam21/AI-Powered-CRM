"""
Campaign Service - Phase 9
Business logic for bulk email campaigns
"""
import logging
import uuid
import jinja2
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from models.campaigns import Campaign, CampaignSend, CampaignTrack, CampaignStatus, EmailStatus
from models.crm import Contact
from auth.models import User

logger = logging.getLogger(__name__)

class CampaignService:
    """Campaign management service"""
    
    @staticmethod
    def create_campaign(db: Session, user_id: int, campaign_data: Dict[str, Any]) -> Campaign:
        """Create new campaign"""
        try:
            campaign = Campaign(
                user_id=user_id,
                name=campaign_data.get("name"),
                description=campaign_data.get("description"),
                subject=campaign_data.get("subject"),
                template=campaign_data.get("template"),
                from_name=campaign_data.get("from_name"),
                reply_to=campaign_data.get("reply_to"),
                variables=campaign_data.get("variables", {}),
                throttle_per_minute=campaign_data.get("throttle_per_minute", 2),
                contact_group_ids=campaign_data.get("contact_group_ids", []),
                segment_criteria=campaign_data.get("segment_criteria", {}),
                open_tracking_enabled=campaign_data.get("open_tracking_enabled", True),
                click_tracking_enabled=campaign_data.get("click_tracking_enabled", True),
                scheduled_at=campaign_data.get("scheduled_at"),
                status=CampaignStatus.DRAFT
            )
            
            db.add(campaign)
            db.commit()
            db.refresh(campaign)
            
            logger.info(f"✅ Campaign created: {campaign.name} (ID: {campaign.id})")
            return campaign
        except Exception as e:
            logger.error(f"❌ Campaign creation failed: {e}")
            db.rollback()
            raise

    @staticmethod
    def personalize_email(template: str, variables: Dict[str, Any], contact: Contact) -> str:
        """Personalize email template with contact data"""
        try:
            # Map variables to contact attributes
            context = {}
            for var_name, attr_path in variables.items():
                # Parse attribute path like "Contact.first_name"
                if "." in attr_path:
                    _, attr = attr_path.split(".", 1)
                    context[var_name] = getattr(contact, attr, "")
                else:
                    context[var_name] = getattr(contact, attr_path, "")
            
            # Render template with Jinja2
            tmpl = jinja2.Template(template)
            return tmpl.render(**context)
        except Exception as e:
            logger.warning(f"⚠️ Personalization failed: {e}, using template as-is")
            return template

    @staticmethod
    def prepare_bulk_send(db: Session, campaign_id: int) -> List[CampaignSend]:
        """Prepare emails for sending"""
        try:
            campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
            if not campaign:
                raise ValueError(f"Campaign {campaign_id} not found")
            
            # Get recipient contacts
            query = db.query(Contact).filter(Contact.user_id == campaign.user_id)
            
            # Filter by specific contacts if provided
            if campaign.contact_group_ids:
                query = query.filter(Contact.id.in_(campaign.contact_group_ids))
            
            contacts = query.all()
            
            logger.info(f"📧 Preparing {len(contacts)} emails for campaign {campaign.name}")
            
            # Create send records
            sends = []
            for contact in contacts:
                tracking_id = str(uuid.uuid4())
                personalized_subject = CampaignService.personalize_email(
                    campaign.subject, 
                    campaign.variables, 
                    contact
                )
                personalized_body = CampaignService.personalize_email(
                    campaign.template, 
                    campaign.variables, 
                    contact
                )
                
                # Add tracking pixel if enabled
                if campaign.open_tracking_enabled:
                    tracking_pixel = f'<img src="/api/v1/campaigns/track/{{tracking_id}}/open" width="1" height="1" />'
                    personalized_body += tracking_pixel.replace("{tracking_id}", tracking_id)
                
                send = CampaignSend(
                    campaign_id=campaign_id,
                    contact_id=contact.id,
                    recipient_email=contact.email,
                    personalized_subject=personalized_subject,
                    personalized_body=personalized_body,
                    tracking_id=tracking_id,
                    status=EmailStatus.PENDING
                )
                sends.append(send)
            
            # Bulk insert
            db.bulk_save_objects(sends)
            db.commit()
            
            # Update campaign
            campaign.recipient_count = len(contacts)
            campaign.status = CampaignStatus.SCHEDULED
            db.commit()
            
            logger.info(f"✅ Created {len(sends)} send records")
            return sends
        except Exception as e:
            logger.error(f"❌ Bulk send preparation failed: {e}")
            db.rollback()
            raise

    @staticmethod
    def get_pending_sends(db: Session, limit: int = 10) -> List[CampaignSend]:
        """Get pending emails to send (respecting throttle)"""
        try:
            # Get pending sends ordered by created_at
            sends = db.query(CampaignSend).filter(
                CampaignSend.status == EmailStatus.PENDING
            ).order_by(CampaignSend.created_at).limit(limit).all()
            
            return sends
        except Exception as e:
            logger.error(f"❌ Failed to get pending sends: {e}")
            return []

    @staticmethod
    def mark_sent(db: Session, send_id: int):
        """Mark email as sent"""
        try:
            send = db.query(CampaignSend).filter(CampaignSend.id == send_id).first()
            if not send:
                return
            
            send.status = EmailStatus.SENT
            send.sent_at = datetime.utcnow()
            db.commit()
            
            # Update campaign metrics
            campaign = send.campaign
            campaign.sent_count += 1
            db.commit()
        except Exception as e:
            logger.error(f"❌ Mark sent failed: {e}")
            db.rollback()

    @staticmethod
    def mark_bounced(db: Session, send_id: int, error: str = None):
        """Mark email as bounced"""
        try:
            send = db.query(CampaignSend).filter(CampaignSend.id == send_id).first()
            if not send:
                return
            
            send.status = EmailStatus.BOUNCED
            send.bounced_at = datetime.utcnow()
            if error:
                send.error_message = error
            
            db.commit()
            
            # Update campaign metrics
            campaign = send.campaign
            campaign.bounced_count += 1
            db.commit()
        except Exception as e:
            logger.error(f"❌ Mark bounced failed: {e}")
            db.rollback()

    @staticmethod
    def mark_failed(db: Session, send_id: int, error: str = None, retry: bool = True):
        """Mark email as failed with retry logic"""
        try:
            send = db.query(CampaignSend).filter(CampaignSend.id == send_id).first()
            if not send:
                return
            
            send.attempt_count += 1
            send.error_message = error
            
            if send.attempt_count >= send.max_retries or not retry:
                send.status = EmailStatus.FAILED
                logger.warning(f"❌ Email {send.id} failed after {send.attempt_count} attempts")
            else:
                send.status = EmailStatus.RETRYING
                # Exponential backoff: 30min, 1h, 2h
                delay_minutes = 30 * (2 ** (send.attempt_count - 1))
                send.next_retry_at = datetime.utcnow() + timedelta(minutes=delay_minutes)
                logger.info(f"🔄 Retrying email {send.id} in {delay_minutes} minutes")
            
            db.commit()
            
            # Update campaign metrics
            campaign = send.campaign
            if send.status == EmailStatus.FAILED:
                campaign.failed_count += 1
            db.commit()
        except Exception as e:
            logger.error(f"❌ Mark failed failed: {e}")
            db.rollback()

    @staticmethod
    def track_open(db: Session, tracking_id: str, user_agent: str = None, ip_address: str = None):
        """Track email open"""
        try:
            send = db.query(CampaignSend).filter(
                CampaignSend.tracking_id == tracking_id
            ).first()
            
            if not send:
                logger.warning(f"⚠️ Tracking ID not found: {tracking_id}")
                return
            
            # Record track event
            track = CampaignTrack(
                campaign_id=send.campaign_id,
                send_id=send.id,
                tracking_id=tracking_id,
                event_type="open",
                user_agent=user_agent,
                ip_address=ip_address
            )
            db.add(track)
            
            # Update send record (first open only)
            if send.status != EmailStatus.OPENED:
                send.status = EmailStatus.OPENED
                send.opened_at = datetime.utcnow()
                send.opened_count = 1
                
                # Update campaign metrics
                campaign = send.campaign
                campaign.opened_count += 1
            else:
                send.opened_count += 1
            
            db.commit()
            logger.info(f"📖 Email opened: {tracking_id}")
        except Exception as e:
            logger.error(f"❌ Track open failed: {e}")
            db.rollback()

    @staticmethod
    def track_click(db: Session, tracking_id: str, link_url: str = None, 
                   user_agent: str = None, ip_address: str = None):
        """Track email click"""
        try:
            send = db.query(CampaignSend).filter(
                CampaignSend.tracking_id == tracking_id
            ).first()
            
            if not send:
                logger.warning(f"⚠️ Tracking ID not found: {tracking_id}")
                return
            
            # Record track event
            track = CampaignTrack(
                campaign_id=send.campaign_id,
                send_id=send.id,
                tracking_id=tracking_id,
                event_type="click",
                link_url=link_url,
                user_agent=user_agent,
                ip_address=ip_address
            )
            db.add(track)
            
            # Update send record (first click only)
            if send.status != EmailStatus.CLICKED:
                send.status = EmailStatus.CLICKED
                send.clicked_at = datetime.utcnow()
                send.clicked_count = 1
                
                # Update campaign metrics
                campaign = send.campaign
                campaign.clicked_count += 1
            else:
                send.clicked_count += 1
            
            db.commit()
            logger.info(f"🔗 Email clicked: {tracking_id}")
        except Exception as e:
            logger.error(f"❌ Track click failed: {e}")
            db.rollback()

    @staticmethod
    def get_campaign_analytics(db: Session, campaign_id: int) -> Dict[str, Any]:
        """Get campaign analytics"""
        try:
            campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
            if not campaign:
                return {}
            
            # Calculate metrics
            campaign.calculate_metrics()
            db.commit()
            
            return {
                "campaign_id": campaign.id,
                "name": campaign.name,
                "status": campaign.status.value,
                "sent_count": campaign.sent_count,
                "opened_count": campaign.opened_count,
                "clicked_count": campaign.clicked_count,
                "bounced_count": campaign.bounced_count,
                "failed_count": campaign.failed_count,
                "open_rate": round(campaign.open_rate, 2),
                "click_rate": round(campaign.click_rate, 2),
                "bounce_rate": round(campaign.bounce_rate, 2),
                "created_at": campaign.created_at,
                "started_at": campaign.started_at,
                "completed_at": campaign.completed_at
            }
        except Exception as e:
            logger.error(f"❌ Analytics retrieval failed: {e}")
            return {}

    @staticmethod
    def get_send_stats(db: Session, campaign_id: int) -> Dict[str, int]:
        """Get send statistics for campaign"""
        try:
            stats = {
                "total": db.query(CampaignSend).filter(
                    CampaignSend.campaign_id == campaign_id
                ).count(),
                "pending": db.query(CampaignSend).filter(
                    CampaignSend.campaign_id == campaign_id,
                    CampaignSend.status == EmailStatus.PENDING
                ).count(),
                "sent": db.query(CampaignSend).filter(
                    CampaignSend.campaign_id == campaign_id,
                    CampaignSend.status == EmailStatus.SENT
                ).count(),
                "opened": db.query(CampaignSend).filter(
                    CampaignSend.campaign_id == campaign_id,
                    CampaignSend.status == EmailStatus.OPENED
                ).count(),
                "clicked": db.query(CampaignSend).filter(
                    CampaignSend.campaign_id == campaign_id,
                    CampaignSend.status == EmailStatus.CLICKED
                ).count(),
                "bounced": db.query(CampaignSend).filter(
                    CampaignSend.campaign_id == campaign_id,
                    CampaignSend.status == EmailStatus.BOUNCED
                ).count(),
                "failed": db.query(CampaignSend).filter(
                    CampaignSend.campaign_id == campaign_id,
                    CampaignSend.status == EmailStatus.FAILED
                ).count(),
            }
            return stats
        except Exception as e:
            logger.error(f"❌ Send stats failed: {e}")
            return {}
