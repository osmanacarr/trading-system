"use client";

import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

// Bloomberg Terminal login ekranina benzer, sade/profesyonel giris ekrani
// (2026-08-13, kullanicinin acik tasarim talebi). Sifre asla client-side
// state disina (localStorage, vs.) YAZILMAZ - sadece fetch govdesinde bir
// kez POST edilir, sunucu bcrypt.compare ile dogrular (bkz. app/api/auth/
// login/route.ts).
function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const res = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        setError(data.error ?? "giriş başarısız");
        setSubmitting(false);
        return;
      }
      const from = searchParams.get("from");
      router.replace(from && from.startsWith("/") ? from : "/");
      router.refresh();
    } catch {
      setError("sunucuya ulaşılamadı");
      setSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-term-bg-0 px-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <h1 className="mono-tabular text-3xl font-bold tracking-[0.2em] text-term-cyan">AOFTRADE</h1>
          <p className="mt-2 text-[10px] tracking-widest text-term-text-faint">PAPER TRADING TERMINAL</p>
        </div>

        <form
          onSubmit={handleSubmit}
          className="flex flex-col gap-3 rounded-sm border border-term-border bg-term-panel/60 p-5"
        >
          <div className="flex flex-col gap-1">
            <label htmlFor="username" className="label-xs text-[9px] text-term-text-dim">
              kullanıcı adı
            </label>
            <input
              id="username"
              type="text"
              autoComplete="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="rounded-sm border border-term-border bg-term-bg-1 px-3 py-2 text-[13px] mono-tabular text-term-text outline-none focus:border-term-cyan/60"
              autoFocus
            />
          </div>
          <div className="flex flex-col gap-1">
            <label htmlFor="password" className="label-xs text-[9px] text-term-text-dim">
              şifre
            </label>
            <input
              id="password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="rounded-sm border border-term-border bg-term-bg-1 px-3 py-2 text-[13px] mono-tabular text-term-text outline-none focus:border-term-cyan/60"
            />
          </div>

          {error && <p className="text-[11px] text-term-red">{error}</p>}

          <button
            type="submit"
            disabled={submitting || !username || !password}
            className="mt-2 rounded-sm border border-term-cyan/40 bg-term-cyan-dim py-2 text-[12px] font-medium tracking-wide text-term-cyan transition-colors hover:bg-term-cyan/20 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {submitting ? "giriş yapılıyor…" : "GİRİŞ"}
          </button>
        </form>

        <p className="mt-4 text-center text-[9px] text-term-text-faint">
          bu form karar desteğidir, yatırım tavsiyesi değildir
        </p>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={null}>
      <LoginForm />
    </Suspense>
  );
}
