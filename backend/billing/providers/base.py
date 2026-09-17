from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class CheckoutResult:
    checkout_url: str
    session_id: str
    provider_customer_id: str


@dataclass
class ProviderSubscription:
    subscription_id: str
    customer_id: str
    status: str
    plan_slug: str
    current_period_start: Optional[str] = None
    current_period_end: Optional[str] = None
    cancel_at_period_end: bool = False


@dataclass
class ProviderWebhookEvent:
    event_id: str
    event_type: str
    provider: str
    data: Dict[str, Any]


class PaymentProvider(ABC):
    """Abstract interface for SaaS payment and subscription management."""

    @abstractmethod
    def create_customer(self, org_id: int, email: str, name: str) -> str:
        """Create a payment customer record and return the provider customer ID."""
        pass

    @abstractmethod
    def create_checkout(
        self,
        customer_id: str,
        plan_slug: str,
        interval: str = "month",
        success_url: str = "",
        cancel_url: str = "",
    ) -> CheckoutResult:
        """Create a checkout session and return the redirect URL."""
        pass

    @abstractmethod
    def change_subscription(self, subscription_id: str, new_plan_slug: str) -> bool:
        """Upgrade or downgrade an existing subscription."""
        pass

    @abstractmethod
    def cancel_subscription(self, subscription_id: str, at_period_end: bool = True) -> bool:
        """Cancel an existing subscription."""
        pass

    @abstractmethod
    def get_subscription(self, subscription_id: str) -> Optional[ProviderSubscription]:
        """Fetch subscription status directly from the provider."""
        pass

    @abstractmethod
    def verify_webhook_signature(
        self, payload: bytes or str, signature: str, secret: str
    ) -> bool:
        """Verify the cryptographic authenticity of a webhook event payload."""
        pass

    @abstractmethod
    def parse_webhook_event(self, payload: Dict[str, Any]) -> ProviderWebhookEvent:
        """Parse raw webhook payload into standardized ProviderWebhookEvent."""
        pass
