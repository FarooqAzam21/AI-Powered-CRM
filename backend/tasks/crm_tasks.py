"""
CRM Celery Tasks - Phase 6
Async tasks for advanced CRM operations
"""
import logging
from datetime import datetime
from celery import shared_task
from sqlalchemy.orm import Session
from sqlalchemy import and_
from database import SessionLocal
from auth.models import AIRecommendation
from models.crm import Contact, CustomerProfile, Deal
from services.profile_service import CustomerProfileService
from services.deal_service import DealService
from services.activity_service import ActivityTimelineService
from services.relationship_service import RelationshipService
from services.recommendation_service import RecommendationEngine
import traceback

logger = logging.getLogger(__name__)

# =================== PROFILE GENERATION ===================

@shared_task(bind=True, name="tasks.crm.generate_customer_profile")
def generate_customer_profile(self, contact_id: int):
    """
    Generate AI customer profile from email history
    Async task: Updates profile with AI insights
    """
    db = None
    try:
        db = SessionLocal()
        
        logger.info(f"📊 [Profile] Generating profile for contact {contact_id}...")
        
        profile = CustomerProfileService.generate_profile(db=db, contact_id=contact_id)
        
        if profile:
            return {
                "status": "success",
                "profile_id": profile.id,
                "contact_id": contact_id,
                "summary": profile.summary
            }
        else:
            return {"status": "failed", "contact_id": contact_id, "reason": "Profile generation failed"}
            
    except Exception as e:
        logger.error(f"❌ Profile generation failed: {e}\n{traceback.format_exc()}")
        return {"status": "error", "contact_id": contact_id, "error": str(e)}
    finally:
        if db:
            db.close()

@shared_task(bind=True, name="tasks.crm.batch_generate_profiles")
def batch_generate_profiles(self, user_id: int, contact_ids: list):
    """
    Batch generate profiles for multiple contacts
    """
    db = None
    try:
        db = SessionLocal()
        
        logger.info(f"📊 [Batch] Generating profiles for {len(contact_ids)} contacts...")
        
        results = []
        for contact_id in contact_ids:
            try:
                profile = CustomerProfileService.generate_profile(db=db, contact_id=contact_id)
                results.append({
                    "contact_id": contact_id,
                    "status": "success" if profile else "failed"
                })
            except Exception as e:
                logger.warning(f"Profile generation failed for {contact_id}: {e}")
                results.append({"contact_id": contact_id, "status": "error", "error": str(e)})
        
        success_count = sum(1 for r in results if r["status"] == "success")
        logger.info(f"✅ Profiles generated: {success_count}/{len(contact_ids)}")
        
        return {
            "status": "success",
            "user_id": user_id,
            "generated": success_count,
            "total": len(contact_ids),
            "results": results
        }
        
    except Exception as e:
        logger.error(f"❌ Batch profile generation failed: {e}")
        return {"status": "error", "error": str(e)}
    finally:
        if db:
            db.close()

# =================== DEAL MANAGEMENT ===================

@shared_task(bind=True, name="tasks.crm.score_deal")
def score_deal(self, deal_id: int):
    """
    Update deal scoring based on activities and stage
    """
    db = None
    try:
        db = SessionLocal()
        
        deal = db.query(Deal).filter(Deal.id == deal_id).first()
        if not deal:
            return {"status": "failed", "deal_id": deal_id, "reason": "Deal not found"}
        
        logger.info(f"🎯 [Deal] Scoring deal: {deal.name}")
        
        # Calculate AI score based on multiple factors
        stage_score = DealService._calculate_stage_probability(deal.stage)
        
        # Get deal activities
        activities = len(deal.activities)
        activity_score = min(100, activities * 10)
        
        # Contact interactions
        contact = deal.contact if deal.contact_id else None
        contact_score = min(100, contact.score if contact else 0)
        
        # Weighted AI score
        ai_score = (stage_score * 0.5) + (activity_score * 0.3) + (contact_score * 0.2)
        
        deal.ai_score = ai_score
        deal.updated_at = datetime.utcnow()
        db.commit()
        
        logger.info(f"✅ Deal scored: {ai_score:.1f}")
        
        return {
            "status": "success",
            "deal_id": deal_id,
            "ai_score": ai_score
        }
        
    except Exception as e:
        logger.error(f"❌ Deal scoring failed: {e}\n{traceback.format_exc()}")
        return {"status": "error", "deal_id": deal_id, "error": str(e)}
    finally:
        if db:
            db.close()

