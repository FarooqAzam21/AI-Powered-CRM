import hmac
import hashlib
import json
import httpx
import logging
import threading
import time
from sqlalchemy.orm import Session
from datetime import datetime
from auth.models import WebhookSubscription, WebhookDelivery

logger = logging.getLogger(__name__)

def calculate_signature(secret: str, payload_str: str) -> str:
    """
    Computes HMAC-SHA256 signature for a payload string using a secret.
    """
    return hmac.new(
        secret.encode('utf-8'),
        payload_str.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

def trigger_webhook_event(db: Session, workspace_id: int, event_type: str, data: dict):
    """
    Looks up active subscriptions for the given workspace, checks event match,
    and triggers asynchronous delivery.
    """
    try:
        subscriptions = db.query(WebhookSubscription).filter(
            WebhookSubscription.workspace_id == workspace_id,
            WebhookSubscription.is_active == True
        ).all()
        
        for sub in subscriptions:
            if event_type not in sub.events and "*" not in sub.events:
                continue
                
            payload = {
                "event": event_type,
                "timestamp": datetime.utcnow().isoformat(),
                "data": data
            }
            payload_str = json.dumps(payload, default=str)
            signature = calculate_signature(sub.secret_key, payload_str)
            
            # Fire delivery asynchronously in a background thread to prevent blocking
            threading.Thread(
                target=deliver_webhook,
                args=(sub.id, workspace_id, event_type, payload_str, signature, 1),
                daemon=True
            ).start()
    except Exception as e:
        logger.error(f"Failed to trigger webhook event: {e}")

def deliver_webhook(sub_id: int, workspace_id: int, event: str, payload_str: str, signature: str, attempt: int = 1):
    """
    Sends the signed HTTP request to the registered webhook endpoint,
    logging status and retrying up to 3 times on failure.
    """
    headers = {
        "Content-Type": "application/json",
        "X-Webhook-Signature": signature,
        "X-Webhook-Event": event
    }
    
    from database import SessionLocal
    db = SessionLocal()
    
    try:
        sub = db.query(WebhookSubscription).filter(WebhookSubscription.id == sub_id).first()
        if not sub or not sub.is_active:
            return
            
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(sub.url, content=payload_str, headers=headers)
                response_code = response.status_code
                response_body = response.text[:2000]
                status = "success" if 200 <= response_code < 300 else "failed"
        except Exception as exc:
            response_code = None
            response_body = str(exc)[:2000]
            status = "failed"
            
        # Log delivery
        delivery = WebhookDelivery(
            workspace_id=workspace_id,
            subscription_id=sub_id,
            event=event,
            payload=payload_str,
            response_code=response_code,
            response_body=response_body,
            status=status,
            attempt_number=attempt,
            created_at=datetime.utcnow()
        )
        db.add(delivery)
        db.commit()
        
        # Retry failed delivery with backoff (5s, 10s)
        if status == "failed" and attempt < 3:
            time.sleep(5 * attempt)
            deliver_webhook(sub_id, workspace_id, event, payload_str, signature, attempt + 1)
            
    except Exception as e:
        logger.error(f"Error executing webhook delivery: {e}")
    finally:
        db.close()
