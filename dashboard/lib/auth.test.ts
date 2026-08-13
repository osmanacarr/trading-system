import { beforeEach, describe, expect, it } from "vitest";
import { createSessionToken, verifySessionToken } from "./auth";

describe("lib/auth", () => {
  beforeEach(() => {
    process.env.SESSION_SECRET = "test-secret-for-unit-tests-only";
  });

  it("creates a token that verifies back to the same username", async () => {
    const token = await createSessionToken("alice");
    const session = await verifySessionToken(token);
    expect(session).not.toBeNull();
    expect(session?.username).toBe("alice");
  });

  it("rejects a tampered token", async () => {
    const token = await createSessionToken("alice");
    const tampered = token.slice(0, -2) + "xx";
    const session = await verifySessionToken(tampered);
    expect(session).toBeNull();
  });

  it("rejects an empty/garbage token", async () => {
    expect(await verifySessionToken("")).toBeNull();
    expect(await verifySessionToken("not-a-jwt")).toBeNull();
  });

  it("rejects a token signed with a different secret", async () => {
    const token = await createSessionToken("alice");
    process.env.SESSION_SECRET = "a-different-secret";
    const session = await verifySessionToken(token);
    expect(session).toBeNull();
  });
});
