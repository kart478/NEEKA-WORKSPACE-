# Deployment

This project is currently designed for a local desktop deployment model: a Python backend runs on `127.0.0.1` and an Electron client connects to it through the local IPC and API bridge.

## Local development deployment

Backend:

```powershell
cd "C:\Users\SISO\Desktop\NEEKA WORKSPACE\Component-llamacoder"
python api_main.py
```

Desktop shell:

```powershell
cd "C:\Users\SISO\Desktop\NEEKA WORKSPACE\desktop"
npm install
npm run dev
```

## Production build command

The project currently exposes a Windows packaging command:

```powershell
cd "C:\Users\SISO\Desktop\NEEKA WORKSPACE\desktop"
npm run build
npm run package:win
```

This is intended to create an NSIS installer named `NEEKA-Setup-<version>.exe`.

## Production readiness notes

The packaging metadata is present in `desktop/package.json`, including:

- `electron-builder` configuration
- extra resource packaging for the Python backend
- `nsis` installer settings

However, production packaging is not fully verified in this environment. The known blocker is the Windows native Rollup dependency issue that prevents `npm test` and, by extension, a clean local validation of the packaged desktop build path.

## Storage and persistence

The backend persists state in SQLite and writes artifact data to local application-managed storage. The app is not designed to write production data into a read-only installation directory.

## Recommended next step

Before declaring deployment ready, re-run the full desktop validation in a Windows environment without the App Control policy blocking the Rollup native dependency, then verify the packaged installer can start the backend, preserve user data, and complete a normal app lifecycle.