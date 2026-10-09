import { ipcMain } from "electron";
import type { BackendProcessManager } from "../services/backend";
import { validateApiRequest, type ApiRequest } from "../security/validation";

export function registerIpc(backend: BackendProcessManager): void {
  ipcMain.handle("engine:health", async () => {
    try { return { state: backend.getState(), health: await backend.health() }; }
    catch (error) { return { state: backend.getState(), error: error instanceof Error ? error.message : "Engine unavailable" }; }
  });
  ipcMain.handle("api:request", async (_event, rawRequest: ApiRequest) => {
    const apiRequest = validateApiRequest(rawRequest);
    const url = new URL(apiRequest.path, backend.getBaseUrl());
    Object.entries(apiRequest.query || {}).forEach(([key, value]) => url.searchParams.set(key, value));
    const response = await fetch(url, {
      method: apiRequest.method,
      headers: { "Content-Type": "application/json", "X-Request-ID": crypto.randomUUID() },
      body: apiRequest.method === "GET" ? undefined : JSON.stringify(apiRequest.body ?? {}),
    });
    const text = await response.text();
    let data: unknown;
    try { data = text ? JSON.parse(text) : undefined; } catch { throw new Error("Backend returned an invalid response"); }
    if (!response.ok) throw new Error(typeof data === "object" && data && "detail" in data ? String(data.detail) : `API request failed (${response.status})`);
    return data;
  });
}