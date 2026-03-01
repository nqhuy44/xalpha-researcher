"""
Async RSS Feed Collector.

Fetches RSS feeds concurrently with rate limiting, time filtering,
and quantity limits. Uses feedparser for parsing and httpx for async HTTP.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import feedparser
import httpx
import structlog
from pydantic import BaseModel

from src.data.sources.rss_registry import RSSSource

logger = structlog.get_logger(__name__)


class RawArticle(BaseModel):
    """Raw article data extracted from an RSS feed entry."""

    source_name: str
    source_url: str
    title: str
    link: str
    summary: str = ""
    content: str = ""
    published_at: datetime | None = None
    domain: str
    language: str
    raw_data: dict = {}


class FeedResult(BaseModel):
    """Result of fetching a single feed."""

    source_name: str
    articles: list[RawArticle] = []
    error: str | None = None
    duration_ms: int = 0


class RSSCollector:
    """
    Async RSS feed collector with concurrency control.

    Fetches multiple RSS feeds in parallel using asyncio.Semaphore
    for rate limiting. Supports time-based and quantity-based filtering.

    Usage:
        collector = RSSCollector(timeout=30, max_concurrent=10)
        articles = await collector.fetch_all(sources, limit=50, since=some_datetime)
    """

    def __init__(
        self,
        *,
        timeout: int = 30,
        max_concurrent: int = 10,
    ) -> None:
        self._timeout = timeout
        self._semaphore = asyncio.Semaphore(max_concurrent)

    async def fetch_feed(
        self,
        source: RSSSource,
        *,
        limit: int | None = None,
        since: datetime | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> FeedResult:
        """
        Fetch and parse a single RSS feed.

        Args:
            source: RSS source definition.
            limit: Max number of articles to return.
            since: Only return articles published after this datetime.
            client: Shared httpx client (created if not provided).

        Returns:
            FeedResult with parsed articles or error.
        """
        start = asyncio.get_event_loop().time()
        should_close = client is None

        try:
            if client is None:
                client = httpx.AsyncClient(timeout=self._timeout, follow_redirects=True)

            async with self._semaphore:
                response = await client.get(str(source.url))
                response.raise_for_status()

            feed = feedparser.parse(response.text)

            if feed.bozo and not feed.entries:
                return FeedResult(
                    source_name=source.name,
                    error=f"Feed parse error: {feed.bozo_exception}",
                    duration_ms=self._elapsed_ms(start),
                )

            articles = self._extract_articles(feed, source, since=since, limit=limit)

            result = FeedResult(
                source_name=source.name,
                articles=articles,
                duration_ms=self._elapsed_ms(start),
            )

            logger.info(
                "feed_fetched",
                source=source.name,
                articles=len(articles),
                duration_ms=result.duration_ms,
            )

            return result

        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP {e.response.status_code}: {e.response.reason_phrase}"
            logger.warning("feed_fetch_failed", source=source.name, error=error_msg)
            return FeedResult(
                source_name=source.name,
                error=error_msg,
                duration_ms=self._elapsed_ms(start),
            )
        except httpx.RequestError as e:
            error_msg = f"Request error: {e.__class__.__name__}: {e}"
            logger.warning("feed_fetch_failed", source=source.name, error=error_msg)
            return FeedResult(
                source_name=source.name,
                error=error_msg,
                duration_ms=self._elapsed_ms(start),
            )
        except Exception as e:
            error_msg = f"Unexpected error: {e.__class__.__name__}: {e}"
            logger.error("feed_fetch_error", source=source.name, error=error_msg)
            return FeedResult(
                source_name=source.name,
                error=error_msg,
                duration_ms=self._elapsed_ms(start),
            )
        finally:
            if should_close and client is not None:
                await client.aclose()

    async def fetch_all(
        self,
        sources: list[RSSSource],
        *,
        limit: int | None = None,
        since: datetime | None = None,
    ) -> list[FeedResult]:
        """
        Fetch multiple RSS feeds concurrently.

        Args:
            sources: List of RSS source definitions.
            limit: Max articles per source.
            since: Only articles published after this datetime.

        Returns:
            List of FeedResult (one per source, in same order).
        """
        if not sources:
            return []

        async with httpx.AsyncClient(
            timeout=self._timeout,
            follow_redirects=True,
            headers={"User-Agent": "xalpha-researcher/1.0 (RSS Reader)"},
        ) as client:
            tasks = [
                self.fetch_feed(source, limit=limit, since=since, client=client)
                for source in sources
            ]
            results = await asyncio.gather(*tasks, return_exceptions=False)

        succeeded = sum(1 for r in results if r.error is None)
        failed = sum(1 for r in results if r.error is not None)
        total_articles = sum(len(r.articles) for r in results)

        logger.info(
            "fetch_all_complete",
            sources_total=len(sources),
            sources_succeeded=succeeded,
            sources_failed=failed,
            total_articles=total_articles,
        )

        return results

    def _extract_articles(
        self,
        feed: feedparser.FeedParserDict,
        source: RSSSource,
        *,
        since: datetime | None = None,
        limit: int | None = None,
    ) -> list[RawArticle]:
        """Extract and filter articles from a parsed feed."""
        articles: list[RawArticle] = []

        now = datetime.now(timezone.utc)
        
        for entry in feed.entries:
            published_at = self._parse_date(entry)

            # Time filter: skip articles older than `since`
            if since and published_at and published_at < since:
                continue
                
            # Future filter: Data sources often publish articles with broken dates in the year 2030+ by mistake
            # We ignore any article that is set in the future. We allow +1 minute buffer for clock drift
            if published_at and published_at > now + __import__("datetime").timedelta(minutes=1):
                continue

            # Extract content (prefer content field, fallback to summary)
            content = ""
            if hasattr(entry, "content") and entry.content:
                content = entry.content[0].get("value", "")
            summary = getattr(entry, "summary", "")

            article = RawArticle(
                source_name=source.name,
                source_url=str(source.url),
                title=getattr(entry, "title", ""),
                link=getattr(entry, "link", ""),
                summary=summary,
                content=content or summary,
                published_at=published_at,
                domain=source.domain,
                language=source.language,
                raw_data=dict(entry) if hasattr(entry, "keys") else {},
            )
            articles.append(article)

            # Quantity limit
            if limit and len(articles) >= limit:
                break

        return articles

    @staticmethod
    def _parse_date(entry: object) -> datetime | None:
        """Parse date from feed entry, handling multiple formats."""
        # Try published_parsed (struct_time)
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            try:
                from time import mktime

                return datetime.fromtimestamp(mktime(entry.published_parsed), tz=timezone.utc)
            except (ValueError, OverflowError, OSError):
                pass

        # Try published string
        if hasattr(entry, "published") and entry.published:
            try:
                return parsedate_to_datetime(entry.published).replace(tzinfo=timezone.utc)
            except (ValueError, TypeError):
                pass

        # Try updated_parsed
        if hasattr(entry, "updated_parsed") and entry.updated_parsed:
            try:
                from time import mktime

                return datetime.fromtimestamp(mktime(entry.updated_parsed), tz=timezone.utc)
            except (ValueError, OverflowError, OSError):
                pass

        return None

    @staticmethod
    def _elapsed_ms(start: float) -> int:
        """Calculate elapsed time in milliseconds."""
        return int((asyncio.get_event_loop().time() - start) * 1000)
