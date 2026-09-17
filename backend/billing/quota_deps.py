from typing import Callable
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from auth.rbac import get_auth_context, AuthContext, Role
from auth.models import Workspace
from billing.service import BillingService


def get_current_org_id(
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
) -> int:
    """Extracts or resolves the active organization_id for billing."""
    if not auth.user and not auth.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required for billing operation.",
        )

    if auth.organization_id:
        return auth.organization_id

    if auth.workspace_id:
        ws = db.query(Workspace).filter(Workspace.id == auth.workspace_id).first()
        if ws and ws.organization_id:
            return ws.organization_id

    # Fallback to user's direct org_id or default organization (1)
    if auth.user and getattr(auth.user, "organization_id", None):
        return auth.user.organization_id

    return 1


def require_billing_admin(
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
) -> AuthContext:
    """Ensures caller has admin privileges (Super Admin or Workspace Admin) to manage billing."""
    if not auth.user and not auth.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    # Super Admin and Workspace Admin have full billing management rights
    if auth.role in (Role.SUPER_ADMIN, Role.WORKSPACE_ADMIN):
        return auth

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Forbidden: Only Organization or Workspace Administrators can manage billing and subscriptions.",
    )


def require_active_subscription(
    org_id: int = Depends(get_current_org_id),
    db: Session = Depends(get_db),
):
    BillingService.enforce_subscription(org_id, db)
    return True


def make_quota_dep(resource: str, amount: int = 1) -> Callable:
    """Factory creating FastAPI dependency that checks and guards resource quotas."""

    def quota_dependency(
        org_id: int = Depends(get_current_org_id),
        db: Session = Depends(get_db),
    ):
        # 1. Enforce active subscription status
        BillingService.enforce_subscription(org_id, db)

        # 2. Check quota limit
        result = BillingService.check_quota(
            org_id=org_id, resource=resource, requested_amount=amount, db=db
        )
        if not result.allowed:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail={
                    "error": "quota_exceeded",
                    "resource": resource,
                    "limit": result.limit,
                    "used": result.used,
                    "remaining": result.remaining,
                    "message": f"Quota limit exceeded for {resource}. Current limit: {result.limit}. Please upgrade your plan.",
                },
            )
        return result

    return quota_dependency


def make_feature_dep(feature_name: str) -> Callable:
    """Factory creating FastAPI dependency to enforce feature flag permissions."""

    def feature_dependency(
        org_id: int = Depends(get_current_org_id),
        db: Session = Depends(get_db),
    ):
        BillingService.enforce_subscription(org_id, db)
        if not BillingService.has_feature(org_id, feature_name, db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "feature_locked",
                    "feature": feature_name,
                    "message": f"Feature '{feature_name}' is not included in your current plan. Please upgrade to access this feature.",
                },
            )
        return True

    return feature_dependency


# Pre-built quota dependencies
check_contacts_quota = make_quota_dep("contacts")
check_deals_quota = make_quota_dep("deals")
check_campaigns_quota = make_quota_dep("campaigns")
check_emails_quota = make_quota_dep("emails")
check_ai_quota = make_quota_dep("ai_requests")

# Pre-built feature dependencies
require_ai_reply = make_feature_dep("ai_reply")
require_advanced_analytics = make_feature_dep("advanced_analytics")
require_workflow_automation = make_feature_dep("workflow_automation")
