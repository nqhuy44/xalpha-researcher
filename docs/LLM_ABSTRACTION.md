# LLM Reasoning Abstraction Layer

To ensure the system remains model-agnostic and future-proof, xalpha-researcher uses an abstraction layer that categorizes LLMs into three functional tiers. This allows for seamless switching between Cloud providers (Gemini, OpenAI) and Local inference (Ollama, vLLM).

## Tier Definitions

| Tier | Characteristics | Typical Models | System Responsibility |
|---|---|---|---|
| **FastTier** | High throughput, low cost, specialized extraction. | Gemini 2.5 Flash-Lite, Qwen 2.5 7B, GPT-4o-mini | News extraction, EOD cleanup, initial drafting. |
| **DeepTier** | Complex reasoning, large context window, adversarial. | Gemini 2.5 Pro, GPT-4o, DeepSeek-V3, Llama 3.1 70B | Bull/Bear arguments, high-confidence rebuttals. |
| **JudgeTier** | Strict schema compliance, extreme neutrality, verification. | Gemini 2.5 Pro (optimized), GPT-4o | Final verdict synthesis, portfolio risk auditing. |

## Provider Support Matrix

### Cloud Providers
- **Gemini (Default)**: Leverages native structured output support and large context windows for raw data ingestion.
- **OpenAI**: Supported through standard ChatCompletion API wrappers.

### Local Inference Strategy
- **Ollama**: Primary for development; provides a standard OpenAI-compatible `/v1/chat/completions` endpoint.
- **vLLM / llama.cpp**: Recommended for high-performance production local deployments.

## Model Routing & Fallback
The system implements a hierarchical fallback logic:
1. Attempt task with **Ollama (Local)** if enabled.
2. If Local fails or times out, escalate to **FastTier (Cloud)**.
3. If reasoning depth is insufficient (detected via confidence scores), escalate to **DeepTier (Cloud)**.

## Per-Call Token Usage Tracking (I2/O1)

Every `LLMService.generate_structured` call persists a row to the `llm_usage` table (fire-and-forget — never blocks the call path). The row captures:

| Field | Source |
|---|---|
| `ticker` / `node` / `debate_run_id` | Passed by the calling node |
| `role` / `provider` / `model` | Resolved by `get_provider_and_model` |
| `input_tokens` / `output_tokens` / `cached_tokens` | From provider `usage_metadata` |
| `latency_ms` | Wall-clock time around the provider call |
| `status` | `success` or `error` |

Provider coverage:
- **Gemini**: `response.usage_metadata.prompt_token_count / candidates_token_count / cached_content_token_count`
- **OpenAI / Grok / DeepSeek / Ollama**: `response.usage.prompt_tokens / completion_tokens`
- **Claude**: `response.usage.input_tokens / output_tokens`

The `LLMProvider.generate_structured` ABC now returns `Tuple[Any, UsageDict]`. The `LLMService` layer unwraps it — callers continue to receive only the Pydantic result with no interface change.

## Debate-Level Cost Tracing (O2)

`DebateEngine` creates a `debate_traces` row before invoking the LangGraph graph (`status="running"`) and updates it to `completed`/`failed` once the graph finishes. The finalization step aggregates all `llm_usage` rows for the run into:

- Total input / output / cached tokens
- Per-node breakdown JSONB (`{node: {input_tokens, output_tokens, calls, latency_ms}}`)
- Estimated cost in USD (computed from a `_MODEL_PRICE_PER_M` table in `engine.py`)
- FK to the resulting `debate_verdicts` row

`AnalystState.debate_run_id` threads the trace ID through the LangGraph state so every node can tag its `llm_usage` rows automatically.

## Token Budget Alert (O3)

After each debate, `_finalize_debate_trace` compares `total_input_tokens` against `DEBATE_INPUT_TOKEN_BUDGET = 200_000`. If exceeded, it emits a structured `logger.warning("debate_token_budget_exceeded", ...)` including the overage count. This acts as a canary for prompt regressions — a sudden spike in input tokens on a known ticker flags that a context block has grown unexpectedly.
