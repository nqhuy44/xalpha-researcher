# Feature: Signal Agent (Quantitative Screener)

**Status: 🔲 Planned**

## Overview

The Signal Agent screens the entire Vietnamese equity universe using a combination of CANSLIM fundamental analysis and technical indicator signals.

## Responsibilities

- Score stocks against 7 CANSLIM criteria.
- Compute technical indicators (RSI, MACD, Bollinger Bands, MA).
- Rank stocks by Relative Strength (RS Rating).
- Combine fundamental + technical signals into Buy/Sell recommendations.
- Filter out "junk" stocks via profit margin, debt, and asset quality checks.

## CANSLIM Scoring

| Criterion | Metric | Threshold |
|---|---|---|
| **C** — Current Earnings | Q-o-Q EPS growth | ≥20-25% |
| **A** — Annual Earnings | Annual profit growth | 3-5 consecutive years |
| **N** — New Products/Mgmt | New catalysts | 52-week high, new leadership |
| **S** — Supply & Demand | Volume analysis | Breakout volume at accumulation |
| **L** — Leader/Laggard | RS Rating | ≥80th-90th percentile |
| **I** — Institutional | Fund participation | Increasing institutional ownership |
| **M** — Market Direction | Market trend | Avoid buying in corrections |

## Technical Indicators

| Indicator | Usage |
|---|---|
| RSI (14) | Overbought/oversold detection |
| MACD (12, 26, 9) | Trend momentum and crossovers |
| Bollinger Bands (20, 2) | Volatility and mean reversion |
| SMA/EMA (20, 50, 200) | Trend direction and support/resistance |
| Volume Profile | Supply/demand zone identification |

## Technical Design

| Component | Technology |
|---|---|
| Structured ML | XGBoost (non-linear financial patterns) |
| Chart Patterns | Random Forest / CNN |
| Data Source | vnstock (SSI/TCBS) — 20+ years history |
| LLM Assignment | Gemini 2.5 Flash (real-time scoring) |

## Output Schema

```json
{
  "symbol": "HPG",
  "canslim_score": 6.2,
  "canslim_breakdown": {"C": 1.0, "A": 0.8, "N": 0.9, ...},
  "technical_signal": "BUY",
  "technical_indicators": {"rsi": 42.3, "macd_signal": "bullish_cross"},
  "confidence": 0.78,
  "rs_rating": 92,
  "shap_breakdown": {...}
}
```

## API Contract

```
POST /api/v1/signal/scan       # Run full market scan
GET  /api/v1/signal/{symbol}   # Get signal for specific stock
GET  /api/v1/signal/top        # Get top-ranked signals
```
