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

- 2 tests passed
- 2 test files passed

## TypeScript validation

This check is still useful and was executed successfully:

```powershell
cd "C:\Users\SISO\Desktop\NEEKA WORKSPACE\desktop"
npm run typecheck
```

Result:

- TypeScript compile check passed

## Production build

Run from the desktop root:

```powershell
npm run build
```

Verified outcome in this environment:

- Electron main, preload, and renderer bundles built successfully

## Recommended additional validation

1. execute `npm run package:win`
2. launch the packaged installer and verify the backend lifecycle

Do not treat the desktop suite as passing until the native dependency is available and the tests run successfully on the Windows host.