"""
HiringAgent — Handles HR and recruitment related AI tasks.
"""
import logging
from typing import Dict, Any
from sqlalchemy.orm import Session

from ai.agents.base_agent import BaseAgent
from ai.agents.agent_context import AgentContext

logger = logging.getLogger(__name__)


class HiringAgent(BaseAgent):
    agent_name = "hiring_agent"
    supported_tasks = [
        "parse_resume",
        "score_candidate",
        "generate_interview_questions"
    ]

    async def prepare_context(self, ctx: AgentContext, db: Session) -> str:
        if ctx.contact_id:
            return self.context_builder.build_context(db, ctx.contact_id)
        return ""

    async def build_prompt(self, ctx: AgentContext, crm_context: str) -> str:
        if ctx.task_type == "parse_resume":
            return self.prompt_manager.render(
                "agents/hiring_parse", 
                resume_text=ctx.payload.get("resume_text")
            )
            
        elif ctx.task_type == "score_candidate":
            return self.prompt_manager.render(
                "agents/hiring_score", 
                candidate_data=ctx.payload.get("candidate_data"),
                job_description=ctx.payload.get("job_description")
            )
            
        elif ctx.task_type == "generate_interview_questions":
            return self.prompt_manager.render(
                "agents/hiring_questions", 
                candidate_data=ctx.payload.get("candidate_data"),
                role=ctx.payload.get("role")
            )

        raise ValueError(f"Unknown task type for HiringAgent: {ctx.task_type}")

    async def validate(self, raw_output: str, ctx: AgentContext) -> Dict[str, Any]:
        """
        All hiring tasks return structured JSON (parsed skills, scores).
        """
        return self.parser._extract_json(raw_output)

    async def update_memory(self, result_data: Dict[str, Any], ctx: AgentContext, db: Session):
        """
        Update memory with hiring notes.
        """
        if ctx.task_type == "parse_resume" and ctx.contact_id:
            memory = self._get_agent_memory(db, ctx.contact_id)
            if memory and "skills" in result_data:
                memory.update({"hiring_notes": [f"Parsed skills: {', '.join(result_data['skills'][:5])}"]})
