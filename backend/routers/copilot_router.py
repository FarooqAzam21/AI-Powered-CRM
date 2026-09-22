from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from auth.rbac import get_auth_context, AuthContext, Role
from auth.dependencies import require_workspace_member
from ai.services.ai_service import get_ai_service
from ai.memory.conversation_memory import get_memory_service
from ai.rag.retrieval_service import get_retrieval_service
from ai.tools.tool_registry import get_tool_registry
from billing.service import BillingService

router = APIRouter(prefix="/api/v1/copilot", tags=["AI Copilot & Platform"])


# --- Schemas ---
class ChatRequest(BaseModel):
    query: str = Field(..., description="Prompt or query for the AI Copilot")
    conversation_id: Optional[int] = Field(None, description="Existing conversation ID to continue")
    contact_id: Optional[int] = None
    deal_id: Optional[int] = None
    agent: Optional[str] = None


class CreateConversationRequest(BaseModel):
    title: Optional[str] = "New Conversation"
    agent: Optional[str] = "copilot"


class ConfirmActionRequest(BaseModel):
    message_id: int
    action_type: str
    params: Dict[str, Any]


class RejectActionRequest(BaseModel):
    message_id: int


class RAGIndexRequest(BaseModel):
    content: str
    source_type: str = "custom"
    source_id: Optional[str] = None
    title: Optional[str] = ""
    metadata: Optional[Dict[str, Any]] = None


# --- Endpoints ---

@router.get("/status")
async def get_copilot_status(
    auth: AuthContext = Depends(require_workspace_member),
    db: Session = Depends(get_db),
):
    """Returns AI model health, active agent status, and remaining workspace AI quota."""
    ai_service = get_ai_service()
    is_healthy = await ai_service.provider.health_check()
    org_id = auth.organization_id or 1
    quota_res = BillingService.check_quota(org_id, "ai_requests", 1, db)

    return {
        "status": "ready",
        "provider": "ollama",
        "model": ai_service.provider.model,
        "ollama_connected": is_healthy,
        "context_limit": ai_service.provider.context_size,
        "quota": {
            "used": quota_res.used,
            "limit": quota_res.limit,
            "remaining": quota_res.remaining,
            "unlimited": quota_res.limit == -1,
        },
    }


