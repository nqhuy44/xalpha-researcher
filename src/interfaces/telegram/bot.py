"""
Telegram Bot Server — Standalone interface for XAlpha.

Run as: python -m src.interfaces.telegram.bot
"""

import asyncio
import structlog

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)
from telegram.constants import ParseMode

from src.config.settings import settings

logger = structlog.get_logger(__name__)


class TelegramBot:
    """
    Standalone Telegram Bot server.
    Receives user commands and dispatches tasks to agents.
    """

    def __init__(self):
        self.token = settings.telegram.token
        self.chat_id = settings.telegram.chat_id

        if not self.token:
            raise RuntimeError("TELEGRAM__TOKEN is required. Set it in .env")

        self.app = Application.builder().token(self.token).build()
        self._register_handlers()

    def _register_handlers(self):
        """Register all command handlers."""
        self.app.add_handler(CommandHandler("start", self._cmd_start))
        self.app.add_handler(CommandHandler("help", self._cmd_help))
        self.app.add_handler(CommandHandler("status", self._cmd_status))
        self.app.add_handler(CommandHandler("news", self._cmd_news))
        self.app.add_handler(CommandHandler("chatid", self._cmd_chatid))

    # --- Handlers ---

    async def _cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        text = (
            f"Xin chào {user.first_name}. Tôi là Lena, hệ thống phân tích AI của XAlpha.\n\n"
            "Tôi chịu trách nhiệm thu thập, phân tích và cung cấp thông tin tài chính chiến lược.\n"
            "Sử dụng /help để xem tài liệu điều khiển."
        )
        await self._safe_reply(update, text)

    async def _cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = (
            "*Tài Liệu Cấp Lệnh:*\n"
            "/start - Khởi tạo phiên làm việc\n"
            "/status - Truy xuất trạng thái kết nối\n"
            "/news - Thực thi lệnh quét và phân tích dữ liệu\n"
            "/chatid - Xem mã số định danh của Group/Chat này\n"
            "/help - Hiển thị tài liệu này"
        )
        await self._safe_reply(update, text, parse_mode=ParseMode.MARKDOWN)

    async def _cmd_chatid(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        chat_type = update.effective_chat.type
        text = (
            f"Mã Chat ID của bạn ({chat_type}) là: `{chat_id}`\n\n"
            f"Bạn có thể sao chép mã này vào .env:\n"
            f"`TELEGRAM__CHAT_ID={chat_id}`"
        )
        await self._safe_reply(update, text, parse_mode=ParseMode.MARKDOWN)

    async def _cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Perform a live health check on database connectivity."""
        from src.db.session import engine

        db_status = "Unreachable"
        try:
            async with engine.connect() as conn:
                await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
                db_status = "Connected"
        except Exception as e:
            db_status = f"Error: {e}"

        text = (
            "*Trạng Thái Hệ Thống XAlpha:*\n"
            f"- Database: {db_status}\n"
            "- News Agent: Standby"
        )
        await self._safe_reply(update, text, parse_mode=ParseMode.MARKDOWN)

    async def _cmd_news(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Trigger news collection, Gemini summarization, and reply."""
        from src.agents.news.collector import NewsCollector
        from src.services.llm import GeminiService

        await self._safe_reply(
            update, "Đang kích hoạt quy trình thu thập dữ liệu. Quá trình này mất khoảng 1-2 phút."
        )

        try:
            collector = NewsCollector()
            # Chỉ thu thập tin tức trong 24h qua để tránh tin cũ
            result = await collector.collect(hours_ago=24, persist=True)
        except Exception as e:
            logger.error("news_collection_failed", error=str(e))
            await self._safe_reply(
                update, 
                "⚠️ *Hệ thống đang gặp sự cố kỹ thuật.*\n"
                "Tôi không thể truy xuất dữ liệu lúc này. Vui lòng thử lại sau ít phút."
            )
            return

        if result.total_after_dedup == 0:
            summary_topics = ["Không có bản ghi dữ liệu mới nào so với chu kỳ trước."]
            await self._safe_reply(update, summary_topics[0])
            return
            
        await self._safe_reply(update, "Dữ liệu đã thu thập. Đang phân tích và tổng hợp...")
        llm = GeminiService()
        summary_topics = await llm.summarize_news_batch(result.articles)

        # Meta report message
        meta_msg = (
            "*Báo Cáo Thu Thập Dữ Liệu*\n\n"
            f"- Bản ghi truy xuất: {result.total_fetched}\n"
            f"- Bản ghi lưu mới: {result.total_after_dedup}\n"
        )
        # Gửi từng chủ đề trực tiếp cho người dùng yêu cầu
        user_chat_id = update.effective_chat.id
        await self.send_message(meta_msg, chat_id=user_chat_id)

        # Gửi từng chủ đề riêng biệt
        for topic_msg in summary_topics:
            await self.send_message(topic_msg, chat_id=user_chat_id)

    async def _safe_reply(self, update: Update, text: str, parse_mode: str | None = None):
        """Helper to reply to a message while handling length limits and parsing errors."""
        if not update.message:
            return

        # Truncate if too long (Telegram limit is ~4096)
        if len(text) > 3500:
            text = text[:3500] + "\n...[Nội dung bị cắt ngắn]"

        try:
            await update.message.reply_text(text, parse_mode=parse_mode)
        except Exception:
            # Fallback to plain text if markdown fails
            try:
                await update.message.reply_text(text)
            except Exception as e:
                logger.error("telegram_reply_failed", error=str(e))

    async def send_message(self, text: str, chat_id: int | str | None = None, parse_mode: str = ParseMode.MARKDOWN):
        """Public API for agents to push notifications. Falls back to config chat_id if not provided."""
        target_id = chat_id or self.chat_id
        if not target_id:
            logger.warning("telegram_chat_id_missing", message="Cannot send message without a target chat ID.")
            return
            
        # Handle maximum message lengths per Telegram limits
        if len(text) > 3500:
            text = text[:3500] + "\n...[Báo cáo bị cắt ngắn do giới hạn độ dài]"
            
        try:
            await self.app.bot.send_message(
                chat_id=target_id, text=text, parse_mode=parse_mode
            )
        except Exception as e:
            logger.error("telegram_send_failed", error=str(e))
            # Fallback to plain text if markdown parsing fails
            try:
                await self.app.bot.send_message(chat_id=target_id, text=text)
            except Exception as e2:
                logger.error("telegram_fallback_send_failed", error=str(e2))

    async def _error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Log Errors caused by Updates."""
        from telegram.error import NetworkError, TimedOut, Forbidden
        
        error = context.error
        if isinstance(error, (NetworkError, TimedOut)):
            logger.warn("telegram_network_error", error=str(error))
        elif isinstance(error, Forbidden):
            logger.error("telegram_forbidden_error", error=str(error))
        else:
            logger.error("telegram_unexpected_error", error=str(error), exc_info=error)

    def run(self):
        """Start the bot in polling mode (blocking)."""
        logger.info("telegram_bot_starting")
        self.app.add_error_handler(self._error_handler)
        self.app.run_polling()


def main():
    bot = TelegramBot()
    bot.run()


if __name__ == "__main__":
    main()
