import json
import logging
import os
import sys
import time
from typing import Any, Dict

SENSITIVE_FIELD_NAMES = {
    "password", "pass", "secret", "jwt", "token", "api_key", "apikey",
    "authorization", "access_token", "refresh_token", "credit_card",
    "client_secret", "private_key"
}


def redact_sensitive_data(data: Any) -> Any:
    """Recursively redacts sensitive fields from log dictionaries or objects."""
    if isinstance(data, dict):
        redacted = {}
        for k, v in data.items():
            if any(s in str(k).lower() for s in SENSITIVE_FIELD_NAMES):
                redacted[k] = "[REDACTED]"
            elif isinstance(v, (dict, list)):
                redacted[k] = redact_sensitive_data(v)
            else:
                redacted[k] = v
        return redacted
    elif isinstance(data, list):
        return [redact_sensitive_data(item) for item in data]
    return data


class JSONLogFormatter(logging.Formatter):
    """
    Production-grade JSON log formatter.
    Outputs structured JSON lines with request, tenant, service, and timing context.
    """

    def __init__(self, service_name: str = "ai-crm-backend", environment: str = "development"):
        super().__init__()
        self.service_name = service_name
        self.environment = environment

    def format(self, record: logging.LogRecord) -> str:
        log_entry: Dict[str, Any] = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S") + f".{int(record.msecs):03d}Z",
            "level": record.levelname,
            "service": self.service_name,
            "environment": self.environment,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Include request correlation metadata if present on record
        for attr in ("request_id", "organization_id", "workspace_id", "user_id", "task_id", "execution_id", "duration_ms", "error_type", "path", "method", "status_code"):
            val = getattr(record, attr, None)
            if val is not None:
                log_entry[attr] = val

        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Redact any extra dictionary attached to extra
        if hasattr(record, "extra") and isinstance(record.extra, dict):
            log_entry["extra"] = redact_sensitive_data(record.extra)

        return json.dumps(log_entry, default=str)


def setup_structured_logging(log_level: str = "INFO", log_format: str = "json", environment: str = "development"):
    """
    Configures root logger with standard stream handler using JSON or Text format.
    """
    root_logger = logging.getLogger()
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    root_logger.setLevel(numeric_level)

    # Remove existing handlers
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(numeric_level)

    if log_format.lower() == "json":
        formatter = JSONLogFormatter(environment=environment)
    else:
        formatter = logging.Formatter(
            "%(asctime)s - [%(levelname)s] - %(name)s - %(message)s"
        )

    stream_handler.setFormatter(formatter)
    root_logger.addHandler(stream_handler)
