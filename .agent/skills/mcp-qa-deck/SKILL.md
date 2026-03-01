---
name: Shuttles QA Deck
description: Quality Assurance server for token-optimized test execution, coverage analysis, and local failure diagnosis.
---

# Shuttles QA Deck (mcp-qa-deck)

## 🚨 MANDATORY: TEST EXECUTION PROTOCOL

**You MUST NOT use the native terminal (`run_command`) to execute tests (pytest, etc.).** This burns excessive tokens and pollutes the context with standard output logs.

### 1. Running Tests
ALWAYS use `qa-deck.run_test_compact` to execute tests. It returns a concise JSON summary and only the necessary failure details.

- **Tool:** `run_test_compact`
- **Arguments:** `test_command` (e.g. `pytest tests/test_core.py`), `working_dir`

### 2. Coverage Analysis
Instead of reading raw coverage reports, use `get_coverage_gaps` to identify strictly which lines are missing tests.

- **Tool:** `get_coverage_gaps`
- **Arguments:** `coverage_file_path`, `target_file`

### 3. Failure Diagnosis
If a test fails with a massive, complex stack trace, **DO NOT read it yourself**. Offload the analysis to the local hardware.

- **Tool:** `diagnose_failure_local`
- **Arguments:** `raw_stack_trace`, `test_name`
- **Benefit:** Uses local RTX 3060 to perform heavy lifting, returning only a 2-sentence root cause.

## Integration with Strategy
This skill complements `mcp-strategy` by providing the "Execution & Verification" layer for QA. Always prioritize these tools during the `VERIFICATION` phase of any task.
