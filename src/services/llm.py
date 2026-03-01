"""
LLM Service — Wrapper for integrating Google Gemini API.
"""

import os
from pathlib import Path
import structlog
from google import genai
from google.genai import types

from src.config.settings import settings

logger = structlog.get_logger(__name__)


class GeminiService:
    """Wrapper around google-genai for executing language model tasks."""

    def __init__(self):
        self.api_key = settings.gemini.api_key
        self.model_pro = settings.gemini.model_pro
        self.model_flash = settings.gemini.model_flash
        
        if not self.api_key:
            logger.warning("gemini_api_key_missing", message="LLM features will be disabled or fail.")
            self.client = None
        else:
            self.client = genai.Client(api_key=self.api_key)

    def load_prompt(self, filename: str) -> str:
        """Load a prompt template from src/prompts directory."""
        # Calculate optimal path
        prompt_dir = Path(__file__).resolve().parent.parent / "prompts"
        prompt_path = prompt_dir / filename
        
        if not prompt_path.exists():
            logger.error("prompt_not_found", path=str(prompt_path))
            return ""
            
        return prompt_path.read_text(encoding="utf-8")

    async def summarize_news_batch(self, articles: list) -> list[str]:
        """
        Summarize a batch of news articles.
        Takes a list of NewsArticleDTO objects.
        Returns a list of topic-based summaries.
        """
        if not self.client:
            return ["Cảnh báo hệ thống: Khóa truy cập API Gemini chưa được cấu hình. Bỏ qua quy trình phân tích."]
            
        if not articles:
            return ["Dữ liệu trống. Không có bản ghi mới để phân tích."]

        # Limit to top N to avoid massive tokens
        top_articles = articles[:20]

        # TOON format: Array of Arrays for token efficiency
        # Header: [domain, source, title, description]
        toon_rows = [["domain", "source", "title", "desc"]]
        for a in top_articles:
            toon_rows.append([
                a.domain,
                a.source_name,
                a.title,
                (a.description or "")[:120],
            ])

        import json
        articles_text = json.dumps(toon_rows, ensure_ascii=False, separators=(",", ":"))
        
        prompt_template = self.load_prompt("news_summary.txt")
        if not prompt_template:
            return "Lỗi cấu hình: Không thể truy xuất chỉ thị phân tích (prompt)."
            
        prompt = prompt_template.replace("{articles_text}", articles_text)

        logger.info("gemini_summarization_starting", count=len(top_articles))
        try:
            # We use flash for speed and lower cost in summarization tasks
            response = await self.client.aio.models.generate_content(
                model=self.model_flash,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.3, # low temp for news summary
                )
            )
            text = str(response.text)
            # Tách chuỗi theo format mới trong prompt
            if "---TOPIC_SPLIT---" in text:
                parts = [p.strip() for p in text.split("---TOPIC_SPLIT---") if p.strip()]
                return parts
            # Nếu AI không tuân thủ hoàn toàn, fallback:
            return [text]
        except Exception as e:
            logger.error("gemini_summarization_failed", error=str(e))
            return [f"Gián đoạn quy trình phân tích AI. Lỗi ghi nhận: {str(e)}"]
