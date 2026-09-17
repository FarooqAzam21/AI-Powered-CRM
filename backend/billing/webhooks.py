import logging
from typing import Dict, Any, Optional
from datetime import datetime
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from billing.models import BillingWebhookEvent, Subscription, SubscriptionHistory
from billing.providers.base import PaymentProvider
from billing.providers.mock_provider import get_payment_provider

logger = logging.getLogger(__name__)


class BillingWebhookHandler:
    def __init__(self, provider: Optional[PaymentProvider] = None, webhook_secret: str = "mock_secret_key"):
        self.provider = provider or get_payment_provider()
        self.webhook_secret = webhook_secret

    def handle_webhook(
        self,
        raw_body: bytes or str,
        payload: Dict[str, Any],
        signature: Optional[str],
        provider_name: str,
        db: Session,
    ) -> Dict[str, Any]:
        """Processes incoming provider webhooks with strict idempotency and signature checks."""
        # 1. Signature Verification
        if signature:
            is_valid = self.provider.verify_webhook_signature(
                raw_body, signature, self.webhook_secret
            )
            if not is_valid:
                logger.warning("Invalid webhook signature for provider %s", provider_name)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid webhook signature.",
                )

        # 2. Parse Event
        event = self.provider.parse_webhook_event(payload)

        # 3. Idempotency Check
        existing_event = (
            db.query(BillingWebhookEvent)
            .filter(BillingWebhookEvent.event_id == event.event_id)
            .first()
        )
        if existing_event:
            logger.info("Duplicate webhook event ignored: %s", event.event_id)
            return {
                "status": "already_processed",
                "event_id": event.event_id,
                "message": "Event has already been processed.",
            }

        # 4. Record Event
        webhook_log = BillingWebhookEvent(
            provider=provider_name,
            event_id=event.event_id,
            event_type=event.event_type,
            payload=payload,
            processed_at=datetime.utcnow(),
            status="processing",
        )
        db.add(webhook_log)
        db.commit()

        # 5. Dispatch Event Actions
        result = self._dispatch(event.event_type, event.data, db)

        webhook_log.status = "success"
        db.commit()

        return {
            "status": "processed",
            "event_id": event.event_id,
            "event_type": event.event_type,
            "result": result,
        }

    def _dispatch(self, event_type: str, data: Dict[str, Any], db: Session) -> Dict[str, Any]:
        """Maps webhook event to corresponding subscription state mutation."""
        customer_id = data.get("customer") or data.get("customer_id")
        sub_id = data.get("subscription") or data.get("id")

        # Find corresponding subscription in DB
        sub = None
        if customer_id:
            sub = db.query(Subscription).filter(
                Subscription.provider_customer_id == customer_id
            ).first()
        if not sub and sub_id:
            sub = db.query(Subscription).filter(
                Subscription.provider_subscription_id == sub_id
            ).first()

        if not sub:
            logger.info("Webhook event %s: no matching subscription found", event_type)
            return {"action": "none", "reason": "subscription_not_found"}

        if event_type == "customer.subscription.deleted":
            sub.status = "canceled"
            sub.canceled_at = datetime.utcnow()
            db.commit()
            db.add(
                SubscriptionHistory(
                    organization_id=sub.organization_id,
                    subscription_id=sub.id,
                    event_type="provider_subscription_canceled",
                    notes=f"Provider canceled subscription: {event_type}",
                )
            )
            db.commit()
            return {"action": "canceled", "subscription_id": sub.id}

        elif event_type == "invoice.payment_failed":
            sub.status = "past_due"
            db.commit()
            db.add(
                SubscriptionHistory(
                    organization_id=sub.organization_id,
                    subscription_id=sub.id,
                    event_type="payment_failed",
                    notes="Provider notified of payment failure. Status set to past_due.",
                )
            )
            db.commit()
            return {"action": "past_due", "subscription_id": sub.id}

        elif event_type in ("invoice.payment_succeeded", "customer.subscription.updated"):
            sub.status = "active"
            db.commit()
            db.add(
                SubscriptionHistory(
                    organization_id=sub.organization_id,
                    subscription_id=sub.id,
                    event_type="payment_succeeded",
                    notes=f"Provider payment succeeded: {event_type}",
                )
            )
            db.commit()
            return {"action": "renewed", "subscription_id": sub.id}

        return {"action": "unhandled_event", "event_type": event_type}
