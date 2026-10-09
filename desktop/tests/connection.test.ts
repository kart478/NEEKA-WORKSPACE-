import { describe, expect, it } from "vitest";
import { connectionStateFromHealth } from "../renderer/src/app/connection";

describe("desktop connection state", () => {
  it("maps engine health into user-facing states", () => {
    expect(connectionStateFromHealth({ health: { status: "ok" } })).toBe("READY");
    expect(connectionStateFromHealth({ health: { status: "warming" } })).toBe("DEGRADED");
    expect(connectionStateFromHealth({ error: "offline" })).toBe("ERROR");
  });
});