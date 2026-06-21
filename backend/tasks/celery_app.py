"""
Celery Configuration and App Setup
Async task queue for email, AI, and campaign processing
Uses Redis as message broker
"""
from celery import Celery
from celery.schedules import crontab
import logging
import os

logger = logging.getLogger(__name__)

# =================== CELERY APP ===================
broker_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
result_backend = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")

celery_app = Celery(
    "ai_crm",
    broker=broker_url,
    backend=result_backend,
)

# Configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes hard limit
    task_soft_time_limit=28 * 60,  # 28 minutes soft limit
    worker_max_tasks_per_child=100,
    worker_prefetch_multiplier=1,  # One task at a time (memory efficient)
    result_expires=3600,  # Results expire after 1 hour
    task_acks_late=True,
)

# =================== PERIODIC TASKS ===================
celery_app.conf.beat_schedule = {
    "sync-gmail-every-5-minutes": {
        "task": "tasks.email_tasks.sync_gmail_emails",
        "schedule": crontab(minute="*/5"),
        "options": {"queue": "email"},
    },
    "check-lead-follow-ups-every-hour": {
        "task": "tasks.lead_tasks.check_follow_ups",
        "schedule": crontab(minute=0),
        "options": {"queue": "leads"},
    },
    "process-pending-campaigns-every-minute": {
        "task": "tasks.campaign_tasks.process_campaigns",
        "schedule": crontab(minute="*"),
        "options": {"queue": "campaigns"},
    },
    "cleanup-expired-tokens-daily": {
        "task": "tasks.auth_tasks.cleanup_expired_tokens",
        "schedule": crontab(hour=2, minute=0),
        "options": {"queue": "maintenance"},
    },
    "refresh-customer-profiles-daily": {
        "task": "tasks.crm.periodic_profile_refresh",
        "schedule": crontab(hour=1, minute=0),
        "options": {"queue": "crm"},
    },
    "score-deals-every-6-hours": {
        "task": "tasks.crm.periodic_deal_scoring",
        "schedule": crontab(minute=0, hour="*/6"),
        "options": {"queue": "crm"},
    },
    "refresh-analytics-daily": {
        "task": "tasks.analytics.periodic_analytics_refresh",
        "schedule": crontab(hour=3, minute=0),
        "options": {"queue": "analytics"},
    },
    "refresh-dashboard-metrics-every-30s": {
        "task": "tasks.dashboard.periodic_metrics_refresh",
        "schedule": crontab(minute="*/1"),  # Every minute (crontab min resolution)
        "options": {"queue": "dashboard"},
    },
    "refresh-pipeline-every-60s": {
        "task": "tasks.dashboard.periodic_pipeline_refresh",
        "schedule": crontab(minute="*"),  # Every 60 seconds
        "options": {"queue": "dashboard"},
    },
    "refresh-territory-every-60s": {
        "task": "tasks.dashboard.periodic_territory_refresh",
        "schedule": crontab(minute="*"),  # Every 60 seconds
        "options": {"queue": "dashboard"},
    },
    "monitor-active-campaigns-every-minute": {
        "task": "tasks.campaign_tasks.periodic_campaign_monitor",
        "schedule": crontab(minute="*"),  # Every minute
        "options": {"queue": "campaigns"},
    },
    "process-retry-sends-every-30-minutes": {
        "task": "tasks.campaign_tasks.retry_failed_sends",
        "schedule": crontab(minute="*/30"),  # Every 30 minutes
        "options": {"queue": "campaigns"},
    },
}

# =================== TASK ROUTING ===================
celery_app.conf.task_routes = {
    "tasks.email_tasks.*": {"queue": "email"},
    "tasks.ai_tasks.*": {"queue": "ai"},
    "tasks.lead_tasks.*": {"queue": "leads"},
    "tasks.campaign_tasks.*": {"queue": "campaigns"},
    "tasks.auth_tasks.*": {"queue": "maintenance"},
    "tasks.crm.*": {"queue": "crm"},
    "tasks.analytics.*": {"queue": "analytics"},
    "tasks.dashboard.*": {"queue": "dashboard"},
    "workers.email_tasks.*": {"queue": "email"},
    "workers.campaign_tasks.*": {"queue": "campaigns"},
}

# =================== TASK IMPORTS ===================
# Import all task modules to register them with Celery
try:
    from . import (
        email_tasks, ai_tasks, lead_tasks, campaign_tasks,
        auth_tasks, crm_tasks, analytics_tasks, dashboard_tasks
    )
    import workers.email_tasks  # noqa: F401
    import workers.campaign_tasks  # noqa: F401
    logger.info("✅ All task modules imported successfully")
except ImportError as e:
    logger.warning(f"⚠️ Some task modules could not be imported: {e}")

logger.info("✅ Celery app configured")
