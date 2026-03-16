# Recommendations: Multi-Agent Collaboration Design (Roadmap)

**Status: 🔲 Optimization Roadmap (Proposed)**

This document details the proposed architectural improvements for the xalpha-researcher Multi-Agent System (MAS), focusing on **Reduced Token Consumption**, **Structured Reasoning**, and **Cost-Aware Escalation**.

## 1. Architectural Improvements

### 1.1 The "Gatekeeper" Filter (L0 Defense)
- **Problem**: Every signal triggers a full LLM workflow, even for "junk" stocks.
- **Solution**: A hard-rule node to reject tickers with low liquidity (<100k avg vol) or low market cap (<100B VND).
- **Benefit**: 100% token saving for non-viable candidates.

### 1.2 Structured Information Contract
- **Problem**: monolithic `context: str` causes hallucinations and high token usage.
- **Solution**: Transition to a structured `MarketIntelligence` model separating financials, technicals, and sentiment.
- **Benefit**: Agents process only relevant fields, reducing input context size.

## 2. Debate & Reasoning Optimization

### 2.1 Compact Argument Format (JSON-First)
To reduce token usage by ~40%, move from free-text arguments to a strictly structured "Fact-Logic-Score" triple.

**Standardized Output Schema**:
```json
{
  "fact": "Exports +30% YoY",
  "logic": "Resilient demand in key markets",
  "score": 8
}
```

### 2.2 Safety Verification (Referee Layer)
To prevent hallucinations and reasoning errors from the final Judge, a conditional **Referee Layer** has been introduced.
- **Logic**: Evaluates the Judge's Verdict against the raw context and debate transcript.
- **Trigger**: Only runs when Judge confidence is < 75% or if it is auditing a re-attempted verdict. Does not flag valid analytical price projections.
- **Cost Savings**: Significant token savings because it avoids running validation on every single routine decision, only on low-confidence edge cases or repeated failures.

### 2.2 Conflict-based Rebuttal Filtering
- **Logic**: If Bull and Bear consensus on 80% of points, skip rebuttals and proceed to Judge.
- **Early Exit**: If consensus is >90% (e.g., both agree it's a bubble), skip the Judge node and issue an automated warning.

## 3. Cost-Aware Model Routing

| Layer | Responsibility | Model Recommendation |
|---|---|---|
| **Context Refiner** | Summarize raw data | **Local Qwen 3.5** |
| **Initial Arguments** | 5 Bull/Bear facts | **Local Qwen 3.5** |
| **Rebuttals** | Targeted counter-attacks | **Gemini 2.5 Flash-Lite** |
| **Synthesis** | Final Judge Verdict | **Gemini 2.5 Pro** |
| **Verification** | Referee safety audit (Conditional) | **Gemini 2.5 Pro / Claude 3.5** (Deep/Fast depending on need) |

## 4. Potential New Agents

1. **Portfolio Agent**: Acts as an **Advisory Risk Manager**. It reviews the user's manually maintained stock portfolio against intelligence from the Signal and Debate agents. It generates non-executable advisory recommendations (`BUY MORE`, `REDUCE`, `HOLD`, `EXIT`) and applies risk constraints (maximum position sizing, diversification). The agent relies entirely on manual user inputs (via a simple UI) for state tracking.
2. **Macro Watcher**: Provides a daily "Global Market State" to all agents.
3. **Backtest Validator**: Cross-references signals with historical stock reactions.

---
**Senior Architect Note**: Implementing the **Gatekeeper** and **Structural Contract** provides the highest immediate ROI for reliability and cost reduction.
