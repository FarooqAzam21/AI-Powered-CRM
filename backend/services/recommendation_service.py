"""
AI Recommendation Engine - Phase 6
Generates AI-powered recommendations for next actions and sales strategies
"""
import logging
import asyncio
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from auth.models import AIRecommendation
from models.crm import Activity, Contact, CustomerProfile, Deal, EmailMetadata, Interaction, Lead
from ai.ollama_client import generate_cached
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class RecommendationEngine:
    """AI-powered recommendation engine for CRM actions"""
    
    RECOMMENDATION_TYPES = {
        "next_action": "What to do next with this contact",
        "best_time": "Best time to reach out",
        "template_use": "Suggested email template",
        "follow_up_needed": "Follow-up action needed",
        "deal_strategy": "Sales strategy for deal",
        "risk_alert": "Risk alert for opportunity",
        "win_opportunity": "Opportunity to win deal"
    }
    
    @staticmethod
    def generate_contact_recommendations(db: Session, user_id: int, 
                                        contact_id: int) -> List[AIRecommendation]:
        """
        Generate recommendations for a specific contact
        Analyzes: recent emails, activity, lead status, deal pipeline
        """
        try:
            contact = db.query(Contact).filter(Contact.id == contact_id).first()
            if not contact:
                logger.error(f"Contact {contact_id} not found")
                return []
            
            logger.info(f"🧠 Generating recommendations for {contact.email}...")
            
            recommendations = []
            
            # Get contact context
            profile = db.query(CustomerProfile).filter(
                CustomerProfile.contact_id == contact_id
            ).first()
            
            recent_emails = (
                db.query(EmailMetadata)
                .filter(
                    EmailMetadata.user_id == user_id,
                    EmailMetadata.sender_email == contact.email,
                )
                .order_by(desc(EmailMetadata.internal_date))
                .limit(5)
                .all()
            )
            
            recent_activity = db.query(Activity).filter(
                Activity.contact_id == contact_id
            ).order_by(desc(Activity.created_at)).limit(10).all()
            
            lead = db.query(Lead).filter(Lead.contact_id == contact_id).first()
            deals = db.query(Deal).filter(Deal.contact_id == contact_id).all()
            
            # Build context for AI
            context = RecommendationEngine._build_contact_context(
                contact, profile, recent_emails, recent_activity, lead, deals
            )
            
            # Generate next action recommendation
            if recent_emails or recent_activity:
                next_action = RecommendationEngine._generate_next_action(
                    db, user_id, contact_id, context
                )
                if next_action:
                    recommendations.append(next_action)
            
            # Generate best time recommendation
            if profile:
                best_time = RecommendationEngine._generate_best_time(
                    db, user_id, contact_id, profile
                )
                if best_time:
                    recommendations.append(best_time)
            
            # Generate follow-up recommendation if needed
            if recent_activity:
                last_activity = recent_activity[0]
                days_since = (datetime.utcnow() - last_activity.created_at).days
                
                if days_since > 3:
                    follow_up = RecommendationEngine._generate_followup_recommendation(
                        db, user_id, contact_id, days_since
                    )
                    if follow_up:
                        recommendations.append(follow_up)
            
            # Generate deal-specific recommendations
            if deals:
                for deal in deals:
                    if deal.status == "open":
                        deal_rec = RecommendationEngine._generate_deal_recommendation(
                            db, user_id, deal, contact, profile
                        )
                        if deal_rec:
                            recommendations.append(deal_rec)
            
            logger.info(f"✅ Generated {len(recommendations)} recommendations")
            return recommendations
            
        except Exception as e:
            logger.error(f"❌ Recommendation generation failed: {e}")
            return []
    
    @staticmethod
    def _generate_next_action(db: Session, user_id: int, contact_id: int, 
                             context: str) -> Optional[AIRecommendation]:
        """Generate next action recommendation using AI"""
        try:
            prompt = f"""Based on this contact context, suggest the best next action:

{context}

Provide a specific, actionable recommendation (1-2 sentences max)."""
            
            recommendation_text = asyncio.run(generate_cached(prompt, use_compression=True))
            
            rec = AIRecommendation(
                user_id=user_id,
                contact_id=contact_id,
                recommendation_type="next_action",
                title="Recommended Next Action",
                description=recommendation_text,
                confidence_score=0.85,
                expires_at=datetime.utcnow() + timedelta(days=7)
            )
            db.add(rec)
            db.commit()
            db.refresh(rec)
            
            logger.debug(f"✅ Next action recommendation created")
            return rec
            
        except Exception as e:
            logger.error(f"❌ Next action generation failed: {e}")
            return None
    
    @staticmethod
    def _generate_best_time(db: Session, user_id: int, contact_id: int, 
                           profile: CustomerProfile) -> Optional[AIRecommendation]:
        """Generate best time to contact recommendation"""
        try:
            if not profile or not getattr(profile, "response_time_avg", None):
                return None
            
            # Analyze response patterns
            response_hours = profile.response_time_avg
            
            if response_hours < 2:
                time_recommendation = "This contact responds quickly (within 2 hours). Follow up same day."
            elif response_hours < 24:
                time_recommendation = f"This contact typically responds within {int(response_hours)} hours. Plan follow-up next business day."
            else:
                time_recommendation = "This contact responds slowly. Plan follow-ups at least 48 hours apart."
            
            rec = AIRecommendation(
                user_id=user_id,
                contact_id=contact_id,
                recommendation_type="best_time",
                title="Best Time to Contact",
                description=time_recommendation,
                confidence_score=0.90,
                expires_at=datetime.utcnow() + timedelta(days=14)
            )
            db.add(rec)
            db.commit()
            db.refresh(rec)
            
            return rec
            
        except Exception as e:
            logger.error(f"❌ Best time generation failed: {e}")
            return None
    
    @staticmethod
    def _generate_followup_recommendation(db: Session, user_id: int, 
                                        contact_id: int, days_since: int) -> Optional[AIRecommendation]:
        """Generate follow-up needed recommendation"""
        try:
            if days_since < 3:
                return None
            
            urgency = "urgent" if days_since > 7 else "recommended"
            
            rec = AIRecommendation(
                user_id=user_id,
                contact_id=contact_id,
                recommendation_type="follow_up_needed",
                title=f"Follow-up {urgency.capitalize()}",
                description=f"No contact for {days_since} days. Time to reach out and maintain relationship.",
                confidence_score=0.95,
                expires_at=datetime.utcnow() + timedelta(days=2)
            )
            db.add(rec)
            db.commit()
            db.refresh(rec)
            
            return rec
            
        except Exception as e:
            logger.error(f"❌ Follow-up generation failed: {e}")
            return None
    
    @staticmethod
    def _generate_deal_recommendation(db: Session, user_id: int, deal: Deal, 
                                    contact: Contact, profile: Optional[CustomerProfile]) -> Optional[AIRecommendation]:
        """Generate deal-specific recommendation"""
        try:
            if deal.probability < 30:
                strategy = "This deal is low probability. Consider direct discovery call or pivot strategy."
                rec_type = "risk_alert"
                confidence = 0.80
            elif deal.probability > 70:
                strategy = "This deal is high probability. Focus on close logistics and contract terms."
                rec_type = "win_opportunity"
                confidence = 0.85
            else:
                strategy = "This deal needs qualification work. Suggest detailed needs analysis meeting."
                rec_type = "deal_strategy"
                confidence = 0.75
            
            rec = AIRecommendation(
                user_id=user_id,
                deal_id=deal.id,
                contact_id=contact.id,
                recommendation_type=rec_type,
                title=f"Deal Strategy: {deal.name}",
                description=strategy,
                confidence_score=confidence,
                expires_at=datetime.utcnow() + timedelta(days=7)
            )
            db.add(rec)
            db.commit()
            db.refresh(rec)
            
            return rec
            
        except Exception as e:
            logger.error(f"❌ Deal recommendation generation failed: {e}")
            return None
    
    @staticmethod
    def _build_contact_context(contact: Contact, profile: Optional[CustomerProfile],
                              emails, activities: List[Activity],
                              lead: Optional[Lead], deals: List[Deal]) -> str:
        """Build rich context string for AI recommendation"""
        import json

        context_parts = []
        context_parts.append(f"Contact: {contact.name or contact.email}")
        context_parts.append(f"Company: {contact.company or 'Unknown'}")
        context_parts.append(f"Title: {contact.title or 'Unknown'}")
        context_parts.append(f"Engagement Score: {contact.relationship_score}")

        if profile:
            context_parts.append(f"Buyer Persona: {profile.buyer_persona}")
            context_parts.append(f"Communication Style: {profile.communication_style}")
            context_parts.append(f"Engagement Level: {profile.engagement_level}")
            try:
                pain_points = json.loads(profile.pain_points or "[]")
                if pain_points:
                    context_parts.append(f"Pain Points: {', '.join(pain_points[:3])}")
            except json.JSONDecodeError:
                pass
            try:
                interests = json.loads(profile.interests or "[]")
                if interests:
                    context_parts.append(f"Interests: {', '.join(interests[:3])}")
            except json.JSONDecodeError:
                pass

        if emails:
            context_parts.append(f"Last Email: {emails[0].subject}")

        if lead:
            context_parts.append(f"Lead Label: {lead.label}")
            context_parts.append(f"Lead Score: {lead.score}")

        if deals:
            context_parts.append(f"Active Deals: {len([d for d in deals if d.status == 'open'])}")

        return "\n".join(context_parts)
    
    @staticmethod
    def get_active_recommendations(db: Session, user_id: int, 
                                  limit: int = 10) -> List[Dict]:
        """Get active (non-expired, non-dismissed) recommendations for user"""
        try:
            recommendations = db.query(AIRecommendation).filter(
                and_(
                    AIRecommendation.user_id == user_id,
                    AIRecommendation.status == "pending",
                    AIRecommendation.expires_at > datetime.utcnow()
                )
            ).order_by(desc(AIRecommendation.confidence_score)).limit(limit).all()
            
            result = []
            for rec in recommendations:
                result.append({
                    "id": rec.id,
                    "type": rec.recommendation_type,
                    "title": rec.title,
                    "description": rec.description,
                    "contact_id": rec.contact_id,
                    "deal_id": rec.deal_id,
                    "confidence": rec.confidence_score,
                    "created_at": rec.created_at
                })
            
            logger.debug(f"📊 Retrieved {len(result)} active recommendations")
            return result
            
        except Exception as e:
            logger.error(f"❌ Recommendations retrieval failed: {e}")
            return []
    
    @staticmethod
    def mark_recommendation_actioned(db: Session, recommendation_id: int) -> bool:
        """Mark recommendation as actioned"""
        try:
            rec = db.query(AIRecommendation).filter(
                AIRecommendation.id == recommendation_id
            ).first()
            
            if rec:
                rec.status = "actioned"
                rec.actioned_at = datetime.utcnow()
                db.commit()
                logger.debug(f"✅ Recommendation marked as actioned")
                return True
            
            return False
            
        except Exception as e:
            db.rollback()
            logger.error(f"❌ Mark actioned failed: {e}")
            return False
