import json
import re
from datetime import datetime

from cache.redis_client import cache_json, get_cached_json
from models.crm import AIInsight, Contact, Interaction, Lead

BUYING_WORDS = {"pricing", "quote", "demo", "proposal", "buy", "purchase", "contract", "budget"}
URGENT_WORDS = {"urgent", "asap", "today", "immediately", "deadline", "blocked"}
HIRING_WORDS = {"hire", "hiring", "job", "candidate", "resume", "interview", "recruit"}


def extract_company(email: str) -> str:
    domain = (email or "").split("@")[-1].lower()
    if domain in {"gmail.com", "outlook.com", "hotmail.com", "yahoo.com"}:
        return ""
    return domain.split(".")[0].replace("-", " ").title()


def upsert_contact_from_email(db, user_id: int, sender: str, sender_email: str, subject: str, snippet: str, gmail_message_id: str, occurred_at=None):
    sender_email = (sender_email or "").lower()
    if not sender_email:
        return None
    contact = db.query(Contact).filter(Contact.user_id == user_id, Contact.email == sender_email).first()
    if not contact:
        contact = Contact(
            user_id=user_id,
            email=sender_email,
            name=sender or sender_email,
            company=extract_company(sender_email),
            source="gmail",
        )
        db.add(contact)
        db.flush()
    contact.last_interaction_at = occurred_at or datetime.utcnow()
    interaction = Interaction(
        user_id=user_id,
        contact_id=contact.id,
        gmail_message_id=gmail_message_id,
        subject=subject or "",
        snippet=snippet or "",
        occurred_at=occurred_at or datetime.utcnow(),
    )
    db.add(interaction)
    score = score_lead(subject=f"{subject} {snippet}", interaction_count=len(contact.interactions) + 1)
    lead = contact.lead or Lead(user_id=user_id, contact_id=contact.id)
    lead.score = score["score"]
    lead.label = score["label"]
    lead.confidence = score["confidence"]
    lead.recommended_next_action = score["recommended_next_action"]
    lead.buying_intent = score["buying_intent"]
    lead.urgency = score["urgency"]
    lead.hiring_intent = score["hiring_intent"]
    db.add(lead)
    cache_json(f"lead_score:{user_id}:{sender_email}", score, ttl=3600)
    if score["label"] == "hot":
        db.add(
            AIInsight(
                user_id=user_id,
                contact_id=contact.id,
                insight_type="hot_lead",
                payload=json.dumps(score),
                confidence=score["confidence"],
            )
        )
    return contact


def score_lead(subject: str, interaction_count: int = 1) -> dict:
    text = set(re.findall(r"[a-z]+", (subject or "").lower()))
    buying = len(text & BUYING_WORDS) / max(len(BUYING_WORDS), 1)
    urgency = len(text & URGENT_WORDS) / max(len(URGENT_WORDS), 1)
    hiring = len(text & HIRING_WORDS) / max(len(HIRING_WORDS), 1)
    engagement = min(interaction_count * 8, 30)
    raw = min(100, engagement + buying * 45 + urgency * 20 + hiring * 25)
    label = "hot" if raw >= 70 else "warm" if raw >= 40 else "cold"
    action = "Reply within 1 hour" if label == "hot" else "Send personalized follow-up" if label == "warm" else "Add to nurture sequence"
    return {
        "score": round(raw, 1),
        "label": label,
        "confidence": round(min(0.95, 0.45 + interaction_count * 0.05 + buying + urgency), 2),
        "recommended_next_action": action,
        "buying_intent": round(buying, 2),
        "urgency": round(urgency, 2),
        "hiring_intent": round(hiring, 2),
    }
