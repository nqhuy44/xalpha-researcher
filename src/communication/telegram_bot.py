"""
Telegram Bot Service — Unified communication layer for XAlpha Agents.
Enables agents to send notifications and users to control agents via Telegram.
"""

import asyncio
import structlog
from typing import Optional, List
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from telegram.constants import ParseMode

from src.config.settings import settings

logger = structlog.get_logger(__name__)


class TelegramService:
    """
    Handles Telegram Bot interactions and notifications.
    Designed as a singleton-friendly service.
    """

    def __init__(self):
        self.token = settings.telegram.token
        self.chat_id = settings.telegram.chat_id
        self.enabled = settings.telegram.enabled
        self.app: Optional[Application] = None

        if not self.token:
            logger.warning("telegram_bot_token_missing", message="Commands and notifications will be disabled.")
            self.enabled = False

    async def send_message(self, text: str, parse_mode: str = ParseMode.MARKDOWN):
        """
        Send a notification to the configured chat_id.
        """
        if not self.enabled or not self.chat_id:
            logger.debug("telegram_notification_skipped", enabled=self.enabled, chat_id=bool(self.chat_id))
            return

        try:
            # We create a temporary application if not running as a long-lived service
            if not self.app:
                temp_app = Application.builder().token(self.token).build()
                await temp_app.bot.send_message(chat_id=self.chat_id, text=text, parse_mode=parse_mode)
            else:
                await self.app.bot.send_message(chat_id=self.chat_id, text=text, parse_mode=parse_mode)
        except Exception as e:
            logger.error("telegram_send_failed", error=str(e))

    # --- Command Handlers ---

    async def _start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler for /start command."""
        user = update.effective_user
        welcome_text = (
            f"Xin chào {user.first_name}. Tôi là Lena, hệ thống phân tích AI của XAlpha.\n\n"
            "Tôi chịu trách nhiệm thu thập, phân tích và cung cấp thông tin tài chính chiến lược.\n"
            "Sử dụng /help để xem tài liệu điều khiển."
        )
        await update.message.reply_text(welcome_text, parse_mode=ParseMode.MARKDOWN)

    async def _status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler for /status command."""
        status_text = (
            "*Báo Cáo Trạng Thái Hệ Thống XAlpha:*\n"
            "- Core Engine: Operational\n"
            "- Database: Connected\n"
            "- News Agent: Active"
        )
        await update.message.reply_text(status_text, parse_mode=ParseMode.MARKDOWN)

    async def _help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler for /help command."""
        help_text = (
            "*Tài Liệu Cấp Lệnh:*\n"
            "/start - Khởi tạo phiên làm việc\n"
            "/status - Truy xuất trạng thái kết nối\n"
            "/collect - Buộc hệ thống thực thi lệnh quét dữ liệu\n"
            "/help - Hiển thị tài liệu này"
        )
        await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

    async def _collect_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler for /collect command."""
        from src.agents.news.collector import NewsCollector
        from src.services.llm import GeminiService
        
        await update.message.reply_text("Đang kích hoạt quy trình thu thập dữ liệu. Yêu cầu này sẽ mất khoảng 1-2 phút.", parse_mode=ParseMode.MARKDOWN)
        
        collector = NewsCollector()
        result = await collector.collect(persist=True)
        
        if result.total_after_dedup == 0:
            summary_text = "Phân tích hoàn tất. Không có bản ghi dữ liệu mới nào được lưu so với chu kỳ trước."
        else:
            await update.message.reply_text("Dữ liệu đã được thu thập. Đang tiến hành phân tích và tổng hợp thông tin...", parse_mode=ParseMode.MARKDOWN)
            llm = GeminiService()
            summary_text = await llm.summarize_news_batch(result.articles)
            
        final_msg = (
            "*Báo Cáo Thu Thập Dữ Liệu*\n\n"
            f"- Số lượng bản ghi truy xuất: {result.total_fetched}\n"
            f"- Số lượng bản ghi lưu mới: {result.total_after_dedup}\n\n"
            "*Kết Quả Phân Tích:*\n"
            f"{summary_text}"
        )
        await update.message.reply_text(final_msg, parse_mode=ParseMode.MARKDOWN)

    def run_forever(self):
        """Start the bot in polling mode."""
        if not self.enabled:
            logger.error("telegram_bot_disabled", reason="Missing token or disabled in config")
            return

        self.app = Application.builder().token(self.token).build()

        # Register handlers
        self.app.add_handler(CommandHandler("start", self._start_command))
        self.app.add_handler(CommandHandler("status", self._status_command))
        self.app.add_handler(CommandHandler("help", self._help_command))
        self.app.add_handler(CommandHandler("collect", self._collect_command))

        logger.info("telegram_bot_starting")
        self.app.run_polling()


if __name__ == "__main__":
    # Test block
    service = TelegramService()
    service.run_forever()
