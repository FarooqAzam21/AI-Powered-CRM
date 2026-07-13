"""
KnowledgeAgent — Handles RAG retrieval, FAQ, and policy lookup.
"""
import logging
from typing import Dict, Any
from sqlalchemy.orm import Session

from ai.agents.base_agent import BaseAgent
from ai.agents.agent_context import AgentContext

logger = logging.getLogger(__name__)


class KnowledgeAgent(BaseAgent):
    agent_name = "knowledge_agent"
    supported_tasks = [
        "search_knowledge",
        "faq_lookup"
    ]

    async def prepare_context(self, ctx: AgentContext, db: Session) -> str:
        """
        Uses RAG to find relevant knowledge based on the query payload.
        """
        query = ctx.payload.get("query")
        if query and ctx.rag_enabled:
            # Reusing existing KnowledgeBase logic natively
            relevant_chunks = self.kb.search(query, top_k=3)
            if relevant_chunks:
                kb_info = "### Retrieved Knowledge\n"
                for i, chunk in enumerate(relevant_chunks):
                    kb_info += f"[Document {i+1}]: {chunk}\n\n"
                return kb_info
        return ""

    async def build_prompt(self, ctx: AgentContext, crm_context: str) -> str:
        if ctx.task_type in ["search_knowledge", "faq_lookup"]:
            return self.prompt_manager.render(
                "agents/knowledge_search", 
                query=ctx.payload.get("query"),
                retrieved_knowledge=crm_context
            )
            
        raise ValueError(f"Unknown task type for KnowledgeAgent: {ctx.task_type}")

    async def validate(self, raw_output: str, ctx: AgentContext) -> Dict[str, Any]:
        """
        Knowledge answers are usually text with citations, but we'll return structured JSON
        with {"answer": "...", "citations": [...]}.
        """
        return self.parser._extract_json(raw_output)

    async def update_memory(self, result_data: Dict[str, Any], ctx: AgentContext, db: Session):
        pass # Doesn't directly update customer memory unless explicitly chained
