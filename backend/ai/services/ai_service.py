import time
import logging
from typing import Dict, Any, Optional, AsyncIterator, List
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from ai.providers.ollama_provider import OllamaProvider
from ai.context.context_builder import ContextBuilder, get_context_builder
from ai.memory.conversation_memory import MemoryService, get_memory_service
from ai.rag.retrieval_service import RetrievalService, get_retrieval_service
from ai.prompts.prompt_manager import PromptManager, get_prompt_manager
from ai.parser.json_parser import ResponseParser
from ai.agents.orchestrator import AgentOrchestrator, get_agent_orchestrator
from ai.tools.tool_registry import ToolRegistry, get_tool_registry
from billing.service import BillingService
from models.ai_copilot import AIAuditLog
from auth.rbac import Role

logger = logging.getLogger(__name__)


class AIService:
    """
    Centralized Enterprise AI Platform Service.
    Coordinates all LLM generation, RAG, multi-agent orchestration, conversation memory,
    safe tool execution, P3 quota enforcement, and observability logging.
    """

    def __init__(self):
        self.provider = OllamaProvider()
        self.context_builder = get_context_builder()
        self.memory_service = get_memory_service()
        self.retrieval_service = get_retrieval_service()
        self.prompt_manager = get_prompt_manager()
        self.orchestrator = get_agent_orchestrator()
        self.tool_registry = get_tool_registry()

    def enforce_ai_quota(self, org_id: int, db: Session, amount: int = 1) -> None:
        """Enforces P3 enterprise AI request quota."""
        quota = BillingService.check_quota(org_id=org_id, resource="ai_requests", requested_amount=amount, db=db)
        if not quota.allowed:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail={
                    "error": "quota_exceeded",
                    "resource": "ai_requests",
                    "limit": quota.limit,
                    "used": quota.used,
                    "remaining": quota.remaining,
                    "message": f"AI request quota exceeded ({quota.used}/{quota.limit}). Upgrade your subscription plan.",
                },
            )

    def log_ai_audit(
        self,
        db: Session,
        workspace_id: int,
        org_id: int,
        user_id: Optional[int],
        agent: str,
        request_type: str,
        latency_ms: float,
        success: bool,
        error: Optional[str] = None,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
    ):
        try:
            audit = AIAuditLog(
                workspace_id=workspace_id,
                organization_id=org_id,
                user_id=user_id,
                model=self.provider.model,
                agent=agent,
                request_type=request_type,
                latency_ms=round(latency_ms, 2),
                success=success,
                error=error,
                tool_calls=tool_calls,
                quota_consumed=1 if success else 0,
            )
            db.add(audit)
            db.commit()
        except Exception as exc:
            logger.warning("Could not record AI audit log: %s", exc)

    async def copilot_chat(
        self,
        db: Session,
        workspace_id: int,
        org_id: int,
        user_id: int,
        user_role: Role,
        query: str,
        conversation_id: Optional[int] = None,
        contact_id: Optional[int] = None,
        deal_id: Optional[int] = None,
        agent_override: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Main Copilot chat endpoint:
        1. Enforces P3 billing quota
        2. Retrieves RAG knowledge chunks
        3. Builds compact, budgeted, tenant-safe context
        4. Invokes AgentOrchestrator
        5. Saves to Conversation Memory
        6. Increments P3 usage counter and records audit log
        """
        start_time = time.time()
        self.enforce_ai_quota(org_id=org_id, db=db, amount=1)

        # 1. Manage Conversation Memory
        if not conversation_id:
            conv = self.memory_service.create_conversation(
                db=db, workspace_id=workspace_id, user_id=user_id, title=query[:35]
            )
            conversation_id = conv.id
        else:
            conv = self.memory_service.get_conversation(db=db, conversation_id=conversation_id, workspace_id=workspace_id)
            if not conv:
                raise HTTPException(status_code=404, detail="Conversation not found in active workspace.")

        # Record User Message
        self.memory_service.add_message(
            db=db,
            conversation_id=conversation_id,
            workspace_id=workspace_id,
            role="user",
            content=query,
        )

        try:
            # 2. RAG Semantic Retrieval
            rag_docs = await self.retrieval_service.search(db=db, workspace_id=workspace_id, query=query, top_k=2)
            rag_chunks = [d["content"] for d in rag_docs]

            # 3. Context Builder
            ctx_data = self.context_builder.build_copilot_context(
                db=db,
                workspace_id=workspace_id,
                query=query,
                contact_id=contact_id,
                deal_id=deal_id,
                rag_chunks=rag_chunks,
            )

            # 4. Multi-Agent Orchestration
            orch_res = await self.orchestrator.run(
                query=query,
                workspace_id=workspace_id,
                user_role=user_role,
                crm_context=ctx_data["formatted_context"],
                db=db,
                agent_override=agent_override,
            )

            latency = (time.time() - start_time) * 1000

            # 5. Save Assistant Message
            assistant_msg = self.memory_service.add_message(
                db=db,
                conversation_id=conversation_id,
                workspace_id=workspace_id,
                role="assistant",
                content=orch_res["reply"],
                proposed_actions=orch_res["proposed_actions"],
                context_references=ctx_data["references"],
            )

            # 6. Increment P3 Quota Usage
            BillingService.increment_usage(org_id=org_id, resource="ai_requests", amount=1, db=db)

            # 7. Audit Logging
            self.log_ai_audit(
                db=db,
                workspace_id=workspace_id,
                org_id=org_id,
                user_id=user_id,
                agent=orch_res["agent"],
                request_type="copilot_chat",
                latency_ms=latency,
                success=True,
                tool_calls=orch_res["proposed_actions"],
            )

            return {
                "conversation_id": conversation_id,
                "message_id": assistant_msg.id,
                "agent": orch_res["agent"],
                "reply": orch_res["reply"],
                "proposed_actions": orch_res["proposed_actions"],
                "references": ctx_data["references"],
                "latency_ms": round(latency, 1),
            }

        except Exception as exc:
            latency = (time.time() - start_time) * 1000
            self.log_ai_audit(
                db=db,
                workspace_id=workspace_id,
                org_id=org_id,
                user_id=user_id,
                agent="copilot",
                request_type="copilot_chat",
                latency_ms=latency,
                success=False,
                error=str(exc),
            )
            raise

    async def stream_copilot_chat(
        self,
        db: Session,
        workspace_id: int,
        org_id: int,
        user_id: int,
        query: str,
        conversation_id: Optional[int] = None,
    ) -> AsyncIterator[str]:
        """Streams tokens for Copilot chat via SSE."""
        self.enforce_ai_quota(org_id=org_id, db=db, amount=1)
        
        ctx_data = self.context_builder.build_copilot_context(
            db=db, workspace_id=workspace_id, query=query
        )
        prompt = f"{ctx_data['formatted_context']}\n\nUser Question: {query}\nAssistant Answer:"

        # Increment usage on initiation of stream
        BillingService.increment_usage(org_id=org_id, resource="ai_requests", amount=1, db=db)

        async for token in self.provider.stream_generate(prompt):
            yield token


_ai_service = None


def get_ai_service() -> AIService:
    global _ai_service
    if _ai_service is None:
        _ai_service = AIService()
    return _ai_service
