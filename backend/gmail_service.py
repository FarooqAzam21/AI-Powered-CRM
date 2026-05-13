import os
import base64
from email.message import EmailMessage
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from auth.models import User

def get_gmail_service(user: User):
    """Build Gmail API service with user's tokens"""
    creds = Credentials(
        token=user.google_access_token,
        refresh_token=user.google_refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.getenv("GOOGLE_CLIENT_ID"),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET")
    )
    return build('gmail', 'v1', credentials=creds)

def fetch_unread_emails(user: User, max_results=10):
    """Fetch unread emails from user's inbox"""
    try:
        service = get_gmail_service(user)
        results = service.users().messages().list(
            userId='me',
            labelIds=['INBOX', 'UNREAD'],
            maxResults=max_results
        ).execute()
        
        message_list = results.get('messages', [])
        emails = []
        
        for msg in message_list:
            email_data = service.users().messages().get(
                userId='me', 
                id=msg['id'],
                format='full'
            ).execute()
            
            # Basic parsing
            headers = email_data.get('payload', {}).get('headers', [])
            subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), "No Subject")
            sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), "Unknown")
            
            # Simple body extraction
            body = ""
            if 'parts' in email_data['payload']:
                for part in email_data['payload']['parts']:
                    if part['mimeType'] == 'text/plain':
                        data = part['body'].get('data')
                        if data:
                            body = base64.urlsafe_b64decode(data).decode()
                            break
            else:
                data = email_data['payload'].get('body', {}).get('data')
                if data:
                    body = base64.urlsafe_b64decode(data).decode()
            
            emails.append({
                "gmail_id": msg['id'],
                "subject": subject,
                "sender": sender,
                "body": body
            })
            
        return emails
    except HttpError as error:
        print(f"An error occurred: {error}")
        return []

def send_gmail_reply(user: User, to: str, subject: str, body: str, thread_id: str = None):
    """Send an email reply via Gmail API"""
    try:
        service = get_gmail_service(user)
        
        message = EmailMessage()
        message.set_content(body)
        message['To'] = to
        message['From'] = user.email
        message['Subject'] = subject if subject.startswith("Re:") else f"Re: {subject}"

        # encoded message
        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

        create_message = {
            'raw': encoded_message
        }
        
        if thread_id:
            create_message['threadId'] = thread_id

        send_message = service.users().messages().send(
            userId="me",
            body=create_message
        ).execute()
        
        return send_message
    except HttpError as error:
        print(f"An error occurred: {error}")
        return None

def mark_email_as_read(user: User, message_id: str):
    """Remove UNREAD label from a message"""
    try:
        service = get_gmail_service(user)
        service.users().messages().modify(
            userId='me',
            id=message_id,
            body={'removeLabelIds': ['UNREAD']}
        ).execute()
        return True
    except HttpError as error:
        print(f"An error occurred: {error}")
        return False
