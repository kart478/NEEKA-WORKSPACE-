# NEEKA Architecture

NEEKA is a layered work-management system in which the Brain remains the authority for work state, workflow transitions, permissions, and persistence.

```text
Client/API -> Intelligence Gateway -> Application Services -> Brain
           -> Workflow/Automation -> Repositories -> SQLite
```

The API and Intelligence layers do not issue SQL directly. They call application services and the Brain, which keeps workflow rules, dependencies, membership checks, events, and persistence centralized.

The desktop shell sits above the API and is intentionally thin. The renderer cannot reach Node or filesystem APIs directly; it uses the Electron preload bridge and the main-process IPC boundary, which validates requests before forwarding them to the local API.

## Layer boundaries

### Python engine

The core implementation is in `Component-llamacoder/neeka` and includes:

- `brain/`: domain models, workflow rules, events, and engine logic
- `persistence/`: repository interfaces, SQLite repositories, migrations, backups, and sessions
- `api/`: FastAPI routes, schemas, dependencies, and application wiring
- `intelligence/`: provider-neutral planning and permission enforcement
- `knowledge/`: project knowledge, requirements, decisions, notes, references, and search
- `artifacts/`: file storage, validation, checksum handling, and project/task attachment logic

### Desktop shell

The desktop app is in `desktop/` and uses Electron + React + TypeScript. It is designed as a local client shell, not as a second implementation of business logic.

### Data and persistence

SQLite is the persistence layer. The database is versioned with migrations and tests exercise restart/recovery, persistence, membership rules, and artifact handling.

## Project knowledge and artifacts

Knowledge and artifacts are intentionally separated from task state:

- Project knowledge stores documents, requirements, decisions, notes, references, tags, and relationships.
- Artifacts represent the actual uploaded files, with local storage, validation, checksum tracking, and project-membership access control.
- Both systems emit events through the same Brain event pipeline and inherit the same workflow safety rules.

## Security and trust assumptions

The current implementation is designed as a local, same-machine application boundary. It is not a full multi-user authentication system. The prominent controls are:

- renderer isolation in Electron
- API path and method validation in the main process
- project membership enforcement in application services
- intelligence permission modes for read-only, assisted, and autonomous actions

## Current verified status

Verified during this pass:

- backend API and workflow tests pass
- TypeScript compile check passes
- the desktop UI is wired to live backend routes for projects, tasks, knowledge, and artifacts

Open blockers remain:

- the desktop Vitest run is blocked by a local Windows native Rollup policy issue
- Windows packaging is not yet fully validated in this environment

This architecture remains valid despite those blockers; the central principle is still that the Python engine remains authoritative and the desktop shell stays thin.