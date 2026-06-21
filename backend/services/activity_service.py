"""
Activity Timeline Service - Phase 6
Tracks all customer interactions and builds timeline views
"""
import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
from auth.models import User
from models.crm import Activity, Contact, Deal, DealActivity, Interaction, EmailMetadata
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class ActivityTimelineService:
    """Service for activity tracking and timeline generation"""
    
    ACTIVITY_TYPES = {
        "email_sent": {"icon": "📧", "color": "blue"},
        "email_received": {"icon": "📬", "color": "green"},
        "call": {"icon": "☎️", "color": "orange"},
        "meeting": {"icon": "📅", "color": "purple"},
        "note": {"icon": "📝", "color": "gray"},
        "task_completed": {"icon": "✅", "color": "green"},
        "stage_change": {"icon": "📊", "color": "yellow"},
        "proposal_sent": {"icon": "📄", "color": "blue"},
        "deal_created": {"icon": "🎯", "color": "green"}
    }
    
    @staticmethod
    def record_activity(db: Session, user_id: int, contact_id: Optional[int],
                       activity_type: str, subject: Optional[str] = None,
                       description: Optional[str] = None, 
                       direction: str = "outbound") -> Activity:
        """Record a new activity"""
        try:
            activity = Activity(
                user_id=user_id,
                contact_id=contact_id,
                type=activity_type,
                subject=subject,
                description=description,
                direction=direction,
                status="completed"
            )
            db.add(activity)
            db.commit()
            db.refresh(activity)
            
            logger.debug(f"📝 Activity recorded: {activity_type}")
            return activity
            
        except Exception as e:
            db.rollback()
            logger.error(f"❌ Activity recording failed: {e}")
            raise
    
    @staticmethod
    def get_contact_timeline(db: Session, contact_id: int, 
                           days: int = 30, limit: int = 50) -> List[Dict]:
        """
        Get complete activity timeline for a contact
        Returns chronological list of all interactions
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            activities = db.query(Activity).filter(
                and_(
                    Activity.contact_id == contact_id,
                    Activity.created_at >= cutoff_date
                )
            ).order_by(desc(Activity.created_at)).limit(limit).all()
            
            emails = db.query(Email).filter(
                and_(
                    Email.contact_id == contact_id,
                    Email.received_at >= cutoff_date
                )
            ).order_by(desc(Email.received_at)).all()
            
            # Combine activities and emails
            timeline = []
            
            for activity in activities:
                activity_type = activity.type or "note"
                type_info = ActivityTimelineService.ACTIVITY_TYPES.get(
                    activity_type, 
                    {"icon": "📍", "color": "gray"}
                )
                
                timeline.append({
                    "id": f"activity_{activity.id}",
                    "type": activity_type,
                    "timestamp": activity.created_at,
                    "icon": type_info["icon"],
                    "color": type_info["color"],
                    "title": activity.subject or activity_type.replace("_", " ").title(),
                    "description": activity.description,
                    "direction": activity.direction
                })
            
            for email in emails:
                email_type = "email_received" if email.direction != "outbound" else "email_sent"
                type_info = ActivityTimelineService.ACTIVITY_TYPES.get(email_type)
                
                timeline.append({
                    "id": f"email_{email.id}",
                    "type": email_type,
                    "timestamp": email.received_at,
                    "icon": type_info["icon"],
                    "color": type_info["color"],
                    "title": email.subject,
                    "description": email.body[:200] if email.body else "",
                    "category": email.category,
                    "sentiment": email.sentiment
                })
            
            # Sort by timestamp descending
            timeline.sort(key=lambda x: x["timestamp"], reverse=True)
            
            logger.info(f"📋 Timeline: {len(timeline)} activities for contact {contact_id}")
            return timeline
            
        except Exception as e:
            logger.error(f"❌ Timeline retrieval failed: {e}")
            return []
    
    @staticmethod
    def get_user_activity_summary(db: Session, user_id: int, 
                                days: int = 7) -> Dict:
        """
        Get activity summary for user over time period
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            activities = db.query(Activity).filter(
                and_(
                    Activity.user_id == user_id,
                    Activity.created_at >= cutoff_date
                )
            ).all()
            
            emails = db.query(Email).filter(
                and_(
                    Email.user_id == user_id,
                    Email.received_at >= cutoff_date
                )
            ).all()
            
            # Count by type
            activity_counts = {}
            for activity in activities:
                atype = activity.type or "other"
                activity_counts[atype] = activity_counts.get(atype, 0) + 1
            
            email_counts = {
                "email_sent": len([e for e in emails if e.direction == "outbound"]),
                "email_received": len([e for e in emails if e.direction != "outbound"])
            }
            
            summary = {
                "period_days": days,
                "total_activities": len(activities) + len(emails),
                "activities_by_type": activity_counts,
                "email_stats": email_counts,
                "avg_daily_activity": (len(activities) + len(emails)) / days if days > 0 else 0,
                "contacts_engaged": len(set(a.contact_id for a in activities if a.contact_id))
            }
            
            logger.info(f"📊 Activity summary: {summary['total_activities']} activities in {days} days")
            return summary
            
        except Exception as e:
            logger.error(f"❌ Summary generation failed: {e}")
            return {}
    
    @staticmethod
    def get_deal_activity_timeline(db: Session, deal_id: int) -> List[Dict]:
        """Get activity timeline for a specific deal"""
        try:
            activities = db.query(DealActivity).filter(
                DealActivity.deal_id == deal_id
            ).order_by(desc(DealActivity.created_at)).all()
            
            timeline = []
            for activity in activities:
                timeline.append({
                    "id": activity.id,
                    "type": activity.activity_type,
                    "timestamp": activity.created_at,
                    "description": activity.description,
                    "value_impact": activity.value_impact,
                    "probability_impact": activity.probability_impact
                })
            
            return timeline
            
        except Exception as e:
            logger.error(f"❌ Deal timeline retrieval failed: {e}")
            return []
    
    @staticmethod
    def get_interactions_between_dates(db: Session, contact_id: int,
                                      start_date: datetime, end_date: datetime) -> List[Dict]:
        """Get all interactions between two dates"""
        try:
            activities = db.query(Activity).filter(
                and_(
                    Activity.contact_id == contact_id,
                    Activity.created_at >= start_date,
                    Activity.created_at <= end_date
                )
            ).order_by(desc(Activity.created_at)).all()
            
            result = []
            for activity in activities:
                result.append({
                    "type": activity.type,
                    "date": activity.created_at,
                    "description": activity.description or activity.subject
                })
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Date range retrieval failed: {e}")
            return []
    
    @staticmethod
    def get_most_recent_interactions(db: Session, user_id: int, 
                                   limit: int = 10) -> List[Dict]:
        """
        Get most recent interactions for a user across all contacts
        """
        try:
            activities = db.query(Activity).filter(
                Activity.user_id == user_id
            ).order_by(desc(Activity.created_at)).limit(limit).all()
            
            result = []
            for activity in activities:
                contact = None
                if activity.contact_id:
                    contact = db.query(Contact).filter(Contact.id == activity.contact_id).first()
                
                result.append({
                    "id": activity.id,
                    "type": activity.type,
                    "timestamp": activity.created_at,
                    "contact": contact.email if contact else "Unknown",
                    "description": activity.description or activity.subject,
                    "time_ago": ActivityTimelineService._time_ago(activity.created_at)
                })
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Recent interactions retrieval failed: {e}")
            return []
    
    @staticmethod
    def get_active_contacts(db: Session, user_id: int, days: int = 7) -> List[Dict]:
        """
        Get contacts with recent activity
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            active_contacts = db.query(Contact).filter(
                and_(
                    Contact.user_id == user_id,
                    Contact.last_interaction_at >= cutoff_date
                )
            ).order_by(desc(Contact.last_interaction_at)).all()
            
            result = []
            for contact in active_contacts:
                # Count recent activities
                recent_activities = db.query(Activity).filter(
                    and_(
                        Activity.contact_id == contact.id,
                        Activity.created_at >= cutoff_date
                    )
                ).count()
                
                result.append({
                    "id": contact.id,
                    "email": contact.email,
                    "name": contact.name,
                    "company": contact.company,
                    "last_interaction": contact.last_interaction_at,
                    "recent_activities": recent_activities,
                    "engagement_score": contact.score
                })
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Active contacts retrieval failed: {e}")
            return []
    
    @staticmethod
    def _time_ago(dt: datetime) -> str:
        """Convert datetime to human-readable 'time ago' format"""
        now = datetime.utcnow()
        diff = now - dt
        
        if diff.days > 0:
            return f"{diff.days}d ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours}h ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes}m ago"
        else:
            return "just now"
