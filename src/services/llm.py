"""
LLM Service — Two-stage pipeline for Google Gemini API.

Stage 1 (Flash-Lite): Batch-summarize individual articles (cheap, fast).
Stage 2 (Flash):      Synthesize summaries into topic-grouped analysis (smarter).
"""

import json
import asyncio
import logging
from pathlib import Path
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type

import structlog
from google import genai
from google.genai import types
from google.genai.errors import APIError

from src.config.settings import settings

logger = structlog.get_logger(__name__)

# Max articles per batch for Stage 1 (to avoid exceeding context window)
BATCH_SIZE = 30


class GeminiService:
    """Two-stage LLM pipeline using tiered Gemini models."""

    def __init__(self):
        self.api_key = settings.gemini.api_key
        self.model_pro = settings.gemini.model_pro
        self.model_flash = settings.gemini.model_flash
        self.model_lite = settings.gemini.model_lite

        if not self.api_key:
            logger.warning("gemini_api_key_missing", message="LLM features will be disabled or fail.")
            self.client = None
        else:
            self.client = genai.Client(api_key=self.api_key)

    def load_prompt(self, filename: str) -> str:
        """Load a prompt template from src/prompts directory."""
        prompt_dir = Path(__file__).resolve().parent.parent / "prompts"
        prompt_path = prompt_dir / filename

        if not prompt_path.exists():
            logger.error("prompt_not_found", path=str(prompt_path))
            return ""

        return prompt_path.read_text(encoding="utf-8")

    # -------------------------------------------------------------------------
    # Stage 1: Batch Summarization (Flash-Lite — cheap)
    # -------------------------------------------------------------------------
    @retry(
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type(APIError),
        before_sleep=lambda retry_state: logger.warning(
            "gemini_api_retry",
            attempt=retry_state.attempt_number,
            error=str(retry_state.outcome.exception())
        )
    )
    async def _summarize_batch(self, articles: list) -> list[tuple[str, str]]:
        """
        Summarize a single batch of articles using Flash-Lite.
        Returns a list of tuples: (article_id, summary_text).
        Raises APIError if it fails all retries.
        """
        # Build input text: one article per block
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

        prompt_template = self.load_prompt("news_batch_summarize.txt")
        if not prompt_template:
            return [f"[{a.title}]" for a in articles]

        prompt = prompt_template.replace("{articles_text}", articles_text)

        try:
            response = await self.client.aio.models.generate_content(
                model=self.model_lite,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.2,
                ),
            )
            text = str(response.text)

            # Parse summaries separated by ---ITEM---
            raw_summaries = [s.strip() for s in text.split("---ITEM---") if s.strip()]
            
            results = []
            for i, a in enumerate(articles):
                if i < len(raw_summaries):
                    summary = raw_summaries[i]
                    if summary.upper() != "SKIP":
                        results.append((str(a.article_id), summary))
                else:
                    break
            return results

        except Exception as e:
            logger.error("stage1_batch_failed", error=str(e), batch_size=len(articles))
            # Return empty to allow DB queue to pick this batch up again later
            # instead of permanently marking them as summarized with fake title data
            return []

    # -------------------------------------------------------------------------
    # Stage 2: Synthesis & Analysis (Flash — smarter)
    # -------------------------------------------------------------------------
    @retry(
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type(APIError),
        before_sleep=lambda retry_state: logger.warning(
            "gemini_api_retry",
            attempt=retry_state.attempt_number,
            error=str(retry_state.outcome.exception())
        )
    )
    async def synthesize_reports(self, summaries: list[str]) -> list[str]:
        """
        Take all individual DB-stored summaries and produce a high-level topic-grouped analysis.
        Uses Flash model for deeper reasoning.
        """
        if not self.client:
            return ["Cảnh báo hệ thống: Khóa Gemini bị thiếu."]
        if not summaries:
            return ["Không có dữ liệu đầu vào để phân tích."]

        summaries_text = "\n".join(f"- {s}" for s in summaries)

        prompt_template = self.load_prompt("news_synthesis.txt")
        if not prompt_template:
            return summaries

        prompt = prompt_template.replace("{summaries_text}", summaries_text)

        try:
            response = await self.client.aio.models.generate_content(
                model=self.model_flash,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.3,
                ),
            )
            text = str(response.text)

            if "---TOPIC_SPLIT---" in text:
                parts = [p.strip() for p in text.split("---TOPIC_SPLIT---") if p.strip()]
                return parts

            return [text]

        except Exception as e:
            logger.error("stage2_synthesis_failed", error=str(e))
            return [f"Gián đoạn quy trình tổng hợp AI. Lỗi: {str(e)}"]

    # -------------------------------------------------------------------------
    # Public API: Stage 1 Generator
    # -------------------------------------------------------------------------
    async def generate_article_summaries(self, articles: list) -> list[tuple[str, str]]:
        """
        Stage 1: Generates individual summaries for a list of articles.
        Returns [(article_id, summary_text), ...] to be stored in the DB.
        """
        if not self.client:
            logger.warning("gemini_disabled", message="No API key configured.")
            return []

        if not articles:
            return []

        logger.info("stage1_starting", total_articles=len(articles), batch_size=BATCH_SIZE)

        batches = [articles[i : i + BATCH_SIZE] for i in range(0, len(articles), BATCH_SIZE)]
        
        # Limit concurrency to 3 simultaneous requests to prevent 503 Overload on Gemini Free Tier
        sem = asyncio.Semaphore(3)
        async def _run_with_semaphore(batch: list):
            async with sem:
                return await self._summarize_batch(batch)
                
        batch_tasks = [_run_with_semaphore(batch) for batch in batches]
        batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

        all_summaries: list[tuple[str, str]] = []
        for result in batch_results:
            if isinstance(result, list):
                all_summaries.extend(result)
            elif isinstance(result, Exception):
                logger.error("stage1_batch_exception", error=str(result))

        logger.info(
            "stage1_complete",
            total_articles=len(articles),
            summaries_produced=len(all_summaries),
            batches=len(batches),
        )

        return all_summaries
