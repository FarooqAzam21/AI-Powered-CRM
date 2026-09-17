from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Header, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from auth.rbac import get_auth_context, AuthContext
from billing.models import Plan, SubscriptionHistory
from billing.service import BillingService
from billing.plans import seed_default_plans
from billing.quota_deps import get_current_org_id, require_billing_admin
from billing.providers.mock_provider import get_payment_provider
from billing.webhooks import BillingWebhookHandler

router = APIRouter(prefix="/api/v1/billing", tags=["Billing & Subscriptions"])


# --- Schemas ---
class SubscribeRequest(BaseModel):
    plan_slug: str = Field(..., description="Target plan slug, e.g. starter, professional")
    interval: str = Field("month", description="Billing interval: month or year")


class TrialStartRequest(BaseModel):
    plan_slug: str = Field(..., description="Plan slug to trial")


class CheckoutSessionRequest(BaseModel):
    plan_slug: str
    interval: str = "month"
    success_url: Optional[str] = "/billing?success=true"
    cancel_url: Optional[str] = "/billing?canceled=true"


# --- Endpoints ---

@router.get("/plans")
def list_plans(db: Session = Depends(get_db)):
    """List all publicly available subscription plans."""
    plans = db.query(Plan).filter(Plan.is_active == True, Plan.is_public == True).all()
    if not plans:
        plans = seed_default_plans(db)
    return [
        {
            "id": p.id,
            "name": p.name,
            "slug": p.slug,
            "description": p.description,
            "price_monthly": p.price_monthly,
            "price_yearly": p.price_yearly,
            "trial_days": p.trial_days,
            "limits": p.limits or {},
            "features": p.features or [],
        }
        for p in plans
    ]


@router.get("/subscription")
def get_subscription(
    org_id: int = Depends(get_current_org_id),
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    """Retrieve the current organization's subscription status and plan."""
    sub = BillingService.get_subscription(org_id, db)
    plan = BillingService.get_plan(org_id, db)
    return {
        "subscription": {
            "id": sub.id,
            "organization_id": sub.organization_id,
            "status": sub.status,
            "trial_start": sub.trial_start.isoformat() if sub.trial_start else None,
            "trial_end": sub.trial_end.isoformat() if sub.trial_end else None,
            "current_period_start": sub.current_period_start.isoformat() if sub.current_period_start else None,
            "current_period_end": sub.current_period_end.isoformat() if sub.current_period_end else None,
            "cancel_at": sub.cancel_at.isoformat() if sub.cancel_at else None,
            "is_active": BillingService.is_subscription_active(org_id, db),
            "is_trial": BillingService.is_trial_active(org_id, db),
        },
        "plan": {
            "id": plan.id,
            "name": plan.name,
            "slug": plan.slug,
            "description": plan.description,
            "price_monthly": plan.price_monthly,
            "price_yearly": plan.price_yearly,
            "limits": plan.limits or {},
            "features": plan.features or [],
        },
    }


@router.get("/usage")
def get_usage(
    org_id: int = Depends(get_current_org_id),
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    """Retrieve full usage metrics and quota status for the current organization."""
    return BillingService.get_usage_summary(org_id, db)


@router.post("/subscribe")
def subscribe(
    req: SubscribeRequest,
    org_id: int = Depends(get_current_org_id),
    admin_auth: AuthContext = Depends(require_billing_admin),
    db: Session = Depends(get_db),
):
    """Subscribe, upgrade, or downgrade organization plan."""
    user_id = admin_auth.user.id if admin_auth.user else None
    return BillingService.subscribe_plan(
        org_id=org_id,
        plan_slug=req.plan_slug,
        interval=req.interval,
        user_id=user_id,
        db=db,
    )


@router.post("/cancel")
def cancel_subscription(
    org_id: int = Depends(get_current_org_id),
    admin_auth: AuthContext = Depends(require_billing_admin),
    db: Session = Depends(get_db),
):
    """Cancel subscription at the end of the current billing cycle."""
    user_id = admin_auth.user.id if admin_auth.user else None
    return BillingService.cancel_subscription(org_id=org_id, user_id=user_id, db=db)


@router.post("/trial/start")
def start_trial(
    req: TrialStartRequest,
    org_id: int = Depends(get_current_org_id),
    admin_auth: AuthContext = Depends(require_billing_admin),
    db: Session = Depends(get_db),
):
    """Start a free trial for a specific plan."""
    user_id = admin_auth.user.id if admin_auth.user else None
    return BillingService.start_trial(
        org_id=org_id,
        plan_slug=req.plan_slug,
        user_id=user_id,
        db=db,
    )


@router.get("/features")
def get_features(
    org_id: int = Depends(get_current_org_id),
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    """List all feature flags available under the current active subscription."""
    features = BillingService.get_features(org_id, db)
    return {
        "organization_id": org_id,
        "features": features,
        "has_all": "*" in features,
    }


@router.get("/history")
def get_history(
    org_id: int = Depends(get_current_org_id),
    admin_auth: AuthContext = Depends(require_billing_admin),
    db: Session = Depends(get_db),
):
    """Audit trail of billing and subscription events."""
    events = (
        db.query(SubscriptionHistory)
        .filter(SubscriptionHistory.organization_id == org_id)
        .order_by(SubscriptionHistory.created_at.desc())
        .limit(50)
        .all()
    )
    return [
        {
            "id": e.id,
            "event_type": e.event_type,
            "from_plan_id": e.from_plan_id,
            "to_plan_id": e.to_plan_id,
            "notes": e.notes,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in events
    ]


@router.post("/checkout")
def create_checkout_session(
    req: CheckoutSessionRequest,
    org_id: int = Depends(get_current_org_id),
    admin_auth: AuthContext = Depends(require_billing_admin),
    db: Session = Depends(get_db),
):
    """Generates a payment checkout session for plan upgrade."""
    sub = BillingService.get_subscription(org_id, db)
    provider = get_payment_provider()
    cust_id = sub.provider_customer_id or provider.create_customer(
        org_id=org_id,
        email=admin_auth.user.email if admin_auth.user else f"org_{org_id}@local.test",
        name=f"Org {org_id}",
    )
    checkout = provider.create_checkout(
        customer_id=cust_id,
        plan_slug=req.plan_slug,
        interval=req.interval,
        success_url=req.success_url or "",
        cancel_url=req.cancel_url or "",
    )
    return {
        "checkout_url": checkout.checkout_url,
        "session_id": checkout.session_id,
    }


@router.post("/webhooks/{provider}")
async def handle_provider_webhook(
    provider: str,
    request: Request,
    stripe_signature: Optional[str] = Header(None, alias="stripe-signature"),
    x_webhook_signature: Optional[str] = Header(None, alias="x-webhook-signature"),
    db: Session = Depends(get_db),
):
    """Standardized webhook endpoint with cryptographic verification and idempotency."""
    raw_body = await request.body()
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    signature = stripe_signature or x_webhook_signature
    handler = BillingWebhookHandler()
    return handler.handle_webhook(
        raw_body=raw_body,
        payload=payload,
        signature=signature,
        provider_name=provider,
        db=db,
    )
