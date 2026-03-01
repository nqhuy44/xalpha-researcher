---
name: Shuttles Cargo DB
description: Database introspection, schema mapping, and query performance analysis.
---

# Cargo DB Skill

This skill provides deterministic database introspection to ensure consistent schema understanding and performance safety.

## Core Tools

### 1. `get_tables`
- **Use Case**: Getting an overview of the data architecture.
- **Protocol**: Use this once per session to reset your "mental model" of the DB.

### 2. `get_schema`
- **Use Case**: Checking column types, nullability, and foreign keys.
- **Mandate**: Verify the schema before writing any raw SQL or updating ORM models.

### 3. `explain_query`
- **Use Case**: Auditing performance for complex joins or large scans.
- **Protocol**: Use this before proposing a database migration or a new reporting query.

### 4. `find_join_path`
- **Use Case**: Connecting disparate tables.
- **Mandate**: Use this to find the most efficient FK path instead of guessing.

### 5. The TOON Response Protocol
**Mandatory** for data exploration. All `SELECT` results must be transmitted in TOON format (Array of Arrays) to avoid repeating field names in every row. Refer to `doc-scribe`'s implementation if unsure.

## Data Strategy

1. **Schema First**: Check `docs/DATABASE.md` first, then verify with `get_schema`.
2. **Safety**: Always `EXPLAIN` before you `EXECUTE` (if execution tools are available).
3. **Relationships**: Map the ERD in your head using `find_join_path`.

## Anti-Patterns
- **Guessing Schema**: Proposing code that assumes a column exists without verification.
- **Ignore Indices**: Writing queries without checking if the target columns are indexed via `get_schema`.
