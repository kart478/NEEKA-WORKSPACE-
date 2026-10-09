import { app, BrowserWindow, dialog } from "electron";
import { join } from "node:path";
import { loadConfig } from "./config";
import { registerIpc } from "./ipc";
import { BackendProcessManager } from "./services/backend";

let window: BrowserWindow | undefined;
let backend: BackendProcessManager | undefined;

async function createWindow(): Promise<void> {
  const config = loadConfig();
  backend = new BackendProcessManager(config);
  registerIpc(backend);
  backend.on("log", ({ source, text }) => console.log(`[backend:${source}] ${text.trimEnd()}`));
  try {
    await backend.start();
  } catch (error) {
    await dialog.showMessageBox({ type: "error", title: "NEEKA engine unavailable", message: "NEEKA could not start its local engine.", detail: error instanceof Error ? error.message : "Unknown startup error" });
  }
  window = new BrowserWindow({
    width: 1100,
    height: 720,
    minWidth: 760,
    minHeight: 520,
    show: false,
    webPreferences: { preload: join(__dirname, "../preload/index.js"), contextIsolation: true, nodeIntegration: false, sandbox: true },
  });
  window.once("ready-to-show", () => window?.show());
  if (process.env.ELECTRON_RENDERER_URL) await window.loadURL(process.env.ELECTRON_RENDERER_URL);
  else await window.loadFile(join(__dirname, "../renderer/index.html"));
}

app.whenReady().then(createWindow);
app.on("window-all-closed", () => { if (process.platform !== "darwin") app.quit(); });
app.on("activate", () => { if (!window) void createWindow(); });
app.on("before-quit", async (event) => {
  if (!backend || backend.getState() === "STOPPING") return;
  event.preventDefault();
  await backend.stop();
  app.quit();
});