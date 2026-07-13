from datetime import datetime
from email.utils import parseaddr

from auth.models import User
from crm_email.gmail_cursor_manager import get_or_create_cursor, update_cursor
from gmail_service import get_gmail_service
from models.crm import EmailMetadata
from services.crm_service import upsert_contact_from_email
from services.email_classification_service import apply_learned_rule


def _headers(headers):
    return {h.get("name", "").lower(): h.get("value", "") for h in headers}


def _to_datetime(internal_date):
    if not internal_date:
        return None
    return datetime.utcfromtimestamp(int(internal_date) / 1000)


def _process_message_detail(db, user, detail):
    gmail_id = detail.get("id")
    if not gmail_id:
        return False
    headers = _headers(detail.get("payload", {}).get("headers", []))
    sender_name, sender_email = parseaddr(headers.get("from", ""))
    label_ids = ",".join(detail.get("labelIds", []))
    internal_date = _to_datetime(detail.get("internalDate"))

    existing = db.query(EmailMetadata).filter(
        EmailMetadata.user_id == user.id,
        EmailMetadata.gmail_message_id == gmail_id,
    ).first()
    if existing:
        existing.thread_id = detail.get("threadId") or existing.thread_id
        existing.sender = sender_name or sender_email or existing.sender or "Unknown"
        existing.sender_email = (sender_email or existing.sender_email or "").lower()
        existing.subject = headers.get("subject", existing.subject or "No subject")
        existing.snippet = detail.get("snippet", existing.snippet or "")
        existing.label_ids = label_ids or existing.label_ids
        existing.internal_date = internal_date or existing.internal_date
        return False

    meta = EmailMetadata(
        user_id=user.id,
        gmail_message_id=gmail_id,
        thread_id=detail.get("threadId"),
        sender=sender_name or sender_email or "Unknown",
        sender_email=sender_email.lower(),
        subject=headers.get("subject", "No subject"),
        snippet=detail.get("snippet", ""),
        label_ids=label_ids,
        internal_date=internal_date,
    )
    db.add(meta)
    db.flush()
    apply_learned_rule(db, meta)
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
    return True


def sync_via_history(db, user: User, cursor, service, page_size: int) -> dict | None:
    if not cursor.last_history_id:
        return None
    try:
        history = (
            service.users()
            .history()
            .list(userId="me", startHistoryId=cursor.last_history_id, historyTypes=["messageAdded"], maxResults=page_size)
            .execute()
        )
    except Exception:
        return None

    inserted = 0
    for record in history.get("history", []):
        for added in record.get("messagesAdded", []):
            msg = added.get("message", {})
            gmail_id = msg.get("id")
            if not gmail_id:
                continue
            detail = service.users().messages().get(
                userId="me",
                id=gmail_id,
                format="metadata",
                metadataHeaders=["From", "Subject", "Date"],
            ).execute()
            if _process_message_detail(db, user, detail):
                inserted += 1

    update_cursor(db, cursor, next_page_token=None, last_history_id=history.get("historyId") or cursor.last_history_id)
    db.commit()
    return {"inserted": inserted, "seen": inserted, "mode": "history", "next_page_token": None}


def sync_metadata_page(db, user: User, page_size: int = 10, recent_first: bool = False) -> dict:
    cursor = get_or_create_cursor(db, user.id)
    service = get_gmail_service(user)

    if not recent_first:
        history_result = sync_via_history(db, user, cursor, service, page_size)
        if history_result and history_result.get("inserted", 0) > 0:
            return history_result

    page_token = None if recent_first else cursor.next_page_token
    query = "newer_than:30d" if recent_first else f"after:{cursor.after_timestamp}"

    result = service.users().messages().list(
        userId="me",
        labelIds=["INBOX"],
        q=query,
        maxResults=page_size,
        pageToken=page_token,
    ).execute()
    messages = result.get("messages", []) or []
    inserted = 0
    newest_seen = None
    newest_subject = None

    # Fetch details for all messages, sort by received time descending to ensure newest-first processing
    details = []
    for msg in messages:
        gmail_id = msg["id"]
        detail = service.users().messages().get(
            userId="me",
            id=gmail_id,
            format="metadata",
            metadataHeaders=["From", "Subject", "Date"],
        ).execute()
        details.append(detail)

    details.sort(key=lambda d: _to_datetime(d.get("internalDate")) or datetime.min, reverse=True)

    for detail in details:
        msg_dt = _to_datetime(detail.get("internalDate"))
        if msg_dt and (newest_seen is None or msg_dt > newest_seen):
            newest_seen = msg_dt
            newest_subject = _headers(detail.get("payload", {}).get("headers", [])).get("subject", detail.get("snippet", ""))
        if _process_message_detail(db, user, detail):
            inserted += 1

    update_cursor(
        db,
        cursor,
        next_page_token=None if recent_first else result.get("nextPageToken"),
        last_history_id=result.get("historyId") or cursor.last_history_id,
    )
    db.commit()
    return {
        "inserted": inserted,
        "seen": len(messages),
        "mode": "recent" if recent_first else "list",
        "newest_seen": newest_seen.isoformat() if newest_seen else None,
        "newest_subject": newest_subject,
        "next_page_token": None if recent_first else result.get("nextPageToken"),
    }
