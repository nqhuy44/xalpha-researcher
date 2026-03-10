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
from sqlalchemy import select
from src.db.models.news import NewsArticle

from src.config.settings import settings
from src.agents.analyst.engine import DebateEngine

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
        self.app.add_handler(CommandHandler("analyze", self._cmd_analyze))
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
            "/analyze <ticker> - Phân tích đa chiều (Bull vs Bear) cho 1 mã cổ phiếu\n"
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
        from src.db.session import async_session_factory
        from src.data.persistence.news_repo import NewsRepository
        from src.models.news import NewsArticleDTO

        await self._safe_reply(
            update, "Đang kích hoạt quy trình thu thập dữ liệu. Quá trình này mất khoảng 1-2 phút."
        )

        try:
            # 0. Preload known hashes from DB to avoid re-scraping
            async with async_session_factory() as session:
                repo = NewsRepository(session)
                known_hashes = await repo.get_recent_hashes(days=7)
            
            collector = NewsCollector(known_hashes=known_hashes)
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

        # Meta report message
        meta_msg = (
            "*Báo Cáo Thu Thập Dữ Liệu*\n\n"
            f"- Bản ghi truy xuất từ RSS: {result.total_fetched}\n"
            f"- Bản ghi mới tải về: {result.total_after_dedup}\n"
        )
        user_chat_id = update.effective_chat.id
        await self.send_message(meta_msg, chat_id=user_chat_id)

        try:
            async with async_session_factory() as session:
                repo = NewsRepository(session)
                
                # 2. Single DB query: get ALL unreported articles grouped by domain
                grouped = await repo.get_all_unreported_grouped(limit_per_domain=500)
                
                if not grouped:
                    await self._safe_reply(update, "✅ Hệ thống đã chạy xong, nhưng không có thông tin mới đáng chú ý.")
                    return
                
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

                await self._safe_reply(update, f"Đang xử lý tổng hợp dữ liệu {len(grouped)} chủ đề... Tiến trình này có thể mất vài phút.")
                
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
                        report = await llm.synthesize_reports(summaries_texts)  # returns str now
                        
                        # Fix: check if it's a list (in case it wasn't reloaded) or string
                        if isinstance(report, list):
                            report = "\n".join(report)
                            
                        # Build ONE consolidated Telegram message per domain
                        msg = (
                            f"📌 *[{topic_name.upper()}]* ({len(articles)} bài)\n\n"
                            f"{report}"
                        )
                        await self.send_message(msg, chat_id=user_chat_id)
                    else:
                        logger.warning("no_summaries_for_domain", domain=domain)
                    
                    # Always mark as reported to prevent re-processing
                    article_ids = [str(a.id) for a in articles]
                    await repo.mark_as_reported(article_ids)
                        
        except Exception as e:
            logger.error("news_llm_processing_failed", error=str(e), exc_info=True)
            await self._safe_reply(update, "⚠️ *Lỗi xử lý AI.*\nHệ thống không thể tổng hợp tin tức lúc này.")

    async def _cmd_analyze(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await self._safe_reply(update, "Vui lòng nhập ticker. Ví dụ: `/analyze VNM`", parse_mode=ParseMode.MARKDOWN)
            return
            
        ticker = context.args[0].upper()
        
        rounds = 1
        if len(context.args) > 1 and context.args[1].isdigit():
            rounds = int(context.args[1])
            # Limit rounds to prevent abuse/too long generation
            if rounds > 3:
                rounds = 3
        
        status_msg = await update.message.reply_text(f"⏳ Đang khởi tạo phiên phản biện khép kín (Bull vs Bear) cho **{ticker}** với {rounds} vòng phản biện...\nViệc này có thể mất vài phút.")
        
        try:
            async def send_debate_msg(msg: str):
                await self.send_message(msg, chat_id=update.effective_chat.id)
                
            engine = DebateEngine(max_rebuttals=rounds)
            result = await engine.analyze(ticker, on_message=send_debate_msg)
            
            if not result:
                await status_msg.edit_text(f"❌ Phân tích thất bại cho {ticker}. Vui lòng kiểm tra logs.")
                return
                
            verdict, transcript, rounds = result
            
            # Xóa tin nhắn "Đang khởi tạo..." vì transcript đã được gửi xong
            await status_msg.delete()
            
            def get_emoji_for_text(text: str) -> str:
                t = text.lower()
                if "tiềm năng" in t or "mua" in t:
                    return "🟢"
                elif "rủi ro" in t or "bán" in t:
                    return "🔴"
                elif "an toàn" in t or "giữ" in t or "theo dõi" in t:
                    return "🟡"
                return "⚪"
                
            decision_emoji = get_emoji_for_text(verdict.decision)
            st_emoji = get_emoji_for_text(verdict.short_term.action)
            mt_emoji = get_emoji_for_text(verdict.medium_term.action)
            lt_emoji = get_emoji_for_text(verdict.long_term.action)
                
            # Format the verdict beautifully
            msg = [
                f"🧑‍⚖️ **ĐÁNH GIÁ: {ticker} — {decision_emoji} {verdict.decision.upper()}**",
                f"Độ tin cậy tổng thể: {verdict.confidence_score}%",
                f"📊 Điểm số: 🐂 Bull **{verdict.bull_score}** vs 🐻 Bear **{verdict.bear_score}**\n",
                
                "**🎯 KHUYẾN NGHỊ:**",
                f"🌱 _Ngắn hạn (1T)_: {st_emoji} **{verdict.short_term.action.upper()}** (Tin cậy: {verdict.short_term.horizon_confidence}%)",
                f"   MUA: {verdict.short_term.entry_price:,.0f} ➔ TP: {verdict.short_term.target_price:,.0f} | SL: {verdict.short_term.stop_loss:,.0f} (R:R = {verdict.short_term.risk_reward_ratio})",
                f"   Lý do: {verdict.short_term.rationale}\n",
                
                f"🌲 _Trung hạn (6T)_: {mt_emoji} **{verdict.medium_term.action.upper()}** (Tin cậy: {verdict.medium_term.horizon_confidence}%)",
                f"   MUA: {verdict.medium_term.entry_price:,.0f} ➔ TP: {verdict.medium_term.target_price:,.0f} | SL: {verdict.medium_term.stop_loss:,.0f} (R:R = {verdict.medium_term.risk_reward_ratio})",
                f"   Lý do: {verdict.medium_term.rationale}\n",
                
                f"🌳 _Dài hạn (1N+)_: {lt_emoji} **{verdict.long_term.action.upper()}** (Tin cậy: {verdict.long_term.horizon_confidence}%)",
                f"   MUA: {verdict.long_term.entry_price:,.0f} ➔ TP: {verdict.long_term.target_price:,.0f} | SL: {verdict.long_term.stop_loss:,.0f} (R:R = {verdict.long_term.risk_reward_ratio})",
                f"   Lý do: {verdict.long_term.rationale}\n",
                
                "**💡 TỔNG HỢP TỪ THẨM PHÁN:**",
                f"_{verdict.judge_synthesis}_"
            ]
            
            response_text = "\n".join(msg)
            # Send the final verdict
            try:
                await self.send_message(response_text, chat_id=update.effective_chat.id, parse_mode=ParseMode.MARKDOWN)
            except Exception as e:
                logger.error(f"Error sending Markdown: {e}, falling back to plain text.")
                await self.send_message(response_text, chat_id=update.effective_chat.id, parse_mode=None)
                
            # --- Generate and Send HTML Report ---
            from src.agents.analyst.report_generator import generate_html_report, save_report
            try:
                html_content = generate_html_report(ticker, verdict, rounds)
                report_path = save_report(ticker, html_content)
                with open(report_path, "rb") as doc:
                    await self.app.bot.send_document(
                        chat_id=update.effective_chat.id,
                        document=doc, 
                        filename=f"XAlpha_Debate_{ticker}.html",
                        caption=f"📄 Báo cáo Tranh biện HTML chi tiết cho {ticker}"
                    )
            except Exception as e:
                logger.error(f"Failed to generate/send HTML report: {e}", exc_info=True)
            
        except Exception as e:
            logger.error(f"Error in /analyze {ticker}: {e}", exc_info=True)
            # Since status_msg might have been deleted, send a new message
            await self.send_message(f"❌ Có lỗi bất ngờ xảy ra khi phân tích {ticker}.", chat_id=update.effective_chat.id)

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
