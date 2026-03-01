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
            # 1. Fetch new raw articles and persist to DB
            result = await self.collector.collect(hours_ago=12, persist=True)
            
            async with async_session_factory() as session:
                repo = NewsRepository(session)
                
                # 2. Fetch queue of unreported articles in batches grouped by domain
                while True:
                    unreported = await repo.get_unreported_articles_by_domain(limit_per_domain=50)
                    if not unreported:
                        break
                        
                    current_domain = unreported[0].domain
                    
                    # 3. Stage 1: Summarization (Flash-Lite)
                    unsummarized = [a for a in unreported if not a.is_summarized]
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
                        # Generate and save summaries
                        summary_updates = await llm.generate_article_summaries(dtos)
                        if summary_updates:
                            await repo.update_summaries(summary_updates)
                            
                            # Refresh the queue to get the new ai_summaries for this domain
                            # We can just fetch again because it pulls chronologically un-reported
                            unreported_updated = await repo.get_unreported_articles_by_domain(limit_per_domain=50)
                            # Safety check exactly for the domain we are currently pinning
                            unreported = [u for u in unreported_updated if u.domain == current_domain]

                    # 4. Stage 2: Synthesis & Reporting (Flash)
                    summaries_texts = [a.ai_summary for a in unreported if a.ai_summary]
                    
                    if summaries_texts:
                        llm = GeminiService()
                        summary_topics = await llm.synthesize_reports(summaries_texts)
                        
                        domain_map = {
                            "macro": "Kinh tế vĩ mô",
                            "finance": "Tài chính & Kinh doanh",
                            "geopolitics": "Địa chính trị & Thế giới",
                            "tech": "Công nghệ số",
                            "law": "Pháp luật & Chính sách",
                            "real_estate": "Bất động sản",
                            "banking": "Ngân hàng",
                            "general": "Tin tức chung"
                        }
                        topic_name = domain_map.get(current_domain, current_domain.capitalize())
                        
                        final_msg = (
                            f"*Báo Cáo Thu Thập Dữ Liệu Tự Động (Chủ đề: {topic_name})*\n\n"
                            f"- Tin tức trong batch báo cáo: {len(unreported)}\n"
                        )
                        await _notify_telegram(final_msg)
                        
                        for topic in summary_topics:
                            await _notify_telegram(f"📌 **[{topic_name.upper()}]**\n{topic}")
                            
                    # 5. Mark as reported regardless of summary success
                    article_ids = [str(a.id) for a in unreported]
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

