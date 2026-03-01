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
            result = await self.collector.collect(hours_ago=12, persist=True)

            if result.total_after_dedup == 0:
                summary_topics = ["Không có bản ghi dữ liệu mới nào được phát hiện."]
            else:
                llm = GeminiService()
                summary_topics = await llm.summarize_news_batch(result.articles)

            final_msg = (
                "*Báo Cáo Thu Thập Dữ Liệu Tự Động*\n\n"
                f"- Nguồn tin khả dụng: {result.sources_succeeded}/{result.sources_succeeded + result.sources_failed}\n"
                f"- Số lượng bản ghi mới: {result.total_after_dedup}\n\n"
            )
            await _notify_telegram(final_msg)
            
            for topic in summary_topics:
                await _notify_telegram(topic)

            logger.info(
                "scheduled_task_complete",
                succeeded=result.sources_succeeded,
                failed=result.sources_failed,
                articles=result.total_after_dedup,
            )
        except Exception as e:
            logger.error("scheduled_task_failed", error=str(e))

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

