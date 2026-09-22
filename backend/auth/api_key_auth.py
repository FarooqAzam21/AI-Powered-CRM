"""
P6 — Public API Key Authentication Dependency
Resolves:
API Key -> Organization -> Workspace -> Scopes -> P3 Billing State -> P3 Quota -> Multi-tier Rate Limiting.
Never trusts client-supplied organization_id or workspace_id headers.
"""
import hashlib
import secrets
import time
from datetime import datetime
from typing import List, Optional

from fastapi import Request, Response, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
from fastapi.security.api_key import APIKeyHeader
from sqlalchemy.orm import Session
from sqlalchemy import or_

from database import get_db
from models.developer import DeveloperAPIKey, PublicAPILog
from auth.models import APIKey, Workspace, Organization
from billing.service import BillingService
from utils.rate_limiter import check_multi_tier_rate_limit

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
bearer_scheme = OAuth2PasswordBearer(tokenUrl="", auto_error=False)


class APIKeyContext:
    def __init__(
        self,
        api_key_id: int,
        key_name: str,
        organization_id: int,
        workspace_id: int,
        scopes: List[str],
        plan_slug: str,
    ):
        self.api_key_id = api_key_id
        self.key_name = key_name
        self.organization_id = organization_id
        self.workspace_id = workspace_id
        self.scopes = scopes
        self.plan_slug = plan_slug

    def has_scope(self, required_scope: str) -> bool:
        if "*" in self.scopes or "admin" in self.scopes:
            return True
        if required_scope in self.scopes:
            return True
        # Check wildcard resource e.g. "contacts:*" covers "contacts:read"
        if ":" in required_scope:
            resource, action = required_scope.split(":", 1)
            if f"{resource}:*" in self.scopes:
                return True
        return False


def get_api_key_context(
    request: Request,
    response: Response,
    api_key_header_val: Optional[str] = Depends(api_key_header),
    bearer_token: Optional[str] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> APIKeyContext:
    """
    Extracts, validates, rate limits, and scopes Public API key requests.
    Supports:
      - X-API-Key: crm_...
      - Authorization: Bearer crm_...
    """
    start_time = time.time()
    raw_key = api_key_header_val or bearer_token

    if not raw_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Provide via 'X-API-Key' header or 'Authorization: Bearer <key>'.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    raw_key = raw_key.strip()
    if not (raw_key.startswith("crm_live_") or raw_key.startswith("crm_test_") or raw_key.startswith("crm_")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key format. Key must start with 'crm_'.",
        )

    hashed = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
    prefix = raw_key[:12]

    # Look up in DeveloperAPIKey first, then legacy APIKey fallback
    matched_key = None
    dev_key = db.query(DeveloperAPIKey).filter(
        DeveloperAPIKey.key_prefix == prefix,
        DeveloperAPIKey.status == "active",
    ).first()

    if dev_key and secrets.compare_digest(dev_key.hashed_key, hashed):
        matched_key = dev_key
        org_id = dev_key.organization_id
        ws_id = dev_key.workspace_id
        scopes = dev_key.scopes or []
        rate_limit = dev_key.rate_limit or 60
        daily_limit = dev_key.daily_limit or 1000
        key_id = dev_key.id
        key_name = dev_key.name
        is_legacy = False
    else:
        # Fallback to legacy APIKey table
        legacy_key = db.query(APIKey).filter(
            APIKey.status == "active",
            or_(APIKey.key_prefix == prefix, APIKey.key == raw_key, APIKey.hashed_key == hashed),
        ).first()

        if legacy_key:
            # Check constant-time hash or plaintext
            if legacy_key.hashed_key and secrets.compare_digest(legacy_key.hashed_key, hashed):
                matched_key = legacy_key
            elif legacy_key.key and secrets.compare_digest(legacy_key.key, raw_key):
                matched_key = legacy_key

        if matched_key:
            ws_id = matched_key.workspace_id
            # Resolve organization from workspace
            ws = db.query(Workspace).filter(Workspace.id == ws_id).first()
            org_id = ws.organization_id if ws else 1
            scopes = matched_key.permissions or []
            rate_limit = matched_key.rate_limit or 60
            daily_limit = matched_key.daily_limit or 1000
            key_id = matched_key.id
            key_name = matched_key.name
            is_legacy = True

    if not matched_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key or key has been revoked.",
        )

    # Expiration check
    if matched_key.expires_at and matched_key.expires_at < datetime.utcnow():
        matched_key.status = "expired"
        matched_key.is_active = False
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key has expired.",
        )

    # Enforce P3 Subscription State
    sub = BillingService.get_or_create_subscription(org_id, db)
    plan_slug = (sub.plan.slug if sub.plan else "free").lower()

    if sub.status in ("suspended", "expired"):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Organization subscription is {sub.status}. Please update your billing status.",
        )

    # Enforce P3 api_requests Quota
    quota_res = BillingService.check_quota(org_id, "api_requests", db=db)
    if not quota_res.allowed:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "error": "quota_exceeded",
                "message": "Monthly API requests quota exceeded. Please upgrade your plan.",
                "quota": quota_res.to_dict(),
            },
        )

    # Multi-tier Rate Limiting (Organization plan + API Key minute/daily)
    endpoint_tag = None
    if "/ai/" in request.url.path:
        endpoint_tag = "ai_complete"
    elif "/execute" in request.url.path:
        endpoint_tag = "workflow_execute"

    allowed, remaining, retry_after, reason = check_multi_tier_rate_limit(
        org_id=org_id,
        key_id=key_id,
        key_minute_limit=rate_limit,
        key_daily_limit=daily_limit,
        plan_slug=plan_slug,
        endpoint_tag=endpoint_tag,
    )

    response.headers["X-RateLimit-Limit"] = str(rate_limit)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    response.headers["X-RateLimit-Reset"] = str(retry_after if retry_after > 0 else 60 - (int(time.time()) % 60))

    if not allowed:
        response.headers["Retry-After"] = str(retry_after)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded: {reason}",
            headers={"Retry-After": str(retry_after)},
        )

    # Meter usage against P3 UsageCounter
    BillingService.increment_usage(org_id, "api_requests", 1, db=db)

    # Update API key last used info
    matched_key.last_used_at = datetime.utcnow()
    matched_key.last_ip = request.client.host if request.client else None
    db.commit()

    # Pass context
    ctx = APIKeyContext(
        api_key_id=key_id,
        key_name=key_name,
        organization_id=org_id,
        workspace_id=ws_id,
        scopes=scopes,
        plan_slug=plan_slug,
    )

    # Attach to request state for request logging
    request.state.api_key_context = ctx
    request.state.api_start_time = start_time

    return ctx


def require_scope(required_scope: str):
    """
    Dependency factory ensuring API key has the required scope.
    """
    def _scope_checker(ctx: APIKeyContext = Depends(get_api_key_context)) -> APIKeyContext:
        if not ctx.has_scope(required_scope):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: API Key lacks required scope '{required_scope}'.",
            )
        return ctx

    return _scope_checker
