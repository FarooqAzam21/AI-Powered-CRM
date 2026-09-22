"""
P6 — Webhook Celery Tasks
Asynchronous HTTP dispatch with exponential backoff retries and auto-deactivation
for persistently failing endpoints.
"""
import json
import logging
from datetime import datetime, timedelta
import requests

from tasks.celery_app import celery_app
from database import SessionLocal
from models.developer import WebhookEndpoint, WebhookDeliveryRecord

logger = logging.getLogger(__name__)

RETRY_BACKOFF_SECONDS = [30, 120, 600]  # 30s, 2m, 10m
MAX_ENDPOINT_FAILURES = 20              # Auto-deactivate endpoint after 20 consecutive failures


def execute_webhook_delivery(
    *,
    delivery_id: int,
    url: str,
    payload_json: str,
    signature: str,
    event_type: str,
    event_id: str,
    attempt: int = 1,
) -> bool:
    """
    Synchronous worker routine executing the HTTP POST and updating delivery records.
    """
    db = SessionLocal()
    try:
        delivery = db.query(WebhookDeliveryRecord).filter(WebhookDeliveryRecord.id == delivery_id).first()
        if not delivery:
            logger.error("WebhookDeliveryRecord %d not found", delivery_id)
            return False

        endpoint = db.query(WebhookEndpoint).filter(WebhookEndpoint.id == delivery.endpoint_id).first()
        if not endpoint or not endpoint.is_active:
            delivery.status = "failed"
            delivery.error_message = "Endpoint deleted or deactivated"
            db.commit()
            return False

        from utils.ssrf_guard import is_ssrf_safe_url
        from config.settings import get_settings
        settings = get_settings()
        safe, reason = is_ssrf_safe_url(url, allow_private=settings.allow_private_webhook_urls)
        if not safe:
            delivery.status = "failed"
            delivery.error_message = f"SSRF Security Block: {reason}"
            db.commit()
            logger.warning("SSRF Security Block on webhook delivery %d to URL '%s': %s", delivery_id, url, reason)
            return False

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "AI-CRM-Webhook/1.0",
            "X-CRM-Signature": signature,
            "X-CRM-Event": event_type,
            "X-CRM-Delivery": event_id,
        }

        try:
            resp = requests.post(url, data=payload_json, headers=headers, timeout=10)
            delivery.response_code = resp.status_code
            delivery.response_body = resp.text[:2000]
            success = 200 <= resp.status_code < 300
        except Exception as exc:
            delivery.response_code = None
            delivery.response_body = None
            delivery.error_message = str(exc)[:500]
            success = False

        if success:
            delivery.status = "success"
            delivery.delivered_at = datetime.utcnow()
            delivery.error_message = None
            endpoint.failure_count = 0  # Reset consecutive failures
            db.commit()
            return True
        else:
            endpoint.failure_count += 1
            endpoint.last_failure_at = datetime.utcnow()
            if endpoint.failure_count >= MAX_ENDPOINT_FAILURES:
                endpoint.is_active = False
                logger.warning("Endpoint %d exceeded max failure count (%d) — auto-deactivated", endpoint.id, MAX_ENDPOINT_FAILURES)

            if attempt < delivery.max_attempts:
                delivery.status = "retrying"
                backoff = RETRY_BACKOFF_SECONDS[min(attempt - 1, len(RETRY_BACKOFF_SECONDS) - 1)]
                delivery.next_retry_at = datetime.utcnow() + timedelta(seconds=backoff)
                delivery.attempt_number = attempt + 1
                db.commit()

                # Schedule retry via Celery if available
                try:
                    deliver_webhook_async.apply_async(
                        kwargs={
                            "delivery_id": delivery.id,
                            "url": url,
                            "payload_json": payload_json,
                            "signature": signature,
                            "event_type": event_type,
                            "event_id": event_id,
                            "attempt": attempt + 1,
                        },
                        countdown=backoff,
                        queue="webhooks",
                    )
                except Exception:
                    pass
            else:
                delivery.status = "failed"
                delivery.error_message = delivery.error_message or f"HTTP {delivery.response_code} (max attempts reached)"
                db.commit()

            return False
    finally:
        db.close()


@celery_app.task(name="tasks.webhook_tasks.deliver_webhook_async", bind=True, max_retries=0)
def deliver_webhook_async(self, delivery_id: int, url: str, payload_json: str, signature: str, event_type: str, event_id: str, attempt: int = 1):
    """
    Celery task wrapper for webhook delivery.
    """
    return execute_webhook_delivery(
        delivery_id=delivery_id,
        url=url,
        payload_json=payload_json,
        signature=signature,
        event_type=event_type,
        event_id=event_id,
        attempt=attempt,
    )
