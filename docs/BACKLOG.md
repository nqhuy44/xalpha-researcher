# Improvement Backlog — Token Cost & Analytics Review

> Created: 2026-05-10. Findings from a code+docs review focused on token consumption and research quality.
> Mark items `[x]` as you complete them. Each item has a brief rationale, the file(s) involved, and an estimated impact.

---

## 0. Reading guide

- **Impact**: rough estimate of tokens / cost saved or quality gained.
- **Effort**: S (≤1h), M (half day), L (full day+).
- **Depends on**: other backlog items that should land first.

A current single-ticker debate makes **6–10 deep-tier LLM calls** that all carry the same ~50–150 KB context blob. The roadmap in `docs/MULTI_AGENT_DESIGN.md` (Gatekeeper, structured `MarketIntelligence`, compact `fact/logic/score` triple) was designed but **not implemented** — most of this backlog is closing that gap.

**Framing principle: LEAN content first, dense encoding second.** See **T17** for the umbrella. Cutting *what* gets sent (LEAN: T3, T4, T11, T15, …) yields 60–90% input-token reductions. Encoding *how* it's sent more densely (TOON: T16) adds another 30–50% on top. Doing TOON before LEAN means re-tuning the encoder against shrinking payloads, so the suggested order in §8 lands LEAN first.

---

## 1. Bugs — fix first (correctness)

These contradict the documented design and silently waste tokens or miscompute. Address before optimizing.

- [x] **B1. Referee always runs (off-by-one in `referee_router`).** *(fixed 2026-05-10)*
  - File: `src/agents/analyst/graph.py:39-51`, `src/agents/analyst/state.py:88` (default `judge_attempts = 1`).
  - `judge_agent_node` returns `judge_attempts + 1` → on first execution state goes 1→2. The router then hits `if state.judge_attempts > 1: return "referee"` and **always** routes to Referee, so the `confidence < 75` cost-gate is unreachable.
  - **Fix applied**: Re-defined `judge_attempts` as "completed runs", default `0`. After 1st run = 1, 2nd run = 2. `referee_router` keeps `> 1` (now correctly identifies retries). `post_referee_router` changed `<=` → `<` to preserve the "1 initial + 1 retry" cap. Verified with all 6 transition cases.
  - Impact: −1 Pro call per debate (~15–25% of debate cost). Effort: S.

- [x] **B2. `Argument` schema mismatch with Bull/Bear prompts.** *(fixed 2026-05-11)*
  - File: `src/agents/analyst/state.py:6-10` vs `src/prompts/bull_system.txt:53-63` and `src/prompts/bear_system.txt`.
  - Prompts demand `type` and `acknowledged_risk` fields; Pydantic schema has only `claim/evidence/strength`. Either Gemini drops the extras (wasted output tokens) or occasional parse failures trigger Tenacity retries.
  - **Fix applied**: extended `Argument` with `type` (Literal of MACRO/SECTOR/FUNDAMENTAL/TECHNICAL/CATALYST/STRUCTURAL) and `acknowledged_counter`; extended `Rebuttal` with `rebuttal_strength`; normalized `flaw_type` enum (`VALID_BUT_PRICED_IN` → `ALREADY_PRICED_IN`); renamed asymmetric `acknowledged_risk` (Bull) and `acknowledged_bull` (Bear) to a single `acknowledged_counter` in both prompts. JSON-column persistence and dashboard fields are unaffected (additive).
  - Impact: avoids silent retries + cleaner output. Effort: S.

- [x] **B3. Dead code in Bull/Bear rebuttal branches.** *(fixed 2026-05-11)*
  - Files: `src/agents/analyst/nodes/bear_agent.py:38-48`, `src/agents/analyst/nodes/bull_agent.py` (mirror).
  - The `if not bull_claims: bull_text = "..."` block is unconditionally overwritten two lines later by `bull_text_parts`. The guard never takes effect.
  - **Fix applied**: rewrote both nodes against typed `prev_round.bull_arguments`/`bear_arguments`/`*_rebuttals` (no more `hasattr` ducktyping); extracted shared helpers (`format_argument`, `format_rebuttal`, `format_opponent_attacks`, `format_debate_transcript`) into `src/agents/analyst/utils/debate_formatting.py`; collapsed the duplicated transcript-building code in `judge_agent.py` and `referee_agent.py` to one line each. The Judge and Referee transcripts now also surface `type`, `acknowledged_counter`, and `rebuttal_strength` for richer scoring.
  - Effort: S.

