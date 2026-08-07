"use client";

import { useEffect, useState, type FormEvent } from "react";
import { useDashboard } from "@/lib/dashboard-context";
import { formatNumber } from "@/lib/format";

export function ManualEntryModal() {
  const { markingTrade, setMarkingTrade, refetch } = useDashboard();
  const [userEntryPrice, setUserEntryPrice] = useState("");
  const [userSize, setUserSize] = useState("");
  const [note, setNote] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (markingTrade) {
      setUserEntryPrice("");
      setUserSize("");
      setNote("");
      setError(null);
    }
  }, [markingTrade]);

  useEffect(() => {
    function onKeydown(e: KeyboardEvent) {
      if (e.key === "Escape") setMarkingTrade(null);
    }
    window.addEventListener("keydown", onKeydown);
    return () => window.removeEventListener("keydown", onKeydown);
  }, [setMarkingTrade]);

  if (!markingTrade) return null;

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!markingTrade) return;
    const priceNum = parseFloat(userEntryPrice);
    const sizeNum = parseFloat(userSize);
    if (!Number.isFinite(priceNum) || priceNum <= 0) {
      setError("Gecerli bir giris fiyati girin");
      return;
    }
    if (!Number.isFinite(sizeNum) || sizeNum <= 0) {
      setError("Gecerli bir miktar girin");
      return;
    }

    setSubmitting(true);
    setError(null);
    try {
      const res = await fetch("/api/manual-entry", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          symbol: markingTrade.symbol,
          signal_date: markingTrade.date,
          system_entry_price: markingTrade.price,
          user_entry_price: priceNum,
          user_size: sizeNum,
          note,
        }),
      });
      const json = await res.json();
      if (!json.ok) {
        setError(json.error ?? "Bilinmeyen hata");
        return;
      }
      await refetch();
      setMarkingTrade(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Istek gonderilemedi");
    } finally {
      setSubmitting(false);
    }
  }

  const direction = markingTrade.direction === 1 ? "LONG" : "SHORT";

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 px-4"
      onClick={() => setMarkingTrade(null)}
    >
      <form
        onSubmit={handleSubmit}
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-sm rounded-sm border border-term-border bg-term-panel-head shadow-2xl"
      >
        <div className="border-b border-term-border px-4 py-2.5">
          <p className="label-xs text-[9px]">bu sinyali aldim</p>
          <p className="mono-tabular text-sm text-term-text">
            {markingTrade.symbol}{" "}
            <span className={direction === "LONG" ? "text-term-green" : "text-term-red"}>{direction}</span>{" "}
            <span className="text-term-text-faint">
              · sistem: {formatNumber(markingTrade.price, 4)} · {markingTrade.date}
            </span>
          </p>
        </div>

        <div className="space-y-3 px-4 py-3">
          <label className="block">
            <span className="label-xs text-[9px]">gercek giris fiyati</span>
            <input
              type="number"
              step="any"
              required
              autoFocus
              value={userEntryPrice}
              onChange={(e) => setUserEntryPrice(e.target.value)}
              className="mono-tabular mt-1 w-full rounded-sm border border-term-border bg-term-panel px-2 py-1.5 text-sm text-term-text outline-none focus:border-term-cyan/50"
            />
          </label>
          <label className="block">
            <span className="label-xs text-[9px]">gercek miktar</span>
            <input
              type="number"
              step="any"
              required
              value={userSize}
              onChange={(e) => setUserSize(e.target.value)}
              className="mono-tabular mt-1 w-full rounded-sm border border-term-border bg-term-panel px-2 py-1.5 text-sm text-term-text outline-none focus:border-term-cyan/50"
            />
          </label>
          <label className="block">
            <span className="label-xs text-[9px]">not (opsiyonel)</span>
            <textarea
              value={note}
              onChange={(e) => setNote(e.target.value)}
              rows={2}
              className="mt-1 w-full rounded-sm border border-term-border bg-term-panel px-2 py-1.5 text-[12px] text-term-text outline-none focus:border-term-cyan/50"
            />
          </label>
          {error && <p className="text-[11px] leading-relaxed text-term-red">{error}</p>}
        </div>

        <div className="flex justify-end gap-2 border-t border-term-border px-4 py-2.5">
          <button
            type="button"
            onClick={() => setMarkingTrade(null)}
            className="rounded-sm px-3 py-1 text-[11px] text-term-text-dim hover:text-term-text"
          >
            vazgec
          </button>
          <button
            type="submit"
            disabled={submitting}
            className="rounded-sm border border-term-cyan/40 bg-term-cyan-dim px-3 py-1 text-[11px] text-term-cyan disabled:opacity-50"
          >
            {submitting ? "kaydediliyor..." : "kaydet"}
          </button>
        </div>
      </form>
    </div>
  );
}
