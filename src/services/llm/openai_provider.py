import structlog
import json
from typing import Any, List, Optional, Tuple, Dict
from openai import AsyncOpenAI
from pydantic import BaseModel
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type

from src.services.llm.provider import LLMProvider

logger = structlog.get_logger(__name__)

class OpenAIProvider(LLMProvider):
    """OpenAI implementation of LLMProvider (also supports Ollama/vLLM)."""

    def __init__(self, api_key: str, base_url: Optional[str] = None, default_temp: float = 0.2):
        self.api_key = api_key
        self.base_url = base_url
        self.default_temp = default_temp
        if not self.api_key and not self.base_url:
            self.client = None
        else:
            self.client = AsyncOpenAI(api_key=self.api_key or "no-key", base_url=self.base_url)

    async def _create_completion(self, model: str, messages: List[Dict[str, str]], temperature: Optional[float] = None, response_format: Optional[Dict[str, str]] = None) -> Any:
        """Helper to create completion, handling models that don't support temperature."""
        kwargs = {
            "model": model,
            "messages": messages,
        }
        
        # Determine effective temperature
        # 1. Explicitly provided temperature takes precedence
        # 2. If it's a local model (Ollama/vLLM), use default_temp from settings
        # 3. For cloud OpenAI, use model default (don't send temperature)
        eff_temp = temperature
        if eff_temp is None and self.base_url:
            eff_temp = self.default_temp

        # o1 models and some newer ones don't support temperature/top_p other than default (1)
        # or don't support them at all in the API call.
        is_o1 = model.startswith("o1-") or "o1" in model
        
        if eff_temp is not None and not is_o1:
            kwargs["temperature"] = eff_temp
        
        if response_format:
            kwargs["response_format"] = response_format

        try:
            return await self.client.chat.completions.create(**kwargs)
        except Exception as e:
            if "temperature" in str(e).lower() and not is_o1:
                logger.warning("model_unsupported_temperature", model=model, error=str(e))
                # Retry without temperature
                kwargs.pop("temperature", None)
                return await self.client.chat.completions.create(**kwargs)
            raise e

    @retry(
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(3),
    )
    async def generate_text(self, prompt: str, model: str, temperature: Optional[float] = None) -> str:
        if not self.client:
            raise RuntimeError("OpenAI client not initialized.")
        
        response = await self._create_completion(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature
        )
        return response.choices[0].message.content.strip()

    @retry(
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(3),
    )
    async def generate_structured(self, system_prompt: str, user_prompt: str, response_schema: type, model: str, temperature: Optional[float] = None) -> Any:
        if not self.client:
            raise RuntimeError("OpenAI client not initialized.")
            
        response = await self._create_completion(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=temperature,
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content
        return response_schema.model_validate_json(content)

    @retry(
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(3),
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

        response = await self._create_completion(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=None # Use defaults
        )
        text = response.choices[0].message.content

        # Parse summaries separated by ---ITEM---
        raw_summaries = [s.strip() for s in text.split("---ITEM---") if s.strip()]
        
        results = []
        for i, a in enumerate(articles):
            if i < len(raw_summaries):
                summary = raw_summaries[i]
                if summary.upper() != "SKIP":
                    aid = getattr(a, 'article_id', str(getattr(a, 'id', '')))
                    results.append((aid, summary))
            else:
                break
        return results
