import asyncio
import logging
import time
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
import pandas as pd
import vnstock
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from requests.exceptions import RequestException
from src.config.settings import settings

logger = logging.getLogger(__name__)

def return_none_on_error(retry_state):
    exception = retry_state.outcome.exception()
    
    # Do not log tracebacks for KeyError/ValueError which indicate data absence, just log as warning
    if isinstance(exception, (KeyError, ValueError, TypeError)):
        logger.debug(f"Data not found/parseable inside vnstock: {exception}")
    else:
        logger.warning(f"Exhausted retries in vnstock API call (Network/Transient): {exception}")
        
    return None

# We ONLY retry if the exception is one of the network/transient types
# If it's a KeyError, ValueError etc, it will fail immediately and the retry_error_callback captures it
TRANSIENT_ERRORS = (RequestException, ConnectionError, TimeoutError)

vnstock_retry = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(TRANSIENT_ERRORS),
    retry_error_callback=return_none_on_error,
    reraise=False
)
class VnstockClient:
    """
    Centralized wrapper for the vnstock library.
    Handles Bronze API Key initialization and standardizes data extraction logic.
    """
    
    def __init__(self):
        """Initialize the client and set the API key if configured."""
        self._initialize_api_key()

    def _initialize_api_key(self):
        """Initializes the vnstock API key if provided in settings."""
        api_key = settings.vnstock.api_key
        if api_key and api_key.strip():
            try:
                success = vnstock.change_api_key(api_key.strip())
                if success:
                    logger.info("Successfully configured vnstock Bronze API Key.")
                else:
                    logger.warning("vnstock.change_api_key returned False. Key might be invalid.")
            except Exception as e:
                logger.error(f"Failed to set vnstock API key: {e}", exc_info=True)
        else:
            logger.info("No VNSTOCK__API_KEY found in config. Running vnstock in Guest mode.")

    @vnstock_retry
    async def get_company_profile(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetches the company profile for a given ticker symbol."""
        try:
            df = vnstock.Company("VCI", symbol).overview()
            await asyncio.sleep(settings.vnstock.req_delay)
            if df is not None and not df.empty:
                return df.to_dict('records')[0]
        except Exception as e:
            logger.debug(f"Data missing/malformed inside vnstock for {symbol}: {e}")
            
        if settings.vnstock.req_delay > 0:
            await asyncio.sleep(settings.vnstock.req_delay)
        logger.warning(f"No profile data returned for {symbol}")
        return None

    @vnstock_retry
    async def get_company_shareholders(self, symbol: str) -> Optional[pd.DataFrame]:
        """Fetches the major shareholders for a given ticker."""
        try:
            res = vnstock.Company("VCI", symbol).shareholders()
            await asyncio.sleep(settings.vnstock.req_delay)
            return res
        except Exception as e:
            logger.debug(f"Shareholders missing/malformed for {symbol}: {e}")
            await asyncio.sleep(settings.vnstock.req_delay)
            return None

    @vnstock_retry
    async def get_company_officers(self, symbol: str) -> Optional[pd.DataFrame]:
        """Fetches the officers/management for a given ticker."""
        try:
            res = vnstock.Company("VCI", symbol).officers()
            await asyncio.sleep(settings.vnstock.req_delay)
            return res
        except Exception as e:
            logger.debug(f"Officers missing/malformed for {symbol}: {e}")
            await asyncio.sleep(settings.vnstock.req_delay)
            return None

    @vnstock_retry
    async def get_financial_report(
        self, 
        symbol: str, 
        period: str = "quarter", 
        report_type: str = "BalanceSheet"
    ) -> Optional[pd.DataFrame]:
        """Fetches financial reports (BalanceSheet, IncomeStatement, CashFlow)."""
        try:
            finance = vnstock.Finance("VCI", symbol, period)
            if report_type == "BalanceSheet":
                res = finance.balance_sheet()
            elif report_type == "IncomeStatement":
                res = finance.income_statement()
            elif report_type == "CashFlow":
                res = finance.cash_flow()
            else:
                logger.error(f"Unknown report type: {report_type}")
                return None
            
            await asyncio.sleep(settings.vnstock.req_delay)
            return res
        except Exception as e:
            logger.debug(f"Financial report {report_type} missing/malformed for {symbol}: {e}")
            await asyncio.sleep(settings.vnstock.req_delay)
            return None

    @vnstock_retry
    async def get_valuation_ratios(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Fetches current valuation ratios (P/E, P/B, EPS, ROE, etc.) from VCI.
        Returns a dictionary mapping the metric name to its value for the latest quarter.
        """
        try:
            fin = vnstock.Finance("VCI", symbol, "quarter")
            ratio_df = fin.ratio()
            await asyncio.sleep(settings.vnstock.req_delay)
            
            if ratio_df is not None and not ratio_df.empty:
                # Latest quarter is the first row
                latest_row = ratio_df.iloc[0]
                
                # The columns are MultiIndex, we flatten them by taking the second level.
                # Example: ('Chỉ tiêu định giá', 'P/E') -> 'P/E'
                flat_dict = {}
                for col_tuple, val in latest_row.items():
                    if isinstance(col_tuple, tuple) and len(col_tuple) == 2:
                        group, metric = col_tuple
                        flat_dict[metric] = val
                    else:
                        flat_dict[col_tuple] = val
                        
                return flat_dict
        except Exception as e:
            logger.debug(f"Valuation ratios missing/malformed for {symbol}: {e}")
            await asyncio.sleep(settings.vnstock.req_delay)
            return None
        return None

    @vnstock_retry
    async def get_eod_history(
        self, 
        symbol: str, 
        start: str, 
        end: str
    ) -> Optional[pd.DataFrame]:
        """Fetches end-of-day historical OHLCV data."""
        try:
            quote = vnstock.Quote("VCI", symbol)
            res = quote.history(start=start, end=end, interval="1D")
            await asyncio.sleep(settings.vnstock.req_delay)
            if res is not None and not res.empty:
                return res
        except Exception as e:
            logger.debug(f"EOD history missing/malformed for {symbol}: {e}")
            await asyncio.sleep(settings.vnstock.req_delay)
            return None
            
        logger.warning(f"No EOD data returned for {symbol} ({start} to {end})")
        return None

    @vnstock_retry
    async def get_stock_trading_stats(self, symbol: str) -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame]]:
        """Fetches bid/ask and order flow statistics."""
        try:
            t = vnstock.Trading(source="VCI", symbol=symbol)
            bids, asks = t.side_stats()
            await asyncio.sleep(settings.vnstock.req_delay)
            return bids, asks
        except Exception as e:
            logger.debug(f"Trading stats missing/malformed for {symbol}: {e}")
            await asyncio.sleep(settings.vnstock.req_delay)
            return None, None

    async def get_all_tickers(self) -> List[str]:
        """
        Fetches active stock ticker symbols on HSX and HNX markets.
        Filtering out UPCOM, CW, ETF, and UNIT_TRUST to get exactly ~700 premium/midcap stocks.
        """
        try:
            lst = vnstock.Listing("VCI")
            await asyncio.sleep(settings.vnstock.req_delay)
            df = lst.symbols_by_exchange()
            await asyncio.sleep(settings.vnstock.req_delay)
            
            if df is not None and not df.empty:
                df_filtered = df[(df['exchange'].isin(['HSX', 'HNX'])) & (df['type'] == 'STOCK')]
                tickers = df_filtered['symbol'].tolist()
                
                # Remove duplicates just in case, sort alphabetically
                unique_tickers = sorted(list(set(tickers)))
                
                if unique_tickers:
                    logger.info(f"Loaded {len(unique_tickers)} premium tickers (HSX + HNX stocks)")
                    return unique_tickers
                
        except Exception as e:
            logger.error(f"Error fetching ticker list: {e}", exc_info=True)
        return []

    # --- Phase 4: Extended Market Data (MSN Fallback) ---

    async def get_fund_listing(self) -> Optional[pd.DataFrame]:
        """Fetches list of mutual funds from FMarket."""
        try:
            # Re-initialize main client for fund access
            v = vnstock.Vnstock()
            res = v.fund(source='FMARKET').listing()
            await asyncio.sleep(settings.vnstock.req_delay)
            return res
        except Exception as e:
            logger.error(f"Error fetching fund listing: {e}")
        return None

    async def get_gold_history(self) -> Optional[pd.DataFrame]:
        """Fetches latest gold prices for SJC and BTMC."""
        try:
            from vnstock.explorer.misc.gold_price import sjc_gold_price, btmc_goldprice
            sjc = sjc_gold_price()
            await asyncio.sleep(settings.vnstock.req_delay)
            btmc = btmc_goldprice()
            await asyncio.sleep(settings.vnstock.req_delay)
            
            # Combine if both exist
            frames = []
            if sjc is not None and not sjc.empty:
                sjc['branch'] = 'SJC'
                frames.append(sjc)
            if btmc is not None and not btmc.empty:
                btmc['branch'] = 'BTMC'
                frames.append(btmc)
            
            if not frames:
                return None
            return pd.concat(frames, ignore_index=True)
        except Exception as e:
            logger.error(f"Error fetching gold price: {e}")
        return None

    async def get_exchange_rate_history(self) -> Optional[pd.DataFrame]:
        """Fetches historical exchange rates (USDVND, etc.)."""
        try:
            from vnstock.explorer.misc.exchange_rate import vcb_exchange_rate
            # Fetch last 30 days of exchange rates if possible, or just today
            res = vcb_exchange_rate(date='') 
            await asyncio.sleep(settings.vnstock.req_delay)
            return res
        except Exception as e:
            logger.error(f"Error fetching exchange rate: {e}")
        return None

    async def get_commodity_history(
        self, 
        symbol: str, 
        start: str = "2015-01-01", 
        end: Optional[str] = None
    ) -> Optional[pd.DataFrame]:
        """
        Fetches historical commodity prices (Oil, Gas, etc.) using MSN fallback.
        Symbols: 
        - 'CL.1': Crude Oil WTI
        - 'NG.1': Natural Gas
        - 'GC.1': Gold (World)
        - 'BZ.1': Brent Oil
        """
        if end is None:
            end = datetime.now().strftime("%Y-%m-%d")
        
        try:
            # Use direct MSN Quote explorer since vnstock 3.4.2 Quote router is buggy (missing symbol_id)
            from vnstock.explorer.msn.quote import Quote as MsnQuote
            quote = MsnQuote(symbol_id=symbol)
            df = quote.history(start=start, end=end, interval="1D")
            await asyncio.sleep(settings.vnstock.req_delay)
            
            if df is not None and not df.empty:
                return df
            logger.warning(f"No commodity data for {symbol} from {start}")
        except Exception as e:
            logger.error(f"Error fetching commodity {symbol}: {e}")
        return None

    async def get_macro_history(
        self, 
        indicator: str, 
        start: str = "2000-01-01", 
        end: Optional[str] = None
    ) -> Optional[pd.DataFrame]:
        """
        Fetches macroeconomic indicators (GDP, CPI, Interest Rates).
        Fallback: If vnstock.Macro is missing, we use known MSN keys if available.
        Note: Many macro stats are not available via simple Quote API.
        """
        # Mapping for MSN or other sources if found
        # In current vnstock 3.4.2, Macro is actually missing.
        # We might need to use scraping or other sources if requested.
        logger.warning(f"Macro class missing in vnstock 3.4.2. Skipping {indicator}")
        return None

    async def get_index_history(
        self, 
        index_code: str, 
        start: str = "2015-01-01", 
        end: Optional[str] = None
    ) -> Optional[pd.DataFrame]:
        """Fetches historical data for a market index (VNINDEX, VN30, DJI)."""
        if end is None:
            end = datetime.now().strftime("%Y-%m-%d")
        
        try:
            source = "vci" if index_code in ["VNINDEX", "VN30", "HNX", "UPCOM"] else "msn"
            quote = vnstock.Quote(source=source, symbol=index_code)
            res = quote.history(start=start, end=end, interval="1D")
            await asyncio.sleep(settings.vnstock.req_delay)
            return res
        except Exception as e:
            logger.error(f"Error fetching index {index_code}: {e}")
        return None

    def get_index_valuation(self, index_code: str = "VNINDEX") -> Optional[Dict[str, Any]]:
        """
        Fetches current P/E, P/B for a market index.
        Note: V3 might not have a direct Valuation class. 
        Falling back to explorer calls if available.
        """
        try:
            # Try VCI explorer which sometimes has index info
            from vnstock.explorer.vci.financial import Finance
            # Finance in VCI often needs a ticker. 
            # For indices, we might need a different approach.
            return None
        except Exception as e:
            logger.info(f"Could not fetch index valuation for {index_code}: {e}")
        return None