@shared_task(bind=True, name="tasks.crm.check_deal_health")
def check_deal_health(self, user_id: int):
    """
    Check health of all deals (overdue, stalled, etc.)
    """
    db = None
    try:
        db = SessionLocal()
        
        logger.info(f"🏥 [Health] Checking deal health for user {user_id}...")
        
        alerts = []
        
        # Get overdue deals
        overdue_deals = DealService.get_overdue_deals(db=db, user_id=user_id)
        alerts.extend([
            {"type": "overdue", "deal_id": d.id, "name": d.name, "days_overdue": (
                datetime.utcnow() - d.expected_close_date
            ).days}
            for d in overdue_deals
        ])
        
        # Get stalled deals (low probability, no activity)
        stalled_deals = db.query(Deal).filter(
            Deal.user_id == user_id,
            Deal.status == "open",
            Deal.probability < 20,
            Deal.stage == "prospecting"
        ).all()
        
        alerts.extend([
            {"type": "stalled", "deal_id": d.id, "name": d.name}
            for d in stalled_deals
        ])
        
        logger.info(f"✅ Health check: {len(alerts)} issues found")
        
        return {
            "status": "success",
            "user_id": user_id,
            "total_alerts": len(alerts),
            "alerts": alerts
        }
        
    except Exception as e:
        logger.error(f"❌ Health check failed: {e}")
        return {"status": "error", "error": str(e)}
    finally:
        if db:
            db.close()

# =================== ACTIVITY TIMELINE ===================

@shared_task(bind=True, name="tasks.crm.generate_activity_timeline")
def generate_activity_timeline(self, contact_id: int):
    """
    Generate complete activity timeline for contact
    """
    db = None
    try:
        db = SessionLocal()
        
        logger.info(f"📋 [Timeline] Generating timeline for contact {contact_id}...")
        
        timeline = ActivityTimelineService.get_contact_timeline(db=db, contact_id=contact_id)
        
        logger.info(f"✅ Timeline generated: {len(timeline)} events")
        
        return {
            "status": "success",
            "contact_id": contact_id,
            "events_count": len(timeline),
            "timeline": timeline[:10]  # Return first 10 for response
        }
        
    except Exception as e:
        logger.error(f"❌ Timeline generation failed: {e}")
        return {"status": "error", "contact_id": contact_id, "error": str(e)}
    finally:
        if db:
            db.close()

# =================== RELATIONSHIP TRACKING ===================

@shared_task(bind=True, name="tasks.crm.build_relationship_graph")
def build_relationship_graph(self, user_id: int):
    """
    Build relationship graph for all user contacts
    """
    db = None
    try:
        db = SessionLocal()
        
        logger.info(f"🔗 [Relationships] Building graph for user {user_id}...")
        
        graph = RelationshipService.build_relationship_graph(db=db, user_id=user_id)
        
        logger.info(f"✅ Graph built: {graph['stats']['total_contacts']} contacts, {graph['stats']['total_connections']} connections")
        
        return {
            "status": "success",
            "user_id": user_id,
            "stats": graph["stats"]
        }
        
    except Exception as e:
        logger.error(f"❌ Graph building failed: {e}")
        return {"status": "error", "error": str(e)}
    finally:
        if db:
            db.close()

@shared_task(bind=True, name="tasks.crm.identify_influencers")
def identify_influencers(self, user_id: int):
    """
    Identify key influencers in contact network
    """
    db = None
    try:
        db = SessionLocal()
        
        logger.info(f"⭐ [Influencers] Identifying influencers for user {user_id}...")
        
        influencers = RelationshipService.identify_key_influencers(db=db, user_id=user_id)
        
        logger.info(f"✅ Identified {len(influencers)} key influencers")
        
        return {
            "status": "success",
            "user_id": user_id,
            "influencer_count": len(influencers),
            "influencers": influencers[:5]  # Return top 5
        }
        
    except Exception as e:
        logger.error(f"❌ Influencer identification failed: {e}")
        return {"status": "error", "error": str(e)}
    finally:
        if db:
            db.close()

# =================== RECOMMENDATIONS ===================

