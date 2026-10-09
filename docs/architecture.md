# NEEKA Architecture

NEEKA is layered so the Brain remains the authority for work state:

```text
Client/API -> Intelligence Gateway -> Application Services -> Brain
           -> Workflow/Automation -> Repositories -> SQLite
```

The API and Intelligence layers do not issue SQL. Intelligence tools call the
existing Brain methods, so workflow rules, dependencies, permissions, events,
and persistence remain centralized.

Part 8 adds a desktop boundary above the API: the React renderer can only use
the secure Electron preload bridge; Electron main manages the local Python API
process; the Python API remains the only route to application services, Brain,
and persistence. See `docs/desktop.md` for the desktop lifecycle.

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

## Part 7: Workspace Artifacts

Artifacts are the actual files and outputs associated with projects and tasks,
separate from Knowledge. `ArtifactService` coordinates the v5 SQLite
repository and replaceable `ArtifactStorage` abstraction. The initial storage
implementation is local, application-managed, path-validated, checksum-aware,
and uses atomic writes. Artifact access inherits project membership and emits
events through the existing Brain event pipeline.