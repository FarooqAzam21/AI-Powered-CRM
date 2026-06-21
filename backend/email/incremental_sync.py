import re
from datetime import datetime
from email.utils import parseaddr

from auth.models import User
from email.gmail_cursor_manager import get_or_create_cursor, update_cursor
from gmail_service import get_gmail_service
from models.crm import EmailMetadata
from services.crm_service import upsert_contact_from_email


def _headers(headers):
    return {h.get("name", "").lower(): h.get("value", "") for h in headers}


def _to_datetime(internal_date):
    if not internal_date:
        return None
    return datetime.utcfromtimestamp(int(internal_date) / 1000)


def sync_metadata_page(db, user: User, page_size: int = 10) -> dict:
    cursor = get_or_create_cursor(db, user.id)
    service = get_gmail_service(user)
    query = f"after:{cursor.after_timestamp}"
    list_call = service.users().messages().list(
        userId="me",
        labelIds=["INBOX"],
        q=query,
        maxResults=page_size,
        pageToken=cursor.next_page_token,
    )
    result = list_call.execute()
    messages = result.get("messages", [])
    inserted = 0

    for msg in messages:
        gmail_id = msg["id"]
        existing = db.query(EmailMetadata).filter(
            EmailMetadata.user_id == user.id,
            EmailMetadata.gmail_message_id == gmail_id,
        ).first()
        if existing:
            continue
        detail = service.users().messages().get(
            userId="me",
            id=gmail_id,
            format="metadata",
            metadataHeaders=["From", "Subject", "Date"],
        ).execute()
        headers = _headers(detail.get("payload", {}).get("headers", []))
        sender_name, sender_email = parseaddr(headers.get("from", ""))
        meta = EmailMetadata(
            user_id=user.id,
            gmail_message_id=gmail_id,
            thread_id=detail.get("threadId"),
            sender=sender_name or sender_email or "Unknown",
            sender_email=sender_email.lower(),
            subject=headers.get("subject", "No subject"),
            snippet=detail.get("snippet", ""),
            label_ids=",".join(detail.get("labelIds", [])),
            internal_date=_to_datetime(detail.get("internalDate")),
        )
        db.add(meta)
        upsert_contact_from_email(
            db,
            user_id=user.id,
            sender=meta.sender,
            sender_email=meta.sender_email,
            subject=meta.subject,
            snippet=meta.snippet,
            gmail_message_id=gmail_id,
            occurred_at=meta.internal_date,
        )
        inserted += 1

    update_cursor(db, cursor, next_page_token=result.get("nextPageToken"), last_history_id=result.get("historyId"))
    db.commit()
    return {"inserted": inserted, "seen": len(messages), "next_page_token": result.get("nextPageToken")}
