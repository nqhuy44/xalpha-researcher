import structlog
from typing import Any, Dict, List, Optional, Tuple
from google import genai
from google.genai import types
from google.genai.errors import APIError
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type

from src.services.llm.provider import LLMProvider, UsageDict

logger = structlog.get_logger(__name__)

class GeminiProvider(LLMProvider):
    """Google Gemini implementation of LLMProvider."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        if not self.api_key:
            self.client = None
        else:
            self.client = genai.Client(api_key=self.api_key)

    @retry(
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type(APIError),
    )
    async def generate_text(self, prompt: str, model: str, temperature: Optional[float] = None) -> str:
        if not self.client:
            raise RuntimeError("Gemini client not initialized (missing API key).")
        
        config = types.GenerateContentConfig()
        if temperature is not None:
            config.temperature = temperature

        response = await self.client.aio.models.generate_content(
            model=model,
            contents=prompt,
            config=config,
        )
        return str(response.text).strip()

    @retry(
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type(APIError),
    )
    async def generate_structured(self, system_prompt: str, user_prompt: str, response_schema: type, model: str, temperature: Optional[float] = None) -> Tuple[Any, UsageDict]:
        if not self.client:
            raise RuntimeError("Gemini client not initialized (missing API key).")

        full_prompt = f"SYSTEM INSTRUCTIONS:\n{system_prompt}\n\nUSER PROMPT:\n{user_prompt}"

        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=response_schema,
        )
        if temperature is not None:
            config.temperature = temperature

        response = await self.client.aio.models.generate_content(
            model=model,
            contents=full_prompt,
            config=config,
        )

        parsed = response.parsed
        result = response_schema(**parsed) if isinstance(parsed, dict) else parsed

        usage: UsageDict = {"input_tokens": 0, "output_tokens": 0, "cached_tokens": 0}
        if response.usage_metadata:
            usage["input_tokens"] = response.usage_metadata.prompt_token_count or 0
            usage["output_tokens"] = response.usage_metadata.candidates_token_count or 0
            usage["cached_tokens"] = response.usage_metadata.cached_content_token_count or 0

        return result, usage

    @retry(
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type(APIError),
    )
    async def summarize_batch(self, articles: List[Any], model: str, prompt_template: str) -> List[Tuple[str, str]]:
        if not self.client:
            return []
            
        blocks = []
        for i, a in enumerate(articles, 1):
            content_preview = (a.content or a.description or "")[:3000]
            blocks.append(
                f"--- Bài {i} ---\n"
                f"Nguồn: {a.source_name} | Domain: {a.domain}\n"
                f"Tiêu đề: {a.title}\n"
                f"Nội dung:\n{content_preview}"
            )

        articles_text = "\n\n".join(blocks)
        prompt = prompt_template.replace("{articles_text}", articles_text)

        response = await self.client.aio.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(),
        )
        text = str(response.text)

        # Parse summaries separated by ---ITEM---
        raw_summaries = [s.strip() for s in text.split("---ITEM---") if s.strip()]
        
        results = []
        for i, a in enumerate(articles):
            if i < len(raw_summaries):
                summary = raw_summaries[i]
                if summary.upper() != "SKIP":
                    # Note: article object must have article_id or id
                    aid = getattr(a, 'article_id', str(getattr(a, 'id', '')))
                    results.append((aid, summary))
            else:
                break
        return results
