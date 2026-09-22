"""
P6 — Outbound Webhook Dispatcher
Handles event emission, matching subscribed endpoints, generating HMAC signatures,
and scheduling Celery async deliveries.
"""
import time
import hmac
import hashlib
import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from models.developer import WebhookEndpoint, WebhookDeliveryRecord

logger = logging.getLogger(__name__)

# Valid CRM Outbound Webhook Events
VALID_WEBHOOK_EVENTS = {
    "contact.created",
    "contact.updated",
    "contact.deleted",
    "deal.created",
    "deal.updated",
    "deal.stage_changed",
    "email.received",
    "task.created",
    "task.completed",
    "workflow.completed",
    "workflow.failed",
    "approval.created",
    "approval.completed",
}


def calculate_webhook_signature(secret_key: str, payload_bytes: bytes, timestamp: int) -> str:
    """
    Computes HMAC-SHA256 signature in the format:
    t=<timestamp>,v1=<hex_signature>
    Matching modern standard webhook signature protocols (Stripe/GitHub style).
    """
    to_sign = f"{timestamp}.".encode("utf-8") + payload_bytes
    sig = hmac.new(secret_key.encode("utf-8"), to_sign, hashlib.sha256).hexdigest()
    return f"t={timestamp},v1={sig}"


def verify_webhook_signature(secret_key: str, payload_bytes: bytes, signature_header: str, tolerance_seconds: int = 300) -> bool:
    """
    Validates HMAC signature and verifies timestamp freshness against replay attacks.
    """
    try:
        parts = dict(pair.split("=", 1) for pair in signature_header.split(","))
        timestamp = int(parts.get("t", 0))
        received_sig = parts.get("v1", "")

        now = int(time.time())
        if abs(now - timestamp) > tolerance_seconds:
            logger.warning("Webhook signature timestamp expired or in future (now=%s, header=%s)", now, timestamp)
            return False

        expected = hmac.new(
            secret_key.encode("utf-8"),
            f"{timestamp}.".encode("utf-8") + payload_bytes,
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(expected, received_sig)
    except Exception as exc:
        logger.error("Error verifying webhook signature: %s", exc)
        return False


def _sanitize_webhook_payload(data: Dict[str, Any]) -> Dict[str, Any]:
    """Redact sensitive fields from webhook data payloads."""
    sensitive_keys = {"password", "secret", "token", "api_key", "raw_email_body", "credit_card"}
    sanitized = {}
    for k, v in data.items():
        if any(s in k.lower() for s in sensitive_keys):
            sanitized[k] = "[REDACTED]"
        elif isinstance(v, dict):
            sanitized[k] = _sanitize_webhook_payload(v)
        else:
            sanitized[k] = v
    return sanitized


class WebhookDispatcher:

    @staticmethod
    def dispatch_event(
        *,
        event_type: str,
        workspace_id: int,
        organization_id: int,
        data: Dict[str, Any],
        db: Session,
    ) -> int:
        """
        Finds all active webhook endpoints matching the workspace & event_type,
        creates WebhookDeliveryRecord entries, and enqueues Celery delivery tasks.
        Returns the number of endpoints queued.
        """
        if event_type not in VALID_WEBHOOK_EVENTS and not event_type.startswith("test."):
            logger.warning("Unknown webhook event type '%s' — dispatch skipped", event_type)
            return 0

        endpoints = (
            db.query(WebhookEndpoint)
            .filter(
                WebhookEndpoint.workspace_id == workspace_id,
                WebhookEndpoint.organization_id == organization_id,
                WebhookEndpoint.is_active.is_(True),
            )
            .all()
        )

        matching_endpoints = [
            ep for ep in endpoints
            if "*" in (ep.events or []) or event_type in (ep.events or [])
        ]

        if not matching_endpoints:
            return 0

        event_id = str(uuid.uuid4())
        timestamp = int(datetime.utcnow().timestamp())
        sanitized_data = _sanitize_webhook_payload(data)

        payload_obj = {
            "id": event_id,
            "event": event_type,
            "timestamp": timestamp,
            "workspace_id": workspace_id,
            "organization_id": organization_id,
            "data": sanitized_data,
        }
        payload_bytes = json.dumps(payload_obj, sort_keys=True, default=str).encode("utf-8")

        queued_count = 0
        from utils.ssrf_guard import is_ssrf_safe_url
        from config.settings import get_settings
        settings = get_settings()

        for ep in matching_endpoints:
            safe, reason = is_ssrf_safe_url(ep.url, allow_private=settings.allow_private_webhook_urls)
            if not safe:
                logger.warning("SSRF Protection blocked delivery to endpoint %d URL '%s': %s", ep.id, ep.url, reason)
                delivery = WebhookDeliveryRecord(
                    endpoint_id=ep.id,
                    organization_id=organization_id,
                    workspace_id=workspace_id,
                    event_type=event_type,
                    event_id=event_id,
                    payload=payload_obj,
                    status="failed",
                    attempt_number=1,
                    max_attempts=1,
                    error_message=f"SSRF Security Block: {reason}",
                    created_at=datetime.utcnow(),
                )
                db.add(delivery)
                db.commit()
                continue

            signature = calculate_webhook_signature(ep.secret_key, payload_bytes, timestamp)

            delivery = WebhookDeliveryRecord(
                endpoint_id=ep.id,
                organization_id=organization_id,
                workspace_id=workspace_id,
                event_type=event_type,
                event_id=event_id,
                payload=payload_obj,
                status="pending",
                attempt_number=1,
                max_attempts=3,
                created_at=datetime.utcnow(),
            )
            db.add(delivery)
            db.commit()
            db.refresh(delivery)

            # Enqueue Celery async delivery
            try:
                from tasks.webhook_tasks import deliver_webhook_async
                deliver_webhook_async.apply_async(
                    kwargs={
                        "delivery_id": delivery.id,
                        "url": ep.url,
                        "payload_json": payload_bytes.decode("utf-8"),
                        "signature": signature,
                        "event_type": event_type,
                        "event_id": event_id,
                        "attempt": 1,
                    },
                    queue="webhooks",
                )
                queued_count += 1
            except Exception as exc:
                logger.error("Failed to enqueue Celery task for webhook delivery %d: %s", delivery.id, exc)
                # Fallback to local synchronous delivery for development or when Celery is offline
                from tasks.webhook_tasks import execute_webhook_delivery
                execute_webhook_delivery(
                    delivery_id=delivery.id,
                    url=ep.url,
                    payload_json=payload_bytes.decode("utf-8"),
                    signature=signature,
                    event_type=event_type,
                    event_id=event_id,
                    attempt=1,
                )
                queued_count += 1

        return queued_count
