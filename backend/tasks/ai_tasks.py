"""
AI Tasks - Async AI processing with Celery
Email classification, reply generation, entity extraction
"""
from tasks.celery_app import celery_app
from database import SessionLocal
from auth.models import Email, Lead, Contact
from services.ai_service import ai_service
import logging
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)

@celery_app.task(bind=True, name="tasks.ai_tasks.classify_email_batch")
def classify_email_batch(self, email_ids: list):
    """
    Classify multiple emails at once
    Useful for batch processing during sync
    """
    try:
        db = SessionLocal()
        results = []
        
        for email_id in email_ids:
            email = db.query(Email).filter(Email.id == email_id).first()
            if not email:
                continue
            
            logger.info(f"🤖 Classifying email {email_id}: {email.subject[:40]}")
            
            # Run async classification
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                classification = loop.run_until_complete(
                    ai_service.classify_email(email.subject, email.body or "")
                )
                loop.close()
                
                email.category = classification.get("category", "general")
                email.confidence = classification.get("confidence", 0.5)
                email.action = classification.get("action", "draft_response")
                email.priority = classification.get("priority", "medium")
                
                results.append({
                    "email_id": email_id,
                    "status": "classified",
                    "category": email.category
                })
            except Exception as e:
                logger.error(f"Failed to classify {email_id}: {e}")
                results.append({"email_id": email_id, "status": "failed"})
        
        db.commit()
        db.close()
        
        logger.info(f"✅ Batch classification complete: {len(results)} emails")
        return {"processed": len(results), "results": results}
        
    except Exception as e:
        logger.error(f"❌ Batch classification failed: {e}")
        raise

@celery_app.task(bind=True, name="tasks.ai_tasks.detect_intent")
def detect_intent(self, email_id: int, contact_id: int = None):
    """
    Detect intent from email (hiring, buying, support, etc.)
    Updates Lead record with AI-detected intent
    """
    try:
        db = SessionLocal()
        email = db.query(Email).filter(Email.id == email_id).first()
        
        if not email:
            return {"error": "Email not found"}
        
        logger.info(f"🎯 Detecting intent for: {email.subject[:40]}")
        
        # Extract entities and detect intent
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        entities = loop.run_until_complete(
            ai_service.extract_entities(email.body or "")
        )
        loop.close()
        
        # Determine intent from content
        intent = "general"
        if any(keyword in email.body.lower() for keyword in ["hire", "hiring", "position", "job"]):
            intent = "hiring"
        elif any(keyword in email.body.lower() for keyword in ["buy", "purchase", "order", "budget"]):
            intent = "buying"
        elif any(keyword in email.body.lower() for keyword in ["help", "support", "issue", "problem"]):
            intent = "support"
        
        # Update or create lead
        if contact_id:
            lead = db.query(Lead).filter(Lead.contact_id == contact_id).first()
            if lead:
                lead.intent_detected = intent
                db.commit()
        
        logger.info(f"✅ Intent detected: {intent}")
        return {
            "email_id": email_id,
            "intent": intent,
            "entities": entities
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Intent detection failed: {e}")
        raise
    finally:
        db.close()

@celery_app.task(bind=True, name="tasks.ai_tasks.extract_sentiment")
def extract_sentiment(self, email_id: int):
    """
    Analyze email sentiment (positive, neutral, negative)
    """
    try:
        db = SessionLocal()
        email = db.query(Email).filter(Email.id == email_id).first()
        
        if not email:
            return {"error": "Email not found"}
        
        logger.info(f"😊 Analyzing sentiment for: {email.subject[:40]}")
        
        # Simple sentiment analysis (can be enhanced with ML)
        sentiment = "neutral"
        text = (email.subject + " " + (email.body or "")).lower()
        
        positive_keywords = ["excellent", "great", "amazing", "wonderful", "thanks", "appreciated", "good"]
        negative_keywords = ["bad", "terrible", "awful", "horrible", "angry", "frustrated", "disappointed"]
        
        pos_count = sum(1 for word in positive_keywords if word in text)
        neg_count = sum(1 for word in negative_keywords if word in text)
        
        if pos_count > neg_count:
            sentiment = "positive"
        elif neg_count > pos_count:
            sentiment = "negative"
        
        email.sentiment = sentiment
        db.commit()
        
        logger.info(f"✅ Sentiment: {sentiment}")
        return {
            "email_id": email_id,
            "sentiment": sentiment
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Sentiment analysis failed: {e}")
        raise
    finally:
        db.close()
