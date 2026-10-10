# NEEKA Desktop Foundation

The desktop shell is a thin Electron front end over the real Python NEEKA API. It does not duplicate business logic; it calls the existing FastAPI service layer and keeps rendering concerns separate from work state, workflow rules, and persistence.

## Architecture

```text
React renderer -> preload bridge -> Electron main -> local HTTP API
                                             -> api_main.py -> NEEKA Brain -> SQLite
```

Key properties:

- The renderer may only use the preload bridge (`window.neeka.*`), not raw Node APIs.
- IPC validation restricts requests to `/api/v1/...` and blocks disallowed methods or traversal attempts.
- Electron main owns the local backend lifecycle and performs clean shutdowns.
- The backend remains the single source of truth for workflow, membership, knowledge, artifacts, and automation results.

## Backend lifecycle

`BackendProcessManager` starts the Python backend on `127.0.0.1`, watches the health endpoint, surfaces startup failures, and stops the child process during app shutdown. The app keeps the backend private to the local machine and intentionally avoids binding to a broader network address.

Development commands:

```powershell
cd "C:\Users\SISO\Desktop\NEEKA WORKSPACE\Component-llamacoder"
python -m pytest tests
python api_main.py
```

Desktop development commands:

```powershell
cd "C:\Users\SISO\Desktop\NEEKA WORKSPACE\desktop"
npm install
npm run dev
npm run typecheck
npm test
```

Production packaging command:

```powershell
cd "C:\Users\SISO\Desktop\NEEKA WORKSPACE\desktop"
npm run build
npm run package:win
```

## Security and protections

The desktop shell currently enforces:

- `contextIsolation: true`
- `nodeIntegration: false`
- `sandbox: true`
- API path validation before any request is forwarded to the local backend
- no direct renderer access to the filesystem or child-process APIs

This is a useful local boundary, but it is not a replacement for user authentication or a full hardened desktop trust model.

## Verified status

Currently verified:

- backend Python tests pass in the repository
- TypeScript compile check passes
- UI shell is wired to the real API surface for projects, tasks, knowledge, and artifacts

Still blocked in this environment:

- `npm test` fails because the Windows native Rollup binary (`@rollup/rollup-win32-x64-msvc`) is blocked by local App Control policy, so the desktop Vitest run cannot complete here
- full production packaging has not been verified in this environment

## Current limits

The workspace shell is functional but intentionally not a full project-management product. The app does not yet include a hardened user-authentication flow, deeper permission enforcement in the renderer, or a fully verified Windows installer build. The backend remains authoritative for all business logic and persistence.