import { SignJWT, jwtVerify } from "jose";

// Basit, tek-kullanicili oturum yonetimi (2026-08-13, kullanicinin acik
// guvenlik kurallarina gore - bkz. ilgili konusma):
// - Sifre DUZ METIN olarak hicbir yerde YOK - sadece bcrypt hash'i
//   (ADMIN_PASSWORD_HASH) Vercel env variable'inda tutulur, koda GOMULMEZ.
// - Oturum, imzali/stateless bir JWT (jose - Edge runtime uyumlu, middleware
//   Node degil Edge'de calisir) - sunucu tarafinda bir session store YOK
//   (Vercel serverless fonksiyonlari stateless, bu basitligi ZORUNLU kilar).
// - Cookie httpOnly+secure+sameSite=lax - localStorage'da TUTULMAZ (XSS riski).
export const SESSION_COOKIE_NAME = "session";
export const SESSION_MAX_AGE_SECONDS = 60 * 60 * 24 * 7; // 7 gun

function getSecretKey(): Uint8Array {
  const secret = process.env.SESSION_SECRET;
  if (!secret) {
    throw new Error("SESSION_SECRET tanimli degil (bkz. dashboard/README.md 'Giris ekrani kurulumu')");
  }
  return new TextEncoder().encode(secret);
}

export async function createSessionToken(username: string): Promise<string> {
  return new SignJWT({ sub: username })
    .setProtectedHeader({ alg: "HS256" })
    .setIssuedAt()
    .setExpirationTime(`${SESSION_MAX_AGE_SECONDS}s`)
    .sign(getSecretKey());
}

export async function verifySessionToken(token: string): Promise<{ username: string } | null> {
  try {
    const { payload } = await jwtVerify(token, getSecretKey());
    if (typeof payload.sub !== "string") return null;
    return { username: payload.sub };
  } catch {
    return null; // suresi gecmis, imzasi gecersiz, bozuk - hepsi "gecersiz oturum"
  }
}
