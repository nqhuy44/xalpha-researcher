"""
Article Processor — Normalization, deduplication, and domain enrichment.

Takes raw RSS articles and produces clean, deduplicated ProcessedArticle objects
ready for storage and downstream analysis.
"""

from __future__ import annotations

import hashlib
import re
import uuid
from datetime import datetime, timezone
from html import unescape

import structlog
from src.data.sources.rss_collector import RawArticle
from src.models.news import NewsArticleDTO, ProcessingResult

logger = structlog.get_logger(__name__)

# Regex patterns for HTML cleanup
_HTML_TAG_RE = re.compile(r"<[^>]+>")
_MULTI_SPACE_RE = re.compile(r"\s+")
_CDATA_RE = re.compile(r"<!\[CDATA\[(.*?)\]\]>", re.DOTALL)




class ArticleProcessor:
    """
    Processes raw RSS articles into clean, deduplicated articles.

    Operations:
    1. Strip HTML tags and normalize whitespace.
    2. Unescape HTML entities.
    3. Generate content hash for deduplication.
    4. Remove duplicate articles (same title+link hash).

    Usage:
        processor = ArticleProcessor()
        result = processor.process(raw_articles)
        print(f"Kept {result.total_output}/{result.total_input} articles")
    """

    def __init__(self, *, known_hashes: set[str] | None = None) -> None:
        """
        Initialize processor.

        Args:
            known_hashes: Set of previously seen content hashes for
                          cross-batch deduplication. Pass in hashes from
                          previous runs to avoid re-processing old articles.
        """
        self._known_hashes: set[str] = known_hashes or set()

    @property
    def known_hashes(self) -> set[str]:
        """Read-only access to accumulated content hashes."""
        return frozenset(self._known_hashes)

    def process(self, articles: list[RawArticle]) -> ProcessingResult:
        """
        Process a batch of raw articles.

        Args:
            articles: List of raw articles from RSS collector.

        Returns:
            ProcessingResult with cleaned, deduplicated articles.
        """
        if not articles:
            return ProcessingResult(
                articles=[],
                total_input=0,
                total_output=0,
                duplicates_removed=0,
            )

        processed: list[NewsArticleDTO] = []
        seen_in_batch: set[str] = set()

        for raw in articles:
            try:
                article = self._process_single(raw)
            except Exception:
                logger.warning("article_processing_failed", title=raw.title[:80], link=raw.link)
                continue

            # Dedup: skip if hash already seen (in this batch or known)
            if article.content_hash in seen_in_batch or article.content_hash in self._known_hashes:
                continue

            seen_in_batch.add(article.content_hash)
            self._known_hashes.add(article.content_hash)
            processed.append(article)

        duplicates = len(articles) - len(processed)

        logger.info(
            "articles_processed",
            input=len(articles),
            output=len(processed),
            duplicates=duplicates,
        )

        return ProcessingResult(
            articles=processed,
            total_input=len(articles),
            total_output=len(processed),
            duplicates_removed=duplicates,
        )

    def _process_single(self, raw: RawArticle) -> NewsArticleDTO:
        """Process a single raw article into a clean NewsArticleDTO."""
        title = self._clean_text(raw.title)
        summary = self._clean_text(raw.summary)
        content = self._clean_text(raw.content)

        # Use summary as content fallback
        if not content and summary:
            content = summary

        content_hash = self._compute_hash(title, raw.link)

        return NewsArticleDTO(
            article_id=str(uuid.uuid4()),
            content_hash=content_hash,
            url=raw.link,
            title=title,
            author=None,  # Not extracting author from RSS summary for now
            description=summary,
            content=content,
            source_name=raw.source_name,
            domain=raw.domain,
            language=raw.language,
            published_at=raw.published_at or datetime.now(tz=timezone.utc),
            ingested_at=datetime.now(tz=timezone.utc),
        )

    @staticmethod
    def _clean_text(text: str) -> str:
        """
        Clean text by removing HTML tags, CDATA wrappers, and normalizing whitespace.

        Args:
            text: Raw text potentially containing HTML.

        Returns:
            Clean, normalized text.
        """
        if not text:
            return ""

        # Remove CDATA wrappers
        text = _CDATA_RE.sub(r"\1", text)
        # Remove HTML tags
        text = _HTML_TAG_RE.sub(" ", text)
        # Unescape HTML entities
        text = unescape(text)
        # Normalize whitespace
        text = _MULTI_SPACE_RE.sub(" ", text)

        return text.strip()

    @staticmethod
    def _compute_hash(title: str, link: str) -> str:
        """
        Compute content hash for deduplication.

        Uses normalized title + link to detect duplicate articles
        even when published by different RSS feeds of the same source.

        Args:
            title: Cleaned article title.
            link: Article URL.

        Returns:
            SHA-256 hex digest (first 16 chars for brevity).
        """
        # Normalize title: lowercase, strip extra spaces
        normalized = f"{title.lower().strip()}|{link.strip()}"
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]
