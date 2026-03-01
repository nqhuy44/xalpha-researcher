"""
HTML Scraper — Extracts clean text from news article URLs.

Uses `trafilatura` to strip away ads, navigation, and HTML boilerplate,
yielding only the core article text to drastically reduce token usage.
"""

from __future__ import annotations

import asyncio
import structlog
import trafilatura
import httpx
from typing import List

from src.models.news import NewsArticleDTO

logger = structlog.get_logger(__name__)

# Max characters to keep from an article to prevent blowing up the LLM token limit
# 15,000 chars is roughly 3,500 - 4,500 tokens depending on the language (Vietnamese is slightly denser in tokens).
MAX_ARTICLE_CHARS = 15000


class HTMLScraper:
    """
    Asynchronous HTML scraper that fetches and cleans articles using Trafilatura.
    """

    def __init__(self, timeout: int = 20, max_concurrent: int = 10):
        self._timeout = timeout
        self._semaphore = asyncio.Semaphore(max_concurrent)

    async def fetch_and_clean(self, url: str, client: httpx.AsyncClient) -> str | None:
        """
        Fetch the HTML of a URL and extract the main body text.
        """
        try:
            async with self._semaphore:
                response = await client.get(url, follow_redirects=True)
                response.raise_for_status()
                
            # Trafilatura extracting text from HTML
            # include_links=False, include_images=False helps to further reduce noise
            extracted_text = trafilatura.extract(
                response.text,
                include_links=False,
                include_images=False,
                include_formatting=False,
                include_tables=True,
                url=url
            )
            
            if extracted_text:
                if len(extracted_text) > MAX_ARTICLE_CHARS:
                    logger.debug("article_truncated", url=url, original_length=len(extracted_text))
                    extracted_text = extracted_text[:MAX_ARTICLE_CHARS] + "\n\n[...Bài viết đã được cắt bớt để tối ưu...]"
                return extracted_text.strip()
                
            return None
        except httpx.HTTPError as e:
            logger.debug("scraper_http_error", url=url, error=str(e))
            return None
        except Exception as e:
            logger.debug("scraper_unexpected_error", url=url, error=str(e))
            return None

    async def enrich_articles(self, articles: List[NewsArticleDTO]) -> List[NewsArticleDTO]:
        """
        Concurrently fetch full HTML text for a list of articles and update their content field.
        If scraping fails, the original RSS summary content is retained.
        """
        if not articles:
            return articles

        logger.info("scraping_full_articles", count=len(articles))
        start_time = asyncio.get_event_loop().time()
        
        async with httpx.AsyncClient(
            timeout=self._timeout,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 xalpha-researcher/1.0"}
        ) as client:
            # Create a task for each article
            tasks = [
                self.fetch_and_clean(article.url, client)
                for article in articles
            ]
            
            # Run all requests concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
        success_count = 0
        for article, extracted_text in zip(articles, results):
            if isinstance(extracted_text, str) and extracted_text:
                # Override the short RSS summary with the full scraped article text
                article.content = extracted_text
                success_count += 1
                
        duration = asyncio.get_event_loop().time() - start_time
        logger.info("scraping_complete", success=success_count, total=len(articles), duration_s=round(duration, 2))
        
        return articles
