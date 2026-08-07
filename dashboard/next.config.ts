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
    "/api/**": ["../paper_trading/logs/**", "../paper_trading/data/**"],
  },
};

export default nextConfig;
