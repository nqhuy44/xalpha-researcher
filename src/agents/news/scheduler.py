"""
Async scheduler for News Agent tasks.
Uses APScheduler to trigger periodic collections based on app settings.
"""

import asyncio
import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from src.agents.news.collector import NewsCollector
from src.services.llm import GeminiService
from src.config.settings import settings
from src.db.session import async_session_factory
from src.data.persistence.news_repo import NewsRepository
from src.models.news import NewsArticleDTO

logger = structlog.get_logger(__name__)


async def _notify_telegram(text: str):
    """Lightweight push notification to Telegram. No polling server needed."""
    if not settings.telegram.token or not settings.telegram.chat_id:
        logger.debug("telegram_notification_skipped")
        return
    try:
        from telegram import Bot
        from telegram.constants import ParseMode
        bot = Bot(token=settings.telegram.token)
        
        # Ngăn chặn lỗi text quá dài (Telegram max ~4096)
        if len(text) > 3500:
            text = text[:3500] + "\n...[Báo cáo bị cắt ngắn do giới hạn độ dài]"
            
        try:
            await bot.send_message(
                chat_id=settings.telegram.chat_id, text=text, parse_mode=ParseMode.MARKDOWN
            )
        except Exception:
            # Fallback to plain text if Markdown fails to parse
            await bot.send_message(
                chat_id=settings.telegram.chat_id, text=text
            )
    except Exception as e:
        logger.error("telegram_notify_failed", error=str(e))


class NewsScheduler:
    """
    Orchestrates periodic news collection tasks.
    Schedule is dynamically loaded from settings.news.schedule_hours.
    """

    def __init__(self, collector: NewsCollector | None = None):
        self.collector = collector or NewsCollector()
        self.scheduler = AsyncIOScheduler()

    async def run_collection_task(self):
        """Standard collection task for the scheduler."""
        logger.info("scheduled_task_starting", task="Full News Collection")
        try:
            # 0. Preload known hashes from DB to avoid re-scraping
            async with async_session_factory() as session:
                repo = NewsRepository(session)
                known_hashes = await repo.get_recent_hashes(days=7)
            
            logger.info("preloaded_known_hashes", count=len(known_hashes))
            self.collector = NewsCollector(known_hashes=known_hashes)

            # 1. Fetch new raw articles and persist to DB
            result = await self.collector.collect(hours_ago=12, persist=True)
            
            async with async_session_factory() as session:
                repo = NewsRepository(session)
                
                # 2. Single DB query: get ALL unreported articles grouped by domain
                grouped = await repo.get_all_unreported_grouped(limit_per_domain=500)
                
                if not grouped:
                    logger.info("no_unreported_articles_to_process")
                    return
                
                logger.info("unreported_articles_found", 
                           domains=list(grouped.keys()),
                           total=sum(len(v) for v in grouped.values()))
                
                domain_map = {
                    "macro": "Kinh tế vĩ mô",
                    "finance": "Tài chính & Kinh doanh",
                    "geopolitics": "Địa chính trị & Thế giới",
                    "tech": "Công nghệ số",
                    "law": "Pháp luật & Chính sách",
                    "real_estate": "Bất động sản",
                    "banking": "Ngân hàng",
                    "general": "Tin tức chung",
                }

                # 3. Process each domain exactly ONCE
                for domain, articles in grouped.items():
                    topic_name = domain_map.get(domain, domain.capitalize())
                    
                    # Stage 1: Summarization (Flash-Lite)
                    unsummarized = [a for a in articles if not a.is_summarized]
                    if unsummarized:
                        llm = GeminiService()
                        dtos = [
                            NewsArticleDTO(
                                article_id=str(a.id),
                                content_hash=a.content_hash,
                                url=a.url,
                                title=a.title,
                                content=a.content,
                                source_name=a.source_name,
                                domain=a.domain,
                                description=a.description,
                                published_at=a.published_at,
                                ingested_at=a.ingested_at,
                            ) for a in unsummarized
                        ]
                        summary_updates = await llm.generate_article_summaries(dtos)
                        if summary_updates:
                            await repo.update_summaries(summary_updates)
                            # Refresh summaries for synthesis
                            for a in articles:
                                for aid, summary_text in summary_updates:
                                    if str(a.id) == aid:
                                        a.ai_summary = summary_text

                    # Stage 2: Synthesis (Flash) — ONE report per domain
                    summaries_texts = [a.ai_summary for a in articles if a.ai_summary]
                    
                    if summaries_texts:
                        llm = GeminiService()
                        report = await llm.synthesize_reports(summaries_texts)
                        
                        # Build ONE consolidated Telegram message per domain
                        msg = (
                            f"📌 *[{topic_name.upper()}]* ({len(articles)} bài)\n\n"
                            f"{report}"
                        )
                        await _notify_telegram(msg)
                    else:
                        logger.warning("no_summaries_for_domain", domain=domain)
                    
                    # Always mark as reported to prevent re-processing
                    article_ids = [str(a.id) for a in articles]
                    await repo.mark_as_reported(article_ids)

            logger.info("scheduled_task_complete")
        except Exception as e:
            logger.error("scheduled_task_failed", error=str(e), exc_info=True)

    def start(self):
        """Configure jobs based on settings and start the scheduler."""
        hours = settings.news.schedule_hours

        if not hours:
            logger.warning("scheduler_no_jobs_configured", reason="settings.news.schedule_hours is empty")
            return

        for hour in hours:
            job_id = f"news_collection_{hour:02d}00"
            self.scheduler.add_job(
                self.run_collection_task,
                CronTrigger(hour=hour, minute=0, timezone="Asia/Ho_Chi_Minh"),
                name=f"News Collection at {hour:02d}:00",
                id=job_id,
                replace_existing=True,
            )

        logger.info("scheduler_started", configured_hours=hours)
        self.scheduler.start()

    async def run_forever(self):
        """Keep the process alive."""
        self.start()
        try:
            while True:
                await asyncio.sleep(3600)
        except (KeyboardInterrupt, SystemExit):
            self.scheduler.shutdown()
            logger.info("scheduler_shutdown")


if __name__ == "__main__":
    scheduler = NewsScheduler()
    asyncio.run(scheduler.run_forever())

