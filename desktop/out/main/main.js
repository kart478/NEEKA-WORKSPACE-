"use strict";
const electron = require("electron");
const node_path = require("node:path");
const node_child_process = require("node:child_process");
const node_events = require("node:events");
const node_http = require("node:http");
function loadConfig() {
  const environment = process.env.NODE_ENV === "production" ? "production" : "development";
  const backendRoot = process.env.NEEKA_BACKEND_ROOT || (environment === "production" ? node_path.join(process.resourcesPath, "backend") : node_path.resolve(electron.app.getAppPath(), "..", "Component-llamacoder"));
  return {
    environment,
    version: electron.app.getVersion(),
    backendHost: "127.0.0.1",
    backendPort: Number(process.env.NEEKA_BACKEND_PORT || 8e3),
    backendRoot,
    pythonExecutable: process.env.NEEKA_PYTHON || (environment === "production" ? node_path.join(backendRoot, "runtime", "python.exe") : "python"),
    logLevel: process.env.NEEKA_LOG_LEVEL || "INFO"
  };
}
const allowedMethods = /* @__PURE__ */ new Set(["GET", "POST", "PATCH", "DELETE"]);
function validateApiRequest(request) {
  if (!request || typeof request.path !== "string" || !request.path.startsWith("/api/v1/")) {
    throw new Error("Only NEEKA API paths are allowed");
  }
  if (request.path.includes("//") || request.path.includes("..") || request.path.includes("\\")) {
    throw new Error("Invalid API path");
  }
  const method = (request.method || "GET").toUpperCase();
  if (!allowedMethods.has(method)) throw new Error("Invalid API method");
  if (request.query && Object.keys(request.query).some((key) => !/^[A-Za-z0-9_.-]+$/.test(key))) {
    throw new Error("Invalid API query");
  }
  return { ...request, method };
}
function registerIpc(backend2) {
  electron.ipcMain.handle("engine:health", async () => {
    try {
      return { state: backend2.getState(), health: await backend2.health() };
    } catch (error) {
      return { state: backend2.getState(), error: error instanceof Error ? error.message : "Engine unavailable" };
    }
  });
  electron.ipcMain.handle("api:request", async (_event, rawRequest) => {
    const apiRequest = validateApiRequest(rawRequest);
    const url = new URL(apiRequest.path, backend2.getBaseUrl());
    Object.entries(apiRequest.query || {}).forEach(([key, value]) => url.searchParams.set(key, value));
    const response = await fetch(url, {
      method: apiRequest.method,
      headers: { "Content-Type": "application/json", "X-Request-ID": crypto.randomUUID() },
      body: apiRequest.method === "GET" ? void 0 : JSON.stringify(apiRequest.body ?? {})
    });
    const text = await response.text();
    let data;
    try {
      data = text ? JSON.parse(text) : void 0;
    } catch {
      throw new Error("Backend returned an invalid response");
    }
    if (!response.ok) throw new Error(typeof data === "object" && data && "detail" in data ? String(data.detail) : `API request failed (${response.status})`);
    return data;
  });
}
class BackendProcessManager extends node_events.EventEmitter {
  constructor(config) {
    super();
    this.config = config;
  }
  config;
  process;
  state = "STARTING";
  output = "";
  getState() {
    return this.state;
  }
  getBaseUrl() {
    return `http://${this.config.backendHost}:${this.config.backendPort}`;
  }
  getLogs() {
    return this.output.slice(-12e3);
  }
  async start() {
    if (this.process) return;
    this.setState("STARTING");
    this.process = node_child_process.spawn(this.config.pythonExecutable, ["api_main.py"], {
      cwd: this.config.backendRoot,
      env: { ...process.env, API_HOST: this.config.backendHost, API_PORT: String(this.config.backendPort), LOG_LEVEL: this.config.logLevel },
      stdio: ["ignore", "pipe", "pipe"],
      windowsHide: true
    });
    this.process.stdout?.on("data", (data) => this.capture("stdout", data.toString()));
    this.process.stderr?.on("data", (data) => this.capture("stderr", data.toString()));
    this.process.once("error", (error) => {
      this.capture("process", error.message);
      this.setState("ERROR");
    });
    this.process.once("exit", (code) => {
      this.capture("process", `backend exited with code ${code ?? "unknown"}`);
      this.process = void 0;
      if (this.state !== "STOPPING") this.setState("ERROR");
    });
    this.setState("CONNECTING");
    await this.waitForHealth();
    this.setState("READY");
  }
  async waitForHealth(timeoutMs = 15e3) {
    const deadline = Date.now() + timeoutMs;
    while (Date.now() < deadline) {
      if (this.state === "ERROR") throw new Error(`Backend failed to start: ${this.getLogs()}`);
      try {
        const health = await this.health();
        if (health.status === "ok") return;
      } catch {
      }
      await new Promise((resolvePromise) => setTimeout(resolvePromise, 250));
    }
    this.setState("ERROR");
    throw new Error(`Backend health check timed out: ${this.getLogs()}`);
  }
  health() {
    return new Promise((resolvePromise, reject) => {
      const requestHandle = node_http.request(`${this.getBaseUrl()}/health`, { timeout: 2e3 }, (response) => {
        let data = "";
        response.setEncoding("utf8");
        response.on("data", (chunk) => data += chunk);
        response.on("end", () => response.statusCode === 200 ? resolvePromise(JSON.parse(data)) : reject(new Error(`Health returned ${response.statusCode}`)));
      });
      requestHandle.on("error", reject);
      requestHandle.on("timeout", () => requestHandle.destroy(new Error("Health check timed out")));
      requestHandle.end();
    });
  }
  async stop() {
    if (!this.process) return;
    this.setState("STOPPING");
    const child = this.process;
    await new Promise((resolvePromise) => {
      const timer = setTimeout(() => {
        child.kill();
        resolvePromise();
      }, 3e3);
      child.once("exit", () => {
        clearTimeout(timer);
        resolvePromise();
      });
      child.kill();
    });
    this.process = void 0;
  }
  capture(source, text) {
    this.output += `[${source}] ${text}`;
    this.emit("log", { source, text });
  }
  setState(state) {
    this.state = state;
    this.emit("state", state);
  }
}
let window;
let backend;
async function createWindow() {
  const config = loadConfig();
  backend = new BackendProcessManager(config);
  registerIpc(backend);
  backend.on("log", ({ source, text }) => console.log(`[backend:${source}] ${text.trimEnd()}`));
  try {
    await backend.start();
  } catch (error) {
    await electron.dialog.showMessageBox({ type: "error", title: "NEEKA engine unavailable", message: "NEEKA could not start its local engine.", detail: error instanceof Error ? error.message : "Unknown startup error" });
  }
  window = new electron.BrowserWindow({
    width: 1100,
    height: 720,
    minWidth: 760,
    minHeight: 520,
    show: false,
    webPreferences: { preload: node_path.join(__dirname, "../preload/preload.js"), contextIsolation: true, nodeIntegration: false, sandbox: true }
  });
  window.once("ready-to-show", () => window?.show());
  if (process.env.ELECTRON_RENDERER_URL) await window.loadURL(process.env.ELECTRON_RENDERER_URL);
  else await window.loadFile(node_path.join(__dirname, "../renderer/index.html"));
}
electron.app.whenReady().then(createWindow);
electron.app.on("window-all-closed", () => {
  if (process.platform !== "darwin") electron.app.quit();
});
electron.app.on("activate", () => {
  if (!window) void createWindow();
});
electron.app.on("before-quit", async (event) => {
  if (!backend || backend.getState() === "STOPPING") return;
  event.preventDefault();
  await backend.stop();
  electron.app.quit();
});
