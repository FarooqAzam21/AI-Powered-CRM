"""
One-time migration: copy legacy contacts/leads/deals into crm_* tables.
Safe to run repeatedly — skips rows that already exist.
"""
import logging
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def sync_legacy_crm_data(db: Session) -> dict:
    stats = {"contacts": 0, "leads": 0, "deals": 0}
    try:
        from auth.models import Contact as LegacyContact
        from auth.models import Deal as LegacyDeal
        from auth.models import Lead as LegacyLead
        from models.crm import Contact, Deal, Lead
    except ImportError as exc:
        logger.warning("Legacy CRM models unavailable: %s", exc)
        return stats

    id_map: dict[int, int] = {}

    for legacy in db.query(LegacyContact).all():
        existing = (
            db.query(Contact)
            .filter(Contact.user_id == legacy.user_id, Contact.email == legacy.email.lower())
            .first()
        )
        if existing:
            id_map[legacy.id] = existing.id
            continue
        contact = Contact(
            user_id=legacy.user_id,
            email=(legacy.email or "").lower(),
            name=legacy.name or "",
            company=legacy.company or "",
            title=legacy.title or "",
            source="legacy_import",
            last_interaction_at=legacy.last_interaction_at,
        )
        db.add(contact)
        db.flush()
        id_map[legacy.id] = contact.id
        stats["contacts"] += 1

    for legacy in db.query(LegacyLead).all():
        contact_id = id_map.get(legacy.contact_id)
        if not contact_id:
            continue
        existing = db.query(Lead).filter(Lead.user_id == legacy.user_id, Lead.contact_id == contact_id).first()
        if existing:
            continue
        label = legacy.temperature or "cold"
        if label not in {"hot", "warm", "cold"}:
            label = "warm" if (legacy.score or 0) >= 40 else "cold"
        db.add(
            Lead(
                user_id=legacy.user_id,
                contact_id=contact_id,
                score=legacy.score or 0.0,
                label=label,
                recommended_next_action=legacy.ai_notes or "Review contact",
            )
        )
        stats["leads"] += 1

    for legacy in db.query(LegacyDeal).all():
        contact_id = id_map.get(legacy.contact_id) if legacy.contact_id else None
        existing = db.query(Deal).filter(
            Deal.user_id == legacy.user_id,
            Deal.title == legacy.name,
            Deal.value == (legacy.value or 0.0),
        ).first()
        if existing:
            continue
        db.add(
            Deal(
                user_id=legacy.user_id,
                contact_id=contact_id,
                title=legacy.name,
                description=legacy.description or "",
                stage=legacy.stage or "prospecting",
                status=legacy.status or "open",
                value=legacy.value or 0.0,
                probability=legacy.probability if legacy.probability is not None else 10.0,
                expected_close_at=legacy.expected_close_date,
                actual_close_at=legacy.actual_close_date,
                stage_moved_at=legacy.stage_moved_at,
                close_reason=legacy.close_reason or "",
                ai_score=legacy.ai_score or 0.0,
                ai_recommendation=legacy.ai_recommendation or "",
            )
        )
        stats["deals"] += 1

    if any(stats.values()):
        db.commit()
        logger.info("Legacy CRM sync complete: %s", stats)
    return stats
