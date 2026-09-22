import logging
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from models.crm import Contact, Deal, EmailMetadata, Activity, CustomerProfile
from auth.rbac import Role

logger = logging.getLogger(__name__)


@dataclass
class ToolDefinition:
    name: str
    description: str
    parameters: Dict[str, Any]
    required_role: Role = Role.VIEWER
    is_mutation_proposal: bool = False
    handler: Optional[Callable] = None


class ToolRegistry:
    """
    Safe internal tool registry for CRM AI Copilot and Agents.
    Validates workspace isolation, user context, and RBAC on every invocation.
    Proposals for mutations are strictly separated from actual database changes.
    """

    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}
        self._register_default_tools()

    def register(self, tool: ToolDefinition):
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        return self._tools.get(name)

    def list_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters,
                "is_mutation_proposal": t.is_mutation_proposal,
            }
            for t in self._tools.values()
        ]

    def _register_default_tools(self):
        # 1. get_contact
        self.register(ToolDefinition(
            name="get_contact",
            description="Retrieve contact details by ID strictly within the active workspace.",
            parameters={"contact_id": "int"},
            required_role=Role.VIEWER,
            handler=self._handle_get_contact,
        ))

        # 2. search_contacts
        self.register(ToolDefinition(
            name="search_contacts",
            description="Search contacts by name, email, or company in the active workspace.",
            parameters={"query": "str", "limit": "int"},
            required_role=Role.VIEWER,
            handler=self._handle_search_contacts,
        ))

        # 3. get_deal
        self.register(ToolDefinition(
            name="get_deal",
            description="Retrieve pipeline deal details by ID.",
            parameters={"deal_id": "int"},
            required_role=Role.VIEWER,
            handler=self._handle_get_deal,
        ))

        # 4. search_deals
        self.register(ToolDefinition(
            name="search_deals",
            description="Search deals by title, stage, or status in the active workspace.",
            parameters={"query": "str", "stage": "str", "status": "str"},
            required_role=Role.VIEWER,
            handler=self._handle_search_deals,
        ))

        # 5. get_email
        self.register(ToolDefinition(
            name="get_email",
            description="Retrieve metadata for a specific email message.",
            parameters={"email_id": "int"},
            required_role=Role.VIEWER,
            handler=self._handle_get_email,
        ))

        # 6. search_emails
        self.register(ToolDefinition(
            name="search_emails",
            description="Search recent emails in the workspace by subject or snippet keyword.",
            parameters={"query": "str", "limit": "int"},
            required_role=Role.VIEWER,
            handler=self._handle_search_emails,
        ))

        # 7. get_customer_profile
        self.register(ToolDefinition(
            name="get_customer_profile",
            description="Retrieve persona and intelligence profile for a contact.",
            parameters={"contact_id": "int"},
            required_role=Role.VIEWER,
            handler=self._handle_get_customer_profile,
        ))

        # 8. get_sales_metrics
        self.register(ToolDefinition(
            name="get_sales_metrics",
            description="Retrieve aggregated sales pipeline and deal conversion metrics for the workspace.",
            parameters={},
            required_role=Role.VIEWER,
            handler=self._handle_get_sales_metrics,
        ))

        # 9. create_task (Proposal only!)
        self.register(ToolDefinition(
            name="create_task",
            description="Proposes creating a new follow-up or CRM task. Requires human confirmation.",
            parameters={"title": "str", "priority": "str", "contact_id": "int", "description": "str"},
            required_role=Role.WORKSPACE_ADMIN,
            is_mutation_proposal=True,
            handler=self._handle_propose_task,
        ))

        # 10. draft_email (Proposal only!)
        self.register(ToolDefinition(
            name="draft_email",
            description="Proposes an email draft to send to a contact. Requires human confirmation.",
            parameters={"to_email": "str", "subject": "str", "body": "str", "contact_id": "int"},
            required_role=Role.WORKSPACE_ADMIN,
            is_mutation_proposal=True,
            handler=self._handle_propose_email,
        ))

    # --- Tool Execution with RBAC and Workspace Safety ---

    async def execute_tool(
        self,
        name: str,
        params: Dict[str, Any],
        workspace_id: int,
        user_role: Role,
        db: Session,
    ) -> Dict[str, Any]:
        tool = self.get_tool(name)
        if not tool:
            return {"error": f"Tool '{name}' not found."}

        # RBAC Check (Viewer < Security Analyst < Workspace Admin < Super Admin)
        role_levels = {
            Role.VIEWER: 10,
            Role.SECURITY_ANALYST: 20,
            Role.WORKSPACE_ADMIN: 30,
            Role.SUPER_ADMIN: 40,
        }
        user_level = role_levels.get(user_role, 0)
        required_level = role_levels.get(tool.required_role, 10)

        # Allow admin operations for Workspace Admin and Super Admin
        if user_level < required_level and user_role not in (Role.WORKSPACE_ADMIN, Role.SUPER_ADMIN):
            return {"error": f"Permission denied: {name} requires {tool.required_role} role."}

        try:
            return await tool.handler(params, workspace_id, db)
        except Exception as exc:
            logger.error("Error executing tool %s: %s", name, exc)
            return {"error": str(exc)}

    # --- Handlers ---

    async def _handle_get_contact(self, params: dict, workspace_id: int, db: Session) -> dict:
        cid = params.get("contact_id")
        contact = db.query(Contact).filter(Contact.id == cid, Contact.workspace_id == workspace_id).first()
        if not contact:
            return {"found": False, "message": "Contact not found"}
        return {
            "found": True,
            "id": contact.id,
            "name": contact.name,
            "email": contact.email,
            "company": contact.company,
            "title": contact.title,
            "lead_status": contact.lead_status,
        }

    async def _handle_search_contacts(self, params: dict, workspace_id: int, db: Session) -> dict:
        q = params.get("query", "").strip()
        limit = min(params.get("limit", 5), 20)
        query = db.query(Contact).filter(Contact.workspace_id == workspace_id)
        if q:
            query = query.filter(
                or_(
                    Contact.name.ilike(f"%{q}%"),
                    Contact.email.ilike(f"%{q}%"),
                    Contact.company.ilike(f"%{q}%"),
                )
            )
        contacts = query.limit(limit).all()
        return {
            "count": len(contacts),
            "contacts": [{"id": c.id, "name": c.name, "email": c.email, "company": c.company} for c in contacts],
        }

    async def _handle_get_deal(self, params: dict, workspace_id: int, db: Session) -> dict:
        did = params.get("deal_id")
        deal = db.query(Deal).filter(Deal.id == did, Deal.workspace_id == workspace_id).first()
        if not deal:
            return {"found": False, "message": "Deal not found"}
        return {
            "found": True,
            "id": deal.id,
            "title": deal.title,
            "value": deal.value,
            "stage": deal.stage,
            "status": deal.status,
            "probability": deal.probability,
        }

    async def _handle_search_deals(self, params: dict, workspace_id: int, db: Session) -> dict:
        q = params.get("query", "").strip()
        stage = params.get("stage")
        status_filter = params.get("status")

        query = db.query(Deal).filter(Deal.workspace_id == workspace_id)
        if q:
            query = query.filter(Deal.title.ilike(f"%{q}%"))
        if stage:
            query = query.filter(Deal.stage == stage)
        if status_filter:
            query = query.filter(Deal.status == status_filter)

        deals = query.limit(10).all()
        return {
            "count": len(deals),
            "deals": [{"id": d.id, "title": d.title, "value": d.value, "stage": d.stage, "status": d.status} for d in deals],
        }

    async def _handle_get_email(self, params: dict, workspace_id: int, db: Session) -> dict:
        eid = params.get("email_id")
        email = db.query(EmailMetadata).filter(EmailMetadata.id == eid, EmailMetadata.workspace_id == workspace_id).first()
        if not email:
            return {"found": False, "message": "Email not found"}
        return {
            "found": True,
            "id": email.id,
            "subject": email.subject,
            "sender": email.sender,
            "category": email.category,
            "priority": email.priority,
            "snippet": email.snippet,
        }

    async def _handle_search_emails(self, params: dict, workspace_id: int, db: Session) -> dict:
        q = params.get("query", "").strip()
        limit = min(params.get("limit", 5), 10)
        query = db.query(EmailMetadata).filter(EmailMetadata.workspace_id == workspace_id)
        if q:
            query = query.filter(
                or_(
                    EmailMetadata.subject.ilike(f"%{q}%"),
                    EmailMetadata.snippet.ilike(f"%{q}%"),
                )
            )
        emails = query.order_by(EmailMetadata.received_at.desc()).limit(limit).all()
        return {
            "count": len(emails),
            "emails": [{"id": e.id, "subject": e.subject, "sender": e.sender, "priority": e.priority} for e in emails],
        }

    async def _handle_get_customer_profile(self, params: dict, workspace_id: int, db: Session) -> dict:
        cid = params.get("contact_id")
        profile = (
            db.query(CustomerProfile)
            .join(Contact, CustomerProfile.contact_id == Contact.id)
            .filter(CustomerProfile.contact_id == cid, Contact.workspace_id == workspace_id)
            .first()
        )
        if not profile:
            return {"found": False, "message": "Profile not found"}
        return {
            "found": True,
            "contact_id": cid,
            "buyer_persona": profile.buyer_persona,
            "pain_points": profile.pain_points,
            "interests": profile.interests,
        }

    async def _handle_get_sales_metrics(self, params: dict, workspace_id: int, db: Session) -> dict:
        total_deals = db.query(func.count(Deal.id)).filter(Deal.workspace_id == workspace_id).scalar() or 0
        won_deals = db.query(func.count(Deal.id)).filter(Deal.workspace_id == workspace_id, Deal.status == "won").scalar() or 0
        pipeline_val = db.query(func.sum(Deal.value)).filter(Deal.workspace_id == workspace_id, Deal.status == "open").scalar() or 0.0
        return {
            "total_deals": total_deals,
            "won_deals": won_deals,
            "open_pipeline_value": float(pipeline_val),
            "conversion_rate": round((won_deals / total_deals * 100) if total_deals > 0 else 0.0, 1),
        }

    async def _handle_propose_task(self, params: dict, workspace_id: int, db: Session) -> dict:
        """Constructs an action proposal for human confirmation (NO direct mutation)."""
        return {
            "action_type": "create_task",
            "status": "proposed",
            "requires_confirmation": True,
            "summary": f"Create Task: '{params.get('title')}' (Priority: {params.get('priority', 'medium')})",
            "params": {
                "title": params.get("title", "Follow-up"),
                "priority": params.get("priority", "medium"),
                "contact_id": params.get("contact_id"),
                "description": params.get("description", ""),
            },
        }

    async def _handle_propose_email(self, params: dict, workspace_id: int, db: Session) -> dict:
        """Constructs an email draft proposal for human confirmation."""
        return {
            "action_type": "draft_email",
            "status": "proposed",
            "requires_confirmation": True,
            "summary": f"Draft Email to {params.get('to_email')}: '{params.get('subject')}'",
            "params": {
                "to_email": params.get("to_email"),
                "subject": params.get("subject"),
                "body": params.get("body"),
                "contact_id": params.get("contact_id"),
            },
        }

    # --- Confirmation Execution Layer ---

    def execute_confirmed_action(
        self,
        action_type: str,
        params: Dict[str, Any],
        workspace_id: int,
        user_id: int,
        db: Session,
    ) -> Dict[str, Any]:
        """Safely mutates the database ONLY after explicit user confirmation."""
        if action_type == "create_task":
            task = Activity(
                workspace_id=workspace_id,
                user_id=user_id,
                type="task",
                title=params.get("title", "New Task"),
                description=params.get("description", ""),
                contact_id=params.get("contact_id"),
                status="pending",
            )
            db.add(task)
            db.commit()
            db.refresh(task)
            return {
                "success": True,
                "action": "task_created",
                "task_id": task.id,
                "message": f"Task '{task.title}' created successfully.",
            }

        elif action_type == "draft_email":
            # Saves draft or logs interaction
            return {
                "success": True,
                "action": "email_drafted",
                "message": f"Email draft to {params.get('to_email')} prepared.",
                "draft": params,
            }

        elif action_type == "update_deal":
            deal_id = params.get("deal_id")
            deal = db.query(Deal).filter(Deal.id == deal_id, Deal.workspace_id == workspace_id).first()
            if not deal:
                return {"success": False, "error": "Deal not found"}
            if "stage" in params:
                deal.stage = params["stage"]
            if "value" in params:
                deal.value = float(params["value"])
            db.commit()
            return {
                "success": True,
                "action": "deal_updated",
                "deal_id": deal.id,
                "message": f"Deal '{deal.title}' updated successfully.",
            }

        return {"success": False, "error": f"Unknown action type '{action_type}'"}


_tool_registry = None


def get_tool_registry() -> ToolRegistry:
    global _tool_registry
    if _tool_registry is None:
        _tool_registry = ToolRegistry()
    return _tool_registry
