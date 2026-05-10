import logging
import uuid
from typing import Dict, Any, Optional

from sqlalchemy import select, desc, update
from src.db.session import async_session_factory
from src.db.models.portfolio import PortfolioPosition, PortfolioSuggestion
from src.db.models.finance import StockEOD

from src.agents.portfolio.state import PortfolioState, AnalystSignal
from src.agents.portfolio.graph import portfolio_graph
from src.agents.analyst.state import Verdict

logger = logging.getLogger(__name__)

# B7: gate the LLM-driven graph on whether the verdict is actually actionable.
# - If the user already holds the ticker, we MUST evaluate (could be a sell/reduce signal).
# - If they don't hold it, the only useful action is a buy candidate, which requires a
#   bullish verdict above a confidence floor. Otherwise the graph would burn a Pro call
#   to conclude "no action".
ACTIONABLE_DECISIONS = {"Tiềm năng", "Khả quan"}
PORTFOLIO_TRIGGER_CONFIDENCE = 70  # aligned with the T2 verdict-cache threshold


class PortfolioEngine:
    """Facade for executing the Portfolio Agent graph based on Analyst signals."""

    async def process_signal(self, ticker: str, verdict: Verdict, verdict_id: Optional[uuid.UUID] = None) -> Optional[PortfolioState]:
        """
        Gathers portfolio context and runs the Portfolio Graph.
        """
        logger.info(f"Starting Portfolio Engine for {ticker}")
        
        # 1. Gather Portfolio Context
        current_cash = 0.0
        current_positions = {}
        total_nav = 0.0
        current_price = 0.0
        
        try:
            async with async_session_factory() as db:
                # Get Cash
                cash_stmt = select(PortfolioPosition).where(PortfolioPosition.symbol == "CASH")
                cash_res = await db.execute(cash_stmt)
                cash_pos = cash_res.scalar_one_or_none()
                if cash_pos:
                    current_cash = cash_pos.cost_basis
                    
                # Get All Positions
                pos_stmt = select(PortfolioPosition).where(PortfolioPosition.symbol != "CASH")
                pos_res = await db.execute(pos_stmt)
                positions = pos_res.scalars().all()
                
                # We need market value for total NAV, so we fetch latest EOD for each
                for pos in positions:
                    avg_price = pos.cost_basis / pos.shares if pos.shares > 0 else 0.0
                    price_stmt = select(StockEOD.close).where(StockEOD.ticker == pos.symbol).order_by(desc(StockEOD.trade_date)).limit(1)
                    price_res = await db.execute(price_stmt)
                    latest_price = price_res.scalar_one_or_none() or avg_price
                    
                    if latest_price < 1000 and latest_price > 0:
                        latest_price *= 1000
                        
                    market_value = pos.shares * latest_price
                    current_positions[pos.symbol] = {
                        "shares": pos.shares,
                        "avg_price": avg_price,
                        "market_price": latest_price,
                        "market_value": market_value
                    }
                    total_nav += market_value
                    
                    if pos.symbol == ticker:
                        current_price = latest_price
                    if pos.symbol == ticker:
                        current_price = latest_price
                        
                # Add cash to NAV
                total_nav += current_cash
                
                # If ticker isn't in portfolio, fetch its current price anyway
                if ticker not in current_positions:
                    price_stmt = select(StockEOD.close).where(StockEOD.ticker == ticker).order_by(desc(StockEOD.trade_date)).limit(1)
                    price_res = await db.execute(price_stmt)
                    latest_price = price_res.scalar_one_or_none() or 0.0
                    if latest_price < 1000 and latest_price > 0:
                        latest_price *= 1000
                    current_price = latest_price

        except Exception as e:
            logger.error(f"Failed to fetch portfolio context: {e}")
            return None

        # B7: short-circuit before the LLM graph if the verdict isn't actionable for this user.
        # We have current_positions in hand at this point — the position lookup above is cheap
        # SQL; the graph below is the Pro call we're trying to avoid burning on dead-end cases.
        is_held = ticker in current_positions
        is_buy_candidate = (
            verdict.decision in ACTIONABLE_DECISIONS
            and verdict.confidence_score >= PORTFOLIO_TRIGGER_CONFIDENCE
        )
        if not (is_held or is_buy_candidate):
            logger.info(
                f"Skipping Portfolio graph for {ticker}: not held and verdict={verdict.decision!r} "
                f"confidence={verdict.confidence_score} below actionable threshold "
                f"(decisions={sorted(ACTIONABLE_DECISIONS)}, min_conf={PORTFOLIO_TRIGGER_CONFIDENCE})."
            )
            return None

        # 2. Map Analyst Verdict to AnalystSignal
        signal = AnalystSignal(
            symbol=ticker,
            decision=verdict.decision,
            confidence_score=verdict.confidence_score,
            short_term_action=verdict.short_term.action,
            short_term_target=verdict.short_term.target_price,
            short_term_confidence=verdict.short_term.horizon_confidence,
            context_layer_assessment=verdict.context_layer_assessment,
            current_price=current_price
        )
        
        # 3. Fetch Global News (Macro/Supply Chain perspective) from DB
        global_news = ""
        try:
            from src.db.models.news import NewsArticle
            import datetime

            since_date = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=5)
            domains = ["macro", "geopolitics", "finance", "tech"]
            news_lines = []
            
            async with async_session_factory() as db:
                for domain in domains:
                    stmt = select(NewsArticle).where(
                        NewsArticle.domain == domain,
                        NewsArticle.published_at >= since_date
                    ).order_by(desc(NewsArticle.published_at)).limit(5)
                    
                    res = await db.execute(stmt)
                    articles = res.scalars().all()
                    
                    for art in articles:
                        # Use AI summary if available, else description or truncated content
                        summary = art.ai_summary or art.description or (art.content[:200] + "...")
                        news_lines.append(f"- [{art.domain.upper()}] {art.title}: {summary}")
            
            if news_lines:
                global_news = "\n".join(news_lines)
                logger.info(f"Fetched {len(news_lines)} global news items from DB for Portfolio portfolio_context.")
            else:
                logger.info("No recent news found in DB matching criteria.")
                
        except Exception as news_e:
            logger.warning(f"Failed to fetch global news from DB for Portfolio: {news_e}")
        
        # 4. Initialize State
        initial_state = PortfolioState(
            ticker=ticker,
            signal=signal,
            current_cash=current_cash,
            current_positions=current_positions,
            total_nav=total_nav,
            global_news=global_news
        )
        
        # 4. Invoke Graph
        try:
            logger.info("Executing LangGraph Portfolio Workflow...")
            # We use invoke for a blocking, single-pass run through the simple portfolio pipeline.
            final_state_raw = await portfolio_graph.ainvoke(initial_state.model_dump())
            final_state = PortfolioState(**final_state_raw)
            
            # 5. Extract Suggestion for Persistence
            final_trade = None
            rationale_texts = []
            
            if final_state.approved_trades:
                final_trade = final_state.approved_trades[-1]
            elif final_state.proposed_trades:
                final_trade = final_state.proposed_trades[-1]

            if final_trade:
                logger.info("Found final trade", action=final_trade.action)
                try:
                    # Extract values from the new nested structure
                    suggested_shares = 0
                    if hasattr(final_trade, "suggestion") and final_trade.suggestion:
                        suggested_shares = getattr(final_trade.suggestion, "suggested_shares", 0)
                        low = getattr(final_trade.suggestion.entry_price_range, "low", 0.0)
                        high = getattr(final_trade.suggestion.entry_price_range, "high", 0.0)
                        suggested_price = (low + high) / 2
                    else:
                        suggested_price = current_price
                    
                    suggested_cost = int(suggested_shares * suggested_price)

                    # Rationale from the new 'notes' field (which is summarized Vietnamese)
                    # Combine with risk check reason if it's a rejection
                    rationale_parts = []
                    if trade_notes := getattr(final_trade, "notes", ""):
                        rationale_parts.append(trade_notes)
                    if getattr(final_trade, "reason", "") and final_trade.reason not in ["Passed all risk checks.", "Passed sell checks.", "No action required on this ticker.", "No action required."]:
                        rationale_parts.append(f"Lưu ý rủi ro: {final_trade.reason}")
                    
                    rationale_combined = " | ".join(rationale_parts) if rationale_parts else None

                    logger.info("Saving PortfolioSuggestion", ticker=ticker, action=final_trade.action, verdict_id=verdict_id)
                    async with async_session_factory() as db:
                        # Soft delete old
                        stmt = update(PortfolioSuggestion).where(
                            PortfolioSuggestion.symbol == ticker,
                            PortfolioSuggestion.is_active == True
                        ).values(is_active=False)
                        await db.execute(stmt)
                        
                        # Insert new
                        sugg = PortfolioSuggestion(
                            symbol=ticker,
                            analyst_decision=verdict.decision,
                            analyst_confidence=verdict.confidence_score,
                            suggested_action=final_trade.action,
                            suggested_shares=suggested_shares,
                            suggested_cost=suggested_cost,
                            rationale=rationale_combined,
                            verdict_id=verdict_id,
                            is_active=True
                        )
                        db.add(sugg)
                        await db.commit()
                        logger.info(f"Persisted PortfolioSuggestion for {ticker}")
                except Exception as db_e:
                    logger.error(f"Failed to persist PortfolioSuggestion for {ticker}", error=str(db_e))

            return final_state
            
        except Exception as e:
            logger.error(f"Portfolio Engine graph execution failed for {ticker}: {e}", exc_info=True)
            return None
