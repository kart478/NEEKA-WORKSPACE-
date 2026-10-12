import { afterEach, describe, expect, it, vi } from "vitest";
import { apiClient } from "../renderer/src/services/api/client";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("desktop API client", () => {
  it("reports a useful error when the preload bridge is unavailable", async () => {
    vi.stubGlobal("window", {});
    await expect(apiClient.request({ path: "/api/v1/projects" })).rejects.toThrow(
      "The desktop bridge is unavailable. Restart NEEKA Work Engine.",
    );
  });

  it("forwards typed requests through the preload bridge", async () => {
    const request = vi.fn().mockResolvedValue([{ id: "project-1" }]);
    vi.stubGlobal("window", { neeka: { request, health: vi.fn() } });

    await expect(apiClient.request<{ id: string }[]>({ path: "/api/v1/projects" })).resolves.toEqual([{ id: "project-1" }]);
    expect(request).toHaveBeenCalledWith({ path: "/api/v1/projects" });
  });
});
