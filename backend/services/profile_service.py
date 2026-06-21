"""
Customer Profile AI Generator - Phase 6
Generates AI-based customer profiles from email history and interactions
"""
import logging
import json
import asyncio
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func
from auth.models import User
from models.crm import Contact, EmailMetadata, Activity, Interaction, CustomerProfile
from ai.ollama_client import generate_cached, generate_classification
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)

class CustomerProfileService:
    """Service for AI-generated customer profiles"""
    
    @staticmethod
    def generate_profile(db: Session, contact_id: int, use_cache: bool = True) -> Optional[CustomerProfile]:
        """
        Generate AI profile for contact based on email history and interactions
        """
        try:
            contact = db.query(Contact).filter(Contact.id == contact_id).first()
            if not contact:
                logger.error(f"Contact {contact_id} not found")
                return None
            
            logger.info(f"🧠 Generating profile for {contact.email}...")
            
            # Check if profile already exists
            profile = db.query(CustomerProfile).filter(
                CustomerProfile.contact_id == contact_id
            ).first()
            
            # Gather email history and interactions
            emails = (
                db.query(EmailMetadata)
                .filter(EmailMetadata.user_id == contact.user_id, EmailMetadata.sender_email == contact.email)
                .all()
            )
            activities = db.query(Activity).filter(Activity.contact_id == contact_id).all()
            interactions = db.query(Interaction).filter(Interaction.contact_id == contact_id).all()
            
            if not emails and not interactions:
                logger.warning(f"No email history for {contact.email}")
                if not profile:
                    profile = CustomerProfileService._create_empty_profile(db, contact_id, contact.user_id)
                return profile

            email_texts = [
                f"Subject: {e.subject}\n{e.snippet[:500]}" for e in emails[-10:]
            ]
            for inter in interactions[-5:]:
                email_texts.append(f"Subject: {inter.subject}\n{inter.snippet[:500]}")
            email_context = "\n\n---\n\n".join(email_texts)
            
            # Generate summary
            summary_prompt = f"""Analyze these customer emails and provide a brief professional summary:

{email_context}

Provide a concise 2-3 sentence summary about this customer."""
            
            summary = asyncio.run(generate_cached(summary_prompt, use_compression=True, use_context=False))
            
            # Detect pain points and interests
            pain_points = CustomerProfileService._extract_pain_points(email_context)
            interests = CustomerProfileService._extract_interests(email_context)
            
            # Analyze communication style
            communication_style = CustomerProfileService._analyze_communication(emails)
            
            # Calculate response time
            response_time = CustomerProfileService._calculate_response_time(emails)
            
            # Detect buyer persona
            buyer_persona = CustomerProfileService._detect_buyer_persona(email_context)
            
            # Detect tech stack
            technologies = CustomerProfileService._detect_technologies(email_context)
            
            # Update or create profile
            if profile:
                profile.summary = summary
                profile.pain_points = json.dumps(pain_points)
                profile.interests = json.dumps(interests)
                profile.communication_style = communication_style
                profile.buyer_persona = buyer_persona
                profile.engagement_level = CustomerProfileService._calculate_engagement_level(activities)
                profile.company_industry = contact.company or profile.company_industry or "Unknown"
                profile.generated_at = datetime.utcnow()
            else:
                profile = CustomerProfile(
                    contact_id=contact_id,
                    user_id=contact.user_id,
                    summary=summary,
                    buyer_persona=buyer_persona,
                    pain_points=json.dumps(pain_points),
                    interests=json.dumps(interests),
                    communication_style=communication_style,
                    engagement_level=CustomerProfileService._calculate_engagement_level(activities),
                    company_industry=contact.company or "Unknown",
                    ai_model="tinyllama",
                    generated_at=datetime.utcnow(),
                )
            
            db.add(profile)
            db.commit()
            db.refresh(profile)
            
            logger.info(f"✅ Profile generated for {contact.email}")
            return profile
            
        except Exception as e:
            db.rollback()
            logger.error(f"❌ Profile generation failed: {e}")
            return None
    
    @staticmethod
    def _extract_pain_points(email_context: str) -> List[str]:
        """Extract potential pain points from email context"""
        pain_keywords = {
            "challenge": "Facing challenges",
            "problem": "Experiencing problems",
            "issue": "Technical issues",
            "struggling": "Struggling with",
            "difficult": "Finding it difficult",
            "slow": "Performance issues",
            "expensive": "Cost concerns",
            "manual": "Manual processes",
            "time-consuming": "Time management",
            "frustrated": "User frustration"
        }
        
        pain_points = []
        context_lower = email_context.lower()
        
        for keyword, pain_point in pain_keywords.items():
            if keyword in context_lower:
                pain_points.append(pain_point)
        
        return pain_points[:5]  # Limit to top 5
    
    @staticmethod
    def _extract_interests(email_context: str) -> List[str]:
        """Extract interests and use cases from email context"""
        interest_keywords = {
            "marketing": "Marketing automation",
            "sales": "Sales enablement",
            "crm": "CRM solutions",
            "analytics": "Data analytics",
            "automation": "Business automation",
            "integration": "System integration",
            "security": "Security",
            "compliance": "Compliance",
            "scalability": "Scalability",
            "performance": "Performance optimization"
        }
        
        interests = []
        context_lower = email_context.lower()
        
        for keyword, interest in interest_keywords.items():
            if keyword in context_lower:
                interests.append(interest)
        
        return interests[:5]
    
    @staticmethod
    def _analyze_communication(emails) -> str:
        """Analyze communication style from email patterns"""
        if not emails:
            return "Unknown"

        avg_length = sum(len(getattr(e, "snippet", "") or "") for e in emails) / len(emails)
        
        if avg_length > 500:
            return "Detailed/Technical"
        elif avg_length > 200:
            return "Balanced"
        else:
            return "Brief/Direct"
    
    @staticmethod
    def _calculate_response_time(emails: List[EmailMetadata]) -> float:
        """Calculate average response time in hours"""
        if len(emails) < 2:
            return 0
        
        times = []
        for i in range(1, len(emails)):
            try:
                if emails[i].received_at and emails[i-1].received_at:
                    diff = (emails[i].received_at - emails[i-1].received_at).total_seconds() / 3600
                    if 0 < diff < 168:  # 0-7 days
                        times.append(diff)
            except:
                pass
        
        return sum(times) / len(times) if times else 0
    
    @staticmethod
    def _calculate_email_frequency(emails: List[EmailMetadata]) -> str:
        """Estimate email frequency"""
        if len(emails) < 2:
            return "Low"
        
        if len(emails) > 20:
            return "High"
        elif len(emails) > 5:
            return "Medium"
        else:
            return "Low"
    
    @staticmethod
    def _calculate_engagement_level(activities: List[Activity]) -> str:
        """Calculate engagement level from interactions"""
        if not activities:
            return "Low"
        
        if len(activities) > 10:
            return "High"
        elif len(activities) > 3:
            return "Medium"
        else:
            return "Low"
    
    @staticmethod
    def _detect_buyer_persona(email_context: str) -> str:
        """Detect buyer persona from language patterns"""
        context_lower = email_context.lower()
        
        if any(word in context_lower for word in ["budget", "roi", "decision", "approval"]):
            return "Decision Maker"
        elif any(word in context_lower for word in ["technical", "implementation", "spec", "requirement"]):
            return "Technical Influencer"
        elif any(word in context_lower for word in ["department", "team", "end-user", "user"]):
            return "End User"
        else:
            return "Influencer"
    
    @staticmethod
    def _detect_technologies(email_context: str) -> List[str]:
        """Detect technologies mentioned in emails"""
        tech_keywords = [
            "salesforce", "hubspot", "pipedrive", "zoho",
            "slack", "teams", "zoom", "google",
            "aws", "azure", "cloud", "api",
            "python", "javascript", "java", "c#",
            "react", "angular", "vue", "node"
        ]
        
        context_lower = email_context.lower()
        detected = [tech for tech in tech_keywords if tech in context_lower]
        
        return detected[:5]
    
    @staticmethod
    def _create_empty_profile(db: Session, contact_id: int, user_id: int) -> CustomerProfile:
        """Create empty profile placeholder"""
        profile = CustomerProfile(
            contact_id=contact_id,
            user_id=user_id,
            summary="Profile generation pending",
            buyer_persona="Unknown",
            communication_style="Unknown",
            engagement_level="Low"
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)
        return profile
    
    @staticmethod
    def update_profile_from_email(db: Session, contact_id: int, email: EmailMetadata) -> None:
        """Update profile insights when new email arrives"""
        try:
            profile = db.query(CustomerProfile).filter(
                CustomerProfile.contact_id == contact_id
            ).first()
            
            if not profile:
                return
            
            # Update engagement level
            profile.engagement_level = CustomerProfileService._calculate_engagement_level(
                db.query(Activity).filter(Activity.contact_id == contact_id).all()
            )
            profile.generated_at = datetime.utcnow()
            
            db.commit()
            
        except Exception as e:
            logger.warning(f"Could not update profile: {e}")
    
    @staticmethod
    def get_profile(db: Session, contact_id: int) -> Optional[CustomerProfile]:
        """Get customer profile"""
        return db.query(CustomerProfile).filter(
            CustomerProfile.contact_id == contact_id
        ).first()
    
    @staticmethod
    def list_profiles_by_engagement(db: Session, user_id: int, 
                                   engagement_level: Optional[str] = None) -> List[CustomerProfile]:
        """List profiles filtered by engagement level"""
        query = db.query(CustomerProfile).filter(CustomerProfile.user_id == user_id)
        
        if engagement_level:
            query = query.filter(CustomerProfile.engagement_level == engagement_level)
        
        return query.order_by(CustomerProfile.last_updated_at.desc()).all()
