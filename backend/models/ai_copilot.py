from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
    JSON,
    Boolean,
    Float,
)
from sqlalchemy.orm import relationship
from database import Base


class AIConversation(Base):
    __tablename__ = "ai_conversations"

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(
        Integer, ForeignKey("workspaces.id"), nullable=False, index=True
    )
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String, default="New Conversation")
    agent = Column(String, default="copilot")
    extra_metadata = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    messages = relationship(
        "AIMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="AIMessage.created_at.asc()",
    )


class AIMessage(Base):
    __tablename__ = "ai_messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(
        Integer, ForeignKey("ai_conversations.id"), nullable=False, index=True
    )
    role = Column(String, nullable=False)  # user, assistant, system, tool
    content = Column(Text, nullable=False)
    tool_calls = Column(JSON, nullable=True)
    proposed_actions = Column(JSON, nullable=True)
    action_status = Column(
        String, nullable=True
    )  # proposed, confirmed, rejected, executed
    context_references = Column(JSON, nullable=True)
    tokens_used = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    conversation = relationship("AIConversation", back_populates="messages")


class RAGDocument(Base):
    __tablename__ = "ai_rag_documents"

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(
        Integer, ForeignKey("workspaces.id"), nullable=False, index=True
    )
    source_type = Column(
        String, nullable=False, index=True
    )  # contact, deal, email, knowledge_doc, note
    source_id = Column(String, nullable=True, index=True)
    title = Column(String, default="")
    content = Column(Text, nullable=False)
    chunk_index = Column(Integer, default=0)
    embedding = Column(JSON, nullable=True)  # List of vector weights
    extra_metadata = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)


class AIAuditLog(Base):
    __tablename__ = "ai_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(
        Integer, ForeignKey("workspaces.id"), nullable=False, index=True
    )
    organization_id = Column(
        Integer, ForeignKey("organizations.id"), nullable=False, index=True
    )
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    model = Column(String, default="qwen2.5:1.5b")
    agent = Column(String, default="copilot")
    request_type = Column(String, default="chat")
    latency_ms = Column(Float, default=0.0)
    success = Column(Boolean, default=True)
    error = Column(Text, nullable=True)
    tool_calls = Column(JSON, nullable=True)
    quota_consumed = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
