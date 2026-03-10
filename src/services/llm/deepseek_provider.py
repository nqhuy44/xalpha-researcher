from typing import Optional
from src.services.llm.openai_provider import OpenAIProvider

class DeepSeekProvider(OpenAIProvider):
    """DeepSeek implementation (OpenAI-compatible)."""

    def __init__(self, api_key: str, default_temp: float = 0.2):
        super().__init__(
            api_key=api_key,
            base_url="https://api.deepseek.com",
            default_temp=default_temp
        )
