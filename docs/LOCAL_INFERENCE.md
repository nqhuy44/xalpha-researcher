# Local Inference Strategy

xalpha-researcher is designed to operate seamlessly in restricted environments using local Large Language Models (LLMs). This document outlines the supported local inference engines and deployment patterns.

## 1. Supported Engines

### Ollama (Recommended for Development)
Ollama is the easiest way to run models locally. It provides an OpenAI-compatible API by default.
- **Port**: `11434`
- **Installation**: [ollama.com](https://ollama.com)
- **Model Pull**: `ollama pull qwen2.5:7b` (FastTier) or `ollama pull llama3.1:70b` (DeepTier).

### vLLM (Recommended for Production)
For high-throughput requirements, vLLM is the preferred engine.
- **Features**: PagedAttention, continuous batching.
- **Integration**: Start vLLM with `--api-key` and `--served-model-name` to match the OpenAI protocol.

### llama.cpp
Suitable for resource-constrained hardware (MacBooks, cheap GPUs).
- **Format**: GGUF (quantized).
- **Server**: Use the `server` binary with the `-c` (context size) flag optimized for financial data (>32k tokens).

## 2. Configuration Pattern

To switch from Cloud to Local, update your `.env` or settings YAML:

```yaml
llm:
  provider: "ollama"  # or "openai", "gemini"
  base_url: "http://localhost:11434/v1"
  api_key: "ollama"   # non-empty placeholder
  tiers:
    fast: "qwen2.5:7b"
    deep: "llama3.1:70b"
    judge: "llama3.1:70b"
```

## 3. Hardware Requirements

| Tier | Model Size | VRAM (Quantized) | Recommended Hardware |
|---|---|---|---|
| **FastTier** | 7B - 14B | 6GB - 12GB | RTX 3060+, Apple M1/M2 |
| **DeepTier** | 70B+ | 40GB - 80GB | A100 / H100, 2x RTX 3090/4090 |

## 4. Troubleshooting
- **Context Limit**: Financial contexts can be large. Ensure the local server is configured with `num_ctx` (Ollama) or `--n-ctx` (llama.cpp) set to at least **32,768**.
- **Schema Compliance**: Local models may occasionally fail strict JSON schema output. The system will automatically retry using a Cloud provider if `ALLOW_FALLBACK` is enabled.