- [x] **B4. `TICKER_NEWS_30D` uses `ILIKE %TICKER%` (false positives).** *(fixed 2026-05-11)*
  - File: `src/agents/analyst/nodes/data_aggregator.py:97-105`.
  - Tickers like `BCG`, `VIC`, `HAG` match unrelated content (vaccines, "Vietnam International Cup", word fragments). False-positive news is sent to all 4 nodes × N rounds.
  - **Fix applied**: switched from `ILIKE '%TICKER%'` to a Postgres POSIX regex match (`description ~* :t`) with the word-boundary anchor `\y` on each side (`\yBCG\y`). Eliminates substring noise like `BCGdebate` while keeping legitimate matches (`Cổ phiếu BCG`, `bcg corp`, punctuation-adjacent forms). Ticker is alphanumeric-sanitized before being embedded in the pattern. Pure entity-meaning collisions (`Vaccine BCG`) remain — those need semantic match (see I1) rather than a tokenizer change.
  - Impact: better analyst quality + smaller context. Effort: M.

- [x] **B5. `[GLOBAL_MACRO_NEWS_7D]` is uncapped.** *(fixed 2026-05-11)*
  - File: `src/agents/analyst/nodes/data_aggregator.py:120-128`.
  - 5 articles × N domains × 7 days → up to ~280 rows joined into context, replicated into every node × every round.
  - **Fix applied**: tightened the windowed query — `ROW_NUMBER() … rn <= 2` (was `<= 5`) per `(domain, day)` plus a hard outer `LIMIT 30`. The header was updated to "top 2/day per domain, capped at 30 most recent" to keep the prompt label honest. Longer-term replacement is still T11 (pre-synthesized macro digest).
  - Impact: large input-token reduction. Effort: M.

- [x] **B6. Misleading log: "TOON context".** *(fixed 2026-05-11)*
  - File: `src/agents/analyst/nodes/data_aggregator.py:231`.
  - Log said "Generated X characters of TOON context" but no TOON encoding actually happened — the format is pipe-tabular text with section headers. Audit confirmed there is exactly one "TOON" reference in the source tree, and it's this log line.
  - **Fix applied**: renamed the log to "pipe-tabular context" so it truthfully describes the current output. The full TOON encoder + adoption is split out as **T16**.
  - Effort: S.

- [x] **B7. Engine triggers Portfolio for every verdict, including non-held + negative ones.** *(fixed 2026-05-11)*
  - File: `src/agents/analyst/engine.py:146-156`, `src/agents/portfolio/engine.py:14-21,84-99`.
  - The analyst engine unconditionally invoked `PortfolioEngine.process_signal`, which always ran the LangGraph portfolio workflow (a Pro-tier call) even when the verdict was bearish/neutral and the user didn't hold the ticker. The "ALWAYS TRIGGER" comment justified it as needed for UI tracking, but the dashboard already filters suggestions by held symbols (`AIAnalysisList.tsx`), so a missing row on a non-actionable verdict is the correct UI signal.
  - **Fix applied**: gate moved inside `PortfolioEngine.process_signal` after the (cheap) position fetch and before the LLM graph invocation. Two module-level constants make the policy explicit: `ACTIONABLE_DECISIONS = {"Tiềm năng", "Khả quan"}` and `PORTFOLIO_TRIGGER_CONFIDENCE = 70` (aligned with the T2 verdict-cache threshold). Skip rule: run if `ticker in current_positions` (held → always evaluate sell/reduce) OR (`decision ∈ ACTIONABLE_DECISIONS` AND `confidence_score ≥ 70`); otherwise log + return `None`. The analyst engine's stale "ALWAYS TRIGGER" comment was rewritten to describe the new short-circuit and the log line now distinguishes "skipped" from `execution_status`.
  - Note: a previously-active `PortfolioSuggestion` row for a ticker is no longer auto-soft-deleted on skip (soft-delete still happens when a new row is being created). Practical impact is limited because the dashboard filters by currently-held symbols, but if it becomes a problem the cleanup is a one-line addition to the skip branch.
  - Impact: −1 Pro call on the meaningful fraction of debates that produce neutral/bearish verdicts on tickers the user doesn't hold. Effort: S.

- [ ] **B8. Referee `VOID` action documented but not handled in graph.**
  - File: `src/prompts/referee_system.txt` (defines VOID), `src/agents/analyst/graph.py:53-66` (only checks `is_valid`).
  - VOID and OVERRIDE collapse into the same path. Decide if VOID should hard-stop with a special verdict, or remove it from the prompt.
  - Effort: S.

- [ ] **B9. Judge/Referee threshold inconsistency.**
  - Files: `src/prompts/judge_system.txt:48-54` (Tiềm năng ≥ 8 pts) vs `src/prompts/referee_system.txt:36-40` (Tiềm năng > 10 pts).
  - Two different thresholds → Referee can flag valid Judge verdicts as logic flaws.
  - Fix: pick one set, reference it from a single shared prompt fragment.
  - Effort: S.

