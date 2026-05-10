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
   - **Referee Node**: Evaluates the Judge's Verdict against the raw context and transcript. Triggered only when the Judge's `confidence_score < 75` OR the current verdict is a retry produced after a previous Referee `OVERRIDE` (i.e. `judge_attempts > 1`). Catches hallucinations, logical errors, and extreme bias without generating new financial arguments. On a retry-triggered run, Referee fires regardless of confidence so the corrected verdict is always re-audited; on an `OVERRIDE`, the graph loops back to Judge up to `max_judge_attempts` (default 2 = 1 initial + 1 retry).

## 4. Technical State & Schema

The debate is governed by the `AnalystState` ([state.py](file:///home/nqhuy/nqhuy/xalpha-researcher/src/agents/analyst/state.py)).

### AnalystState (LangGraph State)
- `ticker` / `company_name`: Stock symbol (e.g., "HPG") and resolved name.
- `context`: A comprehensive string containing EOD technicals, financial reports, and news (built by `data_aggregator`).
- `rounds`: A growing list of `DebateRound` objects (using `operator.add`).
- `current_round` / `max_rounds`: Loop control. `max_rounds` is set by `DebateEngine` from its `max_rebuttals` constructor arg (`max_rounds = max_rebuttals + 1`, since round 1 is the opening).
- `judge_attempts` / `max_judge_attempts`: Number of *completed* judge runs (starts at 0) and the cap (default 2 = 1 initial + 1 retry). Drives the Referee retry loop.
- `verdict` / `referee_decision` / `referee_history`: Latest Judge output, latest Referee decision, and the full sequence of Referee decisions across retries.

### Argument Schema (Bull/Bear opening output)
Used in round 1. Both sides produce the **same** Pydantic shape; only the prompt differs.
- `type`: one of `MACRO | SECTOR | FUNDAMENTAL | TECHNICAL | CATALYST | STRUCTURAL`. Slot 5 is `CATALYST` for Bull and `STRUCTURAL` for Bear; slots 1–4 are shared.
- `claim`: concise main point in Vietnamese.
- `evidence`: data + logical chain backing the claim.
- `acknowledged_counter`: the strongest opposing point this side concedes (intellectual honesty rule). Surfaced to the Judge in the transcript.
- `strength`: self-assessed score 1–10.

### Rebuttal Schema (Bull/Bear rebuttal output)
Used in rounds 2..N. Each rebuttal targets one opponent argument and is produced verbatim against `claim`.
- `target_claim`: verbatim copy of the opponent's `claim`. The graph relies on this for thread-matching in `report_generator.py`.
- `flaw_type`: one of `DATA_ERROR | INFERENCE_ERROR | SCOPE_ERROR | MAGNITUDE_ERROR | ALREADY_PRICED_IN`.
- `counter_evidence`: data and logic that dismantle the targeted claim.
- `rebuttal_strength`: 1–10 self-assessed strength of this counter.

All four schemas (`Argument`, `Rebuttal`, plus the per-round container `DebateRound` and the top-level `AnalystState`) are defined in `src/agents/analyst/state.py`. Single-source-of-truth formatters for prompts and transcripts live in `src/agents/analyst/utils/debate_formatting.py`.

### Result Schema (Verdict)
The final structured output from the Judge:
- `decision`: Qualitative assessment, exactly one of `Tiềm năng | Khả quan | Trung lập | Rủi ro | An toàn`.
- `confidence_score`: 0-100.
- `bull_score` / `bear_score`: Winning points for each persona.
- `judge_synthesis`: A concise summary of the prevailing logic.
- `horizons`: Specific targets, stop-losses, and actionable `action` directives (e.g., Mua, Bán, Giữ) for Short, Medium, and Long term, each with an individual `horizon_confidence` score and detailed strategy `rationale`.

## 5. Implementation Details

| Component | Responsibility |
|---|---|
| `data_aggregator.py` | Fetches EOD, Financials, Sector Peers, and News into a unified string. News blocks: `[TICKER_NEWS_30D]` uses a Postgres word-boundary regex (`~* '\yTICKER\y'`) to avoid substring false positives like `BCGdebate`; `[GLOBAL_MACRO_NEWS_7D]` is capped at 2 articles per `(domain, day)` with an outer `LIMIT 30` to keep the macro section bounded across debates. |
| `bull_agent.py` | Implementation of the long-term growth persona. |
| `bear_agent.py` | Implementation of the risk-auditor/short-seller persona. |
| `judge_agent.py` | Impartial arbiter using high-reasoning Gemini models. |
| `referee_agent.py` | Safety verification layer that critically audits the judge's verdict for logic flaws and hallucinations. Runs conditionally to save tokens. |
| `report_generator.py` | Converts the debate state into a modern responsive HTML report. |

## 6. Model Usage

While the system is designed for multi-model routing, the current implementation prioritizes **Gemini 2.5 Pro** for all structured output nodes to ensure strict schema compliance and deep reasoning quality. See [MULTI_AGENT_DESIGN.md](file:///home/nqhuy/nqhuy/xalpha-researcher/docs/MULTI_AGENT_DESIGN.md) for the optimization roadmap.
