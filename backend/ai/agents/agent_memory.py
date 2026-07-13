"""
SharedAgentMemory — all agents read and write shared customer memory
through this helper, backed by the existing MemoryManager + CustomerMemory model.
"""
from __future__ import annotations
import json
import logging
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session
from models.ai_memory import CustomerMemory

logger = logging.getLogger(__name__)


class AgentMemory:
    """
    Thin wrapper around CustomerMemory that gives agents a clean read/write API.
    Uses the existing CustomerMemory model — no duplication.
    """

    def __init__(self, db: Session, contact_id: int):
        self.db = db
        self.contact_id = contact_id
        self._memory: Optional[CustomerMemory] = None

    def _get_or_create(self) -> CustomerMemory:
        if self._memory is None:
            self._memory = (
                self.db.query(CustomerMemory)
                .filter(CustomerMemory.contact_id == self.contact_id)
                .first()
            )
            if not self._memory:
                self._memory = CustomerMemory(contact_id=self.contact_id)
                self.db.add(self._memory)
                self.db.flush()
        return self._memory

    def read(self) -> Dict[str, Any]:
        """Returns a full snapshot of the customer memory as a dict."""
        m = self._get_or_create()
        return {
            "communication_style": m.communication_style or "",
            "products_discussed": self._parse_json(m.products_discussed),
            "pain_points": self._parse_json(m.pain_points),
            "meeting_history": m.meeting_history or "",
            "buying_signals": self._parse_json(m.buying_signals),
            "objections": self._parse_json(m.objections),
            "previous_summaries": m.previous_summaries or "",
            "preferences": self._parse_json(m.preferences),
            # Extended agent fields (added in Phase 6)
            "support_history": self._parse_json(getattr(m, "support_history", "[]")),
            "campaign_history": self._parse_json(getattr(m, "campaign_history", "[]")),
            "hiring_notes": self._parse_json(getattr(m, "hiring_notes", "[]")),
        }

    def update(self, updates: Dict[str, Any]) -> bool:
        """Merges updates into customer memory and commits."""
        try:
            m = self._get_or_create()
            list_fields = [
                "products_discussed", "pain_points", "buying_signals",
                "objections", "preferences", "support_history",
                "campaign_history", "hiring_notes"
            ]
            str_fields = ["communication_style", "meeting_history", "previous_summaries"]

            for field in list_fields:
                if field in updates and isinstance(updates[field], list):
                    # Merge — deduplicate
                    existing = self._parse_json(getattr(m, field, "[]"))
                    merged = list(dict.fromkeys(existing + updates[field]))
                    setattr(m, field, json.dumps(merged))

            for field in str_fields:
                if field in updates and updates[field]:
                    setattr(m, field, str(updates[field]))

            self.db.commit()
            logger.info(f"Agent memory updated for contact {self.contact_id}")
            return True
        except Exception as e:
            logger.error(f"AgentMemory update failed for contact {self.contact_id}: {e}")
            self.db.rollback()
            return False

    def append_summary(self, agent_name: str, summary: str):
        """Appends a short summary from this agent to previous_summaries."""
        try:
            m = self._get_or_create()
            existing = m.previous_summaries or ""
            entry = f"[{agent_name}]: {summary[:200]}"
            # Keep last 5 summaries
            parts = existing.split("\n---\n") if existing else []
            parts.append(entry)
            m.previous_summaries = "\n---\n".join(parts[-5:])
            self.db.commit()
        except Exception as e:
            logger.error(f"AgentMemory append_summary failed: {e}")

    @staticmethod
    def _parse_json(value: str) -> list:
        try:
            result = json.loads(value) if value else []
            return result if isinstance(result, list) else []
        except Exception:
            return []
