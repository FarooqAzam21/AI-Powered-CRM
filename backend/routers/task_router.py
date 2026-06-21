"""
Task Status Router - Check Celery task status
Frontend polls this to get async task progress
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.orm import Session
from tasks.celery_app import celery_app
from auth.dependencies import get_current_user
from database import SessionLocal
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tasks", tags=["Tasks"])

# =================== PYDANTIC MODELS ===================
class TaskStatusResponse(BaseModel):
    task_id: str
    status: str  # pending, started, success, failure
    result: Optional[dict] = None
    error: Optional[str] = None
    progress: Optional[float] = None  # 0-100

class TaskSubmitResponse(BaseModel):
    task_id: str
    status: str
    message: str

# =================== TASK STATUS CHECKS ===================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/status/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get status of a Celery task
    
    Statuses:
    - pending: Task not yet started
    - started: Task is running
    - success: Task completed successfully
    - failure: Task failed
    - retry: Task will be retried
    """
    try:
        task = celery_app.AsyncResult(task_id)
        
        if task.state == "PENDING":
            response = {
                "task_id": task_id,
                "status": "pending",
                "progress": 0
            }
        elif task.state == "STARTED":
            response = {
                "task_id": task_id,
                "status": "started",
                "progress": 50
            }
        elif task.state == "SUCCESS":
            response = {
                "task_id": task_id,
                "status": "success",
                "result": task.result,
                "progress": 100
            }
        elif task.state == "FAILURE":
            response = {
                "task_id": task_id,
                "status": "failure",
                "error": str(task.info),
                "progress": 0
            }
        else:
            response = {
                "task_id": task_id,
                "status": task.state.lower(),
                "progress": 25
            }
        
        logger.info(f"✅ Task status: {response['status']}")
        return response
        
    except Exception as e:
        logger.error(f"❌ Error getting task status: {e}")
        raise HTTPException(status_code=500, detail="Error fetching task status")

@router.post("/classify-email/{email_id}", response_model=TaskSubmitResponse)
async def classify_email_async(
    email_id: int,
    current_user: dict = Depends(get_current_user)
):
    """
    Submit email for AI classification (async)
    Returns task_id to poll for results
    """
    try:
        from tasks.ai_tasks import classify_email_batch
        
        task = classify_email_batch.delay([email_id])
        
        logger.info(f"📧 Email classification submitted: {email_id} -> Task: {task.id}")
        
        return TaskSubmitResponse(
            task_id=task.id,
            status="pending",
            message=f"Email classification queued. Task ID: {task.id}"
        )
    except Exception as e:
        logger.error(f"❌ Error submitting classification: {e}")
        raise HTTPException(status_code=500, detail="Error submitting task")

@router.post("/score-lead/{lead_id}", response_model=TaskSubmitResponse)
async def score_lead_async(
    lead_id: int,
    current_user: dict = Depends(get_current_user)
):
    """
    Submit lead for AI scoring (async)
    """
    try:
        from tasks.lead_tasks import score_lead
        
        task = score_lead.delay(lead_id)
        
        logger.info(f"🎯 Lead scoring submitted: {lead_id} -> Task: {task.id}")
        
        return TaskSubmitResponse(
            task_id=task.id,
            status="pending",
            message=f"Lead scoring queued. Task ID: {task.id}"
        )
    except Exception as e:
        logger.error(f"❌ Error submitting score task: {e}")
        raise HTTPException(status_code=500, detail="Error submitting task")

@router.post("/sync-gmail", response_model=TaskSubmitResponse)
async def sync_gmail_async(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Trigger Gmail sync for current user (async)
    """
    try:
        from auth.models import User
        from tasks.email_tasks import sync_gmail_emails
        
        user = db.query(User).filter(User.email == current_user["sub"]).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        task = sync_gmail_emails.delay(user.id)
        
        logger.info(f"📧 Gmail sync submitted for {user.email} -> Task: {task.id}")
        
        return TaskSubmitResponse(
            task_id=task.id,
            status="pending",
            message=f"Gmail sync queued. Task ID: {task.id}"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error submitting sync task: {e}")
        raise HTTPException(status_code=500, detail="Error submitting task")

@router.post("/generate-reply/{email_id}", response_model=TaskSubmitResponse)
async def generate_reply_async(
    email_id: int,
    tone: str = "professional",
    current_user: dict = Depends(get_current_user)
):
    """
    Generate AI draft reply for email (async)
    """
    try:
        from tasks.email_tasks import generate_reply
        
        task = generate_reply.delay(email_id, tone)
        
        logger.info(f"✍️ Reply generation submitted: {email_id} -> Task: {task.id}")
        
        return TaskSubmitResponse(
            task_id=task.id,
            status="pending",
            message=f"Reply generation queued. Task ID: {task.id}"
        )
    except Exception as e:
        logger.error(f"❌ Error submitting reply task: {e}")
        raise HTTPException(status_code=500, detail="Error submitting task")

@router.post("/process-campaigns", response_model=TaskSubmitResponse)
async def process_campaigns_async(
    current_user: dict = Depends(get_current_user)
):
    """
    Trigger campaign processing (async)
    """
    try:
        from tasks.campaign_tasks import process_campaigns
        
        task = process_campaigns.delay()
        
        logger.info(f"📧 Campaign processing submitted -> Task: {task.id}")
        
        return TaskSubmitResponse(
            task_id=task.id,
            status="pending",
            message=f"Campaign processing queued. Task ID: {task.id}"
        )
    except Exception as e:
        logger.error(f"❌ Error submitting campaign task: {e}")
        raise HTTPException(status_code=500, detail="Error submitting task")

@router.get("/health")
async def tasks_health():
    """
    Check if Celery is running and accessible
    """
    try:
        # Send a ping to Celery
        celery_app.control.inspect().ping()
        
        return {
            "status": "healthy",
            "celery": "connected",
            "broker": "redis" if "redis" in str(celery_app.conf.broker_url) else "unknown"
        }
    except Exception as e:
        logger.error(f"❌ Celery health check failed: {e}")
        return {
            "status": "unhealthy",
            "celery": "disconnected",
            "error": str(e)
        }
