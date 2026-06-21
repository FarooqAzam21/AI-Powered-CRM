import time
from datetime import datetime

from models.crm import GmailSyncCursor


def get_or_create_cursor(db, user_id: int) -> GmailSyncCursor:
    cursor = db.query(GmailSyncCursor).filter(GmailSyncCursor.user_id == user_id).first()
    if cursor:
        return cursor
    cursor = GmailSyncCursor(user_id=user_id, after_timestamp=int(time.time()) - 14 * 86400)
    db.add(cursor)
    db.commit()
    db.refresh(cursor)
    return cursor


def update_cursor(db, cursor: GmailSyncCursor, next_page_token=None, last_history_id=None):
    cursor.next_page_token = next_page_token
    if last_history_id:
        cursor.last_history_id = last_history_id
    cursor.last_sync_at = datetime.utcnow()
    if not next_page_token:
        cursor.after_timestamp = int(time.time()) - 60
    db.commit()
    db.refresh(cursor)
    return cursor
