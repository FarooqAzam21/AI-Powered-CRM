from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from billing.models import Plan
import logging

logger = logging.getLogger(__name__)

PLAN_DEFAULTS: Dict[str, Dict[str, Any]] = {
    "free": {
        "name": "Free",
        "slug": "free",
        "description": "Essential CRM features for individuals and small teams getting started.",
        "price_monthly": 0.0,
        "price_yearly": 0.0,
        "trial_days": 14,
        "is_active": True,
        "is_public": True,
        "limits": {
            "contacts": 100,
            "users": 2,
            "workspaces": 1,
            "deals": 50,
            "emails": 500,
            "campaigns": 2,
            "ai_requests": 10,
            "api_requests": 100,
            "storage_mb": 100,
            "automations": 0,
            "workflows": 0,
            "workflow_runs": 0,
            "ai_workflow_actions": 0,
        },
        "features": [
            "basic_crm",
            "email_classify",
        ],
    },
    "starter": {
        "name": "Starter",
        "slug": "starter",
        "description": "Powerful capabilities for growing businesses needing AI replies and team collaboration.",
        "price_monthly": 29.0,
        "price_yearly": 290.0,
        "trial_days": 14,
        "is_active": True,
        "is_public": True,
        "limits": {
            "contacts": 1000,
            "users": 5,
            "workspaces": 2,
            "deals": 500,
            "emails": 5000,
            "campaigns": 10,
            "ai_requests": 100,
            "api_requests": 1000,
            "storage_mb": 1000,
            "automations": 5,
            "workflows": 3,
            "workflow_runs": 50,
            "ai_workflow_actions": 0,
        },
        "features": [
            "basic_crm",
            "email_classify",
            "ai_reply",
            "advanced_crm",
        ],
    },
    "professional": {
        "name": "Professional",
        "slug": "professional",
        "description": "Complete suite with advanced analytics, workflow automation, and custom integrations.",
        "price_monthly": 99.0,
        "price_yearly": 990.0,
        "trial_days": 14,
        "is_active": True,
        "is_public": True,
        "limits": {
            "contacts": 10000,
            "users": 25,
            "workspaces": 10,
            "deals": 5000,
            "emails": 50000,
            "campaigns": 50,
            "ai_requests": 1000,
            "api_requests": 10000,
            "storage_mb": 10000,
            "automations": 50,
            "workflows": 25,
            "workflow_runs": 1000,
            "ai_workflow_actions": 500,
        },
        "features": [
            "basic_crm",
            "email_classify",
            "ai_reply",
            "advanced_crm",
            "advanced_analytics",
            "api_access",
            "webhooks",
            "workflow_automation",
            "ai_workflow_actions",
        ],
    },
    "enterprise": {
        "name": "Enterprise",
        "slug": "enterprise",
        "description": "Unlimited scale, dedicated support, custom integrations, and SLA guarantees.",
        "price_monthly": 299.0,
        "price_yearly": 2990.0,
        "trial_days": 30,
        "is_active": True,
        "is_public": True,
        "limits": {
            "contacts": -1,
            "users": -1,
            "workspaces": -1,
            "deals": -1,
            "emails": -1,
            "campaigns": -1,
            "ai_requests": -1,
            "api_requests": -1,
            "storage_mb": -1,
            "automations": -1,
            "workflows": -1,
            "workflow_runs": -1,
            "ai_workflow_actions": -1,
        },
        "features": ["*"],
    },
}

# In-memory plan cache
_PLAN_CACHE: Dict[str, Plan] = {}


def invalidate_plan_cache():
    global _PLAN_CACHE
    _PLAN_CACHE.clear()


def seed_default_plans(db: Session) -> List[Plan]:
    """Ensures default plans exist in database without overwriting customizations."""
    created_or_found = []
    for slug, data in PLAN_DEFAULTS.items():
        existing = db.query(Plan).filter(Plan.slug == slug).first()
        if not existing:
            plan = Plan(
                name=data["name"],
                slug=slug,
                description=data.get("description"),
                price_monthly=data["price_monthly"],
                price_yearly=data["price_yearly"],
                trial_days=data.get("trial_days", 14),
                is_active=data.get("is_active", True),
                is_public=data.get("is_public", True),
                limits=data["limits"],
                features=data["features"],
            )
            db.add(plan)
            db.commit()
            db.refresh(plan)
            created_or_found.append(plan)
            logger.info("Seeded billing plan: %s", slug)
        else:
            created_or_found.append(existing)
    invalidate_plan_cache()
    return created_or_found


def get_cached_plan(db: Session, plan_id: int) -> Optional[Plan]:
    key = f"id:{plan_id}"
    if key in _PLAN_CACHE:
        try:
            return db.merge(_PLAN_CACHE[key], load=False)
        except Exception:
            _PLAN_CACHE.pop(key, None)
    plan = db.query(Plan).filter(Plan.id == plan_id).first()
    if plan:
        _PLAN_CACHE[key] = plan
    return plan


def get_cached_plan_by_slug(db: Session, slug: str) -> Optional[Plan]:
    key = f"slug:{slug}"
    if key in _PLAN_CACHE:
        try:
            return db.merge(_PLAN_CACHE[key], load=False)
        except Exception:
            _PLAN_CACHE.pop(key, None)
    plan = db.query(Plan).filter(Plan.slug == slug).first()
    if plan:
        _PLAN_CACHE[key] = plan
    return plan
