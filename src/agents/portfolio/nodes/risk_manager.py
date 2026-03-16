import logging
from typing import Dict, Any

from src.agents.portfolio.state import PortfolioState, TradeAction

logger = logging.getLogger(__name__)

def risk_manager_node(state: PortfolioState) -> Dict[str, Any]:
    """
    Validates proposed trades against hard-coded risk management rules.
    Acts purely deterministically (no LLM) to guarantee safety.
    """
    logger.info(f"Running Risk Manager for {state.ticker}")
    
    approved_trades = []
    
    for trade in state.proposed_trades:
        # Default to REJECTED unless proven otherwise
        trade.status = "REJECTED"
        
        # Extract core suggestion data for easy access
        sug = trade.suggestion
        action = trade.action
        shares = sug.suggested_shares
        # Use mid-price for risk calculation
        price = (sug.entry_price_range.low + sug.entry_price_range.high) / 2
        
        if action in ["GIỮ", "THEO_DÕI", "TĂNG_TIỀN_MẶT"]:
            trade.status = "APPROVED"
            trade.reason = "No action required on this ticker."
            approved_trades.append(trade)
            continue
            
        if action in ["MUA_MỚI", "MUA_THÊM"]:
            # Rule 1: Do we have enough cash?
            required_cash = shares * price
            if required_cash > state.current_cash:
                trade.reason = f"Insufficient funds. Requires {required_cash:,.0f}, but only have {state.current_cash:,.0f}."
                approved_trades.append(trade)
                continue
                
            # Rule 2: Max Allocation limit (e.g., no more than 25% of NAV in a single ticker)
            current_holding_value = state.current_positions.get(trade.symbol, {}).get("market_value", 0.0)
            projected_allocation = (current_holding_value + required_cash) / max(state.total_nav, 1.0)
            
            if projected_allocation > 0.30: # Soften slightly as per user's request for "thoáng hơn"
                trade.reason = f"Exceeds max allocation limit of 30%. Projected: {projected_allocation:.2%}."
                approved_trades.append(trade)
                continue
                
            # If all checks pass
            trade.status = "APPROVED"
            trade.reason = "Passed all risk checks."
            approved_trades.append(trade)
            
        elif action in ["CHỐT_LỜI_MỘT_PHẦN", "GIẢM_TỶ_TRỌNG", "CẮT_LỖ", "BÁN_TOÀN_BỘ"]:
            # Rule 3: Do we own it?
            current_shares = state.current_positions.get(trade.symbol, {}).get("shares", 0)
            if current_shares < shares:
                trade.reason = f"Insufficient shares to sell. Own {current_shares}, trying to sell {shares}."
                approved_trades.append(trade)
                continue
                
            trade.status = "APPROVED"
            trade.reason = "Passed sell checks."
            approved_trades.append(trade)
            
        else:
            trade.reason = f"Unknown or unhandled action type: {action}"
            approved_trades.append(trade)

    return {"approved_trades": approved_trades}
