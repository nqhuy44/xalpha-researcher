import structlog
from typing import Any, List, Optional, Tuple, Dict
from src.services.llm.openai_provider import OpenAIProvider

logger = structlog.get_logger(__name__)

class OllamaProvider(OpenAIProvider):
    """Ollama-specific implementation that enforces num_ctx and temperature."""

    def __init__(self, base_url: str, default_temp: float = 0.2, default_num_ctx: int = 4096):
        # Ollama doesn't need a real API key
        super().__init__(api_key="ollama", base_url=base_url, default_temp=default_temp)
        self.default_num_ctx = default_num_ctx

    async def _create_completion(self, model: str, messages: List[Dict[str, str]], temperature: Optional[float] = None, response_format: Optional[Dict[str, str]] = None) -> Any:
        """Helper to create completion, always passing Ollama-specific parameters."""
        kwargs = {
            "model": model,
            "messages": messages,
            "temperature": temperature if temperature is not None else self.default_temp,
            "extra_body": {
                "num_ctx": self.default_num_ctx
            }
        }
        
        if response_format:
            kwargs["response_format"] = response_format

        return await self.client.chat.completions.create(**kwargs)
