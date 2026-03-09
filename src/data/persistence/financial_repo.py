"""
Repository for financial data persistence.
"""

import logging
import math
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy import select, update, delete, func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.finance import (
    Company, FinancialReport, StockEOD,
    MarketIndexStats, MacroIndicator, MutualFundNav, CommodityPrice,
    StockTradingStats
)

logger = logging.getLogger(__name__)

def clean_nan_recursive(obj):
    """Recursively removes NaN (float or string) from nested dictionaries and lists for JSONB compatibility."""
    if isinstance(obj, dict):
        return {k: clean_nan_recursive(v) for k, v in obj.items() if not (isinstance(v, float) and math.isnan(v)) and not (isinstance(v, str) and v.lower() == 'nan')}
    elif isinstance(obj, list):
        return [clean_nan_recursive(item) for item in obj]
    elif isinstance(obj, float) and math.isnan(obj):
        return None
    elif isinstance(obj, str) and obj.lower() == 'nan':
        return None
    return obj


class FinancialRepository:
    """
    Handles persistence of company profiles, financial reports, and EOD data.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    def _parse_float(self, val: Any) -> Optional[float]:
        """Safely parses a value from string (with commas) or numbers to float."""
        if val is None:
            return None
        if isinstance(val, (int, float)):
            return float(val)
        if isinstance(val, str):
            # Remove any commas or thousands separators
            clean_str = val.replace(',', '').strip()
            if not clean_str:
                return None
            try:
                return float(clean_str)
            except ValueError:
                logger.warning(f"Could not parse float from string: {val}")
                return None
        return None

    def _ensure_datetime(self, val: Any) -> Optional[datetime]:
        """Ensures a value is a timezone-aware datetime."""
        if val is None:
            return None
        
        # Handle decimal/float timestamps (MSN often returns these)
        if isinstance(val, (int, float)):
            import math
            if math.isnan(val):
                return None
            # Check if it's too big for seconds (likely milliseconds)
            if val > 1e11:
                val = val / 1000.0
            val = datetime.fromtimestamp(val)
        
        if isinstance(val, str):
            try:
                val = datetime.fromisoformat(val)
            except ValueError:
                # Try simple date parsing if ISO fails
                try:
                    val = datetime.strptime(val, "%Y-%m-%d")
                except ValueError:
                    logger.warning(f"Could not parse date string: {val}")
                    return None
        
        from datetime import date as dt_date
        if isinstance(val, dt_date) and not isinstance(val, datetime):
            val = datetime.combine(val, datetime.min.time())
        
        if isinstance(val, datetime):
            import pytz
            if val.tzinfo is None:
                val = pytz.UTC.localize(val)
            return val
        
        return None

    async def upsert_company(self, profile: Dict[str, Any]) -> Optional[Company]:
        """
        Upserts a company profile.
        """
        ticker = profile.get('symbol')  # vnstock v3 uses 'symbol'
        if not ticker:
            logger.error("Cannot upsert company without symbol/ticker")
            return None

        # Prepare values for upsert
        values = {
            "ticker": ticker,
            "company_name": profile.get("company_profile"), # Detailed profile
            "short_name": profile.get("shortName"),
            "industry": profile.get("icb_name3"), # Level 3 industry
            "sector": profile.get("icb_name2"), # Level 2 sector
            "market_cap": profile.get("charter_capital"),
            "shareholders": profile.get("shareholders"),
            "officers": profile.get("officers"),
        }

        # Filter out None values and NaNs to avoid overwriting with nulls if field is missing
        clean_values = {}
        for k, v in values.items():
            if v is None:
                continue
            v_cleaned = clean_nan_recursive(v)
            if v_cleaned is None:
                continue
            clean_values[k] = v_cleaned

        stmt = insert(Company).values(**clean_values)
        
        update_dict = {k: v for k, v in clean_values.items() if k != 'ticker'}
        if not update_dict:
            # If nothing else to update (e.g., this is a blank stub), just bump the timestamp
            from sqlalchemy.sql import func
            update_dict = {"last_updated": func.now()}
            
        on_conflict_stmt = stmt.on_conflict_do_update(
            index_elements=['ticker'],
            set_=update_dict
        ).returning(Company)

        try:
            result = await self.session.execute(on_conflict_stmt)
            company = result.scalar_one()
            await self.session.commit()
            return company
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error upserting company {ticker}: {e}", exc_info=True)
            return None

    async def upsert_financial_reports(
        self, 
        ticker: str, 
        report_type: str, 
        period: str, 
        reports: List[Dict[str, Any]]
    ) -> int:
        """
        Upserts a list of financial reports for a ticker.
        Returns the number of reports upserted.
        """
        if not reports:
            return 0

        upserted_count = 0
        for report_data in reports:
            # Extract year and quarter/length
            year = report_data.get('yearReport')
            # Use 0 as default for yearly reports to ensure UniqueConstraint works
            quarter = report_data.get('lengthReport', 0) if period == "quarter" else 0

            if year is None:
                logger.warning(f"Skipping report for {ticker} due to missing yearReport")
                continue

            clean_data = clean_nan_recursive(report_data)

            values = {
                "ticker": ticker,
                "report_type": report_type,
                "period": period,
                "year": year,
                "quarter": quarter,
                "data": clean_data
            }

            stmt = insert(FinancialReport).values(**values)
            on_conflict_stmt = stmt.on_conflict_do_update(
                constraint='uix_ticker_period_year_type',
                set_={"data": clean_data}
            )

            try:
                await self.session.execute(on_conflict_stmt)
                upserted_count += 1
            except Exception as e:
                logger.error(f"Error upserting report for {ticker} {year} {quarter}: {e}")
                continue
        
        try:
            await self.session.commit()
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to commit financial reports for {ticker}: {e}")
            return 0
            
        return upserted_count

    async def touch_company_last_updated(self, ticker: str) -> None:
        """Touch the company's last_updated timestamp without changing any other data.
        Used to mark a ticker as 'recently attempted' when the API returns empty data,
        preventing pointless retries on every single run.
        """
        try:
            from sqlalchemy import update
            stmt = (
                update(Company)
                .where(Company.ticker == ticker)
                .values(last_updated=func.now())
            )
            await self.session.execute(stmt)
            await self.session.commit()
        except Exception as e:
            logger.warning(f"Failed to touch last_updated for {ticker}: {e}")

    async def upsert_eod_records(
        self,
        ticker: str,
        records: List[Dict[str, Any]]
    ) -> int:
        """
        Upserts a list of EOD OHLCV records for a ticker.
        Returns the number of records upserted.
        """
        if not records:
            return 0

        upserted_count = 0
        for row in records:
            # Parse the trade_date from the 'time' column
            trade_date = row.get('time')
            if trade_date is None:
                logger.warning(f"Skipping EOD record for {ticker} due to missing 'time'")
                continue

            # Ensure trade_date is a datetime object and localized
            if isinstance(trade_date, str):
                trade_date = datetime.fromisoformat(trade_date)
            
            if trade_date.tzinfo is None:
                # Assuming vnstock returns local time or UTC naive, localizing to UTC
                import pytz
                trade_date = pytz.UTC.localize(trade_date)

            values = {
                "ticker": ticker,
                "trade_date": trade_date,
                "open": row.get("open", 0),
                "high": row.get("high", 0),
                "low": row.get("low", 0),
                "close": row.get("close", 0),
                "volume": int(row.get("volume", 0)),
            }

            stmt = insert(StockEOD).values(**values)
            on_conflict_stmt = stmt.on_conflict_do_update(
                constraint='uix_ticker_trade_date',
                set_={
                    "open": values["open"],
                    "high": values["high"],
                    "low": values["low"],
                    "close": values["close"],
                    "volume": values["volume"],
                }
            )

            try:
                await self.session.execute(on_conflict_stmt)
                upserted_count += 1
            except Exception as e:
                logger.error(f"Error upserting EOD for {ticker} {trade_date}: {e}")
                continue
        
        try:
            await self.session.commit()
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to commit EOD records for {ticker}: {e}")
            return 0

        return upserted_count

    async def get_latest_eod_date(self, ticker: str) -> Optional[datetime]:
        """
        Returns the latest trade_date for a ticker in stock_eod.
        Used for incremental sync to avoid re-fetching old data.
        """
        stmt = select(StockEOD.trade_date).where(
            StockEOD.ticker == ticker
        ).order_by(StockEOD.trade_date.desc()).limit(1)
        result = await self.session.execute(stmt)
        row = result.scalar_one_or_none()
        return row

    async def get_all_latest_eod_dates(self) -> Dict[str, datetime]:
        """Returns the latest trade_date for all tickers for bulk checking."""
        from sqlalchemy import func
        stmt = select(StockEOD.ticker, func.max(StockEOD.trade_date)).group_by(StockEOD.ticker)
        result = await self.session.execute(stmt)
        return {row[0]: row[1] for row in result.all() if row[1] is not None}

    async def get_all_companies_last_updated(self) -> Dict[str, datetime]:
        """Returns the last_updated time for all companies for bulk checking."""
        stmt = select(Company.ticker, Company.last_updated)
        result = await self.session.execute(stmt)
        return {row[0]: row[1] for row in result.all() if row[1] is not None}

    async def get_company(self, ticker: str) -> Optional[Company]:
        """Fetch company by ticker."""
        stmt = select(Company).where(Company.ticker == ticker)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_latest_commodity_date(self, symbol: str) -> Optional[datetime]:
        """Returns the latest price_date for a commodity symbol."""
        stmt = select(CommodityPrice.price_date).where(
            CommodityPrice.symbol == symbol
        ).order_by(CommodityPrice.price_date.desc()).limit(1)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_latest_index_date(self, index_code: str) -> Optional[datetime]:
        """Returns the latest trade_date for a market index."""
        stmt = select(MarketIndexStats.trade_date).where(
            MarketIndexStats.index_code == index_code
        ).order_by(MarketIndexStats.trade_date.desc()).limit(1)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert_market_index_stats(self, records: List[Dict[str, Any]]) -> int:
        """Upserts market index statistics."""
        if not records:
            return 0
        upserted_count = 0
        for row in records:
            trade_date = self._ensure_datetime(row.get('time'))
            if not trade_date: continue

            values = {
                "index_code": row.get("index_code"),
                "trade_date": trade_date,
                "pe": row.get("pe"),
                "pb": row.get("pb"),
                "dividend_yield": row.get("dividend_yield"),
                "market_cap": row.get("market_cap"),
            }
            stmt = insert(MarketIndexStats).values(**values)
            on_conflict_stmt = stmt.on_conflict_do_update(
                constraint='uix_index_trade_date',
                set_={k: v for k, v in values.items() if k not in ['index_code', 'trade_date']}
            )
            try:
                await self.session.execute(on_conflict_stmt)
                upserted_count += 1
            except Exception as e:
                logger.error(f"Error upserting index stats {values['index_code']} {trade_date}: {e}")
        
        await self.session.commit()
        return upserted_count

    async def upsert_macro_indicators(self, records: List[Dict[str, Any]]) -> int:
        """Upserts macroeconomic indicators."""
        if not records: return 0
        upserted_count = 0
        for row in records:
            report_date = self._ensure_datetime(row.get('time'))
            if not report_date: continue

            values = {
                "name": row.get("name"),
                "report_date": report_date,
                "value": self._parse_float(row.get("value")),
                "unit": row.get("unit"),
            }
            # Skip invalid values
            if values["value"] is None:
                continue

            stmt = insert(MacroIndicator).values(**values)
            on_conflict_stmt = stmt.on_conflict_do_update(
                constraint='uix_macro_indicator_date',
                set_={"value": values["value"], "unit": values["unit"]}
            )
            try:
                await self.session.execute(on_conflict_stmt)
                upserted_count += 1
            except Exception as e:
                logger.error(f"Error upserting macro {values['name']} {report_date}: {e}")
        
        await self.session.commit()
        return upserted_count

    async def upsert_fund_nav(self, records: List[Dict[str, Any]]) -> int:
        """Upserts mutual fund NAV records."""
        if not records: return 0
        upserted_count = 0
        for row in records:
            nav_date = self._ensure_datetime(row.get('time'))
            if not nav_date: continue

            values = {
                "fund_code": row.get("fund_code"),
                "nav_date": nav_date,
                "nav": self._parse_float(row.get("nav")),
                "source": row.get("source", "FMARKET"),
            }
            # Skip invalid NAV
            if values["nav"] is None:
                continue

            stmt = insert(MutualFundNav).values(**values)
            on_conflict_stmt = stmt.on_conflict_do_update(
                constraint='uix_fund_nav_date',
                set_={"nav": values["nav"]}
            )
            try:
                await self.session.execute(on_conflict_stmt)
                upserted_count += 1
            except Exception as e:
                logger.error(f"Error upserting fund NAV {values['fund_code']} {nav_date}: {e}")
        
        await self.session.commit()
        return upserted_count

    async def upsert_commodity_prices(self, records: List[Dict[str, Any]]) -> int:
        """Upserts commodity or FX prices."""
        if not records: return 0
        upserted_count = 0
        for row in records:
            price_date = self._ensure_datetime(row.get('time'))
            if not price_date: continue

            values = {
                "symbol": row.get("symbol"),
                "price_date": price_date,
                "price": self._parse_float(row.get("price")),
                "currency": row.get("currency", "VND"),
            }
            # Skip invalid prices
            if values["price"] is None:
                continue

            stmt = insert(CommodityPrice).values(**values)
            on_conflict_stmt = stmt.on_conflict_do_update(
                constraint='uix_commodity_price_date',
                set_={"price": values["price"], "currency": values["currency"]}
            )
            try:
                await self.session.execute(on_conflict_stmt)
                upserted_count += 1
            except Exception as e:
                logger.error(f"Error upserting commodity {values['symbol']} {price_date}: {e}")
        
        await self.session.commit()
        return upserted_count

    async def upsert_stock_trading_stats(self, records: List[Dict[str, Any]]) -> int:
        """Upserts stock trading statistics (bid/ask)."""
        if not records: return 0
        upserted_count = 0
        for row in records:
            trade_date = self._ensure_datetime(row.get('trade_date'))
            if not trade_date: continue

            values = {
                "ticker": row.get("ticker"),
                "trade_date": trade_date,
                "total_buy_vol": row.get("total_buy_vol"),
                "total_sell_vol": row.get("total_sell_vol"),
                "buy_count": row.get("buy_count"),
                "sell_count": row.get("sell_count"),
            }
            stmt = insert(StockTradingStats).values(**values)
            on_conflict_stmt = stmt.on_conflict_do_update(
                constraint='uix_ticker_trading_stats_date',
                set_={k: v for k, v in values.items() if k not in ['ticker', 'trade_date']}
            )
            try:
                await self.session.execute(on_conflict_stmt)
                upserted_count += 1
            except Exception as e:
                logger.error(f"Error upserting trading stats {values['ticker']} {trade_date}: {e}")
        
        await self.session.commit()
        return upserted_count
