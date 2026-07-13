from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ai.ai_generator import get_ai_generator
from auth.dependencies import get_current_user
from auth.models import User
from database import get_db
from gmail_service import fetch_email_body
from models.crm import Contact, EmailMetadata
from services.email_classification_service import apply_learned_rule, learn_rule_from_email
from tasks.task_router import enqueue_task
from utils.sanitize import sanitize_email_html, sanitize_text

router = APIRouter(prefix="/email", tags=["Email"])


class ClassifyBatchRequest(BaseModel):
    ids: list[str] | None = None
    limit: int = 10


class ManualClassifyRequest(BaseModel):
    category: str
    learn: bool = True


def _user(db: Session, token: dict) -> User:
    user = db.query(User).filter(User.email == token["sub"]).first()
    if not user:
        raise HTTPException(404, "User not found")
    return user


@router.post("/sync")
def start_sync(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    user = _user(db, current_user)
    if not user.gmail_connected:
        raise HTTPException(400, "Gmail is not connected")
    task = enqueue_task(
        "workers.email_tasks.sync_gmail_metadata",
        "email",
        {"user_id": user.id, "recent_first": True},
        user_id=user.id,
    )
    return {"task_id": task["id"], "status": task["status"], "result": task.get("result")}


def _serialize_email_meta(meta: EmailMetadata, contact: Contact | None = None) -> dict:
    return {
        "id": meta.id,
        "gmail_message_id": meta.gmail_message_id,
        "thread_id": meta.thread_id,
        "sender": meta.sender,
        "sender_email": meta.sender_email,
        "subject": meta.subject,
        "snippet": meta.snippet,
        "label_ids": meta.label_ids,
        "internal_date": meta.internal_date.isoformat() if meta.internal_date else None,
        "body_fetched": meta.body_fetched,
        "ai_status": meta.ai_status,
        "contact_id": contact.id if contact else None,
        "contact_name": contact.name if contact else None,
        "company": contact.company if contact else None,
    }


@router.get("/metadata")
def list_metadata(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    q: str | None = Query(None, max_length=120),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = _user(db, current_user)
    query = db.query(EmailMetadata).filter(EmailMetadata.user_id == user.id)
    if q:
        term = f"%{sanitize_text(q, 120)}%"
        query = query.outerjoin(
            Contact,
            (Contact.user_id == user.id) & (Contact.email == EmailMetadata.sender_email),
        ).filter(
            or_(
                EmailMetadata.sender.ilike(term),
                EmailMetadata.sender_email.ilike(term),
                EmailMetadata.subject.ilike(term),
                EmailMetadata.snippet.ilike(term),
                Contact.name.ilike(term),
                Contact.company.ilike(term),
            )
        )
    rows = query.order_by(EmailMetadata.internal_date.desc().nullslast(), EmailMetadata.id.desc()).offset(offset).limit(limit).all()
    results = []
    for meta in rows:
        contact = None
        if meta.sender_email:
            contact = db.query(Contact).filter(Contact.user_id == user.id, Contact.email == meta.sender_email).first()
        results.append(_serialize_email_meta(meta, contact))
    return results


@router.get("/search")
def search_metadata(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    q: str | None = Query(None, max_length=120),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = _user(db, current_user)
    query = db.query(EmailMetadata).filter(EmailMetadata.user_id == user.id)
    if q:
        term = f"%{sanitize_text(q, 120)}%"
        query = query.outerjoin(
            Contact,
            (Contact.user_id == user.id) & (Contact.email == EmailMetadata.sender_email),
        ).filter(
            or_(
                EmailMetadata.sender.ilike(term),
                EmailMetadata.sender_email.ilike(term),
                EmailMetadata.subject.ilike(term),
                EmailMetadata.snippet.ilike(term),
                Contact.name.ilike(term),
                Contact.company.ilike(term),
            )
        )
    rows = query.order_by(EmailMetadata.internal_date.desc().nullslast(), EmailMetadata.id.desc()).offset(offset).limit(limit).all()
    results = []
    for meta in rows:
        contact = None
        if meta.sender_email:
            contact = db.query(Contact).filter(Contact.user_id == user.id, Contact.email == meta.sender_email).first()
        results.append(_serialize_email_meta(meta, contact))
    return results


@router.get("/{gmail_message_id}")
def get_email(
    gmail_message_id: str,
    include_body: bool = Query(False),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = _user(db, current_user)
    meta = db.query(EmailMetadata).filter(EmailMetadata.user_id == user.id, EmailMetadata.gmail_message_id == gmail_message_id).first()
    if not meta:
        raise HTTPException(404, "Email not found")

    contact = None
    if meta.sender_email:
        contact = db.query(Contact).filter(Contact.user_id == user.id, Contact.email == meta.sender_email).first()

    email_data = _serialize_email_meta(meta, contact)
    email_data["recipient"] = user.email
    email_data["source"] = "gmail"

    if include_body or meta.body_fetched:
        body = fetch_email_body(user, gmail_message_id)
        if isinstance(body, dict) and "body" in body:
            email_data["body"] = sanitize_email_html(body.get("body"))
            meta.body_fetched = True
            db.commit()
        else:
            email_data["body"] = ""
    else:
        email_data["body"] = None

    return email_data


@router.get("/body/{gmail_message_id}")
def get_body(gmail_message_id: str, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    user = _user(db, current_user)
    meta = db.query(EmailMetadata).filter(EmailMetadata.user_id == user.id, EmailMetadata.gmail_message_id == gmail_message_id).first()
    if not meta:
        raise HTTPException(404, "Email not found")
    body = fetch_email_body(user, gmail_message_id)
    if isinstance(body, dict) and "body" in body:
        body["body"] = sanitize_email_html(body.get("body"))
    meta.body_fetched = True
    db.commit()
    return body


@router.post("/classify/{gmail_message_id}")
async def classify_synced_email(gmail_message_id: str, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    user = _user(db, current_user)
    meta = db.query(EmailMetadata).filter(EmailMetadata.user_id == user.id, EmailMetadata.gmail_message_id == gmail_message_id).first()
    if not meta:
        raise HTTPException(404, "Email not found")

    learned = apply_learned_rule(db, meta)
    if learned:
        db.commit()
        db.refresh(meta)
        return {
            "email": meta,
            "classification": {"category": learned, "confidence": 1.0, "action": "learned_rule", "priority": "medium"},
            "source": "learned_rule",
        }

    try:
        meta.ai_status = "processing"
        db.commit()
        generator = get_ai_generator()
        result = await generator.generate_classification(
            subject=meta.subject or "",
            body=meta.snippet or "",
        )
        category = str(result.get("category") or "classified")[:80]
        meta.ai_status = category or "classified"
        if category and category not in {"unknown", "classified"}:
            learn_rule_from_email(db, meta, category)
        db.commit()
        db.refresh(meta)
        return {"email": meta, "classification": result, "source": "ai"}
    except Exception as exc:
        meta.ai_status = "failed"
        db.commit()
        raise HTTPException(500, f"Classification failed: {exc}")


@router.post("/classify/{gmail_message_id}/manual")
def manually_classify_synced_email(
    gmail_message_id: str,
    payload: ManualClassifyRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = _user(db, current_user)
    meta = db.query(EmailMetadata).filter(EmailMetadata.user_id == user.id, EmailMetadata.gmail_message_id == gmail_message_id).first()
    if not meta:
        raise HTTPException(404, "Email not found")

    category = sanitize_text(payload.category, 80).strip()
    if not category:
        raise HTTPException(400, "Category is required")

    meta.ai_status = category
    rule = learn_rule_from_email(db, meta, category) if payload.learn else None
    db.commit()
    db.refresh(meta)
    return {
        "email": meta,
        "classification": {"category": category, "confidence": 1.0, "action": "user_label", "priority": "medium"},
        "rule_id": rule.id if rule else None,
        "source": "manual",
    }


@router.post("/classify")
async def classify_synced_email_batch(payload: ClassifyBatchRequest, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    user = _user(db, current_user)
    limit = min(max(payload.limit, 1), 25)
    query = db.query(EmailMetadata).filter(EmailMetadata.user_id == user.id)
    if payload.ids:
        query = query.filter(EmailMetadata.gmail_message_id.in_(payload.ids))
    else:
        query = query.filter(EmailMetadata.ai_status.in_(["queued", "failed", "unknown"]))

    rows = query.order_by(EmailMetadata.internal_date.desc().nullslast(), EmailMetadata.id.desc()).limit(limit).all()
    generator = get_ai_generator()
    results = []

    for meta in rows:
        learned = apply_learned_rule(db, meta)
        if learned:
            db.commit()
            results.append(
                {
                    "gmail_message_id": meta.gmail_message_id,
                    "status": "classified",
                    "source": "learned_rule",
                    "classification": {"category": learned, "confidence": 1.0, "action": "learned_rule", "priority": "medium"},
                }
            )
            continue

        try:
            meta.ai_status = "processing"
            db.commit()
            result = await generator.generate_classification(
                subject=meta.subject or "",
                body=meta.snippet or "",
            )
            category = str(result.get("category") or "classified")[:80]
            meta.ai_status = category or "classified"
            if category and category not in {"unknown", "classified"}:
                learn_rule_from_email(db, meta, category)
            db.commit()
            db.refresh(meta)
            results.append({"gmail_message_id": meta.gmail_message_id, "status": "classified", "source": "ai", "classification": result})
        except Exception as exc:
            meta.ai_status = "failed"
            db.commit()
            results.append({"gmail_message_id": meta.gmail_message_id, "status": "failed", "error": str(exc)})

    return {"count": len(results), "results": results}


@router.post("/draft")
def request_draft(payload: dict, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    user = _user(db, current_user)
    task = enqueue_task("workers.email_tasks.generate_reply", "ai", payload, user_id=user.id)
    return {"task_id": task["id"], "status": task["status"]}


@router.get("/context/{gmail_message_id}")
def get_email_context(
    gmail_message_id: str,
    include_body: bool = Query(False),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = _user(db, current_user)
    meta = db.query(EmailMetadata).filter(EmailMetadata.user_id == user.id, EmailMetadata.gmail_message_id == gmail_message_id).first()
    if not meta:
        raise HTTPException(404, "Email not found")

    contact = None
    if meta.sender_email:
        contact = db.query(Contact).filter(Contact.user_id == user.id, Contact.email == meta.sender_email).first()

    email_data = _serialize_email_meta(meta, contact)
    email_data["recipient"] = user.email
    email_data["contact_id"] = contact.id if contact else None
    email_data["thread_id"] = meta.thread_id
    email_data["body"] = None

    if include_body or meta.body_fetched:
        body = fetch_email_body(user, gmail_message_id)
        if isinstance(body, dict) and "body" in body:
            email_data["body"] = sanitize_email_html(body.get("body"))
            meta.body_fetched = True
            db.commit()

    email_data["crm_context"] = {
        "contact_id": contact.id if contact else None,
        "contact_name": contact.name if contact else None,
        "company": contact.company if contact else None,
        "lead_score": contact.lead.score if contact and contact.lead else None,
        "pipeline_stage": contact.lead.label if contact and contact.lead else None,
    }

    return email_data
