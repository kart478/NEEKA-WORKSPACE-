import { contextBridge, ipcRenderer } from "electron";

contextBridge.exposeInMainWorld("neeka", {
  health: () => ipcRenderer.invoke("engine:health"),
  request: (request: { method?: string; path: string; body?: unknown; query?: Record<string, string> }) => ipcRenderer.invoke("api:request", request),
});