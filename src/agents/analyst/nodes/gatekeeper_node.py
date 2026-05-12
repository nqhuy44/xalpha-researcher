import logging
from datetime import datetime, timezone
from typing import Any, Dict

from sqlalchemy import text

from src.agents.analyst.state import AnalystState
from src.config.settings import settings
from src.db.session import async_session_factory

logger = logging.getLogger(__name__)

# VN market timezone label used in Postgres AT TIME ZONE expressions.
_VN_TZ = "Asia/Ho_Chi_Minh"


async def gatekeeper_node(state: AnalystState) -> Dict[str, Any]:
    """
    L0 rule-based filter. Runs before data_aggregator so no SQL-heavy context
    is assembled for tickers that should not be analysed.

    Checks (in order, short-circuit on first failure):
      1. Warn-list — admin-flagged tickers always skipped.
      2. Company exists in DB — can't evaluate market-cap/volume otherwise.
      3. Market cap >= settings.gatekeeper.min_market_cap (default 100B VND).
      4. 30-day avg volume >= settings.gatekeeper.min_avg_volume_30d (default 100k shares).
      5. No fresh high-confidence verdict already exists for this ticker today
         (confidence >= settings.gatekeeper.cache_confidence_threshold, default 70).

    Sets gatekeeper_passed=False + skip_reason when any check fails.
    """
    ticker = state.ticker
    cfg = settings.gatekeeper

    logger.info(f"Gatekeeper checking {ticker}")

    # 1. Warn-list (no DB needed)
    if ticker.upper() in [t.upper() for t in cfg.warn_list]:
        logger.warning(f"gatekeeper_skip ticker={ticker} reason=WARN_LIST")
        return {"gatekeeper_passed": False, "skip_reason": "WARN_LIST"}

    async with async_session_factory() as session:

        # 2. Company exists + market cap
        row = (await session.execute(
            text("SELECT market_cap FROM company_profiles WHERE ticker = :t"),
            {"t": ticker},
        )).fetchone()

        if row is None:
            logger.warning(f"gatekeeper_skip ticker={ticker} reason=NO_COMPANY_DATA")
            return {"gatekeeper_passed": False, "skip_reason": "NO_COMPANY_DATA"}

        market_cap = row[0]
        if market_cap is not None and market_cap < cfg.min_market_cap:
            logger.info(
                f"gatekeeper_skip ticker={ticker} reason=LOW_MARKET_CAP "
                f"market_cap={market_cap:,} threshold={cfg.min_market_cap:,}"
            )
            return {"gatekeeper_passed": False, "skip_reason": "LOW_MARKET_CAP"}

        # 3. 30-day average volume
        vol_row = (await session.execute(
            text("""
                SELECT AVG(volume)::bigint
                FROM stock_eod
                WHERE ticker = :t
                  AND trade_date >= NOW() - INTERVAL '30 days'
            """),
            {"t": ticker},
        )).fetchone()

        avg_vol = vol_row[0] if vol_row else None
        if avg_vol is not None and avg_vol < cfg.min_avg_volume_30d:
            logger.info(
                f"gatekeeper_skip ticker={ticker} reason=LOW_VOLUME "
                f"avg_vol_30d={avg_vol:,} threshold={cfg.min_avg_volume_30d:,}"
            )
            return {"gatekeeper_passed": False, "skip_reason": "LOW_VOLUME"}

        # 4. Cache hit — fresh high-confidence verdict already exists today (VN date)
        cache_row = (await session.execute(
            text(f"""
                SELECT id, confidence_score
                FROM debate_verdicts
                WHERE ticker = :t
                  AND is_active = TRUE
                  AND DATE(created_at AT TIME ZONE '{_VN_TZ}') =
                      DATE(NOW() AT TIME ZONE '{_VN_TZ}')
                  AND confidence_score >= :threshold
                LIMIT 1
            """),
            {"t": ticker, "threshold": cfg.cache_confidence_threshold},
        )).fetchone()

        if cache_row is not None:
            logger.info(
                f"gatekeeper_skip ticker={ticker} reason=CACHE_HIT "
                f"verdict_id={cache_row[0]} confidence={cache_row[1]}"
            )
            return {"gatekeeper_passed": False, "skip_reason": "CACHE_HIT"}

    logger.info(f"Gatekeeper passed for {ticker}")
    return {"gatekeeper_passed": True}
