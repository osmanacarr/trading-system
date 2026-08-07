import type { NextConfig } from "next";
import path from "node:path";

// dashboard/ repo kokunun ALT dizini (bkz. lib/paths.ts) - paper_trading/
// dosyalari dashboard/'un DISINDA, kardes bir klasorde. Vercel'de "Root
// Directory" = dashboard olarak ayarlandiginda, varsayilan tracing sadece
// dashboard/ alt agacini serverless fonksiyona dahil eder; paper_trading/
// disarida kalirsa API route'lari (/api/trades, /api/positions, ...) prod'da
// dosya bulamaz. outputFileTracingRoot + outputFileTracingIncludes bu ikisini
// acikca repo kokune genisletip data/log dosyalarini fonksiyon paketine dahil
// eder (bkz. README "Vercel'e deploy" - Root Directory monorepo ayari ile
// BIRLIKTE calisir, biri tek basina yetmez).
const REPO_ROOT = path.join(__dirname, "..");

const nextConfig: NextConfig = {
  outputFileTracingRoot: REPO_ROOT,
  outputFileTracingIncludes: {
    // paper_trading/logs ve data: yukarida aciklandigi gibi, monorepo disi.
    // better-sqlite3'un prebuilds/build/Release altindaki NATIVE (.node)
    // ikilisi: better-sqlite3/lib/binding.js bunu process.platform/arch'a
    // gore DINAMIK olarak require ediyor - @vercel/nft'in statik analizi bu
    // tur dinamik require'lari bazen tam cozemiyor (bkz. Next.js "output"
    // dokumaninin "Common include patterns for native/runtime assets"
    // notu). Acikca dahil etmek, bu yuzden state.db okumasinin (digerlerinin
    // aksine native modul gerektiren TEK route) production'da sessizce
    // bos donmesine karsi somut bir onlem.
    "/api/**": [
      "../paper_trading/logs/**",
      "../paper_trading/data/**",
      "node_modules/better-sqlite3/prebuilds/**/*",
      "node_modules/better-sqlite3/build/Release/**/*",
    ],
  },
};

export default nextConfig;