- [ ] **B10. Sector peers query peg date from primary ticker only.**
  - File: `src/agents/analyst/nodes/data_aggregator.py:206-211`.
  - `WHERE se.trade_date = (SELECT MAX(trade_date) FROM stock_eod WHERE ticker = :t)` — if a peer has a more recent close, it's missed; if the primary ticker hasn't traded today, peers show stale data.
  - Fix: use each peer's own latest trade_date (`DISTINCT ON (ticker)`).
  - Effort: S.

---

## 2. Token-saving — Tier 1 (highest ROI, do these next)

- [ ] **T1. Implement L0 Gatekeeper.** (Promised in `docs/MULTI_AGENT_DESIGN.md`, `docs/FLOWS.md` §2.)
  - Pre-debate SQL filter: `market_cap < 100B VND`, `30d avg vol < 100k`, ticker in warn-list, debate already exists for `(ticker, today)` with confidence ≥ threshold.
  - Wire as a node before `data_aggregator` that returns early-stop with a "skipped" verdict.
  - Impact: 100% saving for rejected tickers + cache hits. Effort: M.

- [ ] **T2. Verdict cache (per ticker, per market session).**
  - File: new short-circuit at `src/agents/analyst/engine.py:32` (before graph invoke).
  - Skip the graph if `(ticker, trade_date_today)` already has a verdict in `verdicts` with `confidence_score ≥ 70` and the inputs (latest EOD date, latest news ts) haven't changed.
  - Impact: avoids duplicate Telegram-triggered re-runs. Effort: S.

- [ ] **T3. Replace monolithic `context: str` with structured `MarketIntelligence` Pydantic model.** (Promised in `docs/MULTI_AGENT_DESIGN.md` §1.2.)
  - File: new `src/agents/analyst/intelligence.py` with sections (`profile`, `financials`, `eod`, `technicals`, `ticker_news`, `macro_digest`, `peers`, `vnindex_trend`).
  - Each node selects its slice: Bull/Bear get fundamentals+technicals+ticker_news+macro_digest; Judge additionally gets transcript; Referee gets only the verdict + a compact "facts cited" subset.
  - Impact: 30–50% input-token reduction per node. Effort: L. Depends on: B5.

- [ ] **T4. Truncate context for rebuttal rounds.**
  - Files: `src/agents/analyst/nodes/bull_agent.py:50`, `bear_agent.py:51`.
  - Round-2 nodes don't need the 50 KB context again — they "read" it in round 1. Pass only a `[KEY_FACTS]` ~1 KB extract (latest close, RSI, MACD, top-3 ticker news, VNINDEX trend) + opponent's claims.
  - Impact: ~80% reduction on rebuttal-round input. Effort: S. Depends on: T3 (cleaner if using slices).

- [ ] **T5. Demote `portfolio_manager` from Pro to deterministic Python + Flash for narrative.**
  - Files: `src/agents/portfolio/nodes/portfolio_manager.py:56`, `src/prompts/portfolio_manager.txt`.
  - Position sizing is math (Kelly + concentration cap + horizon target). Compute it deterministically; then call Flash (`role="fast"`) only to write the rationale text.
  - Impact: replaces a Pro call with a Flash call (~10× cheaper) on every verdict. Effort: M.

- [ ] **T6. Use Flash-Lite for opening rounds, Pro only for rebuttals + Judge.**
  - Files: `src/agents/analyst/nodes/bull_agent.py:27`, `bear_agent.py:27` (currently `role="deep"`).
  - Round-1 is extraction ("read context, output 5 bullets") — Flash handles this fine. Reserve Pro for adversarial rebuttals where reasoning matters.
  - Impact: ~70% saving on 2 of 5 debate calls. Effort: S.

---

## 3. Token-saving — Tier 2 (caching layer)

- [ ] **T7. Gemini Context Caching for stable system prompts.**
  - File: `src/services/llm/gemini_provider.py`.
  - System prompts are stable: `judge_system.txt` (121 lines), `referee_system.txt` (123 lines), `bull_system.txt` (65 lines), `bear_system.txt` (70 lines), `portfolio_manager.txt` (251 lines).
  - Use `google.genai` `cached_content` API. Pricing for cached input is ~25% of normal.
  - Impact: ~75% off the system-prompt portion of every call. Effort: M.

