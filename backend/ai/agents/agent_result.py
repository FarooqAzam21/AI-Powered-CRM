"""
AgentResult and WorkflowState — structured output from every agent.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum


class AgentStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    PARTIAL = "partial"


@dataclass
class AgentResult:
    """
    Structured output returned FROM an agent.
    The CRM and other agents only consume AgentResult — never raw strings.
    """
    agent_name: str
    task_type: str
    status: AgentStatus
    data: Dict[str, Any]                     # the actual output
    contact_id: Optional[int] = None
    execution_time_ms: Optional[float] = None
    cached: bool = False                     # whether Redis cache was hit
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    completed_at: datetime = field(default_factory=datetime.utcnow)

    def is_success(self) -> bool:
        return self.status == AgentStatus.SUCCESS

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent": self.agent_name,
            "task": self.task_type,
            "status": self.status.value,
            "data": self.data,
            "contact_id": self.contact_id,
            "execution_time_ms": self.execution_time_ms,
            "cached": self.cached,
            "error": self.error,
            "metadata": self.metadata,
            "completed_at": self.completed_at.isoformat(),
        }


@dataclass
class WorkflowState:
    """
    Tracks the state of a multi-agent workflow chain.
    """
    workflow_id: str
    trigger: str                              # e.g. "new_email", "resume_received"
    contact_id: Optional[int]
    steps: List[str] = field(default_factory=list)    # agent names in order
    results: List[AgentResult] = field(default_factory=list)
    current_step: int = 0
    status: str = "running"                   # running | completed | failed
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    def add_result(self, result: AgentResult):
        self.results.append(result)
        self.current_step += 1
        if self.current_step >= len(self.steps):
            self.status = "completed"
            self.completed_at = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "trigger": self.trigger,
            "contact_id": self.contact_id,
            "steps": self.steps,
            "results": [r.to_dict() for r in self.results],
            "current_step": self.current_step,
            "status": self.status,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
