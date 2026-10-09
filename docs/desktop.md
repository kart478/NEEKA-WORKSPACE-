# NEEKA Desktop Foundation

Part 8 adds a Windows-oriented Electron shell under `desktop/`. It is a
separate TypeScript project and does not move NEEKA business logic out of the
Python engine.

## Architecture

```text
React renderer -> preload bridge -> Electron main -> local HTTP API
                                             -> api_main.py -> NEEKA Brain -> SQLite
```

The renderer receives only `window.neeka.health()` and
`window.neeka.request()`. Node, filesystem, child-process, and database APIs
are never exposed to the renderer. API requests are restricted to `/api/v1/`
and validated in the main process before they reach the backend.

## Backend lifecycle

`BackendProcessManager` starts `api_main.py` on `127.0.0.1`, injects the
configured port, waits for `/health`, captures backend output, reports startup
failure, and stops the child during Electron shutdown. Development uses the
`python` command. Set `NEEKA_PYTHON` for a virtual environment. Production
expects a bundled runtime at `resources/backend/runtime/python.exe`, or an
explicit `NEEKA_PYTHON` override.

The backend binds only to loopback. This is a local trust boundary, not a
replacement for user authentication. Future releases should add a per-process
session token before allowing broader local integrations.

## Commands

From `desktop/`:

```text
npm install
npm run dev
npm test
npm run typecheck
npm run package:win
```

`npm run package:win` produces an NSIS installer named `NEEKA-Setup-<version>.exe`.
The packaging metadata includes the Python backend source as an extra resource;
embedding a Python runtime and installing backend dependencies are intentionally
left for the deployment phase.

## Current limits

The shell is intentionally not a project dashboard. Only the Overview
navigation item is active. API typing currently starts with a small client
surface; the next step is generating request/response types from FastAPI's
OpenAPI document rather than hand-maintaining a second model set.