@shared_task(bind=True, name="tasks.crm.generate_recommendations")
def generate_recommendations(self, user_id: int, contact_id: int):
    """
    Generate AI recommendations for contact
    """
    db = None
    try:
        db = SessionLocal()
        
        logger.info(f"🧠 [Recommendations] Generating for contact {contact_id}...")
        
        recommendations = RecommendationEngine.generate_contact_recommendations(
            db=db,
            user_id=user_id,
            contact_id=contact_id
        )
        
        logger.info(f"✅ Generated {len(recommendations)} recommendations")
        
        return {
            "status": "success",
            "user_id": user_id,
            "contact_id": contact_id,
            "recommendation_count": len(recommendations),
            "recommendations": [
                {
                    "id": r.id,
                    "type": r.recommendation_type,
                    "title": r.title,
                    "confidence": r.confidence_score
                }
                for r in recommendations
            ]
        }
        
    except Exception as e:
        logger.error(f"❌ Recommendation generation failed: {e}\n{traceback.format_exc()}")
        return {"status": "error", "contact_id": contact_id, "error": str(e)}
    finally:
        if db:
            db.close()

@shared_task(bind=True, name="tasks.crm.generate_user_recommendations")
def generate_user_recommendations(self, user_id: int, limit: int = 20):
    """
    Generate recommendations for all active contacts
    """
    db = None
    try:
        db = SessionLocal()
        
        logger.info(f"🧠 [Batch Recommendations] Generating for user {user_id}...")
        
        # Get active contacts (with recent activity)
        active_contacts = ActivityTimelineService.get_active_contacts(
            db=db, user_id=user_id, days=7
        )
        
        total_generated = 0
        for contact_data in active_contacts[:limit]:
            try:
                RecommendationEngine.generate_contact_recommendations(
                    db=db,
                    user_id=user_id,
                    contact_id=contact_data["id"]
                )
                total_generated += 1
            except Exception as e:
                logger.warning(f"Failed to generate recommendations for contact {contact_data['id']}: {e}")
        
        logger.info(f"✅ Generated recommendations for {total_generated} contacts")
        
        return {
            "status": "success",
            "user_id": user_id,
            "generated_count": total_generated
        }
        
    except Exception as e:
        logger.error(f"❌ Batch recommendations failed: {e}")
        return {"status": "error", "error": str(e)}
    finally:
        if db:
            db.close()

# =================== PERIODIC TASKS (Registered in celery_app.py) ===================

@shared_task(bind=True, name="tasks.crm.periodic_profile_refresh")
def periodic_profile_refresh():
    """
    Periodic task: Refresh profiles for active contacts every 24 hours
    To be registered as periodic task in celery_app.py
    """
    db = None
    try:
        db = SessionLocal()
        
        # Get contacts updated in last 3 days with no profile
        contacts_needing_profile = db.query(Contact).filter(
            and_(
                Contact.profile == None,
                Contact.interaction_count > 0
            )
        ).limit(50).all()
        
        for contact in contacts_needing_profile:
            try:
                CustomerProfileService.generate_profile(db=db, contact_id=contact.id)
            except Exception as e:
                logger.warning(f"Could not generate profile for {contact.email}: {e}")
        
        logger.info(f"✅ Periodic: Refreshed {len(contacts_needing_profile)} profiles")
        
        return {"status": "success", "profiles_refreshed": len(contacts_needing_profile)}
        
    except Exception as e:
        logger.error(f"❌ Periodic profile refresh failed: {e}")
        return {"status": "error", "error": str(e)}
    finally:
        if db:
            db.close()

@shared_task(bind=True, name="tasks.crm.periodic_deal_scoring")
def periodic_deal_scoring():
    """
    Periodic task: Score all open deals every 6 hours
    """
    db = None
    try:
        db = SessionLocal()
        
        open_deals = db.query(Deal).filter(Deal.status == "open").all()
        
        for deal in open_deals:
            try:
                score_deal.apply_async(args=[deal.id])
            except Exception as e:
                logger.warning(f"Could not score deal {deal.id}: {e}")
        
        logger.info(f"✅ Periodic: Queued scoring for {len(open_deals)} deals")
        
        return {"status": "success", "deals_scored": len(open_deals)}
        
    except Exception as e:
        logger.error(f"❌ Periodic deal scoring failed: {e}")
        return {"status": "error", "error": str(e)}
    finally:
        if db:
            db.close()
