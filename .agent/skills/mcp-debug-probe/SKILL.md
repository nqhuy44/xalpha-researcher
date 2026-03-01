---
name: Shuttles Debug Probe
description: Runtime diagnostics, log analysis, and automated crash troubleshooting.
---

# Debug Probe Skill

This skill focuses on "Container-Aware" observation and intelligent troubleshooting using runtime metrics and local AI analysis.

## Core Tools

### 1. `run_and_capture`
- **Use Case**: Verifying builds (`make build`), checking environment state, or running generic background commands.
- **Protocol**: Always capture both stdout and stderr to ensure full visibility.
- **Note**: For running Python (pytest) tests, **MANDATORY** use `qa-deck.run_test_compact` instead.

### 2. `tail_filtered_logs`
- **Use Case**: Debugging live race conditions or monitoring background tasks.
- **Mandate**: Always use keywords (e.g., "ERROR", "CRASH", "FATAL") to reduce noise.

### 3. `analyze_crash_local` [REQUIRES LOCAL GPU/Ollama]
- **Use Case**: Pinpointing the root cause of a complex stack trace.
- **Protocol**: Feed the raw messy output from `run_and_capture` directly into this tool. The result is a distilled "Diagnosis" from the local LLM.

### 4. The TOON Response Protocol
**Mandatory** for log analysis and test results. When returning tabular diagnostics or list-based capture data, use the TOON format (Array of Arrays) for extreme efficiency.

## Debugging Workflow

1. **Isolate**: Use `run_and_capture` for the specific failing command.
2. **Trace**: Check `tail_filtered_logs` for any anomalies during execution.
3. **Diagnose**: Use `analyze_crash_local` on the resulting error log.
4. **Fix**: Apply the solution based on the intelligent diagnosis.

## Anti-Patterns
- **Guessing**: Changing code based on assumptions without checking filtered logs.
- **Manual Parsing**: Reading 500 lines of raw tail output instead of using filters.
