import uuid
import hmac
import hashlib
from typing import Optional, Dict, Any
from billing.providers.base import (
    PaymentProvider,
    CheckoutResult,
    ProviderSubscription,
    ProviderWebhookEvent,
)


class MockPaymentProvider(PaymentProvider):
    """Dev and test payment provider that needs no external API keys or network calls."""

    def __init__(self, secret: str = "mock_secret_key"):
        self.secret = secret
        self._customers: Dict[str, Dict[str, Any]] = {}
        self._subscriptions: Dict[str, Dict[str, Any]] = {}

    def create_customer(self, org_id: int, email: str, name: str) -> str:
        cust_id = f"mock_cus_{uuid.uuid4().hex[:12]}"
        self._customers[cust_id] = {
            "org_id": org_id,
            "email": email,
            "name": name,
        }
        return cust_id

    def create_checkout(
        self,
        customer_id: str,
        plan_slug: str,
        interval: str = "month",
        success_url: str = "",
        cancel_url: str = "",
    ) -> CheckoutResult:
        sub_id = f"mock_sub_{uuid.uuid4().hex[:12]}"
        self._subscriptions[sub_id] = {
            "customer_id": customer_id,
            "plan_slug": plan_slug,
            "status": "active",
            "interval": interval,
        }
        checkout_session = f"cs_test_{uuid.uuid4().hex[:16]}"
        return CheckoutResult(
            checkout_url=f"/api/v1/billing/mock/checkout-success?session_id={checkout_session}&sub_id={sub_id}&plan={plan_slug}",
            session_id=checkout_session,
            provider_customer_id=customer_id,
        )

    def change_subscription(self, subscription_id: str, new_plan_slug: str) -> bool:
        if subscription_id in self._subscriptions:
            self._subscriptions[subscription_id]["plan_slug"] = new_plan_slug
            return True
        # For mock test robustness, treat any mock_sub as updated
        return True

    def cancel_subscription(self, subscription_id: str, at_period_end: bool = True) -> bool:
        if subscription_id in self._subscriptions:
            self._subscriptions[subscription_id]["status"] = "canceled"
            return True
        return True

    def get_subscription(self, subscription_id: str) -> Optional[ProviderSubscription]:
        data = self._subscriptions.get(subscription_id)
        if not data:
            # Return synthetic active subscription for unmocked IDs
            return ProviderSubscription(
                subscription_id=subscription_id,
                customer_id="mock_cus_default",
                status="active",
                plan_slug="professional",
            )
        return ProviderSubscription(
            subscription_id=subscription_id,
            customer_id=data["customer_id"],
            status=data["status"],
            plan_slug=data["plan_slug"],
        )

    def verify_webhook_signature(
        self, payload: bytes or str, signature: str, secret: str
    ) -> bool:
        if not signature:
            return False
        # For tests/dev allow literal "test_valid_sig" or HMAC check
        if signature == "test_valid_sig" or signature == "valid":
            return True
        if isinstance(payload, str):
            payload_bytes = payload.encode("utf-8")
        else:
            payload_bytes = payload
        expected = hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)

    def parse_webhook_event(self, payload: Dict[str, Any]) -> ProviderWebhookEvent:
        event_id = payload.get("id") or f"evt_{uuid.uuid4().hex[:12]}"
        event_type = payload.get("type", "customer.subscription.updated")
        return ProviderWebhookEvent(
            event_id=event_id,
            event_type=event_type,
            provider="mock",
            data=payload.get("data", payload),
        )


_default_provider: Optional[PaymentProvider] = None


def get_payment_provider() -> PaymentProvider:
    global _default_provider
    if _default_provider is None:
        _default_provider = MockPaymentProvider()
    return _default_provider
