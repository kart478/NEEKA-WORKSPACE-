# NEEKA Work Engine

NEEKA Work Engine is a local work-management system that keeps Python workflow, permissions, persistence, and API logic authoritative while exposing a thin desktop shell for local access.

## Current status

This repository has passed the backend Python validation suite, the TypeScript compile validation, the desktop Vitest suite, and the desktop production build. The desktop UI is wired to the real backend API for projects, tasks, knowledge, and artifacts.

## Development commands

Backend:

```powershell
cd "C:\Users\SISO\Desktop\NEEKA WORKSPACE\Component-llamacoder"
python -m pytest tests -q
python api_main.py
```

Desktop:

```powershell
# From the repository root:
cd "C:\Users\SISO\Desktop\NEEKA WORKSPACE"
npm run dev

# Or directly from the desktop project:
cd "C:\Users\SISO\Desktop\NEEKA WORKSPACE\desktop"
npm install
npm run dev
npm run typecheck
npm test -- --run
```

Production build:

```powershell
cd "C:\Users\SISO\Desktop\NEEKA WORKSPACE\desktop"
npm run build
npm run package:win
```

## Architecture

The importable implementation lives in `Component-llamacoder/neeka`:

- `brain/` contains domain models, workflow rules, events, and the application engine.
- `persistence/` contains repository interfaces, SQLite repositories, migrations, sessions, and backups.
- `api/` contains FastAPI routes and schemas behind the local service layer.
- `intelligence/` contains provider-neutral planning and permission modes.
- `knowledge/` contains project knowledge records and search.
- `artifacts/` handles file validation, storage, checksum logic, and attachment management.

The desktop shell is in `desktop/`; it calls the real backend and does not replace the Python engine.

See:

- [`docs/architecture.md`](docs/architecture.md)
- [`docs/desktop.md`](docs/desktop.md)
- [`docs/deployment.md`](docs/deployment.md)
- [`docs/testing.md`](docs/testing.md)

## Known limitations

- the production Windows installer has not been fully validated here
- the system is local-only and does not yet implement hardened user authentication for multi-user deployments
