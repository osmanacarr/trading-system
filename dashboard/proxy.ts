import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { SESSION_COOKIE_NAME, verifySessionToken } from "./lib/auth";

// Next.js 16: "middleware.ts" DEPRECATED, "proxy.ts" (bu dosya) + export
// adi "proxy" (middleware DEGIL) yerine gecti - bkz.
// node_modules/next/dist/docs/.../proxy.md "Migration to Proxy" (bu repo
// icin ONEMLI: egitim verisinde middleware.ts olarak biliniyordu, bu
// surumde ISLEMEZ/kullanilmiyor). Node.js runtime'da calisir (v16
// varsayilani), bkz. asagidaki matcher.
//
// 2026-08-13, kullanicinin acik guvenlik talebi: dashboard artik gercek
// finansal veri (equity, pozisyonlar) iceriyor, herkese acik olmamali.
// Basit/tek-kullanicili oturum (bkz. lib/auth.ts) - httpOnly cookie,
// server-side session store YOK (stateless JWT, Vercel serverless'a uygun).
export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;

  const token = request.cookies.get(SESSION_COOKIE_NAME)?.value;

  return verifySessionToken(token ?? "").then((session) => {
    if (session) return NextResponse.next();

    if (pathname.startsWith("/api/")) {
      return NextResponse.json({ error: "unauthorized" }, { status: 401 });
    }
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("from", pathname);
    return NextResponse.redirect(loginUrl);
  });
}

export const config = {
  // /login, /api/auth/login (giris denemesi icin ERISILEBILIR olmali) ve
  // statik varliklar/favicon HARIC her sey korunur (negatif lookahead,
  // bkz. proxy.md "Negative matching").
  matcher: ["/((?!login|api/auth/login|_next/static|_next/image|favicon.ico).*)"],
};
