import bcrypt from "bcryptjs";
import { beforeEach, describe, expect, it } from "vitest";
import { POST } from "./route";
import { SESSION_COOKIE_NAME } from "@/lib/auth";

// Route Handler'lar sade async fonksiyonlar (standart Request alir, Response
// doner) - tam bir Next.js sunucusu ayaga kaldirmadan DOGRUDAN cagrilabilir.
function loginRequest(body: unknown): Request {
  return new Request("http://localhost/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

describe("POST /api/auth/login", () => {
  beforeEach(async () => {
    process.env.SESSION_SECRET = "test-secret-for-unit-tests-only";
    process.env.ADMIN_USERNAME = "testadmin";
    process.env.ADMIN_PASSWORD_HASH = await bcrypt.hash("correct-horse-battery-staple", 10);
  });

  it("başarısız senaryo: yanlış şifre 401 döner, cookie set edilmez", async () => {
    const res = await POST(loginRequest({ username: "testadmin", password: "wrong" }));
    expect(res.status).toBe(401);
    expect(res.headers.get("set-cookie")).toBeNull();
  });

  it("başarısız senaryo: yanlış kullanıcı adı 401 döner", async () => {
    const res = await POST(loginRequest({ username: "someone-else", password: "correct-horse-battery-staple" }));
    expect(res.status).toBe(401);
  });

  it("başarısız senaryo: eksik alan 400 döner", async () => {
    const res = await POST(loginRequest({ username: "testadmin" }));
    expect(res.status).toBe(400);
  });

  it("başarılı senaryo: doğru kimlik bilgisiyle 200 + httpOnly session cookie döner", async () => {
    const res = await POST(loginRequest({ username: "testadmin", password: "correct-horse-battery-staple" }));
    expect(res.status).toBe(200);
    const setCookie = res.headers.get("set-cookie");
    expect(setCookie).toContain(`${SESSION_COOKIE_NAME}=`);
    expect(setCookie).toContain("HttpOnly");
    expect(setCookie).toMatch(/SameSite=lax/i);
  });
});
