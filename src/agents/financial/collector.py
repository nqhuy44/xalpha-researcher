"""
Financial data collector agent.
Orchestrates vnstock fetching and repository persistence.
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from tqdm.asyncio import tqdm

from src.data.sources.vnstock_client import VnstockClient
from src.data.persistence.financial_repo import FinancialRepository
from src.db.session import async_session_factory as SessionLocal

logger = logging.getLogger(__name__)

# Default historical start date for initial EOD sync (10 years)
DEFAULT_EOD_START = "2015-01-01"


class FinancialCollector:
    """
    Orchestrates the lifecycle of financial data collection.
    """

    def __init__(self):
        self.vnstock = VnstockClient()

    async def sync_company(self, ticker: str) -> bool:
        """
        Syncs company profile data.
        """
        logger.debug(f"Syncing profile for {ticker}...")
        profile = await self.vnstock.get_company_profile(ticker)
        if not profile:
            logger.warning(f"Could not fetch profile for {ticker}. Saving blank stub to prevent continuous retries.")
            async with SessionLocal() as session:
                repo = FinancialRepository(session)
                stub = {"symbol": ticker}
                await repo.upsert_company(stub)
            return False

        # Enrich with shareholders and officers
        sh_df = await self.vnstock.get_company_shareholders(ticker)
        if sh_df is not None and not sh_df.empty:
            profile['shareholders'] = sh_df.to_dict('records')

        of_df = await self.vnstock.get_company_officers(ticker)
        if of_df is not None and not of_df.empty:
            profile['officers'] = of_df.to_dict('records')

        # Enrich with real-time valuations
        valuations = await self.vnstock.get_valuation_ratios(ticker)
        if valuations:
            profile['pe_ratio'] = valuations.get('P/E')
            profile['pb_ratio'] = valuations.get('P/B')
            profile['roe'] = valuations.get('ROE (%)')
            profile['roa'] = valuations.get('ROA (%)')
            profile['eps'] = valuations.get('EPS (VND)')
            profile['ev_ebitda'] = valuations.get('EV/EBITDA')

        async with SessionLocal() as session:
            repo = FinancialRepository(session)
            company = await repo.upsert_company(profile)
            return company is not None

    async def sync_financials(self, ticker: str, period: str = "quarter") -> int:
        """
        Syncs all available financial reports for a ticker.
        """
        report_types = ["BalanceSheet", "IncomeStatement", "CashFlow"]
        total_upserted = 0

        async with SessionLocal() as session:
            repo = FinancialRepository(session)
            
            for r_type in report_types:
                logger.debug(f"Syncing {r_type} ({period}) for {ticker}...")
                df = await self.vnstock.get_financial_report(ticker, period=period, report_type=r_type)
                
                if df is not None and not df.empty:
                    reports = df.to_dict('records')
                    count = await repo.upsert_financial_reports(ticker, r_type, period, reports)
                    logger.debug(f"Upserted {count} {r_type} records for {ticker}")
                    total_upserted += count
                else:
                    logger.warning(f"No {r_type} data found for {ticker}")

        return total_upserted

    async def sync_eod(self, ticker: str, is_bootstrap: bool = False, from_date: str = None) -> int:
        """
        Syncs EOD (end-of-day) OHLCV data for a ticker.
        
        Args:
            ticker: Stock symbol.
            is_bootstrap: If True, fetches 10 years of history for new tickers.
            from_date: If provided, skips the DB lookup and uses this as start_date directly.
                       This is set by sync_all_market which already did a bulk DB query.
        """
        end_date = datetime.now().strftime("%Y-%m-%d")
        
        if from_date:
            start_date = from_date
        else:
            # Standalone call (not from sync_all_market): query DB for latest date
            async with SessionLocal() as session:
                repo = FinancialRepository(session)
                latest_date = await repo.get_latest_eod_date(ticker)
                if latest_date:
                    start_date = (latest_date + timedelta(days=1)).strftime("%Y-%m-%d")
                elif is_bootstrap:
                    start_date = DEFAULT_EOD_START
                else:
                    start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

        if start_date > end_date:
            logger.info(f"EOD data for {ticker} is already up-to-date.")
            return 0

        logger.info(f"Syncing EOD for {ticker} from {start_date} to {end_date}...")
        df = await self.vnstock.get_eod_history(ticker, start=start_date, end=end_date)
        
        if df is not None and not df.empty:
            async with SessionLocal() as session:
                repo = FinancialRepository(session)
                
                import pandas as pd
                from sqlalchemy import select, desc
                from src.db.models.finance import StockEOD
                from src.agents.analyst.utils.technical import compute_rsi, compute_macd
                
                try:
                    hist_records = []
                    # For incremental sync, we need ~100 historical bars to warm up RSI/MACD logic.
                    if not is_bootstrap:
                        # Ensure start_date is a datetime object for comparison in SQL
                        from_date_dt = datetime.strptime(start_date, "%Y-%m-%d")
                        if from_date_dt.tzinfo is None:
                            import pytz
                            from_date_dt = pytz.UTC.localize(from_date_dt)

                        stmt = select(StockEOD.trade_date, StockEOD.close).where(
                            StockEOD.ticker == ticker,
                            StockEOD.trade_date < from_date_dt
                        ).order_by(desc(StockEOD.trade_date)).limit(100)
                        res = await session.execute(stmt)
                        for row in res.fetchall():
                            hist_records.append({"time": row[0], "close": row[1]})
                    
                    hist_df = pd.DataFrame(hist_records) if hist_records else pd.DataFrame(columns=['time', 'close'])
                    new_df = df[['time', 'close']].copy()
                    
                    # Combine and sort chronologically for rolling indicators
                    combined_df = pd.concat([hist_df, new_df], ignore_index=True)
                    combined_df['time'] = pd.to_datetime(combined_df['time'], utc=True)
                    combined_df = combined_df.sort_values('time').reset_index(drop=True)
                    
                    combined_df['rsi'] = compute_rsi(combined_df['close'])
                    macd_res = compute_macd(combined_df['close'])
                    combined_df = pd.concat([combined_df, macd_res], axis=1)
                    
                    df['time'] = pd.to_datetime(df['time'], utc=True)
                    # Merge technicals back to the original payload
                    df = pd.merge(df, combined_df[['time', 'rsi', 'MACD', 'MACD_Signal', 'MACD_Hist']], on='time', how='left')
                    df = df.rename(columns={'MACD': 'macd', 'MACD_Signal': 'macd_signal', 'MACD_Hist': 'macd_hist'})
                    
                    # Replace NaN with None for SQLAlchemy insertion
                    df = df.replace({pd.NA: None, float('nan'): None})
                except Exception as e:
                    logger.error(f"Failed to compute technicals during EOD sync for {ticker}: {e}")
                
                records = df.to_dict('records')
                count = await repo.upsert_eod_records(ticker, records)
                
                # Always touch last_updated so we don't retry illiquid stocks 
                # immediately if their latest trade date is still behind market date
                await repo.touch_company_last_updated(ticker)
                
                logger.info(f"Upserted {count} EOD records for {ticker}")
                return count
        else:
            # Touch company's last_updated so we don't retry this ticker
            # on every single run. It will be re-attempted after 1 day.
            async with SessionLocal() as session:
                repo = FinancialRepository(session)
                await repo.touch_company_last_updated(ticker)
            logger.warning(f"No EOD data returned for {ticker} (will skip for 1 day)")
            return 0

    async def sync_full_ticker(self, ticker: str, full_sync: bool = True, is_bootstrap: bool = False):
        """
        Performs a sync for a ticker.
        If full_sync is True: syncs profile + quarterly/yearly financials + EOD.
        If full_sync is False: syncs EOD data ONLY.
        """
        try:
            if full_sync:
                success = await self.sync_company(ticker)
                
                # If creating the company profile completely fails (e.g., dead stock),
                # stop the cascade to save API calls and avoid foreign key issues.
                if not success:
                    logger.debug(f"Halting sync for {ticker} because full profile could not be established.")
                    return
                    
                await self.sync_financials(ticker, period="quarter")
                await self.sync_financials(ticker, period="year")
            
            # EOD sync handles its own daily incremental logic
            await self.sync_eod(ticker, is_bootstrap=is_bootstrap)
            
        except Exception as e:
            logger.error(f"Failed to sync all data for {ticker}: {e}")

    async def _get_market_latest_date(self) -> str:
        """
        Fetches the latest available trading date from VNINDEX.
        Used as the benchmark: if a ticker's latest EOD >= this date, it's up-to-date.
        Handles weekends, holidays, and upstream API lag automatically.
        """
        import pandas as pd
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")
        
        try:
            df = await self.vnstock.get_index_history("VNINDEX", start=start_date)
            if df is not None and not df.empty:
                latest_date = pd.to_datetime(df['time'].max()).strftime("%Y-%m-%d")
                logger.info(f"Market benchmark date (VNINDEX): {latest_date}")
                return latest_date
        except Exception as e:
            logger.warning(f"Could not determine market latest date from VNINDEX: {e}")
            
        # Fallback: yesterday (conservative, avoids re-syncing on non-trading days)
        fallback = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        logger.info(f"Using fallback market date: {fallback}")
        return fallback

    async def sync_all_market(self, batch_size: int = 20, is_bootstrap: bool = False):
        """
        Syncs data for all active tickers on the market.
        Uses a single bulk DB query + market benchmark to determine which tickers truly need updates.
        Only makes API calls for genuinely outdated data.
        """
        tickers = await self.vnstock.get_all_tickers()
        if not tickers:
            logger.error("No tickers found to sync.")
            return

        from datetime import timezone
        from src.config.settings import settings
        safe_delay = settings.vnstock.req_delay

        logger.info(f"Loaded {len(tickers)} active tickers. Checking sync status...")
        
        # 1. Single bulk DB query for all sync metadata
        async with SessionLocal() as session:
            repo = FinancialRepository(session)
            latest_eods = await repo.get_all_latest_eod_dates()  # {ticker: max(trade_date)}
            companies_updated = await repo.get_all_companies_last_updated()  # {ticker: last_updated}
        
        # 2. Determine the REAL latest trading date from the market
        market_date = await self._get_market_latest_date()  # e.g. "2026-03-04"
        now_utc = datetime.now(timezone.utc)
        
        # 3. Categorize tickers: full_sync (profile+finance+eod), eod_only, or skip
        tickers_full_sync = []  # (ticker,)
        tickers_eod_only = []   # (ticker, from_date)
        skipped = 0
        
        for ticker in tickers:
            latest_info = companies_updated.get(ticker)
            latest_eod_info = latest_eods.get(ticker)
            
            last_updated = latest_info['last_updated'] if latest_info else None
            has_valuations = latest_info['has_valuations'] if latest_info else False
            
            # Profile/financials missing, stale (> 7 days), or missing crucial valuations (PE/EPS)
            if not last_updated or (now_utc - last_updated).days >= 7 or not has_valuations:
                tickers_full_sync.append(ticker)
                continue
            
            # Profile is fine. Check EOD freshness against the REAL market date.
            if latest_eod_info:
                latest_eod = latest_eod_info['trade_date']
                has_technicals = latest_eod_info['has_technicals']
                ticker_eod_str = latest_eod.strftime("%Y-%m-%d")
                
                # If missing technicals, we force a sync of at least the last 30 days 
                # to trigger the calculation logic in sync_eod.
                if not has_technicals:
                    from_date = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")
                    tickers_eod_only.append((ticker, from_date))
                    continue

                if ticker_eod_str >= market_date:
                    skipped += 1
                    continue  # Already has the latest candle. Skip entirely.
                    
                # Outdated: calculate exact start date for the gap
                from_date = (latest_eod + timedelta(days=1)).strftime("%Y-%m-%d")
                tickers_eod_only.append((ticker, from_date))
            else:
                # Has profile but zero EOD records (new/dead company).
                # Check if we already attempted recently — skip if last_updated < 1 day.
                if last_updated and (now_utc - last_updated).total_seconds() < 86400:
                    skipped += 1
                    continue  # Already tried recently, API returned nothing.
                if is_bootstrap:
                    tickers_eod_only.append((ticker, DEFAULT_EOD_START))
                else:
                    from_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
                    tickers_eod_only.append((ticker, from_date))
        
        total_work = len(tickers_full_sync) + len(tickers_eod_only)
        
        if total_work == 0:
            logger.info(f"All {len(tickers)} tickers are fully up-to-date (market date: {market_date}). Nothing to do!")
            return

        logger.info(f"Sync plan: {len(tickers_full_sync)} FULL + {len(tickers_eod_only)} EOD-only = {total_work} tickers to process. ({skipped} skipped as up-to-date)")
        
        # 4. Process FULL and EOD syncs in parallel with a Semaphore
        # Target: 120-150 RPM. With delay=1.2s (~0.8 RPS), concurrency=3 yields ~2.5 RPS (150 RPM).
        concurrency_limit = 3 
        sem = asyncio.Semaphore(concurrency_limit)

        async def sem_task(ticker_item, is_full=True):
            async with sem:
                if is_full:
                    await self.sync_full_ticker(ticker_item, full_sync=True, is_bootstrap=is_bootstrap)
                else:
                    ticker, from_date = ticker_item
                    await self.sync_eod(ticker, from_date=from_date)
                await asyncio.sleep(safe_delay)

        try:
            tasks = []
            if tickers_full_sync:
                logger.info(f"Starting parallel FULL sync for {len(tickers_full_sync)} tickers...")
                for ticker in tickers_full_sync:
                    tasks.append(sem_task(ticker, is_full=True))
            
            if tickers_eod_only:
                logger.info(f"Starting parallel EOD sync for {len(tickers_eod_only)} tickers...")
                for ticker_item in tickers_eod_only:
                    tasks.append(sem_task(ticker_item, is_full=False))
            
            if tasks:
                await tqdm.gather(*tasks, desc="Parallel Market Sync", unit="ticker")
        except SystemExit as se:
            logger.warning(f"Upstream Rate Limit triggered SystemExit: {se}")
            logger.info("Sync halted to avoid further bans. Application will continue after cooldown.")
            await asyncio.sleep(60)
        except Exception as e:
            logger.error(f"Unexpected error during market-wide sync: {e}")

        logger.info("Market-wide sync completed.")

    async def bootstrap_all_market(self):
        """
        Performs a deep historical sync (10 years) for the entire market.
        This is a heavy operation meant to be run once.
        """
        logger.info(">>> STARTING 10-YEAR MARKET BOOTSTRAP <<<")
        # 1. Sync all company profiles & EOD history
        await self.sync_all_market(batch_size=10, is_bootstrap=True)
        
        # 2. Sync all market intelligence history
        logger.info("Bootstrapping market intelligence history...")
        await self.sync_market_intelligence()
        
        logger.info(">>> 10-YEAR MARKET BOOTSTRAP COMPLETED <<<")

    # --- Phase 4: Market Intelligence ---

    async def sync_funds(self) -> int:
        """Syncs mutual fund data from FMarket."""
        logger.info("Syncing mutual funds from FMarket...")
        df = await self.vnstock.get_fund_listing()
        if df is not None and not df.empty:
            records = []
            now = datetime.now()
            for _, row in df.iterrows():
                records.append({
                    'fund_code': row.get('short_name'),
                    'nav': row.get('nav'),
                    'time': now,
                    'source': 'FMARKET'
                })
            
            async with SessionLocal() as session:
                repo = FinancialRepository(session)
                count = await repo.upsert_fund_nav(records)
                logger.info(f"Upserted {count} mutual fund NAV records.")
                return count
        return 0

    async def sync_commodities(self) -> int:
        """Syncs gold, global commodities, and FX data."""
        logger.info("Syncing commodities and FX rates...")
        total = 0
        async with SessionLocal() as session:
            repo = FinancialRepository(session)
            
            # 1. Domestic Gold (VCI/Misc fallback)
            gold_df = await self.vnstock.get_gold_history()
            if gold_df is not None and not gold_df.empty:
                records = []
                for _, row in gold_df.iterrows():
                    records.append({
                        'symbol': f"GOLD_{row.get('branch', 'SJC')}",
                        'price': row.get('buy_price'),
                        'time': row.get('date'),
                        'currency': 'VND'
                    })
                total += await repo.upsert_commodity_prices(records)

            # 2. FX Rates (VCI/VCB fallback)
            fx_df = await self.vnstock.get_exchange_rate_history()
            if fx_df is not None and not fx_df.empty:
                records = []
                for _, row in fx_df.iterrows():
                    records.append({
                        'symbol': row.get('currency_code'),
                        'price': row.get('sell'),
                        'time': row.get('date'),
                        'currency': 'VND'
                    })
                total += await repo.upsert_commodity_prices(records)

            # 3. Global Commodities (MSN Fallback)
            commodities = {
                'CL.1': 'CRUDE_OIL_WTI',
                'BZ.1': 'BRENT_OIL',
                'NG.1': 'NATURAL_GAS',
                'GC.1': 'GOLD_WORLD'
            }
            from datetime import timedelta
            today_str = datetime.now().strftime("%Y-%m-%d")

            for sym, name in commodities.items():
                latest_date = await repo.get_latest_commodity_date(name)
                if latest_date:
                    start_date = (latest_date + timedelta(days=1)).strftime("%Y-%m-%d")
                    if start_date > today_str:
                        continue
                else:
                    start_date = "2015-01-01"

                df = await self.vnstock.get_commodity_history(sym, start=start_date)
                if df is not None and not df.empty:
                    import pandas as pd
                    records = []
                    for _, row in df.iterrows():
                        price = row.get('close')
                        if pd.isna(price): continue
                        
                        records.append({
                            'symbol': name,
                            'price': price,
                            'time': row.get('time'),
                            'currency': 'USD'
                        })
                    total += await repo.upsert_commodity_prices(records)
        
        logger.info(f"Commodity/FX sync completed. Total records: {total}")
        return total

    async def sync_stock_stats(self, ticker: str) -> int:
        """Syncs bid/ask and order flow statistics."""
        logger.info(f"Syncing trading stats for {ticker}...")
        try:
            bids, asks = await self.vnstock.get_stock_trading_stats(ticker)
            
            record = {
                'ticker': ticker,
                'trade_date': datetime.now(),
                'total_buy_vol': 0,
                'total_sell_vol': 0,
                'buy_count': 0,
                'sell_count': 0
            }
            
            if bids is not None and not bids.empty:
                record['total_buy_vol'] = int(bids['total_vol'].sum())
                record['buy_count'] = int(len(bids))
            
            if asks is not None and not asks.empty:
                record['total_sell_vol'] = int(asks['total_vol'].sum())
                record['sell_count'] = int(len(asks))
            
            async with SessionLocal() as session:
                repo = FinancialRepository(session)
                count = await repo.upsert_stock_trading_stats([record])
                logger.info(f"Upserted trading stats for {ticker}.")
                return count
        except Exception as e:
            logger.warning(f"Failed to sync trading stats for {ticker}: {e}")
            return 0

    async def sync_market_intelligence(self):
        """Unified sync for Phase 4 market data."""
        logger.info(">>> Starting Phase 4: Market Intelligence Sync <<<")
        try:
            await self.sync_funds()
            await self.sync_commodities()
            
            # Index stats (VNINDEX, VN30)
            async with SessionLocal() as session:
                repo = FinancialRepository(session)
                
                from datetime import timedelta
                today_str = datetime.now().strftime("%Y-%m-%d")
                
                for index in ["VNINDEX", "VN30"]:
                    logger.info(f"Syncing index history for {index}...")
                    
                    latest_date = await repo.get_latest_index_date(index)
                    if latest_date:
                        start_date = (latest_date + timedelta(days=1)).strftime("%Y-%m-%d")
                        if start_date > today_str:
                            logger.info(f"Index {index} is already up-to-date.")
                            continue
                    else:
                        start_date = "2015-01-01"
                        
                    df = await self.vnstock.get_index_history(index, start=start_date)
                    if df is not None and not df.empty:
                        records = []
                        for _, row in df.iterrows():
                            records.append({
                                'index_code': index,
                                'time': row.get('time') or row.get('date'),
                                'market_cap': row.get('volume'), # Fallback
                                'pe': row.get('pe'),
                                'pb': row.get('pb')
                            })
                        count = await repo.upsert_market_index_stats(records)
                        logger.info(f"Upserted {count} index stats for {index}.")
        except Exception as e:
            logger.error(f"Error during market intelligence sync: {e}")
        logger.info(">>> Market Intelligence Sync Finished <<<")


if __name__ == "__main__":
    # Quick manual trigger script for testing
    import sys
    
    async def main():
        ticker = sys.argv[1] if len(sys.argv) > 1 else "FPT"
        collector = FinancialCollector()
        logger.info(f"Starting manual sync for {ticker}")
        await collector.sync_full_ticker(ticker)
        logger.info(f"Sync for {ticker} completed.")

    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
