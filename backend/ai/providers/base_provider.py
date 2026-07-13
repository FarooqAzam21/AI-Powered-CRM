from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional, Dict, Any

class BaseProvider(ABC):
    """
    Abstract base class for all AI model providers.
    Ensures that any future model (e.g., custom fine-tuned models) can be swapped in seamlessly.
    """

    @abstractmethod
    async def generate(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> str:
        """
        Generate a complete response from the model.
        """
        pass

    @abstractmethod
    async def stream_generate(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> AsyncIterator[str]:
        """
        Stream the response from the model token by token.
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the model provider is available and responding.
        """
        pass
