---
name: Shuttles Doc Scribe
description: Efficient documentation management using deterministic patching and local LLM summarization/generation.
---

# Doc Scribe Skill

This skill ensures documentation hygiene and "Ruthless Token Efficiency" by avoiding full-file rewrites and offloading text generation.

## Core Tools

### 1. `get_markdown_toc`
- **Use Case**: Navigating massive READMEs or ARCHITECTURE docs.
- **Protocol**: Use the TOC to identify the exact heading required for a task.

### 2. `patch_doc_section`
- **Use Case**: Updating a specific feature description or fixing a typo.
- **Mandate**: **Never** rewrite a whole `.md` file if you are only changing one section. Use this tool with the target `heading_name`.

### 3. `summarize_doc_local` [REQUIRES LOCAL GPU/Ollama]
- **Use Case**: Distilling naming conventions, deployment steps, or business logic from long docs.
- **Protocol**: Offload the reading task to local Ollama to save input context.

### 4. `generate_inline_docs` [REQUIRES LOCAL GPU/Ollama]
- **Use Case**: Maintaining repository standards for Python docstrings (Google style).
- **Mandate**: Use this for all new public functions/classes in the `shuttles` monorepo.

### 5. The TOON Response Protocol
**Mandatory** for structural data. TOC extraction and any tabular summaries must follow the TOON format (Array of Arrays) to ensure the AI receives maximum information at minimum cost.

## Documentation Guidelines

1. **Deterministic Indexing**: Use `get_markdown_toc` before `view_file`.
2. **Minimal Diffing**: Treat Documentation like Code. Use discrete patches.
3. **Automated Generation**: If a function lacks a docstring, always offer to generate it via `_local`.

## Anti-Patterns
- **Context Burning**: Pasting 200 lines of existing documentation into the chat just to change 2 lines.
- **Manual Summarization**: Writing long summaries of files that could be handled by `summarize_doc_local`.
