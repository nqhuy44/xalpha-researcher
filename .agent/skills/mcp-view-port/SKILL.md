---
name: Shuttles View Port
description: Frontend structural radar, design tokens, and route mapping.
---

# View Port Skill

This skill enables "Visual Reasoning" for the AI by stripping noise and extracting structural metadata from the frontend.

## Core Tools

### 1. `extract_design_tokens`
- **Use Case**: Finding the exact color palette or spacing units (Tailwind/CSS).
- **Protocol**: Use this to ensure new UI components match the existing design system.

### 2. `scan_ui_components`
- **Use Case**: Discovering reusable components and their props.
- **Mandate**: **Always** scan the components folder before building a "new" component to avoid duplication.

### 3. `extract_dom_skeleton`
- **Use Case**: Debugging layout shifts or structural issues.
- **Protocol**: Use this to see a "X-ray" of the DOM without text content noise.

### 4. `map_frontend_routes`
- **Use Case**: Linking to pages or understanding the application flow.
- **Mandate**: Use this to find the correct URL paths (e.g., `/users/:id`).

### 5. The TOON Response Protocol
**Mandatory** for tabular UI data. Component registries (`scan_ui_components`) and route maps (`map_frontend_routes`) should prefer TOON format if the list is extensive, keeping headers separate from row data.

## Frontend Strategy

1. **Token Hygiene**: Stick to values found in `extract_design_tokens`.
2. **Component Reuse**: Scan components, then implementation.
3. **Skeleton Debugging**: If a UI fix is needed, start with the skeleton to see the hierarchy.

## Anti-Patterns
- **Hardcoding Styles**: Using arbitrary hex codes instead of design tokens.
- **DOM Dumping**: Reading 1000 lines of JSX text content instead of the skeleton.
