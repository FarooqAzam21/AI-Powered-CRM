from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from auth.dependencies import get_current_user
from auth.models import User
from database import get_db
from gmail_service import fetch_email_body
from models.crm import EmailMetadata
from tasks.task_router import enqueue_task
from utils.sanitize import sanitize_email_html

router = APIRouter(prefix="/email", tags=["Email"])


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
        {"user_id": user.id},
        user_id=user.id,
    )
    return {"task_id": task["id"], "status": task["status"]}


@router.get("/metadata")
def list_metadata(limit: int = 30, offset: int = 0, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    user = _user(db, current_user)
    limit = min(max(limit, 1), 100)
    rows = db.query(EmailMetadata).filter(EmailMetadata.user_id == user.id).order_by(EmailMetadata.internal_date.desc().nullslast()).offset(offset).limit(limit).all()
    return rows


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


@router.post("/draft")
def request_draft(payload: dict, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    user = _user(db, current_user)
    task = enqueue_task("workers.email_tasks.generate_reply", "ai", payload, user_id=user.id)
    return {"task_id": task["id"], "status": task["status"]}
