# Unified Risk Framework

This document outlines the three layers of defense-in-depth implemented in the xalpha-researcher architecture.

## 1. L1 — Data Quality Gate (Source Layer)
**Goal**: Prevent "Garbage In, Garbage Out".

- **Validation**: Signals from `vnstock` must pass an 8/12 indicator check.
- **Deduplication**: SHA256 hashes prevent processing same news twice.
- **Staleness Check**: EOD data more than 1 day old (relative to market benchmark) is blocked.

## 2. L2 — Adversarial Debate (Intelligence Layer)
**Goal**: Neutralize confirmation bias.

- **The Logic**: 
  - **Bull**: Argues the growth thesis.
  - **Bear**: Argues the risk/prosecution thesis.
  - **Judge**: A high-order LLM (Gemini Pro) that determines the "Truth" by weighing conflicting arguments.
- **Termination Condition**: Debate continues for `max_rebuttals` before the Judge node triggers.
- **Fail-Safe**: If `confidence_score` < 75%, the signal is flagged "INCONCLUSIVE" and blocked from execution.

## 3. L3 — Portfolio Constraint (Sizing Layer)
**Goal**: Absolute capital protection.

- **Kelly Criterion**: Determines aggressive growth fraction based on probability of win.
- **Half-Kelly Adjuster**: Safety buffer specifically for the Vietnamese Frontier Market.
- **VaR 95%**: Absolute stop-signal if the projected loss violates the user's daily risk budget.
- **Liquidity Barrier**: Caps position to <5% of average daily volume.

---

## Escalation Path
`Signal Detected` -> `Gate Passed?` -> `Debate Won? (Score > 75)` -> `Size Allowed? (VaR < Budget)` -> `TELEGRAM ALERT`