- [ ] **T8. Per-debate ephemeral context cache.**
  - File: `src/services/llm/gemini_provider.py` + `src/agents/analyst/graph.py`.
  - Within one graph run, the same `state.context` (or `MarketIntelligence`) is sent 4–6 times. Cache it once at the top of the graph with TTL = expected debate duration (~5 min).
  - Impact: ~75% off the per-debate context portion across ~5 calls. Effort: M. Depends on: T7 (same plumbing).

- [ ] **T9. Redis result cache keyed by `(model, sha256(system+user))`.**
  - File: new wrapper around `LLMService.generate_structured`.
  - Especially valuable for Stage-1 news summaries — the same article is currently re-summarized if scheduling jitters; `content_hash` is already computed in the news pipeline.
  - Impact: meaningful on news Stage 1; modest elsewhere. Effort: M.

---

## 4. Token-saving — Tier 3 (pipeline shape)

- [ ] **T10. Adopt the compact `fact / logic / score` triple.** (Promised in `docs/MULTI_AGENT_DESIGN.md` §2.1.)
  - File: `src/agents/analyst/state.py` (`Argument`, `Rebuttal`).
  - Free-text `claim`+`evidence` averages ~150 tokens. Triple `{fact, logic, score}` compresses to ~50.
  - Impact: smaller transcript fed into Judge + Referee (~3× compression of debate text). Effort: M. Depends on: B2 (do them together).

- [ ] **T11. Pre-synthesized macro digest table.**
  - File: news scheduler + new `macro_digest` table (date, domain, summary).
  - The news scheduler already produces per-domain syntheses for Telegram — store the latest one. The debate's `data_aggregator` injects ~500 tokens of digest in place of `[GLOBAL_MACRO_NEWS_7D]`.
  - Impact: replaces ~280 rows with ~500 tokens. Effort: M. Depends on: B5.

- [ ] **T12. Implement documented early-exit on consensus.** (Promised in `docs/MULTI_AGENT_DESIGN.md` §2.2.)
  - File: `src/agents/analyst/graph.py` `router`.
  - If Round-1 Bull and Bear arguments overlap on ≥80% of facts (Jaccard on `claim` strings or pgvector cosine sim), skip rebuttals and go directly to Judge. >90% → skip Judge, emit auto-warning verdict.
  - Effort: M.

- [ ] **T13. Stage-1 news pre-filter before LLM summarization.**
  - File: `src/agents/news/collector.py` + `src/services/llm/__init__.py:137`.
  - Currently every collected article goes through Flash-Lite; many come back as `SKIP`. Filter at ingest: domain blocklist (entertainment), source-quality score, title regex blocklist.
  - Impact: cuts Stage-1 cost proportional to junk ratio (often 30–50%). Effort: S.

- [ ] **T14. Cap Stage-2 synthesis input.**
  - File: `src/agents/news/scheduler.py:77` (`limit_per_domain=500`).
  - 500 summaries per domain in one Flash call is unnecessary. Top-K by recency+source weight (e.g., 80) is enough for the report quality.
  - Effort: S.

- [ ] **T15. Sequential, deduplicated debate transcript for Judge.**
  - File: `src/agents/analyst/nodes/judge_agent.py:18-40`.
  - Currently the Judge sees raw `bull_arguments + bear_arguments` per round. Many rebuttals re-state opening claims verbatim. Deduplicate and present as a chronologically-merged conflict map (claim → counter → status). Smaller and easier to score.
  - Impact: smaller Judge prompt + arguably better verdicts. Effort: M. Depends on: T10.

