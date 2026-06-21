from dataclasses import dataclass

from config.settings import get_settings


@dataclass(frozen=True)
class LocalModelConfig:
    provider: str
    model: str
    context_window: int
    temperature: float
    idle_unload_seconds: int
    max_prompt_chars: int


def get_local_model_config() -> LocalModelConfig:
    settings = get_settings()
    return LocalModelConfig(
        provider="ollama",
        model=settings.ollama_model,
        context_window=min(settings.ollama_context, 1024),
        temperature=0.2,
        idle_unload_seconds=settings.ollama_idle_unload_seconds,
        max_prompt_chars=3500,
    )
