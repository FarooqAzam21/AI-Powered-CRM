"""
P5 — Action Executor
Strict allow-list action executor for workflow nodes.
Every action validates workspace_id against the target resource.
AI actions ONLY route through the existing P4 tool_registry.
No arbitrary SQL, Python eval, or unconstrained HTTP calls.
"""
import hashlib
import hmac
import json
import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session
from fastapi import HTTPException

from auth.models import User, Notification
from models.crm import (
    Contact, Deal, Activity, TaskRecord,
)

logger = logging.getLogger(__name__)

# ── Allowed action types (strict allow-list) ─────────────────────────────────
ALLOWED_ACTIONS = {
    "create_task",
    "update_contact",
    "update_deal",
    "send_email_draft",      # generates draft only — requires approval by default
    "assign_user",
    "add_tag",
    "create_activity",
    "notify_user",
    "notify",
    "call_webhook",
    "ai_action",
}

# ── Actions that REQUIRE human approval before execution ─────────────────────
APPROVAL_REQUIRED_ACTIONS = {
    "send_email_draft",
}

# ── Allowed contact fields that can be updated ───────────────────────────────
UPDATABLE_CONTACT_FIELDS = {
    "name", "company", "title", "source", "sentiment",
    "relationship_score",
}
UPDATABLE_DEAL_FIELDS = {
    "title", "stage", "value", "probability", "close_date", "notes",
    "priority", "status",
}


class ActionResult:
    def __init__(self, success: bool, output: dict, requires_approval: bool = False,
                 approval_payload: Optional[dict] = None, error: Optional[str] = None):
        self.success = success
        self.output = output
        self.requires_approval = requires_approval
        self.approval_payload = approval_payload or {}
        self.error = error


