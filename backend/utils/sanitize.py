import html
import re
from typing import Any


_SCRIPT_PATTERN = re.compile(r"<\s*script[^>]*>.*?</\s*script\s*>", re.IGNORECASE | re.DOTALL)


def sanitize_text(value: Any, max_length: int = 10000) -> str:
    if value is None:
        return ""
    text = str(value)
    text = _SCRIPT_PATTERN.sub("", text)
    return html.escape(text[:max_length])


def sanitize_email_html(value: Any, max_length: int = 50000) -> str:
    if value is None:
        return ""
    text = str(value)
    text = _SCRIPT_PATTERN.sub("", text)
    text = re.sub(r"on\w+\s*=\s*['\"][^'\"]*['\"]", "", text, flags=re.IGNORECASE)
    text = re.sub(r"javascript:", "", text, flags=re.IGNORECASE)
    return text[:max_length]
