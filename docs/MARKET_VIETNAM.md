# Vietnam Stock Market Constraints (HOSE / HNX / UPCOM)

The system and its agents (including the Portfolio Agent) are designed specifically for the Vietnam stock market. Recommendations **must** abide by the following local market rules:

## 1. Daily Price Limits (Biên độ dao động)
Stocks can only fluctuate within strict daily bands based on their exchange:
- **HOSE (Ho Chi Minh Stock Exchange)**: ±7%
- **HNX (Hanoi Stock Exchange)**: ±10%
- **UPCOM (Unlisted Public Company Market)**: ±15%
*Agent Rule*: Suggested `buy_range` or `take_profit_range` must be aware of these daily limits to be realistic for a single-day order.

## 2. T+2 Settlement Cycle
- Shares purchased today (T+0) arrive in the investor's account at the end of T+2.
- They **cannot be sold until T+2 settlement** is complete (effectively available to trade on T+2 afternoon or T+3 morning).
*Agent Rule*: Short-term stop-loss recommendations must account for the fact that the user is locked in for at least 2 days.

## 3. No Same-Day Trading (Intraday)
Vietnam's market **does not support intraday buy and sell for the same shares** (T+0 trading is not allowed).

## 4. Board Lot Size (Lô chẵn)
- The standard trading lot across all exchanges is **100 shares**.
*Agent Rule*: Any recommendation involving `shares` to buy or sell must be rounded to the nearest multiple of 100.

## 5. Market Sessions (Trading Hours)
- **Morning Session**: 09:00 – 11:30
- **Afternoon Session**: 13:00 – 15:00
*Note*: Includes periodic auction sessions (ATO/ATC) at the open and close depending on the exchange. 

## 6. Liquidity and Slippage
- Many Vietnamese stocks (especially mid/penny caps and UPCOM stocks) have very low liquidity.
*Agent Rule*: The Portfolio Agent must avoid recommending large position sizes in illiquid stocks to prevent the user from suffering severe slippage on entry or exit.
