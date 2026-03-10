# Feature: Analyst Agent (Adversarial Debate)

**Status: ✅ Implemented**

## 1. Overview

The Analyst Agent (internally `src/agents/analyst`) is the system's primary **Risk Intelligence Layer**. It uses a multi-round adversarial debate orchestrated by **LangGraph** to rigorously stress-test investment signals. By pitting an optimistic Bull against a skeptical Bear, the system identifies hidden risks and validates growth catalysts before capital is committed.

## 2. Core Reasoning Principles

- **Single Ground Truth**: Both Bull and Bear receive the *exact same* context string from the `data_aggregator`.
- **Independent Agency**: Personas generate arguments and rebuttals independently in parallel LangGraph nodes.
- **Synthesized Objectivity**: A neutral Judge agent evaluates the entire transcript, cross-referencing claims against the raw context to catch hallucinations.

## 2. Debate Algorithm Specification

The system implements a **Stateful Adversarial Multi-Round (SAMR)** reasoning algorithm.

### Formal Algorithm (Pseudocode)
```python
def AdversarialDebateAlgorithm(ticker, context, max_rounds):
    # Initialize State
    state = AnalystState(ticker=ticker, context=context)
    
    # Round 1: Opening Thesis
    bull_claims = DeepTier.generate(System="BullPersona", User=context)
    bear_claims = DeepTier.generate(System="BearPersona", User=context)
    state.append_round(bull_claims, bear_claims)
    
    # Rounds 2 to N: Conflict Resolution
    for i in range(2, max_rounds + 1):
        # Bull reads previous Bear arguments
        bull_rebuttals = DeepTier.generate(
            System="BullRebuttal", 
            Context=context, 
            Opponent=state.history[-1].bear
        )
        # Bear reads previous Bull arguments
        bear_rebuttals = DeepTier.generate(
            System="BearRebuttal", 
            Context=context, 
            Opponent=state.history[-1].bull
        )
        state.append_round(bull_rebuttals, bear_rebuttals)
    
    # Terminal Step: Judgment
    transcript = state.format_history()
    verdict = JudgeTier.generate(
        System="JudgePersona", 
        User={"context": context, "debate": transcript},
        Schema=VerdictSchema
    )
    return verdict
```

The system follows a state-machine logic with a fan-out/fan-in pattern:

1. **Phase 1: Opening (Round 1)**
   - **Bull Node**: Generates 5 compelling reasons to BUY.
   - **Bear Node**: Generates 5 critical reasons to SELL.
2. **Phase 2: Rebuttals (Rounds 2 to N)**
   - **Bull Node**: Reads Bear's claims from the previous round and provides counter-evidence.
   - **Bear Node**: Reads Bull's claims and identifies weaknesses or contradictory data.
3. **Phase 3: Verdict**
   - **Judge Node**: Consolidates all rounds into a transcript. Performs evidence scoring and issues a final `Verdict` object.
4. **Phase 4: Safety Verification (Conditional)**
   - **Referee Node**: Evaluates the Judge's Verdict against the raw context and transcript. Only triggered if the Judge's confidence is < 70% or the verdict is "STRONG BUY" or "STRONG SELL". Catches hallucinations, logical errors, and extreme bias without generating new financial arguments.

## 4. Technical State & Schema

The debate is governed by the `AnalystState` ([state.py](file:///home/nqhuy/nqhuy/xalpha-researcher/src/agents/analyst/state.py)).

### AnalystState (LangGraph State)
- `ticker`: Stock symbol (e.g., "HPG").
- `context`: A comprehensive string containing EOD technicals, financial reports, and news.
- `rounds`: A growing list of `DebateRound` objects (using `operator.add`).
- `max_rebuttals`: Defines how many rebuttal rounds occur after the opening (default: 2).

### Result Schema (Verdict)
The final structured output from the Judge:
- `decision`: Qualitative assessment ("Tiềm năng", "Rủi ro", "An toàn").
- `confidence_score`: 0-100.
- `bull_score` / `bear_score`: Winning points for each persona.
- `judge_synthesis`: A concise summary of the prevailing logic.
- `horizons`: Specific targets, stop-losses, and actionable `action` directives (e.g., Mua, Bán, Giữ) for Short, Medium, and Long term, each with an individual `horizon_confidence` score and detailed strategy `rationale`.

## 5. Implementation Details

| Component | Responsibility |
|---|---|
| `data_aggregator.py` | Fetches EOD, Financials, Sector Peers, and News into a unified string. |
| `bull_agent.py` | Implementation of the long-term growth persona. |
| `bear_agent.py` | Implementation of the risk-auditor/short-seller persona. |
| `judge_agent.py` | Impartial arbiter using high-reasoning Gemini models. |
| `referee_agent.py` | Safety verification layer that critically audits the judge's verdict for logic flaws and hallucinations. Runs conditionally to save tokens. |
| `report_generator.py` | Converts the debate state into a modern responsive HTML report. |

## 6. Model Usage

While the system is designed for multi-model routing, the current implementation prioritizes **Gemini 2.5 Pro** for all structured output nodes to ensure strict schema compliance and deep reasoning quality. See [MULTI_AGENT_DESIGN.md](file:///home/nqhuy/nqhuy/xalpha-researcher/docs/MULTI_AGENT_DESIGN.md) for the optimization roadmap.
