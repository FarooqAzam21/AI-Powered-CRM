"""
AgentContext and AgentMessage — shared structured input for every agent.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime


@dataclass
class AgentContext:
    """
    Structured input passed INTO an agent.
    Every agent receives this; it never receives raw strings.
    """
    task_type: str                        # e.g. "classify_email", "score_lead"
    payload: Dict[str, Any]              # raw input data
    contact_id: Optional[int] = None     # CRM contact (for memory/context)
    user_id: Optional[int] = None        # CRM user who triggered this
    crm_context: Optional[str] = None    # pre-built context string (optional override)
    rag_enabled: bool = True             # whether to query RAG
    workflow_id: Optional[str] = None    # set when part of a workflow chain
    upstream_results: List[Dict] = field(default_factory=list)  # results from prior agents
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class AgentMessage:
    """
    Structured message exchanged between agents in a workflow.
    Agents NEVER pass raw prompts to each other.
    """
    sender_agent: str
    recipient_agent: str
    task_type: str
    payload: Dict[str, Any]
    contact_id: Optional[int] = None
    context_summary: Optional[str] = None   # compressed context for chained agents
    timestamp: datetime = field(default_factory=datetime.utcnow)
