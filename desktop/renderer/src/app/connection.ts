export type ConnectionState = "STARTING" | "CONNECTING" | "READY" | "DEGRADED" | "ERROR" | "STOPPING";

export function connectionStateFromHealth(result: { health?: { status: string }; error?: string }): ConnectionState {
  if (result.health?.status === "ok") return "READY";
  return result.error ? "ERROR" : "DEGRADED";
}