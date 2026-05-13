from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional
import os
from datetime import datetime
from sqlalchemy.orm import Session
from dotenv import load_dotenv

load_dotenv()

# ================= CORE LOGIC =================
from email_classifier import classify_email
from decision_engine import decide_action
from responder import generate_reply
from auth.auth_router import router as auth_router
from google_auth import router as google_router
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base, SessionLocal
from auth.models import User, Email, Notification
from auth.dependencies import get_current_user
from gmail_service import fetch_unread_emails, send_gmail_reply, mark_email_as_read

app = FastAPI(title="AI Email Agent")

@app.get("/ping")
def ping():
    return {"status": "ok", "message": "Backend is reachable"}

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(google_router)

# Init DB
Base.metadata.create_all(bind=engine)

# ================= MODELS =================
class EmailInbound(BaseModel):
    sender: str
    subject: str
    body: str

class EmailResponse(BaseModel):
    id: str
    category: str
    confidence: float
    action: str
    reason: str
    draft_reply: Optional[str] = None

# In-memory storage for demo (Move to DB later)
EMAILS_DB = []

# ================= ENDPOINTS =================

@app.get("/email/sync")
async def sync_emails(background_tasks: BackgroundTasks, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Manual trigger to sync emails from Gmail for the current user.
    """
    user = db.query(User).filter(User.email == current_user["sub"]).first()
    if not user or not user.gmail_connected:
        raise HTTPException(status_code=400, detail="Gmail not connected or user not found")

    # Fetch from Gmail
    new_emails = fetch_unread_emails(user)
    
    processed_count = 0
    for email_data in new_emails:
        # Check if already exists
        existing = db.query(Email).filter(Email.gmail_message_id == email_data["gmail_id"]).first()
        if existing:
            continue
            
        # 1. Analyze
        category, confidence = classify_email(email_data["subject"], email_data["body"])
        
        # 2. Decide
        action, reason = decide_action(category, confidence)
        
        # 3. Generate Draft
        draft_reply = None
        if action in ["REPLY_IMMEDIATELY", "DRAFT_RESPONSE"]:
            draft_reply = generate_reply(email_data["body"], category, "professional", confidence, [])

        # 4. Save to DB
        new_email = Email(
            user_id=user.id,
            gmail_message_id=email_data["gmail_id"],
            sender=email_data["sender"],
            subject=email_data["subject"],
            body=email_data["body"],
            category=category,
            confidence=confidence,
            action=action,
            reason=reason,
            draft_reply=draft_reply,
            status="SENT" if action == "REPLY_IMMEDIATELY" else "PENDING"
        )
        db.add(new_email)
        
        # 5. Alert if URGENT
        if category == "Urgent Support":
            notif = Notification(
                user_id=user.id,
                title="🚨 Urgent Email Received",
                message=f"Urgent support request from {email_data['sender']}",
                type="URGENT"
            )
            db.add(notif)
            
        # 6. Actually send if REPLY_IMMEDIATELY
        if action == "REPLY_IMMEDIATELY":
            send_gmail_reply(user, email_data["sender"], email_data["subject"], draft_reply, thread_id=email_data["gmail_id"])
            mark_email_as_read(user, email_data["gmail_id"])
            
        processed_count += 1
    
    db.commit()
    return {"message": f"Successfully processed {processed_count} new emails."}

@app.get("/email/history")
def get_email_history(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """Returns all processed emails for the current user."""
    user = db.query(User).filter(User.email == current_user["sub"]).first()
    return db.query(Email).filter(Email.user_id == user.id).order_by(Email.received_at.desc()).all()

@app.get("/email/drafts")
def get_pending_drafts(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """Returns only emails waiting for approval."""
    user = db.query(User).filter(User.email == current_user["sub"]).first()
    return db.query(Email).filter(
        Email.user_id == user.id, 
        Email.action == "DRAFT_RESPONSE", 
        Email.status == "PENDING"
    ).all()

@app.post("/email/approve/{email_id}")
def approve_draft(email_id: int, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """Approves a draft and marks it as SENT."""
    user = db.query(User).filter(User.email == current_user["sub"]).first()
    email = db.query(Email).filter(Email.id == email_id, Email.user_id == user.id).first()
    
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
        
    # Send via Gmail
    send_gmail_reply(user, email.sender, email.subject, email.draft_reply, thread_id=email.gmail_message_id)
    mark_email_as_read(user, email.gmail_message_id)
    
    email.status = "SENT"
    email.processed_at = datetime.utcnow()
    db.commit()
    
    return {"message": "Email approved and sent!", "email": {
        "id": email.id,
        "status": email.status
    }}

@app.get("/notifications")
def get_notifications(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get alerts for the user"""
    user = db.query(User).filter(User.email == current_user["sub"]).first()
    return db.query(Notification).filter(Notification.user_id == user.id, Notification.is_read == False).all()

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting AI Email Agent Backend...")
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
