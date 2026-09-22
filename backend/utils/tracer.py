import uuid
import time
from contextvars import ContextVar
from typing import Optional, Dict

trace_id_var: ContextVar[str] = ContextVar("trace_id", default="")
span_id_var: ContextVar[str] = ContextVar("span_id", default="")


def get_current_trace_id() -> str:
    tid = trace_id_var.get()
    if not tid:
        tid = uuid.uuid4().hex
        trace_id_var.set(tid)
    return tid


def get_current_span_id() -> str:
    sid = span_id_var.get()
    if not sid:
        sid = uuid.uuid4().hex[:16]
        span_id_var.set(sid)
    return sid


def get_w3c_traceparent() -> str:
    """Returns W3C standard traceparent header: 00-<trace_id>-<span_id>-01"""
    return f"00-{get_current_trace_id()}-{get_current_span_id()}-01"


def parse_w3c_traceparent(header_val: str) -> Optional[Dict[str, str]]:
    """Parses W3C traceparent header if valid."""
    try:
        parts = header_val.strip().split("-")
        if len(parts) >= 3 and len(parts[1]) == 32 and len(parts[2]) == 16:
            return {"trace_id": parts[1], "span_id": parts[2]}
    except Exception:
        pass
    return None


class SimpleSpan:
    """Context manager for lightweight span timing and trace propagation."""

    def __init__(self, name: str, attributes: Optional[Dict] = None):
        self.name = name
        self.attributes = attributes or {}
        self.start_time = 0.0
        self.duration_ms = 0.0
        self.span_id = uuid.uuid4().hex[:16]
        self._span_token = None

    def __enter__(self):
        self.start_time = time.time()
        self._span_token = span_id_var.set(self.span_id)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.duration_ms = (time.time() - self.start_time) * 1000
        if self._span_token:
            span_id_var.reset(self._span_token)
