from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from billing.models import (
    Plan,
    Subscription,
    SubscriptionHistory,
    UsageCounter,
)
from billing.plans import get_cached_plan, get_cached_plan_by_slug, seed_default_plans, invalidate_plan_cache
from billing.providers.mock_provider import get_payment_provider


MONTHLY_RESOURCES = {
    "emails",
    "ai_requests",
    "api_requests",
    "campaign_emails",
    "workflow_runs",
}


@dataclass
class QuotaResult:
    allowed: bool
    limit: int
    used: int
    remaining: int
    resource: str
    period_key: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "allowed": self.allowed,
            "limit": self.limit,
            "used": self.used,
            "remaining": self.remaining,
            "resource": self.resource,
            "period_key": self.period_key,
        }


class BillingService:
    @staticmethod
    def get_or_create_subscription(org_id: int, db: Session) -> Subscription:
        """Fetch active subscription or automatically initialize a Free trial subscription."""
        sub = db.query(Subscription).filter(Subscription.organization_id == org_id).first()
        if sub:
            # Check trial expiration
            if sub.status == "trial" and sub.trial_end and datetime.utcnow() > sub.trial_end:
                sub.status = "expired"
                db.commit()
                db.refresh(sub)
            return sub

        # Ensure default plans exist
        free_plan = get_cached_plan_by_slug(db, "free")
        if not free_plan:
            seed_default_plans(db)
            free_plan = get_cached_plan_by_slug(db, "free")

        now = datetime.utcnow()
        trial_days = free_plan.trial_days if free_plan else 14
        sub = Subscription(
            organization_id=org_id,
            plan_id=free_plan.id if free_plan else 1,
            status="active",
            trial_start=now,
            trial_end=now + timedelta(days=trial_days),
            current_period_start=now,
            current_period_end=now + timedelta(days=365),
            extra_metadata={"seeded": True},
        )
        db.add(sub)
        db.commit()
        db.refresh(sub)

        # Log history
        history = SubscriptionHistory(
            organization_id=org_id,
            subscription_id=sub.id,
            event_type="subscription_created",
            to_plan_id=sub.plan_id,
            notes="Default Free subscription created",
        )
        db.add(history)
        db.commit()

        return sub

    @classmethod
    def get_subscription(cls, org_id: int, db: Session) -> Subscription:
        return cls.get_or_create_subscription(org_id, db)

    @classmethod
    def get_plan(cls, org_id: int, db: Session) -> Plan:
        sub = cls.get_subscription(org_id, db)
        plan = get_cached_plan(db, sub.plan_id)
        if not plan:
            plan = db.query(Plan).filter(Plan.id == sub.plan_id).first()
        return plan

    @classmethod
    def is_trial_active(cls, org_id: int, db: Session) -> bool:
        sub = cls.get_subscription(org_id, db)
        if sub.status == "trial":
            if sub.trial_end and datetime.utcnow() > sub.trial_end:
                sub.status = "expired"
                db.commit()
                return False
            return True
        return False

    @classmethod
    def is_subscription_active(cls, org_id: int, db: Session) -> bool:
        sub = cls.get_subscription(org_id, db)
        if sub.status in ("active", "trial"):
            if sub.status == "trial" and sub.trial_end and datetime.utcnow() > sub.trial_end:
                sub.status = "expired"
                db.commit()
                return False
            return True
        return False

    @classmethod
    def enforce_subscription(cls, org_id: int, db: Session) -> None:
        """Raises HTTP 402 if subscription is expired, canceled, or suspended."""
        sub = cls.get_subscription(org_id, db)
        if not cls.is_subscription_active(org_id, db):
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail={
                    "error": "subscription_inactive",
                    "status": sub.status,
                    "message": f"Organization subscription is {sub.status}. Please upgrade or renew your plan.",
                },
            )

    @classmethod
    def _get_period_key(cls, resource: str) -> str:
        if resource in MONTHLY_RESOURCES:
            return datetime.utcnow().strftime("%Y-%m")
        return "total"

    @classmethod
    def get_usage_count(cls, org_id: int, resource: str, db: Session) -> int:
        period_key = cls._get_period_key(resource)
        counter = (
            db.query(UsageCounter)
            .filter(
                UsageCounter.organization_id == org_id,
                UsageCounter.resource == resource,
                UsageCounter.period_key == period_key,
            )
            .first()
        )
        return counter.count if counter else 0

    @classmethod
    def increment_usage(
        cls, org_id: int, resource: str, amount: int = 1, db: Session = None
    ) -> int:
        period_key = cls._get_period_key(resource)
        counter = (
            db.query(UsageCounter)
            .filter(
                UsageCounter.organization_id == org_id,
                UsageCounter.resource == resource,
                UsageCounter.period_key == period_key,
            )
            .first()
        )
        now = datetime.utcnow()
        if not counter:
            counter = UsageCounter(
                organization_id=org_id,
                resource=resource,
                period_key=period_key,
                count=amount,
                last_reset_at=now,
            )
            db.add(counter)
        else:
            counter.count += amount
            counter.updated_at = now
        db.commit()
        db.refresh(counter)
        return counter.count

    @classmethod
    def set_usage(
        cls, org_id: int, resource: str, value: int, db: Session
    ) -> int:
        period_key = cls._get_period_key(resource)
        counter = (
            db.query(UsageCounter)
            .filter(
                UsageCounter.organization_id == org_id,
                UsageCounter.resource == resource,
                UsageCounter.period_key == period_key,
            )
            .first()
        )
        now = datetime.utcnow()
        if not counter:
            counter = UsageCounter(
                organization_id=org_id,
                resource=resource,
                period_key=period_key,
                count=value,
                last_reset_at=now,
            )
            db.add(counter)
        else:
            counter.count = value
            counter.updated_at = now
        db.commit()
        return counter.count

    @classmethod
    def check_quota(
        cls,
        org_id: int,
        resource: str,
        requested_amount: int = 1,
        db: Session = None,
    ) -> QuotaResult:
        """Evaluates whether the org has sufficient quota to consume requested_amount."""
        plan = cls.get_plan(org_id, db)
        limits = plan.limits or {}
        limit = limits.get(resource, -1)  # -1 = unlimited

        period_key = cls._get_period_key(resource)
        used = cls.get_usage_count(org_id, resource, db)

        if limit == -1:
            return QuotaResult(
                allowed=True,
                limit=-1,
                used=used,
                remaining=999999,
                resource=resource,
                period_key=period_key,
            )

        remaining = max(0, limit - used)
        allowed = (used + requested_amount) <= limit

        return QuotaResult(
            allowed=allowed,
            limit=limit,
            used=used,
            remaining=remaining,
            resource=resource,
            period_key=period_key,
        )

    @classmethod
    def has_feature(cls, org_id: int, feature_name: str, db: Session) -> bool:
        """Checks if a feature flag is enabled for the organization's plan."""
        plan = cls.get_plan(org_id, db)
        features = plan.features or []
        if "*" in features:
            return True
        return feature_name in features

    @classmethod
    def get_features(cls, org_id: int, db: Session) -> List[str]:
        plan = cls.get_plan(org_id, db)
        return plan.features or []

    @classmethod
    def get_usage_summary(cls, org_id: int, db: Session) -> Dict[str, Any]:
        """Provides full breakdown of resource usage vs quotas for dashboard."""
        plan = cls.get_plan(org_id, db)
        sub = cls.get_subscription(org_id, db)
        limits = plan.limits or {}

        summary = {}
        for resource, limit in limits.items():
            used = cls.get_usage_count(org_id, resource, db)
            period_key = cls._get_period_key(resource)
            remaining = -1 if limit == -1 else max(0, limit - used)
            pct = 0 if limit <= 0 else min(100, round((used / limit) * 100, 1))
            summary[resource] = {
                "limit": limit,
                "used": used,
                "remaining": remaining,
                "percentage": pct,
                "period_key": period_key,
                "unlimited": limit == -1,
            }

        return {
            "organization_id": org_id,
            "plan": {
                "id": plan.id,
                "name": plan.name,
                "slug": plan.slug,
                "price_monthly": plan.price_monthly,
                "price_yearly": plan.price_yearly,
            },
            "subscription": {
                "id": sub.id,
                "status": sub.status,
                "trial_end": sub.trial_end.isoformat() if sub.trial_end else None,
                "current_period_end": sub.current_period_end.isoformat()
                if sub.current_period_end
                else None,
            },
            "features": plan.features or [],
            "usage": summary,
        }

    @classmethod
    def subscribe_plan(
        cls,
        org_id: int,
        plan_slug: str,
        interval: str = "month",
        user_id: Optional[int] = None,
        db: Session = None,
    ) -> Dict[str, Any]:
        """Upgrades, downgrades, or activates a plan."""
        target_plan = get_cached_plan_by_slug(db, plan_slug)
        if not target_plan:
            raise HTTPException(status_code=404, detail=f"Plan '{plan_slug}' not found.")

        sub = cls.get_subscription(org_id, db)
        from_plan_id = sub.plan_id

        provider = get_payment_provider()
        if not sub.provider_customer_id:
            sub.provider_customer_id = provider.create_customer(
                org_id=org_id, email=f"org_{org_id}@domain.local", name=f"Org {org_id}"
            )

        now = datetime.utcnow()
        period_days = 365 if interval == "year" else 30

        sub.plan_id = target_plan.id
        sub.status = "active"
        sub.current_period_start = now
        sub.current_period_end = now + timedelta(days=period_days)
        sub.canceled_at = None
        sub.cancel_at = None
        db.commit()
        db.refresh(sub)
        invalidate_plan_cache()

        # Audit history
        history = SubscriptionHistory(
            organization_id=org_id,
            subscription_id=sub.id,
            event_type="plan_change",
            from_plan_id=from_plan_id,
            to_plan_id=target_plan.id,
            triggered_by_user_id=user_id,
            notes=f"Changed plan to {target_plan.name} ({interval})",
        )
        db.add(history)
        db.commit()

        return {
            "status": "success",
            "message": f"Successfully subscribed to {target_plan.name}",
            "subscription": {
                "id": sub.id,
                "plan_slug": target_plan.slug,
                "status": sub.status,
                "current_period_end": sub.current_period_end.isoformat(),
            },
        }

    @classmethod
    def cancel_subscription(
        cls, org_id: int, user_id: Optional[int] = None, db: Session = None
    ) -> Dict[str, Any]:
        """Cancels an active subscription at period end."""
        sub = cls.get_subscription(org_id, db)
        now = datetime.utcnow()
        sub.canceled_at = now
        sub.cancel_at = sub.current_period_end or (now + timedelta(days=30))
        sub.status = "canceled"
        db.commit()
        db.refresh(sub)

        history = SubscriptionHistory(
            organization_id=org_id,
            subscription_id=sub.id,
            event_type="canceled",
            from_plan_id=sub.plan_id,
            to_plan_id=sub.plan_id,
            triggered_by_user_id=user_id,
            notes="Subscription canceled by admin",
        )
        db.add(history)
        db.commit()

        return {
            "status": "success",
            "message": "Subscription canceled successfully",
            "subscription_id": sub.id,
            "canceled_at": sub.canceled_at.isoformat(),
        }

    @classmethod
    def start_trial(
        cls,
        org_id: int,
        plan_slug: str,
        user_id: Optional[int] = None,
        db: Session = None,
    ) -> Dict[str, Any]:
        target_plan = get_cached_plan_by_slug(db, plan_slug)
        if not target_plan:
            raise HTTPException(status_code=404, detail=f"Plan '{plan_slug}' not found.")

        sub = cls.get_subscription(org_id, db)
        now = datetime.utcnow()
        trial_days = target_plan.trial_days or 14

        sub.plan_id = target_plan.id
        sub.status = "trial"
        sub.trial_start = now
        sub.trial_end = now + timedelta(days=trial_days)
        sub.current_period_start = now
        sub.current_period_end = sub.trial_end
        db.commit()
        db.refresh(sub)

        history = SubscriptionHistory(
            organization_id=org_id,
            subscription_id=sub.id,
            event_type="trial_started",
            to_plan_id=target_plan.id,
            triggered_by_user_id=user_id,
            notes=f"Started {trial_days}-day trial for {target_plan.name}",
        )
        db.add(history)
        db.commit()

        return {
            "status": "success",
            "message": f"Trial started for {target_plan.name}",
            "trial_end": sub.trial_end.isoformat(),
        }
