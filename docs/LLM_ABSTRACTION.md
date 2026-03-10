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
