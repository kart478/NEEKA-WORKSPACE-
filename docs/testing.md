# Testing

The repository contains both backend Python tests and a small desktop TypeScript validation suite.

## Backend tests

Run from the backend project root:

```powershell
cd "C:\Users\SISO\Desktop\NEEKA WORKSPACE\Component-llamacoder"
python -m pytest tests -q
```

Verified outcome in this environment:

- 36 tests passed
- 0 failed
- 0 skipped

## Desktop tests

Run from the desktop root:

```powershell
cd "C:\Users\SISO\Desktop\NEEKA WORKSPACE\desktop"
npm test -- --run
```

Verified outcome in this environment:

- command fails before tests execute
- root cause: the Windows native Rollup binary was blocked by local App Control policy
- error: missing or blocked `@rollup/rollup-win32-x64-msvc`

## TypeScript validation

This check is still useful and was executed successfully:

```powershell
cd "C:\Users\SISO\Desktop\NEEKA WORKSPACE\desktop"
npm run typecheck
```

Result:

- TypeScript compile check passed

## What this means

The backend is stable from a Python test perspective. The desktop test layer is structurally present and the code compiles, but a native dependency on the host machine prevents the Vitest suite from running in this environment.

## Recommended validation after environment issue is removed

1. clear the stale local install or restore the Windows package set
2. run `npm install` again in `desktop/`
3. execute `npm test -- --run`
4. execute `npm run build`
5. execute `npm run package:win`

Do not treat the desktop suite as passing until the native dependency is available and the tests run successfully on the Windows host.