import logging
from typing import Dict, Any

from langchain_core.messages import SystemMessage, HumanMessage

from src.services.llm import LLMService
from src.config.settings import settings
from src.agents.portfolio.state import PortfolioState, TradeAction

logger = logging.getLogger(__name__)

async def portfolio_manager_node(state: PortfolioState) -> Dict[str, Any]:
    """
    Analyzes the incoming signal and the current portfolio context to propose trades.
    Uses an LLM to determine the appropriate action (BUY/SELL/HOLD) and allocation size.
    """
    logger.info(f"Running Portfolio Manager for {state.ticker}")
    
    llm = LLMService()
    
    # Format current portfolio context for the LLM
    portfolio_context = f"""
    Current Cash: {state.current_cash:,.0f} VND
    Total NAV: {state.total_nav:,.0f} VND
    Current Positions: {state.current_positions}
    """
    
    signal_context = f"""
    [TÍN HIỆU TỪ HỆ THỐNG PHÂN TÍCH]
    - Mã cổ phiếu: {state.signal.symbol}
    - Giá thị trường: {state.signal.current_price:,.0f} VND
    - NHÃN PHÁN QUYẾT: {state.signal.decision}
    - ĐỘ TIN CẬY VÀO NHÃN: {state.signal.confidence_score}% 
      (Ghi chú: % tin cậy này là mức độ chắc chắn của Judge, KHÔNG phải tỉ lệ rủi ro của cổ phiếu)
    
    [TRIỂN VỌNG NGẮN HẠN]
    - Hành động gợi ý: {state.signal.short_term_action}
    - Mục tiêu giá: {state.signal.short_term_target:,.0f} VND
    - Độ tin cậy: {state.signal.short_term_confidence}%
    """

    from pathlib import Path
    import os
    
    prompt_path = Path(__file__).parent.parent.parent.parent / "prompts" / "portfolio_manager.txt"
    with open(prompt_path, "r", encoding="utf-8") as f:
        raw_prompt = f.read()
        
    global_news_context = state.global_news if state.global_news else "No recent macro news available."

    system_prompt = raw_prompt.format(portfolio_context=portfolio_context, signal_context=signal_context, global_news_context=global_news_context)

    human_message = f"Based on the signal and portfolio context, propose a trade for {state.ticker}."
    
    try:
        proposed_trade = await llm.generate_structured(
            system_prompt, human_message, TradeAction, role="judge", agent_name="portfolio_manager",
            ticker=state.ticker, node="portfolio_manager",
        )
        
        # Override fields to ensure consistency
        proposed_trade.symbol = state.ticker
        proposed_trade.status = "PROPOSED"
        
        # Ensure suggested_shares is a multiple of 100 as per rules
        if proposed_trade.suggestion.suggested_shares > 0:
            proposed_trade.suggestion.suggested_shares = (proposed_trade.suggestion.suggested_shares // 100) * 100
            
        return {"proposed_trades": [proposed_trade]}
        
    except Exception as e:
        logger.error(f"Error in portfolio manager: {e}")
        return {"errors": [f"Portfolio Manager failed: {str(e)}"]}
