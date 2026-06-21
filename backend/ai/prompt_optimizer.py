import re

from ai.local_model_config import get_local_model_config


def compress_text(text: str, max_chars: int = 2200) -> str:
    text = re.sub(r"\s+", " ", (text or "")).strip()
    if len(text) <= max_chars:
        return text
    head = text[: int(max_chars * 0.7)]
    tail = text[-int(max_chars * 0.3) :]
    return f"{head}\n[...trimmed for memory...]\n{tail}"


def build_email_prompt(task: str, body: str, context: str = "", tone: str = "professional") -> str:
    cfg = get_local_model_config()
    body = compress_text(body, cfg.max_prompt_chars)
    context = compress_text(context, 900)
    return (
        f"Task: {task}\n"
        f"Tone: {tone}\n"
        "Rules: concise, specific, no placeholders, output only the requested answer.\n"
        f"Context: {context}\n"
        f"Email: {body}"
    )
