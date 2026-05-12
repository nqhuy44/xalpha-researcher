import structlog
import json
import asyncio
from typing import Any, List, Optional, Tuple, Dict
from anthropic import AsyncAnthropic
from pydantic import BaseModel
from tenacity import retry, wait_exponential, stop_after_attempt

from src.services.llm.provider import LLMProvider, UsageDict

logger = structlog.get_logger(__name__)

class ClaudeProvider(LLMProvider):
    """Anthropic Claude implementation of LLMProvider."""

    def __init__(self, api_key: str, default_temp: float = 0.2):
        self.api_key = api_key
        self.default_temp = default_temp
        if not self.api_key:
            self.client = None
        else:
            self.client = AsyncAnthropic(api_key=self.api_key)

    @retry(
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(3),
    )
    async def generate_text(self, prompt: str, model: str, temperature: Optional[float] = None) -> str:
        if not self.client:
            raise RuntimeError("Claude client not initialized.")
        
        response = await self.client.messages.create(
            model=model,
            max_tokens=4096,
            temperature=temperature if temperature is not None else self.default_temp,
            messages=[{"role": "user", "content": prompt}]
        )
        # Claude returns a sequence of content blocks
        return response.content[0].text.strip()

    @retry(
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(3),
    )
    async def generate_structured(self, system_prompt: str, user_prompt: str, response_schema: type, model: str, temperature: Optional[float] = None) -> Tuple[Any, UsageDict]:
        if not self.client:
            raise RuntimeError("Claude client not initialized.")

        response = await self.client.messages.create(
            model=model,
            max_tokens=4096,
            system=system_prompt,
            temperature=temperature if temperature is not None else self.default_temp,
            messages=[
                {"role": "user", "content": user_prompt + "\n\nIMPORTANT: Return ONLY valid JSON matching the schema. No conversational filler or backticks."}
            ]
        )

        content = response.content[0].text.strip()
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        result = response_schema.model_validate_json(content)

        usage: UsageDict = {"input_tokens": 0, "output_tokens": 0, "cached_tokens": 0}
        if response.usage:
            usage["input_tokens"] = response.usage.input_tokens or 0
            usage["output_tokens"] = response.usage.output_tokens or 0

        return result, usage

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

        response = await self.client.messages.create(
            model=model,
            max_tokens=4096,
            temperature=self.default_temp,
            messages=[{"role": "user", "content": prompt}]
        )
        text = response.content[0].text
        
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
