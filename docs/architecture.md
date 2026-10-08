# NEEKA Architecture

NEEKA is layered so the Brain remains the authority for work state:

```text
Client/API -> Intelligence Gateway -> Application Services -> Brain
           -> Workflow/Automation -> Repositories -> SQLite
```

The API and Intelligence layers do not issue SQL. Intelligence tools call the
existing Brain methods, so workflow rules, dependencies, permissions, events,
and persistence remain centralized.

Part 5 adds provider-neutral analysis, planning, controlled tools, permission
modes, and persisted AI audit records. The mock provider is deterministic and
requires no credentials.

## Part 6: Project Knowledge

Project knowledge is persistent information owned by NEEKA, separate from work
state. The `neeka.knowledge` module provides documents, immutable document
versions, requirements, decisions, notes, references, reusable tags, and a
small generic relationship table. `KnowledgeService` enforces project
membership before repository access.

Knowledge writes use the existing Brain event pipeline. SQLite migration v4
creates the knowledge tables and indexes without replacing prior migrations.
The API exposes project-scoped CRUD and local keyword search under `/api/v1`.
Intelligence receives bounded structured knowledge through `ContextBuilder`;
providers and tools never receive direct database access.