- [~] **T16. TOON (Token-Oriented Object Notation) encoder utility + adoption.** *(encoder built 2026-05-11; pilot deferred — see T17)*
  - Files (built): `src/services/encoding/toon.py` (~150 LOC, dependency-free), `src/services/encoding/__init__.py`, `tests/unit/test_toon_encoder.py` (12 passing tests including a savings-vs-JSON sanity floor). Adoption sites (not yet wired): `src/agents/analyst/nodes/referee_agent.py:24` (`model_dump_json` → `encode_pydantic`), `src/agents/analyst/nodes/data_aggregator.py` (each `[BLOCK]` → spec-correct TOON header), and any future structured-record LLM payload.
  - **Background.** TOON is a JSON-alternative format designed to be 30–50% denser when read by LLMs. Spec form: `name[N]{cols}:` followed by indented comma-separated rows for tabular arrays; nested objects use indentation instead of braces. Reference: https://toonformat.dev. **No usable Python library exists today** — `toon-format` 0.1.0 on PyPI is a namespace reservation whose `encode()` raises `NotImplementedError`; the package named `toon` on PyPI is an unrelated neuroscience library. We therefore rolled our own, keeping the API spec-shaped so we can swap to `toon-format` later with no call-site changes.
  - **Why this is now scope-paused: TOON is encoding, not selection.** Validated on a realistic Verdict payload: TOON is 466 chars vs 854 chars JSON (**45% reduction on that payload**). Real but bounded. Meanwhile the system is currently sending a 50–150 KB context blob to every node × every round, much of which the receiving node doesn't need at all. Dropping content (LEAN, see **T17**) saves 60–90% on the same payloads; encoding the bloat denser is the smaller win and should land on top of LEAN, not before it. Encoding a 50 KB payload as TOON yields ~30 KB; making it LEAN yields ~5 KB; doing both yields ~3 KB — the ordering matters because LEAN-then-TOON is purely additive while TOON-then-LEAN forces re-tuning the encoder against shrinking payloads.
  - **Scope of the shipped encoder.** Encoder only — no decoder (LLMs read it; we don't parse it back). Handles scalars (quotes only when content contains delimiter/newline/leading-trailing whitespace), uniform record arrays (tabular), scalar arrays (`name[N]: a,b,c`), nested objects (indented k/v), Pydantic models via `.model_dump()`. Mixed-shape arrays fall back to nested object encoding.
  - **Where adoption helps after LEAN lands.**
    1. Referee verdict input (currently `model_dump_json(indent=2)`) — clean ~30–50% reduction; structured by definition, untouched by LEAN.
    2. `data_aggregator` slices that survive T3 (`MarketIntelligence`) — TOON makes the structure explicit (`peers[5]{ticker,name,close,rsi,date}:`).
    3. Future: portfolio position lists, news Stage-2 article batches.
  - **Where it does NOT help (do not migrate).**
    - `debate_formatting.py` Argument/Rebuttal narratives — Vietnamese free-text claim/evidence/counter-evidence; tabularization hurts LLM comprehension.
    - Portfolio narrative templates and prompt system files.
  - **Roll-out plan (deferred — gated by LEAN milestone).**
    1. ✅ Encoder + unit tests landed (no runtime impact; nothing imports them yet).
    2. ⏸ Pilot on Referee. **Hold** until **T3, T4, T11, T15** complete — those reshape what payloads exist, so wiring TOON before them means re-tuning twice.
    3. After LEAN lands: add `settings.llm.use_toon_encoding: bool = False` feature gate; wire Referee call site; measure tokens before/after using `usage_metadata` (best with I2/O1 for hard numbers, manual diff acceptable).
    4. If pilot saves ≥15% input tokens with no output-quality regression on a 5-ticker test, extend to `data_aggregator` slices one at a time.
    5. Flip the feature gate default to True once stable.
  - **API sketch (already implemented):**
    ```python
    from src.services.encoding import encode, encode_pydantic
    encode({"verdict": {...}})                                      # nested object
    encode_pydantic(state.verdict)                                  # Pydantic shortcut
    encode({"peers": [{"ticker": "HPG", "rsi": 55.2}, ...]})        # auto-detects tabular
    ```
  - Impact: ~30–50% on the Referee call once LEAN-shaped payloads stabilize; smaller wins elsewhere. Effort remaining: S (wire one site + feature gate). **Depends on: T3, T4, T11, T15** (and T17 as the umbrella).

- [ ] **T17. LEAN context engineering (umbrella principle).**
  - Not a single change — a cross-cutting *content-selection* discipline that this backlog has been describing piecemeal. Naming it explicitly so future work has one anchor to read.
  - **Definition.** *LEAN context* = "send each agent only the data it actually needs to reason, and pre-distill anything that can be summarized once and reused many times." The opposite is the current pipeline, which sends one ~50–150 KB monolithic `context` blob to every node × every round, regardless of whether that node uses it.
  - **Why it dominates encoding-level wins.** TOON squeezes ~30–50% off whatever you send. LEAN deletes 60–90% of what gets sent in the first place. They compound (LEAN-then-TOON), but if you only do one, do LEAN first — the encoder optimizes a payload that should not have been that large.
  - **Quantitative target for this codebase.** Today: ~50–150 KB sent ~6–10 times per debate. After LEAN milestone (T3+T4+T11+T15): each node receives the *slice* it consumes, ~2–10 KB; rebuttal rounds use a ~1 KB key-facts extract; macro section is a ~500-token digest; Judge sees a deduplicated conflict map. Realistic input-token reduction across the debate: **5–10×**.
  - **Concrete instances already tracked in this backlog.** T17 doesn't add new code — it groups the existing items so the rationale stays coherent. The LEAN milestone consists of:
    - **T1** — L0 Gatekeeper (skip the whole debate when a ticker doesn't qualify).
    - **T3** — replace monolithic `context: str` with structured `MarketIntelligence`; each node selects its slice.
    - **T4** — round-2+ rebuttals get only a `[KEY_FACTS]` ~1 KB extract, not the full context.
    - **T11** — pre-synthesized macro digest replaces the `[GLOBAL_MACRO_NEWS_7D]` block.
    - **T13 / T14** — drop junk before LLM (Stage-1 pre-filter) and cap Stage-2 input.
    - **T15** — deduped, conflict-mapped transcript for Judge.
    - **I1** — pgvector semantic news selection (LEAN by *relevance*, not just by boundary).
    - Also relevant: **B5** (already done — capped global news), **B7** (skip Portfolio for non-actionable verdicts), **T2** (verdict cache — *don't send anything* on a hit).
  - **Recommended LEAN milestone (one focused effort).** Land **T3 + T4** as a single PR (they share schema work), then **T11**, then **T15**. After this milestone, T16 (TOON) wiring + **T7/T8** (Gemini context caching) become very high-ROI on the now-stable payload shape.
  - **Decision rules for "is this LEAN?"** When designing a new node or prompt, ask: (a) what are the 5–10 facts this LLM call genuinely needs to do its job? (b) can any of them be pre-computed and reused? (c) is anything in the payload there because "the old context blob had it," not because this node uses it? If yes to (c), cut it.
  - **Anti-patterns to flag in review.** Sending the same `state.context` to two nodes that need different slices; recomputing the same digest inside two nodes; passing a transcript to a node that only needs the verdict; including round-1 raw context to a round-2+ node.
  - **Out of scope for T17 itself.** No code, no schema. T17 is a *principle* — implementation lives in T1/T3/T4/T11/T13/T14/T15/I1.
  - **Cross-references.** Pairs with **T16** (encoding) as the two halves of payload optimization. Once LEAN lands, T16 pilot is unblocked. Effort: tracking only — concrete effort sits in the linked items.

- [ ] **I1. pgvector semantic news selection.**
  - File: new embeddings job + replacement for `[TICKER_NEWS_30D]` query.
  - `pgvector` is in dependencies but unused. Embed news at ingest; cosine-search top-K against `(company_name + ticker + sector + product_keywords)`.
  - Replaces brittle `ILIKE`; improves analyst quality AND reduces token count (10 truly relevant items > 30 LIKE-matched). Effort: L. Depends on: B4.

- [ ] **I2. Per-call token logging table.**
  - File: new `llm_usage` table + wrapper in `src/services/llm/__init__.py`.
  - Gemini returns `usage_metadata.prompt_token_count` / `candidates_token_count`. Persist `(ts, ticker, node, role, model, input_tok, output_tok, cached_tok, latency_ms, status)`.
  - **Do this before further optimization** — you can't tell which node burns the most without it. Effort: S.

- [ ] **I3. Debate verdict diff vs prior verdict.**
  - File: `src/data/persistence/verdict_repo.py`.
  - When persisting a new verdict, compute the diff vs the most recent prior verdict for the same ticker (decision change, score gap delta, surviving-points overlap). Surface in dashboard.
  - Effort: M.

- [ ] **I4. PhoBERT sentiment scoring on news.** (Promised in README + `docs/NEWS_AGENT.md`.)
  - File: new `src/models/sentiment/phobert.py`, schedule on ingest.
  - Adds a numeric sentiment score per article — usable in the Bull/Bear `Argument.evidence` directly and as an aggregate input to the Portfolio Agent.
  - Effort: L.

- [ ] **I5. Tighten "context layer" attribution in Judge.**
  - File: `src/prompts/judge_system.txt` Step 1.
  - Force Judge to output `market_wide_attribution_pct + sector_wide_attribution_pct + stock_specific_attribution_pct = 100`. Today the three layers are free text; numerics let the Portfolio Agent reason about whether the call is macro-driven (rotates with market) or stock-specific (independent risk).
  - Effort: S.

- [ ] **I6. Confidence calibration tracking.**
  - File: new periodic job comparing predicted `horizon_confidence` to realized outcomes after the horizon elapses (use actual EOD price hitting target/stop).
  - Persist a calibration curve; feed back into the system prompt as "your historical confidence overstatement is X%". This is real research-grade improvement.
  - Effort: L.

- [ ] **I7. Sector + macro debate specialization.**
  - Today every debate is per-ticker. Add a daily `sector_debate` (one round Bull/Bear per industry) and a weekly `macro_debate` whose verdicts feed downstream into ticker debates as compact priors.
  - Cuts per-ticker macro/sector reasoning load + improves cross-stock consistency. Effort: L.

- [ ] **I8. Adversarial test set / regression debates.**
  - Maintain a fixed list of ~30 historical situations with known outcomes (e.g., FLC Aug 2022 should have been "Rủi ro"). Re-run debates on prompt changes; track decision accuracy + RR realization to prevent prompt-tuning regressions.
  - Effort: L.

- [ ] **I9. Corporate-action-aware EOD resync (dividend / split / bonus share back-adjustment).**
  - Files: `src/agents/financial/collector.py:92-203` (`sync_eod`), `src/agents/financial/collector.py:157-175` (RSI/MACD warm-up), `src/agents/analyst/nodes/data_aggregator.py:80-93` (30d/52w highs+lows + technicals).
  - **Problem.** `sync_eod` is purely incremental: `start_date = latest_db_date + 1 day`. Existing rows are never revisited. But vnstock returns **adjusted** close prices — when a ticker pays a cash dividend, splits, or issues bonus shares, the entire historical price series shifts and what is now in our DB becomes stale relative to what vnstock currently returns. The DB silently holds two regimes: pre-event un-adjusted bars and post-event adjusted bars stitched onto the end.
  - **Concrete blast radius.**
    1. `[EOD_STATS]` 30d_low/high and 52w_low/high in `data_aggregator.py` are computed from un-adjusted historical rows, so they overstate ranges for any ticker that has paid a dividend since the last bootstrap.
    2. RSI/MACD warm-up concatenates the un-adjusted 100-bar DB tail with the freshly-fetched (adjusted) new bar — produces a phantom price gap on the boundary day and a spurious RSI/MACD spike that misleads the Bull/Bear technical layer.
    3. Sector-peer comparisons (`SECTOR_PEERS` block) are skewed: peers that recently paid dividends look artificially weaker vs the primary ticker.
    4. Stock splits / bonus issues are worse — the discontinuity is multiplicative, not a few-percent shift.
    5. The `verdicts` and `report_generator.py` HTML reports archive numbers from this distorted context, so the corruption persists in historical reports too.
  - **Fix — option A (recommended): divergence-sentinel re-fetch.** On each incremental sync, also re-fetch the last ~5 trading days. Compare DB close vs vnstock's freshly-returned close on the overlap window. If any overlap day diverges by more than `EOD_DIVERGENCE_THRESHOLD` (start at 0.3%), treat it as a corporate-action event for that ticker and trigger a full re-fetch from `DEFAULT_EOD_START` with overwrite, then recompute RSI/MACD on the entire series. Self-healing, no schema change, costs only ~5 extra days × 1 ticker per daily sync (negligible).
  - **Fix — option B (precise but heavier): corporate-actions calendar.** Use vnstock's events/dividend endpoint to populate a new `corporate_actions(ticker, ex_date, type, ratio)` table. When the daily worker sees a new ex_date row for a ticker, force a full re-fetch for *just that ticker*. Most accurate; adds an ingest path + table + migration. Pair with A as a precision upgrade once observability (I2/O1) confirms divergence-driven re-fetches are an actual cost item.
  - **Fix — option C (last resort): weekly full resync.** Re-fetch `start=2015-01-01` for every ticker once per week. Simplest to write but, with `VNSTOCK__REQ_DELAY=3.0` and ~700 tickers, runs for several hours and risks vnstock rate-limit bans. Avoid unless A/B prove insufficient.
  - **Implementation sketch for option A** (so future work doesn't re-derive it):
    1. In `sync_eod`, after computing `start_date`, set `overlap_start = (latest_date - timedelta(days=7)).strftime("%Y-%m-%d")` — pulling 5 trading days requires ~7 calendar days because of weekends.
    2. Call `vnstock.get_eod_history(ticker, start=overlap_start, end=end_date)` once. Slice the rows that fall inside `[overlap_start, latest_date]` for the divergence check.
    3. Bulk-load the corresponding stored rows (`StockEOD.trade_date IN overlap_dates`).
    4. For each overlap date, compare `abs(stored.close - fresh.close) / stored.close`. Track `max_diff`.
    5. If `max_diff > 0.003`: log a warning (`"Detected corporate action for {ticker}: max divergence {max_diff:.2%}, full re-fetch triggered"`), call `get_eod_history(ticker, start=DEFAULT_EOD_START, end=end_date)`, recompute RSI/MACD over the *entire* series, and `upsert_eod_records` over all rows.
    6. Otherwise, proceed normally with the new bars only (the overlap fetch is a free byproduct — we can either upsert it idempotently or discard).
    7. Add a `last_corporate_action_check` column on `companies` (or a Redis key) to avoid running the divergence check more than once per ticker per market session.
  - **Cross-references.** Depends on nothing; should land before T2 (verdict cache) and T3 (`MarketIntelligence` slicing), since both will cache or distill the distorted EOD numbers if this is unfixed. Tightly related to: B10 (sector peer date pegging — fixing both together avoids double touching `data_aggregator.py`).
  - **Validation plan.** Pick 2–3 known recent dividend events (e.g., HPG, VNM, FPT — check `vnstock.Company(...).events()`), confirm A correctly detects and re-fetches; verify post-fix `rsi`/`macd` match what TradingView shows on those tickers.
  - Impact: data integrity for **every** technical-driven argument the Bull/Bear/Judge produce. Effort: M (option A alone) — L (A+B together).

---

## 6. Architectural cleanups (low priority, quality of life)

- [ ] **A1. Single `LLMService` instance.**
  - File: every node currently does `llm = LLMService()` — reinitializes all providers per call. Make it a module-level singleton or DI it via graph state.
  - Effort: S.

- [ ] **A2. Move prompt loading to import time.**
  - File: `src/services/llm/__init__.py:125`. `load_prompt` reads from disk on every call. Cache in a dict keyed by filename.
  - Effort: S.

- [ ] **A3. Centralize role→model mapping.**
  - File: `src/services/llm/__init__.py:96-122` has a giant if/elif ladder per provider. Replace with a `MODEL_MATRIX: dict[provider][role] = model` table — fewer bugs when adding a provider.
  - Effort: S.

- [ ] **A4. Repository for analyst data aggregation.**
  - File: `src/agents/analyst/nodes/data_aggregator.py` runs raw `text(...)` SQL inline. Move to `FinancialRepository` / `NewsRepository` for testability.
  - Effort: M.

- [ ] **A5. Stop instantiating `LLMService` inside the news scheduler loop.**
  - File: `src/agents/news/scheduler.py:105, 133`.
  - One per domain iteration. Move to a single instance reused across domains.
  - Effort: S.

- [ ] **A6. Telegram message length truncation drops tail of report silently.**
  - File: `src/agents/news/scheduler.py:32`.
  - For long syntheses the user loses the conclusion. Either chunk into multiple messages or move long reports to the dashboard with a Telegram link.
  - Effort: S.

---

## 7. Observability prerequisites (do early, unblocks the rest)

- [ ] **O1. I2 token-usage table** *(duplicate of I2 — do once)*.
- [ ] **O2. Structured trace per debate run.**
  - One row per debate with total tokens, total cost (computed from a price table), per-node breakdown, total latency, retries.
  - Drives a "Cost per ticker" dashboard tile.
  - Effort: M. Depends on: I2.
- [ ] **O3. Alert when a single debate exceeds a token budget** (e.g., 200K input tokens). Cheap canary for prompt regressions.
  - Effort: S. Depends on: O2.

---

## 8. Suggested execution order

If working through this slowly, this sequence minimizes rework. The guiding principle is **T17 — LEAN context first, encoding second**: optimize *what* you send before optimizing *how* you encode it.

1. **B1–B6 done. Remaining quick fixes: B7, B8, B9, B10** — one afternoon.
2. **I2 / O1** — token logging in place so you can *measure* every subsequent change. Without this, "did LEAN actually help?" is a guess.
3. **T2 (verdict cache)**, **T6 (Flash for openings)** — large saving for low effort while you set up.
4. **T1 (Gatekeeper)** + **I1 (semantic news, depends on B4)** — they share schema work and both reduce *what enters the pipeline*.
5. **🟢 LEAN milestone — biggest single payoff. Do as one focused effort:** **T3 (MarketIntelligence)** + **T4 (truncated rebuttal)** + **T10 (compact triple)** + **T11 (macro digest)** + **T15 (deduped Judge transcript)**. This is the **T17** principle made concrete; targets a 5–10× input-token reduction across the debate.
6. **T7 + T8 (Gemini context caching)** — wire only after LEAN, when the payload shape is stable; otherwise the cache key churns and savings collapse.
7. **🟢 T16 pilot** — wire the (already-built) TOON encoder behind a feature gate, starting with Referee. Now compounds with LEAN instead of optimizing soon-to-be-deleted bytes.
8. **T5 (deterministic Portfolio sizing)** + **B9 (threshold alignment)** — analytics-quality cleanup.
9. **T13 / T14 (news pre-filter / Stage-2 cap)** — news pipeline tuning (also part of LEAN, lower urgency than the analyst-side work).
10. **I9 (corporate-action-aware EOD)** — data-integrity foundation; ideally land before any of the above caches a distorted EOD-derived number.
11. **I3–I8** — research-quality features.
12. **A1–A6** — code-quality cleanups whenever convenient.
