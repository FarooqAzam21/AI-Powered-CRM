"""
P5 — Workflow Scheduler
Time-based trigger support via Celery beat.
Checks scheduled workflows every minute and dispatches them.
"""
import logging
from datetime import datetime
from typing import List

from sqlalchemy.orm import Session
from database import SessionLocal
from models.workflow import Workflow

logger = logging.getLogger(__name__)

# Cron expression mini-parser for scheduled workflows
import re


def _matches_schedule(trigger_config: dict, now: datetime) -> bool:
    """
    Check if a scheduled workflow's trigger_config matches the current time.

    Supported trigger_config formats:
      { "type": "interval",  "minutes": 60 }
      { "type": "cron",     "expression": "0 9 * * 1" }   # Every Monday 9 AM
      { "type": "once",     "datetime": "2026-10-01T09:00:00" }
    """
    schedule_type = trigger_config.get("type", "interval")

    if schedule_type == "interval":
        # Interval: fire every N minutes
        minutes = int(trigger_config.get("minutes", 60))
        return now.minute % max(minutes, 1) == 0

    elif schedule_type == "cron":
        expression = trigger_config.get("expression", "")
        return _match_cron(expression, now)

    elif schedule_type == "once":
        target_str = trigger_config.get("datetime", "")
        try:
            target = datetime.fromisoformat(target_str)
            # Fire within a 1-minute window
            diff = abs((now - target).total_seconds())
            return diff <= 60
        except (ValueError, TypeError):
            return False

    return False


def _match_cron(expression: str, now: datetime) -> bool:
    """
    Minimal 5-field cron matcher: minute hour dom month dow
    Supports * and comma-separated values.
    """
    parts = expression.strip().split()
    if len(parts) != 5:
        return False

    def field_match(field: str, value: int) -> bool:
        if field == "*":
            return True
        for part in field.split(","):
            if part.strip() == str(value):
                return True
            if "/" in part:
                base, step = part.split("/", 1)
                try:
                    if base == "*" and value % int(step) == 0:
                        return True
                except ValueError:
                    pass
        return False

    minute_f, hour_f, dom_f, month_f, dow_f = parts
    return (
        field_match(minute_f, now.minute)
        and field_match(hour_f, now.hour)
        and field_match(dom_f, now.day)
        and field_match(month_f, now.month)
        and field_match(dow_f, now.weekday())  # 0=Monday
    )


def check_and_dispatch_scheduled_workflows():
    """
    Called by Celery beat every minute.
    Finds all active scheduled workflows and dispatches those whose schedule matches now.
    """
    db: Session = SessionLocal()
    now = datetime.utcnow()
    dispatched = 0

    try:
        scheduled_workflows: List[Workflow] = (
            db.query(Workflow)
            .filter(
                Workflow.trigger_type == "scheduled",
                Workflow.status == "active",
                Workflow.is_deleted.is_(False),
            )
            .all()
        )

        for wf in scheduled_workflows:
            trigger_config = wf.trigger_config or {}
            if not _matches_schedule(trigger_config, now):
                continue

            try:
                from workflow.trigger_dispatcher import TriggerDispatcher
                count = TriggerDispatcher.dispatch(
                    trigger_type="scheduled",
                    event_data={"scheduled_at": now.isoformat()},
                    workspace_id=wf.workspace_id,
                    org_id=wf.organization_id,
                    db=db,
                )
                dispatched += count
            except Exception as exc:
                logger.warning("Failed to dispatch scheduled workflow=%d: %s", wf.id, exc)

    except Exception as exc:
        logger.exception("Scheduled workflow check failed: %s", exc)
    finally:
        db.close()

    if dispatched:
        logger.info("Scheduled dispatch: %d workflows fired at %s", dispatched, now.isoformat())
    return dispatched
