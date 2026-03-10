from abc import ABC, abstractmethod
from typing import Any, List, Optional, Tuple
from pydantic import BaseModel

class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    @abstractmethod
    async def generate_text(self, prompt: str, model: str, temperature: float = 0.2) -> str:
        """Simple text generation."""
        pass
        
    @abstractmethod
    async def generate_structured(self, system_prompt: str, user_prompt: str, response_schema: type, model: str, temperature: float = 0.2) -> Any:
        """Structured output generation (Pydantic)."""
        pass

    @abstractmethod
    async def summarize_batch(self, articles: List[Any], model: str, prompt_template: str) -> List[Tuple[str, str]]:
        """Batch summarization specialized for news."""
        pass
