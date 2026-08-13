"use client";

import { useEffect, useState } from "react";
import clsx from "clsx";
import { useDashboard } from "@/lib/dashboard-context";
import { formatNumber } from "@/lib/format";
import { RISK_PER_TRADE } from "@/lib/constants";
import { computePositionSize } from "@/lib/positionSizing";
import { Badge } from "./ui/Badge";
import { EmptyState } from "./ui/EmptyState";
import { ValidationBadge } from "./ui/ValidationBadge";
import type { ActionSheetEntry } from "@/lib/types";

// Gercek sermaye SADECE bu tarayicida saklanir, sunucuya HIC gonderilmez
// (bkz. paper_trading/action_sheet.py modul docstring'i - gorev tanimindaki
// acik gizlilik kisiti). localStorage anahtari kasitli olarak repo adiyla
// prefix'li (baska bir uygulamayla cakismasin diye).
const CAPITAL_STORAGE_KEY = "bb-trade:real-capital";

function useRealCapital(): [number | null, (value: number | null) => void] {
  const [capital, setCapitalState] = useState<number | null>(null);

  useEffect(() => {
    const raw = window.localStorage.getItem(CAPITAL_STORAGE_KEY);
    const parsed = raw ? Number(raw) : NaN;
    if (Number.isFinite(parsed) && parsed > 0) setCapitalState(parsed);
  }, []);

  function setCapital(value: number | null) {
    setCapitalState(value);
    if (value === null) window.localStorage.removeItem(CAPITAL_STORAGE_KEY);
    else window.localStorage.setItem(CAPITAL_STORAGE_KEY, String(value));
  }

  return [capital, setCapital];
}

function formatMinutesAgo(iso: string | undefined): string {
  if (!iso) return "bilinmiyor";
  const then = new Date(iso).getTime();
  if (!Number.isFinite(then)) return "bilinmiyor";
  const minutes = Math.max(0, Math.round((Date.now() - then) / 60_000));
  if (minutes === 0) return "az önce";
  if (minutes === 1) return "1 dakika önce";
  return `${minutes} dakika önce`;
}

function PriceAndPnl({ entry }: { entry: ActionSheetEntry }) {
  if (entry.current_price === null) {
    return <p className="mt-2 text-[10px] text-term-text-faint">canlı fiyat henüz yok</p>;
  }
  const pnl = entry.unrealized_pnl_pct;
  return (
    <div className="mt-2 flex items-center justify-between gap-2 rounded-sm border border-term-border-soft bg-term-bg-1/40 px-2 py-1">
      <span className="label-xs text-[9px] text-term-text-dim">
        güncel <span className="mono-tabular text-term-text">{formatNumber(entry.current_price, 2)}</span>
      </span>
      {pnl !== null && (
        <span className={clsx("mono-tabular text-[11px] font-semibold", pnl >= 0 ? "text-term-green" : "text-term-red")}>
          P&amp;L {pnl >= 0 ? "+" : ""}
          {pnl.toFixed(2)}%
        </span>
      )}
    </div>
  );
}

function ActionStepCard({ entry, capital }: { entry: ActionSheetEntry; capital: number | null }) {
  const stopPct = entry.entry_price > 0 ? (Math.abs(entry.entry_price - entry.stop_price) / entry.entry_price) * 100 : 0;
  const size = capital !== null ? computePositionSize(capital, RISK_PER_TRADE, entry.entry_price, entry.stop_price) : null;
  const quantity = size !== null ? Math.floor(size) : null; // kesirli hisse yok

  return (
    <div
      className={clsx(
        "rounded-sm border p-3",
        entry.is_new_today ? "border-term-green/50 bg-term-green-dim" : "border-term-border bg-term-panel/60"
      )}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="mono-tabular text-sm font-semibold text-term-text">{entry.symbol}</span>
        <div className="flex items-center gap-1.5">
          {entry.is_new_today && <Badge tone="green">YENİ FIRSAT</Badge>}
          {entry.is_near_stop && <Badge tone="amber">⚠ STOP&apos;A YAKIN</Badge>}
          <ValidationBadge status={entry.validation_status} />
          <Badge tone="green">LONG</Badge>
        </div>
      </div>

      <div className="mt-2 grid grid-cols-3 gap-2 text-center">
        <div>
          <p className="label-xs text-[9px]">giriş</p>
          <p className="mono-tabular text-lg font-bold text-term-text">{formatNumber(entry.entry_price, 2)}</p>
        </div>
        <div>
          <p className="label-xs text-[9px]">stop</p>
          <p className="mono-tabular text-lg font-bold text-term-red">{formatNumber(entry.stop_price, 2)}</p>
        </div>
        <div>
          <p className="label-xs text-[9px]">miktar</p>
          <p className="mono-tabular text-lg font-bold text-term-cyan">
            {quantity !== null ? `${quantity} adet` : "sermaye girin"}
          </p>
        </div>
      </div>

      <PriceAndPnl entry={entry} />

      <p className="mt-2 text-[10px] leading-relaxed text-term-text-dim">{entry.exit_explanation}</p>

      <ol className="mt-2 list-decimal space-y-0.5 pl-4 text-[10px] leading-relaxed text-term-text-faint">
        <li>Kendi aracı kurum uygulamanızda {entry.symbol} hissesini bulun</li>
        <li>Güncel piyasa fiyatına yakın (sinyal fiyatı: {formatNumber(entry.entry_price, 2)}) LİMİT EMİR ile alın</li>
        <li>Stop-loss emrinizi {formatNumber(entry.stop_price, 2)} seviyesine koyun (bu, %{stopPct.toFixed(1)} uzaklıkta)</li>
        <li>
          Miktar:{" "}
          {quantity !== null
            ? `${quantity} adet (gerçek sermayenize göre hesaplandı)`
            : "yukarıdaki alana gerçek sermayenizi girin"}
        </li>
        <li>HER GÜN bu formu tekrar kontrol edin — stop seviyesi güncellenebilir</li>
      </ol>
    </div>
  );
}