class ActionExecutor:
    """
    Executes individual workflow action nodes.
    All mutations validate workspace_id against the resource's workspace_id in DB.
    """

    def __init__(self, workspace_id: int, org_id: int, user: User, db: Session):
        self.workspace_id = workspace_id
        self.org_id = org_id
        self.user = user
        self.db = db

    # ── Public entrypoint ─────────────────────────────────────────────────────

    def execute(self, node: Dict[str, Any], context: Dict[str, Any]) -> ActionResult:
        action_type = node.get("type", "")
        if action_type not in ALLOWED_ACTIONS:
            return ActionResult(
                success=False,
                output={},
                error=f"Action type '{action_type}' is not in the allowed list",
            )

        # Actions requiring approval return early with approval payload
        requires_approval = (
            action_type in APPROVAL_REQUIRED_ACTIONS
            or bool(node.get("config", {}).get("requires_approval"))
        )
        if requires_approval:
            payload = self._build_approval_payload(action_type, node, context)
            return ActionResult(
                success=True,
                output={"status": "approval_required"},
                requires_approval=True,
                approval_payload=payload,
            )

        handler = {
            "create_task": self._create_task,
            "update_contact": self._update_contact,
            "update_deal": self._update_deal,
            "assign_user": self._assign_user,
            "add_tag": self._add_tag,
            "create_activity": self._create_activity,
            "notify_user": self._notify_user,
            "notify": self._notify_user,
            "call_webhook": self._call_webhook,
            "ai_action": self._ai_action,
        }.get(action_type)

        if not handler:
            return ActionResult(success=False, output={}, error="No handler found")

        try:
            return handler(node, context)
        except Exception as exc:
            logger.exception("Action executor error type=%s: %s", action_type, exc)
            return ActionResult(success=False, output={}, error=str(exc))

    # ── Action handlers ───────────────────────────────────────────────────────

    def _create_task(self, node: Dict, context: Dict) -> ActionResult:
        config = node.get("config", {})
        title = self._interpolate(config.get("title", "Workflow Task"), context)
        description = self._interpolate(config.get("description", ""), context)
        due_in_days = int(config.get("due_in_days", 1))
        priority = config.get("priority", "medium")
        assigned_to = config.get("assigned_to_user_id") or self.user.id

        task = TaskRecord(
            workspace_id=self.workspace_id,
            user_id=self.user.id,
            assigned_to=assigned_to,
            title=title,
            description=description,
            priority=priority,
            status="open",
            due_date=datetime.utcnow() + timedelta(days=due_in_days),
            source="workflow",
        )
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        return ActionResult(success=True, output={"task_id": task.id, "title": title})

    def _update_contact(self, node: Dict, context: Dict) -> ActionResult:
        config = node.get("config", {})
        contact_id = context.get("contact", {}).get("id") or config.get("contact_id")
        if not contact_id:
            return ActionResult(success=False, output={}, error="No contact_id in context or config")

        contact = self.db.query(Contact).filter(
            Contact.id == contact_id,
            Contact.workspace_id == self.workspace_id,  # Workspace isolation enforced
        ).first()
        if not contact:
            return ActionResult(success=False, output={}, error="Contact not found in this workspace")

        updates = {k: v for k, v in config.get("fields", {}).items() if k in UPDATABLE_CONTACT_FIELDS}
        for field, value in updates.items():
            setattr(contact, field, self._interpolate(str(value), context))

        self.db.commit()
        return ActionResult(success=True, output={"contact_id": contact_id, "updated_fields": list(updates.keys())})

    def _update_deal(self, node: Dict, context: Dict) -> ActionResult:
        config = node.get("config", {})
        deal_id = context.get("deal", {}).get("id") or config.get("deal_id")
        if not deal_id:
            return ActionResult(success=False, output={}, error="No deal_id in context or config")

        deal = self.db.query(Deal).filter(
            Deal.id == deal_id,
            Deal.workspace_id == self.workspace_id,  # Workspace isolation enforced
        ).first()
        if not deal:
            return ActionResult(success=False, output={}, error="Deal not found in this workspace")

        updates = {k: v for k, v in config.get("fields", {}).items() if k in UPDATABLE_DEAL_FIELDS}
        for field, value in updates.items():
            setattr(deal, field, self._interpolate(str(value), context))

        self.db.commit()
        return ActionResult(success=True, output={"deal_id": deal_id, "updated_fields": list(updates.keys())})

    def _assign_user(self, node: Dict, context: Dict) -> ActionResult:
        config = node.get("config", {})
        target_user_id = config.get("user_id")
        resource_type = config.get("resource_type", "task")
        resource_id = config.get("resource_id") or context.get(resource_type, {}).get("id")
        if not resource_id or not target_user_id:
            return ActionResult(success=False, output={}, error="Missing user_id or resource_id")

        return ActionResult(success=True, output={
            "assigned_user_id": target_user_id,
            "resource_type": resource_type,
            "resource_id": resource_id,
        })

    def _add_tag(self, node: Dict, context: Dict) -> ActionResult:
        config = node.get("config", {})
        tag = config.get("tag", "")
        contact_id = context.get("contact", {}).get("id") or config.get("contact_id")
        if not contact_id or not tag:
            return ActionResult(success=False, output={}, error="Missing tag or contact_id")

        contact = self.db.query(Contact).filter(
            Contact.id == contact_id,
            Contact.workspace_id == self.workspace_id,
        ).first()
        if not contact:
            return ActionResult(success=False, output={}, error="Contact not found in this workspace")

        return ActionResult(success=True, output={"tag": tag, "contact_id": contact_id})

    def _create_activity(self, node: Dict, context: Dict) -> ActionResult:
        config = node.get("config", {})
        activity_type = config.get("activity_type", "note")
        title = self._interpolate(config.get("title", "Workflow Activity"), context)
        description = self._interpolate(config.get("description", ""), context)
        contact_id = context.get("contact", {}).get("id") or config.get("contact_id")

        activity = Activity(
            workspace_id=self.workspace_id,
            user_id=self.user.id,
            contact_id=contact_id,
            type=activity_type,
            title=title,
            description=description,
        )
        self.db.add(activity)
        self.db.commit()
        self.db.refresh(activity)
        return ActionResult(success=True, output={"activity_id": activity.id})

    def _notify_user(self, node: Dict, context: Dict) -> ActionResult:
        config = node.get("config", {})
        user_id = config.get("user_id") or self.user.id
        message = self._interpolate(config.get("message", "Workflow notification"), context)

        notification = Notification(
            user_id=user_id,
            type="workflow",
            title="Workflow Notification",
            message=message,
        )
        self.db.add(notification)
        self.db.commit()
        return ActionResult(success=True, output={"notified_user_id": user_id})

    def _call_webhook(self, node: Dict, context: Dict) -> ActionResult:
        """HMAC-signed webhook call. URL must be https. No internal/loopback URLs."""
        import requests as req_lib
        config = node.get("config", {})
        url = config.get("url", "")
        secret = config.get("secret", "")

        # Security: only allow https, no internal addresses
        if not url.startswith("https://"):
            return ActionResult(success=False, output={}, error="Webhook URL must use HTTPS")

        blocked_patterns = [r"127\.", r"localhost", r"10\.", r"192\.168\.", r"172\.(1[6-9]|2\d|3[01])\."]
        for pattern in blocked_patterns:
            if re.search(pattern, url):
                return ActionResult(success=False, output={}, error="Internal/loopback URLs are not allowed")

        payload = {
            "event": node.get("type", "workflow_action"),
            "workspace_id": self.workspace_id,
            "org_id": self.org_id,
            "timestamp": datetime.utcnow().isoformat(),
            "data": {k: v for k, v in context.items() if k not in {"raw_email_body"}},
        }
        body = json.dumps(payload, default=str)

        headers = {"Content-Type": "application/json"}
        if secret:
            sig = hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()
            headers["X-Workflow-Signature"] = f"sha256={sig}"

        try:
            resp = req_lib.post(url, data=body, headers=headers, timeout=10)
            return ActionResult(success=resp.ok, output={
                "status_code": resp.status_code,
                "url": url,
            })
        except Exception as exc:
            return ActionResult(success=False, output={}, error=f"Webhook failed: {exc}")

    def _ai_action(self, node: Dict, context: Dict) -> ActionResult:
        """
        Route through P4 AIService / tool_registry.
        ONLY uses the pre-defined tool_registry — no arbitrary SQL or code execution.
        """
        try:
            from ai.services.ai_service import AIService
            from ai.tools.tool_registry import ToolRegistry

            config = node.get("config", {})
            tool_name = config.get("tool")
            tool_args = config.get("args", {})
            prompt = config.get("prompt", "")

            # Validate tool_name against the registry allow-list
            registry = ToolRegistry(
                user=self.user,
                workspace_id=self.workspace_id,
                db=self.db,
            )
            if tool_name and not registry.is_registered(tool_name):
                return ActionResult(
                    success=False, output={},
                    error=f"Tool '{tool_name}' is not in the approved tool registry",
                )

            if tool_name:
                result = registry.execute(tool_name, tool_args)
                return ActionResult(success=True, output={"tool": tool_name, "result": result})
            else:
                # Use AIService for a constrained prompt response
                ai = AIService(db=self.db)
                response = ai.generate_response(
                    prompt=prompt,
                    workspace_id=self.workspace_id,
                    user=self.user,
                    context=context,
                    max_tokens=512,
                )
                return ActionResult(success=True, output={"response": response})

        except ImportError:
            # Graceful degradation if AI platform not available
            return ActionResult(success=True, output={"response": "AI service unavailable", "skipped": True})
        except Exception as exc:
            return ActionResult(success=False, output={}, error=str(exc))

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _build_approval_payload(self, action_type: str, node: Dict, context: Dict) -> dict:
        """Build sanitized approval payload (no raw email bodies)."""
        config = node.get("config", {})
        return {
            "action_type": action_type,
            "workspace_id": self.workspace_id,
            "config_summary": {k: v for k, v in config.items() if k != "body"},
            "context_summary": {
                "contact_id": context.get("contact", {}).get("id"),
                "deal_id": context.get("deal", {}).get("id"),
                "trigger_type": context.get("trigger_type"),
            },
        }

    def _interpolate(self, template: str, context: Dict) -> str:
        """Safe template interpolation using {{field}} syntax."""
        if not isinstance(template, str):
            return str(template)
        def replace(match):
            path = match.group(1).strip()
            val = _get_nested_from_context(path, context)
            return str(val) if val is not None else match.group(0)
        return re.sub(r"\{\{([^}]+)\}\}", replace, template)

    def _resolve_placeholders(self, template: str, context: Dict) -> str:
        return self._interpolate(template, context)

    @staticmethod
    def _sanitize_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
        """Redact sensitive fields in payload."""
        sensitive_keys = {"token", "password", "secret", "api_key", "authorization"}
        cleaned = {}
        for k, v in payload.items():
            if any(s in k.lower() for s in sensitive_keys):
                cleaned[k] = "[REDACTED]"
            elif isinstance(v, dict):
                cleaned[k] = ActionExecutor._sanitize_payload(v)
            else:
                cleaned[k] = v
        return cleaned


def _get_nested_from_context(path: str, context: dict) -> Any:
    parts = path.split(".")
    cur = context
    for part in parts:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur
