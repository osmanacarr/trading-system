"use client";

import clsx from "clsx";
import { useGozcu } from "@/lib/gozcu-context";
import { Panel } from "../ui/Panel";
import { PulseDot } from "../ui/PulseDot";
import type { BadgeTone } from "../ui/Badge";

function minutesAgo(iso: string | null): number | null {
  if (!iso) return null;
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return null;
  return Math.max(0, Math.round((Date.now() - then) / 60_000));
}

function ageTone(minutes: number | null): BadgeTone {
  if (minutes === null) return "neutral";
  if (minutes <= 10) return "green";
  if (minutes <= 30) return "amber";
  return "red";
}

export function SystemHealthPanel() {
  const { snapshot, activeMarket, killSwitchOn, setKillSwitchOn, lastFetchedAt } = useGozcu();
  const market = snapshot?.markets?.[activeMarket];
  const age = minutesAgo(market?.scanned_at ?? null);
  const tone = ageTone(age);

  return (
    <Panel title="sistem sağlığı">
      <div className="flex flex-col gap-2 px-3 py-3">
        <div className="flex items-center justify-between">
          <span className="label-xs text-[9px]">son tarama</span>
          <span className="flex items-center gap-1.5">
            <PulseDot tone={tone} live={tone === "green"} />
            <span className="mono-tabular text-[11px]">{age !== null ? `${age} dk önce` : "hiç taranmadı"}</span>
          </span>
        </div>
        <div className="flex items-center justify-between">
          <span className="label-xs text-[9px]">taranan / hatalı</span>
          <span className="mono-tabular text-[11px]">
            {market?.scanned_count ?? 0} / {market?.error_count ?? 0}
          </span>
        </div>
        <div className="flex items-center justify-between">
          <span className="label-xs text-[9px]">evren büyüklüğü</span>
          <span className="mono-tabular text-[11px]">{market?.universe_size ?? 0}</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="label-xs text-[9px]">bu sekmede son sayfa yenilemesi</span>
          <span className="mono-tabular text-[10px] text-term-text-dim">
            {lastFetchedAt ? lastFetchedAt.toLocaleTimeString("tr-TR") : "—"}
          </span>
        </div>
        <button
          onClick={() => setKillSwitchOn(!killSwitchOn)}
          className={clsx(
            "mt-1 flex items-center justify-center gap-1.5 rounded-sm border px-2 py-1 text-[10px] font-medium tracking-wide transition-colors",
            killSwitchOn
              ? "border-term-red/40 bg-term-red-dim text-term-red"
              : "border-term-border text-term-text-dim hover:text-term-text"
          )}
          title="Sadece BU SEKMEDEKI otomatik yenilemeyi durdurur/başlatır — arka plandaki GitHub Actions taramasını ETKİLEMEZ"
        >
          {killSwitchOn ? "▶ bu sekmede yenilemeyi başlat" : "⏸ bu sekmede yenilemeyi durdur"}
        </button>
        <p className="label-xs text-[8px] leading-relaxed text-term-text-faint">
          kill-switch sadece bu tarayıcı sekmesini etkiler; arka plandaki tarama devam eder.
        </p>
      </div>
    </Panel>
  );
}
