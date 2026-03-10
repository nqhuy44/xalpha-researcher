import logging
from typing import Dict, Any
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, text
from src.db.session import async_session_factory as AsyncSessionLocal
from src.data.persistence.financial_repo import FinancialRepository
from src.data.persistence.news_repo import NewsRepository
from src.agents.analyst.state import AnalystState

logger = logging.getLogger(__name__)

async def aggregate_data_node(state: AnalystState) -> Dict[str, Any]:
    """
    Fetches raw data from the database and assembles it into a rich 'context' string.
    This string is what the Bull and Bear agents will read.
    """
    ticker = state.ticker
    logger.info(f"Aggregating data for {ticker}...")
    
    context_parts = []
    context_parts.append(f"### DEBATE CONTEXT FOR TICKER: {ticker}")
    context_parts.append(f"Analysis Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}\n")
    
    async with AsyncSessionLocal() as session:
        # 1. Company Profile (including Valuations)
        profile = await session.execute(
            text("SELECT company_name, industry, sector, market_cap, pe_ratio, pb_ratio, roe, roa, eps, ev_ebitda FROM company_profiles WHERE ticker = :t"),
            {"t": ticker}
        )
        p = profile.fetchone()
        if p:
            cap_bnd = round((p.market_cap or 0) / 1_000_000_000, 2)
            context_parts.append("[PROFILE]\nName|Industry|Sector|MarketCap(B)|PE|PB|ROE|ROA|EPS|EV/EBITDA")
            
            eps_val = p.eps if p.eps is not None else "N/A"
            ev_ebitda_val = p.ev_ebitda if p.ev_ebitda is not None else "N/A"
            pe_val = p.pe_ratio if p.pe_ratio is not None else "N/A"
            pb_val = p.pb_ratio if p.pb_ratio is not None else "N/A"
            roe_val = p.roe if p.roe is not None else "N/A"
            roa_val = p.roa if p.roa is not None else "N/A"
            
            context_parts.append(f"{p.company_name}|{p.industry}|{p.sector}|{cap_bnd}|{pe_val}|{pb_val}|{roe_val}|{roa_val}|{eps_val}|{ev_ebitda_val}")
        
        # 2. Latest Financial Report (Annual / Quarterly)
        fin_stmt = text("""
            SELECT year, quarter, data 
            FROM financial_reports 
            WHERE ticker = :t AND report_type = 'IncomeStatement'
            ORDER BY year DESC, quarter DESC NULLS LAST LIMIT 5
        """)
        fin_res = await session.execute(fin_stmt, {"t": ticker})
        reports = fin_res.fetchall()
        if reports:
            context_parts.append("\n[FINANCIALS]\nPeriod|Revenue(B)|NetProfit(B)")
            for r in reports:
                period = f"Q{r.quarter}_{r.year}" if r.quarter else f"FY_{r.year}"
                data_dict = r.data or {}
                
                # Convert all keys to lowercase for easier matching Since APIs return varying casing
                lower_data = {k.lower(): v for k, v in data_dict.items()}
                
                revenue = lower_data.get('revenue', lower_data.get('sales', lower_data.get('revenue (bn. vnd)', 0)))
                net_profit = lower_data.get('net_profit', lower_data.get('posttaxprofit', lower_data.get('net profit for the year', lower_data.get('attributable to parent company', 0))))
                
                rev_bnd = round((revenue or 0) / 1_000_000_000, 2)
                np_bnd = round((net_profit or 0) / 1_000_000_000, 2)
                context_parts.append(f"{period}|{rev_bnd}|{np_bnd}")
                
        # 3. EOD Technicals (Last 30 days summary + latest day + 1y range)
        eod_stmt = text("""
            SELECT trade_date, close, volume, rsi, macd, macd_signal, macd_hist
            FROM stock_eod 
            WHERE ticker = :t 
            ORDER BY trade_date DESC LIMIT 250
        """)
        eod_res = await session.execute(eod_stmt, {"t": ticker})
        eod_data = eod_res.fetchall()
        if eod_data:
            latest = eod_data[0]
            last_30 = eod_data[:30]
            avg_vol_30 = sum(r.volume for r in last_30) / len(last_30)
            high_30 = max(r.close for r in last_30)
            low_30 = min(r.close for r in last_30)
            high_52w = max(r.close for r in eod_data)
            low_52w = min(r.close for r in eod_data)
            
            context_parts.append("\n[EOD_STATS]\nDate|Close|Volume|30dAvgVol|30dLow|30dHigh|52wLow|52wHigh")
            context_parts.append(f"{latest.trade_date.strftime('%Y-%m-%d')}|{latest.close:,.0f}|{latest.volume}|{int(avg_vol_30)}|{low_30:,.0f}|{high_30:,.0f}|{low_52w:,.0f}|{high_52w:,.0f}")
            
            # --- Technical Analysis (RSI, MACD) ---
            if latest.rsi is not None and latest.macd is not None:
                context_parts.append("\n[TECHNICAL_INDICATORS (Daily)]\nRSI(14)|MACD_Line(12,26)|MACD_Signal(9)|MACD_Hist")
                context_parts.append(f"{latest.rsi:.2f}|{latest.macd:.2f}|{latest.macd_signal:.2f}|{latest.macd_hist:.2f}")

        # 4. Recent News (Last 30 days) - TICKER SPECIFIC
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        news_stmt = text("""
            SELECT title, description, ai_summary, published_at, domain, is_summarized
            FROM news_articles
            WHERE published_at >= :d
            AND (description ILIKE :t OR title ILIKE :t OR ai_summary ILIKE :t)
            ORDER BY published_at DESC LIMIT 10
        """)
        search_term = f"%{ticker}%"
        news_res = await session.execute(news_stmt, {"d": thirty_days_ago, "t": search_term})
        articles = news_res.fetchall()
        context_parts.append("\n[TICKER_NEWS_30D]\\nDate|Domain|Title|Summary")
        if articles:
            for a in articles:
                date_str = a.published_at.strftime('%Y-%m-%d')
                content_preview = a.ai_summary if a.is_summarized and a.ai_summary else str(a.description or "")[:200]
                content_preview = content_preview.replace('\n', ' ')
                context_parts.append(f"{date_str}|{a.domain}|{a.title}|{content_preview}")
        else:
            context_parts.append("-|NONE|No highly relevant news found|N/A")
        
        # 4b. GLOBAL / MACRO News (Last 7 days) - 5 articles per domain PER DAY for deep coverage
        # This ensures we don't miss major events across different fields over the week.
        seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
        global_news_stmt = text("""
            SELECT title, ai_summary, published_at, domain, is_summarized FROM (
                SELECT title, ai_summary, published_at, domain, is_summarized,
                       ROW_NUMBER() OVER (PARTITION BY domain, published_at::date ORDER BY published_at DESC) as rn
                FROM news_articles
                WHERE published_at >= :d
            ) ranked WHERE rn <= 5
            ORDER BY published_at DESC
        """)
        global_news_res = await session.execute(global_news_stmt, {"d": seven_days_ago})
        global_articles = global_news_res.fetchall()
        context_parts.append("\n[GLOBAL_MACRO_NEWS_7D] (5 articles per field/category per day - Deep Context)\nDate|Domain|Title|Summary")
        if global_articles:
            for a in global_articles:
                date_str = a.published_at.strftime('%Y-%m-%d')
                content_preview = a.ai_summary if a.is_summarized and a.ai_summary else str(a.title or "")[:200]
                content_preview = content_preview.replace('\n', ' ')
                context_parts.append(f"{date_str}|{a.domain}|{a.title}|{content_preview}")
        else:
            context_parts.append("-|NONE|No recent global news available|N/A")


        
        # 4c. Latest headlines (most recent 5, any domain) for breaking news
        latest_news_stmt = text("""
            SELECT title, ai_summary, published_at, domain, is_summarized
            FROM news_articles
            WHERE published_at >= :d
            ORDER BY published_at DESC LIMIT 5
        """)
        latest_news_res = await session.execute(latest_news_stmt, {"d": seven_days_ago})
        latest_articles = latest_news_res.fetchall()
        context_parts.append("\n[BREAKING_NEWS] (Most recent headlines)\nDate|Domain|Title|Summary")
        if latest_articles:
            for a in latest_articles:
                date_str = a.published_at.strftime('%Y-%m-%d')
                content_preview = a.ai_summary if a.is_summarized and a.ai_summary else str(a.title or "")[:200]
                content_preview = content_preview.replace('\n', ' ')
                context_parts.append(f"{date_str}|{a.domain}|{a.title}|{content_preview}")
            
        # 5. Macro, FX, Commodities & Indices
        context_parts.append("\n[MARKET_CONTEXT]\\nIndicator|Value|Date")
        
        # Macro
        macro_stmt = text("SELECT name, value, report_date FROM macro_indicators ORDER BY report_date DESC LIMIT 5")
        macro_res = await session.execute(macro_stmt)
        for m in macro_res.fetchall():
            context_parts.append(f"{m.name}|{m.value}|{m.report_date}")
            
        # Commodities (Gold, Oil, FX)
        cmd_stmt = text("""
            SELECT DISTINCT ON (symbol) symbol, price, price_date 
            FROM commodity_prices 
            ORDER BY symbol, price_date DESC
        """)
        cmd_res = await session.execute(cmd_stmt)
        for c in cmd_res.fetchall():
            if c.symbol in ['SJC', 'USDVND', 'WTI', 'BRENT']:
                context_parts.append(f"{c.symbol}|{c.price}|{c.price_date.strftime('%Y-%m-%d')}")
                
        # Indices (VNINDEX PE + 5-day trend)
        idx_stmt = text("SELECT index_code, pe, trade_date FROM market_index_stats WHERE index_code = 'VNINDEX' ORDER BY trade_date DESC LIMIT 1")
        idx_res = await session.execute(idx_stmt)
        idx = idx_res.fetchone()
        if idx:
            context_parts.append(f"{idx.index_code}_PE|{idx.pe}|{idx.trade_date.strftime('%Y-%m-%d')}")
        
        # VNINDEX 10-session trend (2 weeks, to detect market-wide selloff vs stock-specific)
        vnindex_trend_stmt = text("""
            SELECT trade_date, close, volume
            FROM stock_eod
            WHERE ticker = 'VNINDEX'
            ORDER BY trade_date DESC LIMIT 10
        """)
        vnindex_res = await session.execute(vnindex_trend_stmt)
        vnindex_data = vnindex_res.fetchall()
        if vnindex_data:
            context_parts.append("\n[VNINDEX_10D_TREND] (2-week market trend to determine if selloff is market-wide or stock-specific)\nDate|Close|Volume")
            for v in vnindex_data:
                context_parts.append(f"{v.trade_date.strftime('%Y-%m-%d')}|{v.close:,.0f}|{v.volume}")
        
        # 6. Sector Peer Performance (same industry, last session)
        if p and p.industry:
            sector_stmt = text("""
                SELECT cp.ticker, cp.company_name, se.close, se.rsi, se.trade_date
                FROM company_profiles cp
                JOIN stock_eod se ON cp.ticker = se.ticker
                WHERE cp.industry = :ind AND cp.ticker != :t
                AND se.trade_date = (SELECT MAX(trade_date) FROM stock_eod WHERE ticker = :t)
                ORDER BY cp.market_cap DESC NULLS LAST
                LIMIT 5
            """)
            sector_res = await session.execute(sector_stmt, {"ind": p.industry, "t": ticker})
            sector_peers = sector_res.fetchall()
            if sector_peers:
                context_parts.append(f"\n[SECTOR_PEERS] (Same industry: {p.industry} — compare to detect sector-wide vs stock-specific trend)\nTicker|Name|Close|RSI|Date")
                for sp in sector_peers:
                    rsi_val = f"{sp.rsi:.1f}" if sp.rsi else "N/A"
                    context_parts.append(f"{sp.ticker}|{sp.company_name}|{sp.close:,.0f}|{rsi_val}|{sp.trade_date.strftime('%Y-%m-%d')}")


    full_context = "\n".join(context_parts)
    logger.info(f"Generated {len(full_context)} characters of TOON context for {ticker}.")
    
    # Update the graph state
    return {"context": full_context}
