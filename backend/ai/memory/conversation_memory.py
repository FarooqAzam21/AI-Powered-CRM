from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from models.ai_copilot import AIConversation, AIMessage


class MemoryService:
    """
    Tenant-safe AI Conversation Memory Service.
    Enforces strict workspace filtering across all conversation and message queries.
    """

    @staticmethod
    def create_conversation(
        db: Session,
        workspace_id: int,
        user_id: int,
        title: Optional[str] = None,
        agent: str = "copilot",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AIConversation:
        conversation = AIConversation(
            workspace_id=workspace_id,
            user_id=user_id,
            title=title or "New Conversation",
            agent=agent,
            extra_metadata=metadata or {},
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
        return conversation

    @staticmethod
    def list_conversations(
        db: Session,
        workspace_id: int,
        user_id: Optional[int] = None,
        limit: int = 30,
    ) -> List[AIConversation]:
        query = db.query(AIConversation).filter(AIConversation.workspace_id == workspace_id)
        if user_id is not None:
            query = query.filter(AIConversation.user_id == user_id)
        return query.order_by(AIConversation.updated_at.desc()).limit(limit).all()

    @staticmethod
    def get_conversation(
        db: Session,
        conversation_id: int,
        workspace_id: int,
    ) -> Optional[AIConversation]:
        """Fetch conversation with strict workspace validation."""
        return (
            db.query(AIConversation)
            .filter(
                AIConversation.id == conversation_id,
                AIConversation.workspace_id == workspace_id,
            )
            .first()
        )

    @classmethod
    def add_message(
        cls,
        db: Session,
        conversation_id: int,
        workspace_id: int,
        role: str,
        content: str,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        proposed_actions: Optional[List[Dict[str, Any]]] = None,
        context_references: Optional[List[Dict[str, Any]]] = None,
        tokens_used: int = 0,
    ) -> AIMessage:
        conv = cls.get_conversation(db, conversation_id, workspace_id)
        if not conv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found in active workspace.",
            )

        msg = AIMessage(
            conversation_id=conversation_id,
            role=role,
            content=content,
            tool_calls=tool_calls,
            proposed_actions=proposed_actions,
            action_status="proposed" if proposed_actions else None,
            context_references=context_references,
            tokens_used=tokens_used,
        )
        db.add(msg)
        conv.updated_at = datetime.utcnow()

        # Update title from first user message if default
        if conv.title == "New Conversation" and role == "user":
            snippet = content.strip().split("\n")[0][:40]
            conv.title = snippet or "Conversation"

        db.commit()
        db.refresh(msg)
        return msg

    @classmethod
    def get_messages(
        cls,
        db: Session,
        conversation_id: int,
        workspace_id: int,
        limit: int = 50,
    ) -> List[AIMessage]:
        conv = cls.get_conversation(db, conversation_id, workspace_id)
        if not conv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found in active workspace.",
            )
        return (
            db.query(AIMessage)
            .filter(AIMessage.conversation_id == conversation_id)
            .order_by(AIMessage.created_at.asc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def delete_conversation(
        db: Session,
        conversation_id: int,
        workspace_id: int,
    ) -> bool:
        conv = (
            db.query(AIConversation)
            .filter(
                AIConversation.id == conversation_id,
                AIConversation.workspace_id == workspace_id,
            )
            .first()
        )
        if not conv:
            return False
        db.delete(conv)
        db.commit()
        return True

    @staticmethod
    def update_action_status(
        db: Session,
        message_id: int,
        workspace_id: int,
        action_status: str,
    ) -> Optional[AIMessage]:
        """Updates the status of a proposed action on an assistant message."""
        msg = (
            db.query(AIMessage)
            .join(AIConversation, AIMessage.conversation_id == AIConversation.id)
            .filter(
                AIMessage.id == message_id,
                AIConversation.workspace_id == workspace_id,
            )
            .first()
        )
        if msg:
            msg.action_status = action_status
            db.commit()
            db.refresh(msg)
        return msg


_memory_service = None


def get_memory_service() -> MemoryService:
    global _memory_service
    if _memory_service is None:
        _memory_service = MemoryService()
    return _memory_service
