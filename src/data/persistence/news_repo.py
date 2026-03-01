"""
Repository for NewsArticle database operations.
"""

import structlog
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.dialects.postgresql import insert

from src.db.models.news import NewsArticle
from src.models.news import NewsArticleDTO

logger = structlog.get_logger(__name__)


class NewsRepository:
    """
    Handles database operations for news articles.
    Implements bulk upsert for efficiency and deduplication.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def upsert_articles(self, articles: List[NewsArticleDTO]) -> int:
        """
        Bulk upserts articles into the database.
        Uses content_hash for deduplication (ON CONFLICT DO NOTHING).
        
        Returns:
            Number of new articles actually inserted.
        """
        if not articles:
            return 0

        # Convert DTOs to dicts for bulk insertion
        data = [
            {
                "content_hash": a.content_hash,
                "url": a.url,
                "title": a.title,
                "author": a.author,
                "description": a.description,
                "content": a.content,
                "source_name": a.source_name,
                "domain": a.domain,
                "language": a.language,
                "published_at": a.published_at,
            }
            for a in articles
        ]

        # Use PostgreSQL ON CONFLICT DO NOTHING on content_hash
        stmt = insert(NewsArticle).values(data)
        stmt = stmt.on_conflict_do_nothing(index_elements=["content_hash"])
        
        result = await self.session.execute(stmt)
        await self.session.commit()
        
        return result.rowcount

    async def get_latest_by_domain(self, domain: str, limit: int = 10) -> List[NewsArticle]:
        """Fetch latest articles for a domain."""
        stmt = (
            select(NewsArticle)
            .where(NewsArticle.domain == domain)
            .order_by(NewsArticle.published_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def delete_older_than(self, days: int) -> int:
        """Cleanup old articles to save space (archive policy)."""
        # (Placeholder for future use in scheduler cleanup tasks)
        pass
