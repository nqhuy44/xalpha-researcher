# Feature: Debate Agent (Adversarial Reasoning)

## Overview

The Debate Agent is the system's risk control mechanism. It employs adversarial reasoning by spawning two personas — **Bull** and **Bear** — to rigorously debate every Buy signal before it reaches the Portfolio Agent.

## Responsibilities

- Receive Buy signal proposals from the Signal Agent.
- Spawn Bull persona to argue **for** the investment.
- Spawn Bear persona to argue **against** the investment.
- Synthesize a multi-dimensional risk report.
- Eliminate confirmation bias through structured adversarial debate.

## Debate Structure

### Bull Persona Arguments

- Growth catalysts (new products, market expansion)
- Favorable economic cycle (low interest rates, high liquidity)
- Undervaluation metrics (low P/E vs historical/sector average)
- Positive technical setup (breakout, volume confirmation)
- Institutional accumulation signals

### Bear Persona Arguments

- Hidden debt / bad debt exposure (especially bond defaults)
- Revenue growth deceleration or margin compression
- Geopolitical risks (trade wars, sanctions, energy disruptions)
- Corporate governance red flags
- Sector-specific risks (e.g., real estate oversupply, tech valuation bubble)
- Inflation / interest rate pressure on leveraged businesses

## Technical Design

| Component | Technology |
|---|---|
| LLM | Gemini 2.5 Pro (2M token context, complex reasoning) |
| Prompting | Structured adversarial prompts with role assignment |
| Grounding | Google Search integration to verify factual claims |
| Context | Full financial reports + sentiment data via RAG |

## Output Schema

```json
{
  "analysis_id": "uuid",
  "symbol": "HPG",
  "bull_argument": "Strong infrastructure spending...",
  "bear_argument": "Margin pressure from rising iron ore...",
  "synthesis": "Net positive with moderate risk...",
  "risk_score": 0.35,
  "confidence": 0.72,
  "recommendation": "BUY_WITH_CAUTION",
  "model_used": "gemini-2.5-pro",
  "tokens": {"input": 45000, "output": 3200}
}
```

## API Contract

```
POST /api/v1/debate/run        # Trigger debate for a signal
GET  /api/v1/debate/{id}       # Get debate result
GET  /api/v1/debate/history    # List past debates
```
