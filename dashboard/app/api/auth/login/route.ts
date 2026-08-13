import bcrypt from "bcryptjs";
import { NextResponse } from "next/server";
import { createSessionToken, SESSION_COOKIE_NAME, SESSION_MAX_AGE_SECONDS } from "@/lib/auth";

export const dynamic = "force-dynamic";

// Sifre karsilastirmasi SADECE burada (Node runtime route handler) yapilir -
// duz metin sifre hicbir yerde saklanmaz, sadece istek govdesinde bir kez
// gecer ve ADMIN_PASSWORD_HASH'e (Vercel env variable, bcrypt hash) karsi
// dogrulanir. Basarili girişte httpOnly+secure+sameSite cookie set edilir -
// localStorage KULLANILMAZ (bkz. lib/auth.ts, proxy.ts modul yorumlari).
export async function POST(request: Request) {
  let body: { username?: unknown; password?: unknown };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "geçersiz istek" }, { status: 400 });
  }

  const { username, password } = body;
  if (typeof username !== "string" || typeof password !== "string" || !username || !password) {
    return NextResponse.json({ error: "kullanıcı adı ve şifre gerekli" }, { status: 400 });
  }

  const adminUsername = process.env.ADMIN_USERNAME;
  const adminPasswordHash = process.env.ADMIN_PASSWORD_HASH;
  if (!adminUsername || !adminPasswordHash) {
    console.error("[auth] ADMIN_USERNAME/ADMIN_PASSWORD_HASH tanimli degil (bkz. dashboard/README.md)");
    return NextResponse.json({ error: "sunucu yapılandırması eksik" }, { status: 500 });
  }

  // Kullanici adi karsilastirmasi sabit-zamanli OLMAK ZORUNDA DEGIL (gizli
  // bir deger degil, bcrypt.compare zaten sifre tarafinda zamanlama
  // saldirisina karsi tasarlanmis) - basit esitlik yeterli.
  const usernameOk = username === adminUsername;
  const passwordOk = await bcrypt.compare(password, adminPasswordHash);

  if (!usernameOk || !passwordOk) {
    return NextResponse.json({ error: "kullanıcı adı veya şifre hatalı" }, { status: 401 });
  }

  const token = await createSessionToken(username);
  const response = NextResponse.json({ ok: true });
  response.cookies.set({
    name: SESSION_COOKIE_NAME,
    value: token,
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: SESSION_MAX_AGE_SECONDS,
  });
  return response;
}
