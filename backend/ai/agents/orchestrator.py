import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from sqlalchemy.orm import Session

from ai.providers.ollama_provider import OllamaProvider
from ai.tools.tool_registry import get_tool_registry
from auth.rbac import Role

logger = logging.getLogger(__name__)


@dataclass
class AgentMetadata:
    name: str
    role_description: str
    system_prompt: str
    allowed_tools: List[str]
    required_role: Role = Role.VIEWER


AGENT_DEFINITIONS = {
    "SalesAgent": AgentMetadata(
        name="SalesAgent",
        role_description="Specialist in lead qualification, deal velocity, pipeline health, and sales strategies.",
        system_prompt=(
            "You are the Sales Intelligence Agent for an Enterprise CRM. "
            "Analyze leads, deal stages, and conversion probabilities. Recommend concrete sales actions."
        ),
        allowed_tools=["get_contact", "search_contacts", "get_deal", "search_deals", "get_sales_metrics", "create_task"],
    ),
    "EmailAgent": AgentMetadata(
        name="EmailAgent",
        role_description="Specialist in email context, communications, tone matching, and customer replies.",
        system_prompt=(
            "You are the Email Intelligence Agent for an Enterprise CRM. "
            "Analyze email threads, communication intent, and compose helpful, professional outreach."
        ),
        allowed_tools=["get_email", "search_emails", "get_contact", "draft_email"],
    ),
    "CRMAnalystAgent": AgentMetadata(
        name="CRMAnalystAgent",
        role_description="Specialist in sales analytics, pipeline metrics, KPI breakdowns, and performance reporting.",
        system_prompt=(
            "You are the CRM Analytics Agent. "
            "Deliver concise summaries of pipeline health, conversion rates, and revenue metrics based on workspace facts."
        ),
        allowed_tools=["get_sales_metrics", "search_deals", "search_contacts"],
    ),
    "ResearchAgent": AgentMetadata(
        name="ResearchAgent",
        role_description="Specialist in customer intelligence, knowledge base retrieval, and persona analysis.",
        system_prompt=(
            "You are the Research & Knowledge Agent for an Enterprise CRM. "
            "Synthesize customer intelligence, past interaction summaries, and knowledge base documentation."
        ),
        allowed_tools=["get_contact", "get_customer_profile", "search_emails"],
    ),
    "TaskAgent": AgentMetadata(
        name="TaskAgent",
        role_description="Specialist in task scheduling, team follow-ups, and operational action proposals.",
        system_prompt=(
            "You are the CRM Task & Operations Agent. "
            "Identify next actions, propose prioritized follow-up tasks, and keep the sales workflow organized."
        ),
        allowed_tools=["create_task", "get_contact", "get_deal"],
    ),
}


class AgentOrchestrator:
    """
    Controlled multi-agent orchestration engine.
    Dispatches queries to the most qualified agent without autonomous uncontrolled loops.
    """

    def __init__(self, provider: Optional[OllamaProvider] = None):
        self.provider = provider or OllamaProvider()
        self.tool_registry = get_tool_registry()

    def route_query_to_agent(self, query: str) -> str:
        """Determines best agent based on intent keywords."""
        q = query.lower()
        if any(k in q for k in ["email", "reply", "draft", "inbox", "message"]):
            return "EmailAgent"
        elif any(k in q for k in ["metric", "kpi", "analytics", "conversion", "revenue", "summary"]):
            return "CRMAnalystAgent"
        elif any(k in q for k in ["task", "follow-up", "followup", "schedule", "reminder", "todo"]):
            return "TaskAgent"
        elif any(k in q for k in ["research", "profile", "persona", "background", "company info"]):
            return "ResearchAgent"
        else:
            return "SalesAgent"

    async def run(
        self,
        query: str,
        workspace_id: int,
        user_role: Role,
        crm_context: str,
        db: Session,
        agent_override: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Executes a targeted agent query with tool assistance and proposal detection.
        """
        agent_name = agent_override or self.route_query_to_agent(query)
        agent = AGENT_DEFINITIONS.get(agent_name, AGENT_DEFINITIONS["SalesAgent"])

        # Detect if an action proposal is warranted
        proposed_actions = []
        q_lower = query.lower()
        if "create" in q_lower and "task" in q_lower:
            tool_res = await self.tool_registry.execute_tool(
                name="create_task",
                params={"title": query[:50], "priority": "high"},
                workspace_id=workspace_id,
                user_role=user_role,
                db=db,
            )
            if tool_res.get("status") == "proposed":
                proposed_actions.append(tool_res)

        elif "draft" in q_lower and "email" in q_lower:
            tool_res = await self.tool_registry.execute_tool(
                name="draft_email",
                params={"to_email": "contact@example.com", "subject": "CRM Follow-up", "body": "Following up on our recent conversation."},
                workspace_id=workspace_id,
                user_role=user_role,
                db=db,
            )
            if tool_res.get("status") == "proposed":
                proposed_actions.append(tool_res)

        # Build prompt
        system_instruction = (
            f"{agent.system_prompt}\n"
            f"Active Agent: {agent.name}\n"
            "Ground your answer strictly in the workspace records provided below. "
            "Be concise, actionable, and professional."
        )

        prompt = (
            f"{crm_context}\n\n"
            f"User Question: {query}\n"
            f"Assistant Answer:"
        )

        reply = await self.provider.generate(prompt=prompt, system_prompt=system_instruction)

        return {
            "agent": agent.name,
            "reply": reply,
            "proposed_actions": proposed_actions,
        }


_orchestrator = None


def get_agent_orchestrator() -> AgentOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = AgentOrchestrator()
    return _orchestrator
