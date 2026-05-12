"""
LLM Service — Model-Agnostic Router and Provider Factory.
"""

import asyncio
import logging
import time
import uuid
from pathlib import Path
from typing import Any, List, Optional, Tuple, Dict
import structlog

from src.config.settings import settings
from src.services.llm.provider import LLMProvider
from src.services.llm.gemini_provider import GeminiProvider
from src.services.llm.openai_provider import OpenAIProvider
from src.services.llm.ollama_provider import OllamaProvider
from src.services.llm.grok_provider import GrokProvider
from src.services.llm.deepseek_provider import DeepSeekProvider
from src.services.llm.claude_provider import ClaudeProvider

logger = structlog.get_logger(__name__)

# Max articles per batch for Stage 1 (to avoid exceeding context window)
BATCH_SIZE = 30

class LLMService:
    """
    Role-based LLM Router that abstracts multiple providers.
    Roles: FAST_REASONING, DEEP_REASONING, JUDGE_REASONING.
    """

    def __init__(self):
        self._providers: Dict[str, LLMProvider] = {}
        self._init_providers()

    def _init_providers(self):
        """Initialize all configured providers."""
        # Gemini
        if settings.gemini.api_key:
            self._providers["gemini"] = GeminiProvider(api_key=settings.gemini.api_key)
        
        # OpenAI
        if settings.openai.api_key:
            self._providers["openai"] = OpenAIProvider(api_key=settings.openai.api_key)
            
        if settings.ollama.base_url:
            self._providers["ollama"] = OllamaProvider(
                base_url=settings.ollama.base_url,
                default_temp=settings.ollama.temperature,
                default_num_ctx=settings.ollama.num_ctx
            )
            
        # Grok (xAI)
        if settings.grok.api_key:
            self._providers["grok"] = GrokProvider(api_key=settings.grok.api_key)
            
        # DeepSeek
        if settings.deepseek.api_key:
            self._providers["deepseek"] = DeepSeekProvider(api_key=settings.deepseek.api_key)
            
        # Claude (Anthropic)
        if settings.claude.api_key:
            self._providers["claude"] = ClaudeProvider(api_key=settings.claude.api_key)

    def get_provider_and_model(self, role: str, agent_name: Optional[str] = None) -> Tuple[LLMProvider, str]:
        """
        Maps a reasoning role and/or agent name to a provider and a specific model.
        Roles: 'fast', 'deep', 'judge'
        Agent Names: 'bull', 'bear', 'judge', 'news_summarizer', etc.
        """
        # 1. Determine provider (Agent specific > Global primary)
        provider_name = settings.llm.provider
        if agent_name and agent_name in settings.llm.agent_providers:
            provider_name = settings.llm.agent_providers[agent_name]
            logger.debug("llm_provider_override", agent=agent_name, provider=provider_name)

        # 2. Map role to tier in settings
        if role == "fast":
            tier_key = settings.llm.fast_model_role
        elif role == "deep":
            tier_key = settings.llm.deep_model_role
        elif role == "judge":
            tier_key = settings.llm.judge_model_role
        else:
            tier_key = "deep"

        provider = self._providers.get(provider_name)
        if not provider:
            # Fallback to any available provider if the requested one is missing
            logger.warning("requested_provider_missing", requested=provider_name, status="falling_back")
            provider_name = next(iter(self._providers.keys()), None)
            provider = self._providers.get(provider_name)
            if not provider:
                raise RuntimeError("No LLM providers configured or available.")
        
        # 3. Resolve model name based on provider and tier
        model_name = ""
        if provider_name == "gemini":
            if tier_key == "fast": model_name = settings.gemini.model_lite
            elif tier_key == "deep": model_name = settings.gemini.model_pro
            else: model_name = settings.gemini.model_pro
        elif provider_name == "openai":
            if tier_key == "fast": model_name = settings.openai.model_fast
            elif tier_key == "deep": model_name = settings.openai.model_deep
            else: model_name = settings.openai.model_deep
        elif provider_name == "ollama":
            if tier_key == "fast": model_name = settings.ollama.model_fast
            elif tier_key == "deep": model_name = settings.ollama.model_deep
            else: model_name = settings.ollama.model_deep
        elif provider_name == "grok":
            if tier_key == "fast": model_name = settings.grok.model_fast
            elif tier_key == "deep": model_name = settings.grok.model_deep
            else: model_name = settings.grok.model_deep
        elif provider_name == "deepseek":
            if tier_key == "fast": model_name = settings.deepseek.model_fast
            elif tier_key == "deep": model_name = settings.deepseek.model_deep
            else: model_name = settings.deepseek.model_deep
        elif provider_name == "claude":
            if tier_key == "fast": model_name = settings.claude.model_fast
            elif tier_key == "deep": model_name = settings.claude.model_deep
            else: model_name = settings.claude.model_deep
            
        return provider, model_name

    def load_prompt(self, filename: str) -> str:
        """Load a prompt template from src/prompts directory."""
        # Path is different now because we are in src/services/llm/__init__.py
        prompt_dir = Path(__file__).resolve().parent.parent.parent / "prompts"
        prompt_path = prompt_dir / filename

        if not prompt_path.exists():
            logger.error("prompt_not_found", path=str(prompt_path))
            return ""

        return prompt_path.read_text(encoding="utf-8")

    async def generate_article_summaries(self, articles: List[Any]) -> List[Tuple[str, str]]:
        """Stage 1: Batch summarization using FastTier."""
        if not articles:
            return []
            
        provider, model = self.get_provider_and_model("fast")
        prompt_template = self.load_prompt("news_batch_summarize.txt")
        
        logger.info("stage1_starting", total_articles=len(articles), provider=type(provider).__name__, model=model)
        
        batches = [articles[i : i + BATCH_SIZE] for i in range(0, len(articles), BATCH_SIZE)]
        sem = asyncio.Semaphore(3)
        
        async def _run_with_semaphore(batch: list):
            async with sem:
                return await provider.summarize_batch(batch, model, prompt_template)
                
        batch_tasks = [_run_with_semaphore(batch) for batch in batches]
        batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

        all_summaries = []
        for result in batch_results:
            if isinstance(result, list):
                all_summaries.extend(result)
            elif isinstance(result, Exception):
                logger.error("stage1_batch_exception", error=str(result))

        return all_summaries

    async def synthesize_reports(self, summaries: List[str]) -> str:
        """Stage 2: Synthetic analysis using DeepTier."""
        if not summaries:
            return "Không có dữ liệu đầu vào để phân tích."
            
        provider, model = self.get_provider_and_model("deep")
        summaries_text = "\n".join(f"- {s}" for s in summaries)
        prompt_template = self.load_prompt("news_synthesis.txt")
        prompt = prompt_template.replace("{summaries_text}", summaries_text)
        
        return await provider.generate_text(prompt, model)

    async def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        response_schema: type,
        role: str = "deep",
        agent_name: Optional[str] = None,
        ticker: Optional[str] = None,
        node: Optional[str] = None,
        debate_run_id: Optional[str] = None,
    ) -> Any:
        """Generic structured output generation. Logs per-call token usage to llm_usage table."""
        provider, model = self.get_provider_and_model(role, agent_name=agent_name)
        provider_name = type(provider).__name__.replace("Provider", "").lower()

        t0 = time.monotonic()
        status = "success"
        try:
            result, usage = await provider.generate_structured(system_prompt, user_prompt, response_schema, model)
            return result
        except Exception:
            status = "error"
            raise
        finally:
            latency_ms = int((time.monotonic() - t0) * 1000)
            asyncio.ensure_future(
                self._persist_usage(
                    debate_run_id=debate_run_id,
                    ticker=ticker,
                    node=node or agent_name,
                    role=role,
                    provider=provider_name,
                    model=model,
                    input_tokens=usage.get("input_tokens", 0) if status == "success" else 0,
                    output_tokens=usage.get("output_tokens", 0) if status == "success" else 0,
                    cached_tokens=usage.get("cached_tokens", 0) if status == "success" else 0,
                    latency_ms=latency_ms,
                    status=status,
                )
            )

    @staticmethod
    async def _persist_usage(
        debate_run_id: Optional[str],
        ticker: Optional[str],
        node: Optional[str],
        role: str,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cached_tokens: int,
        latency_ms: int,
        status: str,
    ) -> None:
        """Fire-and-forget: write one LLMUsage row. Never raises."""
        try:
            from src.db.session import async_session_factory
            from src.db.models.observability import LLMUsage
            run_uuid = uuid.UUID(debate_run_id) if debate_run_id else None
            async with async_session_factory() as session:
                row = LLMUsage(
                    debate_run_id=run_uuid,
                    ticker=ticker,
                    node=node,
                    role=role,
                    provider=provider,
                    model=model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cached_tokens=cached_tokens,
                    latency_ms=latency_ms,
                    status=status,
                )
                session.add(row)
                await session.commit()
        except Exception as exc:
            logger.warning("llm_usage_persist_failed", error=str(exc))
