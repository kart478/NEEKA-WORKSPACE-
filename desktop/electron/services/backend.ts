import { spawn, type ChildProcess } from "node:child_process";
import { EventEmitter } from "node:events";
import { request } from "node:http";
import type { DesktopConfig } from "../config";

export type BackendState = "STARTING" | "CONNECTING" | "READY" | "DEGRADED" | "ERROR" | "STOPPING";

export class BackendProcessManager extends EventEmitter {
  private process?: ChildProcess;
  private state: BackendState = "STARTING";
  private output = "";

  constructor(private readonly config: DesktopConfig) { super(); }

  getState(): BackendState { return this.state; }
  getBaseUrl(): string { return `http://${this.config.backendHost}:${this.config.backendPort}`; }
  getLogs(): string { return this.output.slice(-12000); }

  async start(): Promise<void> {
    if (this.process) return;
    this.setState("STARTING");
    this.process = spawn(this.config.pythonExecutable, ["api_main.py"], {
      cwd: this.config.backendRoot,
      env: { ...process.env, API_HOST: this.config.backendHost, API_PORT: String(this.config.backendPort), LOG_LEVEL: this.config.logLevel },
      stdio: ["ignore", "pipe", "pipe"],
      windowsHide: true,
    });
    this.process.stdout?.on("data", (data: Buffer) => this.capture("stdout", data.toString()));
    this.process.stderr?.on("data", (data: Buffer) => this.capture("stderr", data.toString()));
    this.process.once("error", (error) => { this.capture("process", error.message); this.setState("ERROR"); });
    this.process.once("exit", (code) => {
      this.capture("process", `backend exited with code ${code ?? "unknown"}`);
      this.process = undefined;
      if (this.state !== "STOPPING") this.setState("ERROR");
    });
    this.setState("CONNECTING");
    await this.waitForHealth();
    this.setState("READY");
  }

  async waitForHealth(timeoutMs = 15000): Promise<void> {
    const deadline = Date.now() + timeoutMs;
    while (Date.now() < deadline) {
      if (this.state === "ERROR") throw new Error(`Backend failed to start: ${this.getLogs()}`);
      try {
        const health = await this.health();
        if (health.status === "ok") return;
      } catch { /* startup race: retry until the deadline */ }
      await new Promise((resolvePromise) => setTimeout(resolvePromise, 250));
    }
    this.setState("ERROR");
    throw new Error(`Backend health check timed out: ${this.getLogs()}`);
  }

  health(): Promise<{ status: string; service?: string }> {
    return new Promise((resolvePromise, reject) => {
      const requestHandle = request(`${this.getBaseUrl()}/health`, { timeout: 2000 }, (response) => {
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

  async stop(): Promise<void> {
    if (!this.process) return;
    this.setState("STOPPING");
    const child = this.process;
    await new Promise<void>((resolvePromise) => {
      const timer = setTimeout(() => { child.kill(); resolvePromise(); }, 3000);
      child.once("exit", () => { clearTimeout(timer); resolvePromise(); });
      child.kill();
    });
    this.process = undefined;
  }

  private capture(source: string, text: string): void { this.output += `[${source}] ${text}`; this.emit("log", { source, text }); }
  private setState(state: BackendState): void { this.state = state; this.emit("state", state); }
}