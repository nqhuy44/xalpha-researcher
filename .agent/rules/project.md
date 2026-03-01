---
trigger: manual
---

## 0 🚨 MANDATORY MCP PROTOCOLS
**FAILURE TO FOLLOW THESE PROTOCOLS IS A VIOLATION OF PROJECT INTEGRITY.**
1. **STRUCTURAL FIRST MANDATE**: 
   - NEVER read a file > 100 lines with `view_file` without first using `radar-ast.get_file_skeleton`.
   - NEVER list directories recursively with `list_dir`. Use `radar-ast.get_dir_tree` (max depth 3).
2. **QA-DECK PASS-THROUGH**: 
   - NEVER run `pytest` or any Python tests via native terminal. **MANDATORY** use of `qa-deck.run_test_compact`.
3. **LOCAL-OFFLOAD (Ollama)**: 
   - Any summary, diagnosis, or docstring generation **MUST** use tools with the `_local` suffix (e.g., `radar-ast.summarize_logic_local`, `qa-deck.diagnose_failure_local`).
4. **TOON FORMAT**: 
   - All tabular or list-based data returned by your tools **MUST** use the TOON format (Array of Arrays) to minimize token footprint.
5. **STRATEGY SYNERGY**: 
   - Always refer to [STRATEGY.md](../../mcp-servers/STRATEGY.md) and [mcp-strategy](../../.agent/skills/mcp-strategy/SKILL.md) for detailed tool selection before acting.