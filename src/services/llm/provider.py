from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel

# Usage dict returned alongside structured output: token counts from the provider.
# Zero-filled for providers that don't expose usage metadata.
UsageDict = Dict[str, int]  # keys: input_tokens, output_tokens, cached_tokens

class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def generate_text(self, prompt: str, model: str, temperature: float = 0.2) -> str:
        """Simple text generation."""
        pass

    @abstractmethod
    async def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        response_schema: type,
        model: str,
        temperature: float = 0.2,
    ) -> Tuple[Any, UsageDict]:
        """Structured output generation. Returns (pydantic_result, usage_dict)."""
        pass

    @abstractmethod
    async def summarize_batch(self, articles: List[Any], model: str, prompt_template: str) -> List[Tuple[str, str]]:
        """Batch summarization specialized for news."""
        pass
