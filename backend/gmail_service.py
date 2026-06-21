import base64
from email.message import EmailMessage

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from auth.models import User
from config.settings import get_settings
from utils.security import decrypt_secret


def get_gmail_service(user: User):
    settings = get_settings()
    creds = Credentials(
        token=decrypt_secret(user.google_access_token),
        refresh_token=decrypt_secret(user.google_refresh_token),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
    )
    return build("gmail", "v1", credentials=creds)


def fetch_unread_emails(user: User, max_results=10):
    """Legacy compatibility wrapper. Prefer metadata-first sync."""
    try:
        service = get_gmail_service(user)
        results = service.users().messages().list(
            userId="me",
            labelIds=["INBOX", "UNREAD"],
            maxResults=max_results,
        ).execute()
        emails = []
        for msg in results.get("messages", []):
            body = fetch_email_body(user, msg["id"])
            emails.append({
                "gmail_id": msg["id"],
                "subject": body.get("subject", ""),
                "sender": body.get("sender", ""),
                "body": body.get("body", ""),
            })
        return emails
    except HttpError as error:
        print(f"An error occurred: {error}")
        return []


def fetch_email_body(user: User, message_id: str):
    """Fetch a full email body only when the UI opens that message."""
    try:
        service = get_gmail_service(user)
        email_data = service.users().messages().get(userId="me", id=message_id, format="full").execute()
        headers = email_data.get("payload", {}).get("headers", [])
        subject = next((h["value"] for h in headers if h["name"].lower() == "subject"), "No Subject")
        sender = next((h["value"] for h in headers if h["name"].lower() == "from"), "Unknown")
        return {
            "gmail_message_id": message_id,
            "subject": subject,
            "sender": sender,
            "body": _extract_body(email_data.get("payload", {})),
        }
    except HttpError as error:
        print(f"An error occurred: {error}")
        return {"gmail_message_id": message_id, "body": ""}


def send_gmail_message(user: User, to: str, subject: str, body: str):
    """Send a new email (not a reply). Used by campaigns."""
    try:
        service = get_gmail_service(user)
        message = EmailMessage()
        message.set_content(body)
        message["To"] = to
        message["From"] = user.email
        message["Subject"] = subject
        create_message = {"raw": base64.urlsafe_b64encode(message.as_bytes()).decode()}
        return service.users().messages().send(userId="me", body=create_message).execute()
    except HttpError as error:
        print(f"An error occurred: {error}")
        return None


def send_gmail_reply(user: User, to: str, subject: str, body: str, thread_id: str = None):
    try:
        service = get_gmail_service(user)
        message = EmailMessage()
        message.set_content(body)
        message["To"] = to
        message["From"] = user.email
        message["Subject"] = subject if subject.startswith("Re:") else f"Re: {subject}"

        create_message = {"raw": base64.urlsafe_b64encode(message.as_bytes()).decode()}
        if thread_id:
            create_message["threadId"] = thread_id
        return service.users().messages().send(userId="me", body=create_message).execute()
    except HttpError as error:
        print(f"An error occurred: {error}")
        return None


def mark_email_as_read(user: User, message_id: str):
    try:
        service = get_gmail_service(user)
        service.users().messages().modify(
            userId="me",
            id=message_id,
            body={"removeLabelIds": ["UNREAD"]},
        ).execute()
        return True
    except HttpError as error:
        print(f"An error occurred: {error}")
        return False


def _extract_body(payload):
    data = payload.get("body", {}).get("data")
    if data:
        return base64.urlsafe_b64decode(data).decode(errors="ignore")
    for part in payload.get("parts", []):
        if part.get("mimeType") == "text/plain":
            data = part.get("body", {}).get("data")
            if data:
                return base64.urlsafe_b64decode(data).decode(errors="ignore")
        nested = _extract_body(part)
        if nested:
            return nested
    return ""