function WatchOnlyRow({ entry }: { entry: ActionSheetEntry }) {
  const pnl = entry.unrealized_pnl_pct;
  return (
    <div className="flex flex-wrap items-center justify-between gap-2 rounded-sm border border-term-border-soft bg-term-bg-1/40 px-3 py-1.5">
      <span className="flex items-center gap-2">
        <span className="mono-tabular text-xs text-term-text-dim">{entry.symbol}</span>
        <ValidationBadge status={entry.validation_status} />
        <Badge tone="red">SHORT</Badge>
        <Badge tone="amber">SADECE İZLEME</Badge>
      </span>
      <span className="flex items-center gap-2 mono-tabular text-[10px] text-term-text-faint">
        <span>
          giriş {formatNumber(entry.entry_price, 2)} · stop {formatNumber(entry.stop_price, 2)}
          {entry.current_price !== null && <> · güncel {formatNumber(entry.current_price, 2)}</>}
        </span>
        {pnl !== null && (
          <span className={clsx("font-semibold", pnl >= 0 ? "text-term-green" : "text-term-red")}>
            {pnl >= 0 ? "+" : ""}
            {pnl.toFixed(2)}%
          </span>
        )}
      </span>
    </div>
  );
}

export function ActionSheetPanel() {
  const { data } = useDashboard();
  const sheet = data?.actionSheet ?? null;
  const [capital, setCapital] = useRealCapital();
  const [draft, setDraft] = useState("");

  const entries = sheet?.entries ?? [];
  const actionable = entries.filter((e) => e.applicable);
  const watchOnly = entries.filter((e) => !e.applicable);

  function handleSaveCapital() {
    const parsed = Number(draft);
    if (Number.isFinite(parsed) && parsed > 0) {
      setCapital(parsed);
      setDraft("");
    }
  }

  return (
    <section className="flex flex-col overflow-hidden rounded-sm border border-term-amber/40 bg-term-panel/60">
      {/* Kalici, kapatilamaz uyari (bkz. GozcuWarningBanner.tsx ile AYNI desen) */}
      <div className="flex shrink-0 flex-col items-center justify-center gap-0.5 border-b border-term-amber/40 bg-term-amber-dim px-3 py-1.5 text-center">
        <span className="label-xs text-[10px] font-semibold text-term-amber">⚠ BUGÜNÜN İŞLEM FORMU</span>
        <span className="label-xs text-[9px] text-term-amber/90">
          {sheet?.disclaimer ?? "Bu form karar destegidir, yatirim tavsiyesi degildir. Emirlerinizi kendi sorumlulugunuzda verin."}
        </span>
        {sheet && (
          <span className="label-xs text-[9px] text-term-amber/70">
            fiyatlar {formatMinutesAgo(sheet.prices_updated_at)} güncellendi
          </span>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-2 border-b border-term-border-soft px-3 py-2">
        <label className="label-xs text-[9px] text-term-text-dim" htmlFor="real-capital-input">
          gerçek sermayeniz (yalnızca bu tarayıcıda saklanır, sunucuya gönderilmez):
        </label>
        <input
          id="real-capital-input"
          type="number"
          min={0}
          placeholder={capital !== null ? String(capital) : "örn. 50000"}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSaveCapital()}
          className="w-32 rounded-sm border border-term-border bg-term-bg-1 px-2 py-1 text-[11px] mono-tabular text-term-text outline-none focus:border-term-cyan/60"
        />
        <button
          onClick={handleSaveCapital}
          className="rounded-sm border border-term-cyan/40 bg-term-cyan-dim px-2 py-1 text-[10px] text-term-cyan hover:bg-term-cyan/20"
        >
          kaydet
        </button>
        {capital !== null && (
          <span className="mono-tabular text-[10px] text-term-text-dim">kayıtlı: {formatNumber(capital, 0)}</span>
        )}
      </div>

      <div className="px-3 py-3">
        {entries.length === 0 ? (
          <EmptyState title="açık pozisyon yok" hint="uygulanabilir bir işlem oluştuğunda burada görünecek" />
        ) : (
          <>
            {actionable.length > 0 ? (
              <div className="grid grid-cols-1 gap-2 md:grid-cols-2 xl:grid-cols-3">
                {actionable.map((e) => (
                  <ActionStepCard key={`${e.symbol}::${e.strategy}`} entry={e} capital={capital} />
                ))}
              </div>
            ) : (
              <EmptyState title="bugün uygulanabilir (LONG) pozisyon yok" />
            )}

            {watchOnly.length > 0 && (
              <div className="mt-3 space-y-1">
                <p className="label-xs px-1 text-[9px] text-term-text-faint">
                  sadece izleme (SHORT — açık satış hesabı gerekir, siz uygulayamıyorsunuz)
                </p>
                {watchOnly.map((e) => (
                  <WatchOnlyRow key={`${e.symbol}::${e.strategy}`} entry={e} />
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </section>
  );
}
