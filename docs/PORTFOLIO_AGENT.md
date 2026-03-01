# Feature: Portfolio Agent (Execution & Capital Management)

## Overview

The Portfolio Agent is the final execution layer. It transforms debate-validated signals into concrete capital allocation decisions using mathematical risk models, tailored for Vietnamese frontier market constraints.

## Responsibilities

- Calculate optimal position sizing using Kelly Criterion (Half-Kelly).
- Compute portfolio-level Value at Risk (VaR) at 95% confidence.
- Monitor T+2.5 settlement cycles.
- Track brokerage margin ratios for early margin call warnings.
- Generate SHAP explainability reports for every recommendation.
- Rebalance portfolio based on risk parameters.

## Risk Models

### Kelly Criterion (Half-Kelly)

$$f^* = \frac{1}{2} \cdot \frac{\mu - r}{\sigma^2}$$

- Applied at 50% to account for frontier market volatility.
- When losing, position size decreases with account balance.
- When winning, position size increases (compounding).

### Value at Risk (VaR)

$$VaR_{95\%} = \mu - 1.645 \cdot \sigma$$

- Calculated at portfolio level and per-position.
- Maximum portfolio VaR limit configurable by user.

### Position Sizing

- **Liquidity-adjusted**: Position size capped by average daily volume to avoid slippage on exit.
- **Concentration limit**: No single position exceeds configurable % of total portfolio.

## Vietnam-Specific Features

| Feature | Detail |
|---|---|
| **T+2.5 Settlement** | Track pending settlements, available buying power |
| **Margin Monitoring** | Alert when brokerage margin ratios approach ceiling |
| **Margin Call Warning** | Predict mass margin calls from market-wide leverage data |
| **Foreign Flow** | Track net foreign buying/selling as leading indicator |

## Technical Design

| Component | Technology |
|---|---|
| Risk Calculations | NumPy, SciPy |
| Explainability | SHAP (Shapley values) |
| LLM Assignment | Gemini 2.5 Flash (portfolio analysis) |
| State Management | LangGraph (backtrack, human-in-the-loop) |

## Output Schema

```json
{
  "portfolio_id": "uuid",
  "symbol": "HPG",
  "action": "BUY",
  "kelly_fraction": 0.10,
  "recommended_shares": 500,
  "estimated_cost": 15000000,
  "portfolio_var_before": 0.032,
  "portfolio_var_after": 0.038,
  "shap_breakdown": {
    "foreign_inflow": 0.40,
    "eps_beat": 0.30,
    "technical_breakout": 0.20,
    "sector_rotation": 0.10
  },
  "alert_level": 2
}
```

## API Contract

```
POST /api/v1/portfolio/allocate    # Calculate allocation for signal
GET  /api/v1/portfolio/status      # Current portfolio state
GET  /api/v1/portfolio/risk        # Risk metrics (VaR, Kelly)
POST /api/v1/portfolio/rebalance   # Trigger rebalance
GET  /api/v1/portfolio/alerts      # Pending alerts
```
