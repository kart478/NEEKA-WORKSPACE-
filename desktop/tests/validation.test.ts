import { describe, expect, it } from "vitest";
import { validateApiRequest } from "../electron/security/validation";

describe("IPC API validation", () => {
  it("accepts only scoped API requests", () => {
    expect(validateApiRequest({ path: "/api/v1/projects", query: { page: "1" } }).method).toBe("GET");
    expect(() => validateApiRequest({ path: "/health" })).toThrow();
    expect(() => validateApiRequest({ path: "/api/v1/../health" })).toThrow();
    expect(() => validateApiRequest({ path: "/api/v1/projects", method: "PUT" })).toThrow();
  });
});