@router.get("/conversations")
def list_conversations(
    auth: AuthContext = Depends(require_workspace_member),
    limit: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List recent Copilot conversations for current user in active workspace."""
    memory_service = get_memory_service()
    user_id = auth.user.id if auth.user else None
    convs = memory_service.list_conversations(
        db=db, workspace_id=auth.workspace_id, user_id=user_id, limit=limit
    )
    return [
        {
            "id": c.id,
            "title": c.title,
            "agent": c.agent,
            "created_at": c.created_at.isoformat(),
            "updated_at": c.updated_at.isoformat(),
        }
        for c in convs
    ]


@router.post("/conversations")
def create_conversation(
    req: CreateConversationRequest,
    auth: AuthContext = Depends(require_workspace_member),
    db: Session = Depends(get_db),
):
    """Explicitly create a new conversation."""
    memory_service = get_memory_service()
    user_id = auth.user.id if auth.user else 1
    conv = memory_service.create_conversation(
        db=db,
        workspace_id=auth.workspace_id,
        user_id=user_id,
        title=req.title,
        agent=req.agent or "copilot",
    )
    return {
        "id": conv.id,
        "title": conv.title,
        "agent": conv.agent,
        "created_at": conv.created_at.isoformat(),
    }


@router.get("/conversations/{conversation_id}")
def get_conversation_history(
    conversation_id: int,
    auth: AuthContext = Depends(require_workspace_member),
    db: Session = Depends(get_db),
):
    """Retrieve full conversation messages with references and proposed actions."""
    memory_service = get_memory_service()
    conv = memory_service.get_conversation(db, conversation_id, auth.workspace_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found in active workspace.")

    messages = memory_service.get_messages(db, conversation_id, auth.workspace_id)
    return {
        "id": conv.id,
        "title": conv.title,
        "agent": conv.agent,
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "proposed_actions": m.proposed_actions,
                "action_status": m.action_status,
                "references": m.context_references,
                "created_at": m.created_at.isoformat(),
            }
            for m in messages
        ],
    }


@router.delete("/conversations/{conversation_id}")
def delete_conversation(
    conversation_id: int,
    auth: AuthContext = Depends(require_workspace_member),
    db: Session = Depends(get_db),
):
    """Delete a conversation within active workspace."""
    memory_service = get_memory_service()
    success = memory_service.delete_conversation(db, conversation_id, auth.workspace_id)
    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return {"status": "success", "message": "Conversation deleted."}


@router.post("/chat")
async def copilot_chat(
    req: ChatRequest,
    auth: AuthContext = Depends(require_workspace_member),
    db: Session = Depends(get_db),
):
    """Main Copilot chat endpoint. Uses Ollama, RAG, agent orchestration, and P3 quotas."""
    ai_service = get_ai_service()
    org_id = auth.organization_id or 1
    user_id = auth.user.id if auth.user else 1
    user_role = auth.role or Role.VIEWER

    return await ai_service.copilot_chat(
        db=db,
        workspace_id=auth.workspace_id,
        org_id=org_id,
        user_id=user_id,
        user_role=user_role,
        query=req.query,
        conversation_id=req.conversation_id,
        contact_id=req.contact_id,
        deal_id=req.deal_id,
        agent_override=req.agent,
    )


@router.post("/chat/stream")
async def copilot_chat_stream(
    req: ChatRequest,
    auth: AuthContext = Depends(require_workspace_member),
    db: Session = Depends(get_db),
):
    """Streaming response for AI Copilot via Server-Sent Events (SSE)."""
    ai_service = get_ai_service()
    org_id = auth.organization_id or 1
    user_id = auth.user.id if auth.user else 1

    # Pre-enforce quota prior to initiating response stream to handle HTTP 402 payment errors gracefully
    ai_service.enforce_ai_quota(org_id=org_id, db=db, amount=1)

    async def token_generator():
        async for token in ai_service.stream_copilot_chat(
            db=db,
            workspace_id=auth.workspace_id,
            org_id=org_id,
            user_id=user_id,
            query=req.query,
            conversation_id=req.conversation_id,
        ):
            yield f"data: {token}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(token_generator(), media_type="text/event-stream")


@router.post("/actions/confirm")
def confirm_action(
    req: ConfirmActionRequest,
    auth: AuthContext = Depends(require_workspace_member),
    db: Session = Depends(get_db),
):
    """
    Explicit user confirmation executing a proposed AI action.
    Separates suggestion from mutation.
    """
    tool_registry = get_tool_registry()
    user_id = auth.user.id if auth.user else 1
    res = tool_registry.execute_confirmed_action(
        action_type=req.action_type,
        params=req.params,
        workspace_id=auth.workspace_id,
        user_id=user_id,
        db=db,
    )

    if res.get("success"):
        memory_service = get_memory_service()
        memory_service.update_action_status(
            db=db,
            message_id=req.message_id,
            workspace_id=auth.workspace_id,
            action_status="executed",
        )

    return res


@router.post("/actions/reject")
def reject_action(
    req: RejectActionRequest,
    auth: AuthContext = Depends(require_workspace_member),
    db: Session = Depends(get_db),
):
    """User dismisses/rejects a proposed action."""
    memory_service = get_memory_service()
    memory_service.update_action_status(
        db=db,
        message_id=req.message_id,
        workspace_id=auth.workspace_id,
        action_status="rejected",
    )
    return {"status": "rejected", "message": "Action proposal dismissed."}


@router.post("/rag/index")
async def index_knowledge(
    req: RAGIndexRequest,
    auth: AuthContext = Depends(require_workspace_member),
    db: Session = Depends(get_db),
):
    """Index content into workspace-isolated RAG vector store."""
    retrieval_service = get_retrieval_service()
    chunks_indexed = await retrieval_service.index_document(
        db=db,
        workspace_id=auth.workspace_id,
        source_type=req.source_type,
        content=req.content,
        source_id=req.source_id,
        title=req.title or "",
        metadata=req.metadata or {},
    )
    return {"status": "indexed", "chunks": chunks_indexed}


@router.get("/rag/search")
async def search_knowledge(
    q: str = Query(..., description="Semantic search query"),
    auth: AuthContext = Depends(require_workspace_member),
    db: Session = Depends(get_db),
):
    """Semantic search in workspace knowledge base."""
    retrieval_service = get_retrieval_service()
    results = await retrieval_service.search(db=db, workspace_id=auth.workspace_id, query=q, top_k=5)
    return {"results": results, "count": len(results)}
