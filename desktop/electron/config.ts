import { app } from "electron";
import { join, resolve } from "node:path";

export type DesktopEnvironment = "development" | "production";

export interface DesktopConfig {
  environment: DesktopEnvironment;
  version: string;
  backendHost: string;
  backendPort: number;
  backendRoot: string;
  pythonExecutable: string;
  logLevel: string;
}

export function loadConfig(): DesktopConfig {
  const environment = process.env.NODE_ENV === "production" ? "production" : "development";
  const backendRoot = process.env.NEEKA_BACKEND_ROOT ||
    (environment === "production" ? join(process.resourcesPath, "backend") : resolve(app.getAppPath(), "..", "Component-llamacoder"));
  return {
    environment,
    version: app.getVersion(),
    backendHost: "127.0.0.1",
    backendPort: Number(process.env.NEEKA_BACKEND_PORT || 8000),
    backendRoot,
    pythonExecutable: process.env.NEEKA_PYTHON || (environment === "production" ? join(backendRoot, "runtime", "python.exe") : "python"),
    logLevel: process.env.NEEKA_LOG_LEVEL || "INFO",
  };
}