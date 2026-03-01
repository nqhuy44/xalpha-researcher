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

    async def get_unreported_articles_by_domain(self, limit_per_domain: int = 50) -> List[NewsArticle]:
        """Fetch a batch of unreported articles belonging to a specific domain.
        This groups articles together so the LLM synthesis phase receives contextual batches.
        """
        # Step 1: Find one domain that has unreported articles
        domain_stmt = (
            select(NewsArticle.domain)
            .where(NewsArticle.is_reported == False)
            .limit(1)
        )
        domain_res = await self.session.execute(domain_stmt)
        target_domain = domain_res.scalar_one_or_none()

        if not target_domain:
            return []

        # Step 2: Fetch all unreported articles for that specific domain
        stmt = (
            select(NewsArticle)
            .where(NewsArticle.is_reported == False)
            .where(NewsArticle.domain == target_domain)
            .order_by(NewsArticle.published_at.desc())
            .limit(limit_per_domain)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_summaries(self, updates: List[tuple[str, str]]) -> None:
        """
        Bulk update ai_summary for a list of articles.
        Takes a list of tuples: (article_id, summary_text)
        """
        from sqlalchemy import update
        for article_id, ai_summary in updates:
            stmt = (
                update(NewsArticle)
                .where(NewsArticle.id == article_id)
                .values(ai_summary=ai_summary, is_summarized=True)
            )
            await self.session.execute(stmt)
        await self.session.commit()

    async def mark_as_reported(self, article_ids: List[str]) -> None:
        """Mark a batch of articles as reported."""
        from sqlalchemy import update
        if not article_ids:
            return
        stmt = (
            update(NewsArticle)
            .where(NewsArticle.id.in_(article_ids))
            .values(is_reported=True)
        )
        await self.session.execute(stmt)
        await self.session.commit()

    async def delete_older_than(self, days: int) -> int:
        """Cleanup old articles to save space (archive policy)."""
        # (Placeholder for future use in scheduler cleanup tasks)
        pass
