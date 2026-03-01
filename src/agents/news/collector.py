"""
News Collector — High-level orchestrator for multi-source news ingestion.

Composes SourceRegistry, RSSCollector, and ArticleProcessor into a single
pipeline with domain/source/time/quantity/persistence support.
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

import structlog

from src.config.settings import settings
from src.data.processing.article_processor import ArticleProcessor
from src.data.sources.rss_collector import RSSCollector
from src.data.sources.html_scraper import HTMLScraper
from src.data.sources.rss_registry import SourceRegistry
from src.db.session import async_session_factory
from src.data.persistence.news_repo import NewsRepository
from src.models.news import CollectionResult

logger = structlog.get_logger(__name__)


class NewsCollector:
    """
    High-level orchestrator for multi-source news collection.
    """

    def __init__(
        self,
        *,
        sources_path: str | None = None,
        timeout: int | None = None,
        max_concurrent: int | None = None,
        known_hashes: set[str] | None = None,
    ) -> None:
        # Initialize registry
        self._registry = SourceRegistry(
            config_path=settings.news.sources_path if sources_path is None else __import__("pathlib").Path(sources_path)
        )
        self._registry.load()

        # Initialize collector
        self._collector = RSSCollector(
            timeout=timeout or settings.news.fetch_timeout,
            max_concurrent=max_concurrent or settings.news.max_concurrent,
        )

        # Initialize processor
        self._processor = ArticleProcessor(known_hashes=known_hashes)
        
        # Initialize full-text scraper
        self._html_scraper = HTMLScraper(
            timeout=timeout or settings.news.fetch_timeout,
            max_concurrent=max_concurrent or settings.news.max_concurrent,
        )

    @property
    def registry(self) -> SourceRegistry:
        return self._registry

    @property
    def known_hashes(self) -> frozenset[str]:
        return self._processor.known_hashes

    async def collect(
        self,
        *,
        domains: list[str] | None = None,
        source_names: list[str] | None = None,
        exclude_sources: list[str] | None = None,
        limit: int | None = None,
        since: datetime | None = None,
        hours_ago: int | None = None,
        persist: bool = False,
    ) -> CollectionResult:
        """Run a full news collection cycle."""
        start_time = time.monotonic()

        if since is None and hours_ago is not None:
            since = datetime.now(tz=timezone.utc) - timedelta(hours=hours_ago)

        if limit is None:
            limit = settings.news.default_limit

        sources = self._select_sources(
            domains=domains,
            source_names=source_names,
            exclude_sources=exclude_sources,
        )

        if not sources:
            logger.warning("no_sources_selected", domains=domains, source_names=source_names)
            return CollectionResult(
                articles=[],
                total_fetched=0,
                total_after_dedup=0,
                sources_succeeded=0,
                sources_failed=0,
                duration_seconds=0.0,
                errors=["No sources matched the given filters"],
            )

        logger.info(
            "collection_starting",
            sources=len(sources),
            domains=domains,
            limit=limit,
            since=str(since) if since else None,
        )

        feed_results = await self._collector.fetch_all(sources, limit=limit, since=since)

        all_raw = []
        errors = []
        succeeded = 0
        failed = 0

        for result in feed_results:
            if result.error:
                errors.append(f"[{result.source_name}] {result.error}")
                failed += 1
            else:
                all_raw.extend(result.articles)
                succeeded += 1

        total_fetched = len(all_raw)
        processing_result = self._processor.process(all_raw)
        duration = time.monotonic() - start_time

        collection_result = CollectionResult(
            articles=processing_result.articles,
            total_fetched=total_fetched,
            total_after_dedup=processing_result.total_output,
            sources_succeeded=succeeded,
            sources_failed=failed,
            duration_seconds=round(duration, 2),
            errors=errors,
        )

        logger.info(
            "collection_complete",
            fetched=total_fetched,
            after_dedup=processing_result.total_output,
            duplicates=processing_result.duplicates_removed,
            succeeded=succeeded,
            failed=failed,
            duration_s=collection_result.duration_seconds,
        )

        # HTML Full-text Enrichment
        # We fetch full html text ONLY for the articles that survived deduplication above to save network requests and tokens.
        if processing_result.articles:
            processing_result.articles = await self._html_scraper.enrich_articles(processing_result.articles)

        # Persistence
        if collection_result.articles and persist:
            async with async_session_factory() as session:
                repo = NewsRepository(session)
                inserted = await repo.upsert_articles(collection_result.articles)
                logger.info("collection_persisted", count=len(collection_result.articles), inserted=inserted)

        return collection_result

    def _select_sources(
        self,
        *,
        domains: list[str] | None = None,
        source_names: list[str] | None = None,
        exclude_sources: list[str] | None = None,
    ) -> list:
        if source_names:
            sources = [s for s in self._registry.sources if s.name in source_names and s.enabled]
        elif domains:
            sources = []
            for domain in domains:
                sources.extend(self._registry.list_sources(domain=domain, enabled_only=True))
            # Dedup by name
            seen = set()
            unique = []
            for s in sources:
                if s.name not in seen:
                    seen.add(s.name)
                    unique.append(s)
            sources = unique
        else:
            sources = self._registry.list_sources(enabled_only=True)

        if exclude_sources:
            exclude_set = set(exclude_sources)
            sources = [s for s in sources if s.name not in exclude_set]

        return sources
