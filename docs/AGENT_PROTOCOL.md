# Unified Agent Protocol (UAP)

The Unified Agent Protocol defines the standard communication and state-sharing contract between all agents in the xalpha-researcher ecosystem.

## 1. State Management Contract
All agents must interact with a shared **State Object** that follows a strict Pydantic-enforced schema.

### Message Envelope
Any message exchanged between agents or logged to the history must follow this structure:
```json
{
  "sender": "string",      // e.g., 'bull_agent'
  "recipient": "string",   // e.g., 'judge_agent' or 'broadcast'
  "content": "any",        // Structured data or string
  "metadata": {
    "tier": "string",      // FastTier, DeepTier, JudgeTier
    "model": "string",     // Actual model name used
    "token_usage": "int",
    "timestamp": "iso8601"
  }
}
```

## 2. Capability Schema
Agents are defined by their capabilities rather than their class names:
- `Ingestor`: Capability to fetch and normalize external data.
- `Reasoner`: Capability to generate arguments based on context.
- `Auditor`: Capability to verify claims against a ground-truth context.
- `Executor`: Capability to calculate mathematical outputs (Kelly/VaR).

## 3. Communication Patterns

### Adversarial Fan-out (Debate)
1. **Orchestrator** broadcast `Context` to `Reasoner` group {Agent1, Agent2}.
2. **Reasoners** reply in parallel using `Argument` schema.
3. **Orchestrator** collects and increments round state.

### Verification Fan-in (Judgment)
1. **Orchestrator** sends `Transcript` to `Auditor`.
2. **Auditor** validates `Transcript` against `Context`.
3. **Auditor** returns `Verdict` schema.
