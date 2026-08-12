"use client";

import clsx from "clsx";
import { useDashboard } from "@/lib/dashboard-context";
import { formatNumber } from "@/lib/format";
import { Badge } from "./ui/Badge";
import { EmptyState } from "./ui/EmptyState";
import type { OpportunityEntry } from "@/lib/types";

// "En Iyi N Firsat" - paper_trading/opportunities.py::RISK_WARNING ile AYNI
// felsefe: bu adaylar RISK KATMANI tarafindan REDDEDILDI (butce/korelasyon/
// net yonlu maruziyet). Action Sheet'in "yapin" tonundan BILINCLI OLARAK
// FARKLI (kirmizi/tehlike tonlu basli) - "sistem bunu ONERMIYOR, siz karar
// verirseniz riski SIZ yonetirsiniz" mesaji karismasin diye.

function QualityMetric({ label, value, suffix = "" }: { label: string; value: number | null; suffix?: string }) {
  return (
    <div className="text-center">
      <p className="label-xs text-[9px] text-term-text-faint">{label}</p>
      <p className="mono-tabular text-[11px] text-term-text-dim">
        {value !== null ? `${formatNumber(value, 2)}${suffix}` : "—"}
      </p>
    </div>
  );
}

function OpportunityCard({ entry }: { entry: OpportunityEntry }) {
  return (
    <div className="rounded-sm border border-term-red/30 bg-term-panel/60 p-3">
      <div className="flex items-center justify-between gap-2">
        <span className="mono-tabular text-sm font-semibold text-term-text">{entry.symbol}</span>
        <div className="flex items-center gap-1.5">
          <Badge tone={entry.direction === 1 ? "green" : "red"}>{entry.direction === 1 ? "LONG" : "SHORT"}</Badge>
          <Badge tone={entry.applicable ? "green" : "amber"}>{entry.applicable ? "UYGULANABILIR" : "SADECE IZLEME"}</Badge>
        </div>
      </div>

      <div className="mt-2 flex items-center justify-center gap-4 text-center">
        <div>
          <p className="label-xs text-[9px]">sinyal giris</p>
          <p className="mono-tabular text-base font-bold text-term-text">{formatNumber(entry.entry_price, 2)}</p>
        </div>
        <div>
          <p className="label-xs text-[9px]">stop</p>
          <p className="mono-tabular text-base font-bold text-term-red">{formatNumber(entry.stop_price, 2)}</p>
        </div>
      </div>

      <div className="mt-2 grid grid-cols-3 gap-1 rounded-sm border border-term-border-soft bg-term-bg-1/40 py-1.5">
        <QualityMetric label="kirilim (ATR)" value={entry.atr_distance} suffix="x" />
        <QualityMetric label="hacim orani" value={entry.volume_ratio} suffix="x" />
        <QualityMetric label="govde orani" value={entry.body_ratio} suffix="x" />
      </div>

      <div className="mt-2 rounded-sm border border-term-red/30 bg-term-red-dim px-2 py-1.5">
        <p className="text-[10px] leading-relaxed text-term-red">
          <span className="font-semibold">NEDEN ACILMADI:</span> {entry.rejection_reason}
        </p>
      </div>
    </div>
  );
}

export function OpportunitiesPanel() {
  const { data } = useDashboard();
  const opportunities = data?.opportunities ?? null;
  const entries = opportunities?.entries ?? [];

  return (
    <section className="flex flex-col overflow-hidden rounded-sm border border-term-red/40 bg-term-panel/60">
      <div className="flex shrink-0 flex-col items-center justify-center gap-0.5 border-b border-term-red/40 bg-term-red-dim px-3 py-1.5 text-center">
        <span className="label-xs text-[10px] font-semibold text-term-red">⚠ EN İYİ FIRSATLAR (RİSK BÜTÇESİ TARAFINDAN REDDEDİLDİ)</span>
        <span className="label-xs text-[9px] text-term-red/90">
          {opportunities?.risk_warning ??
            "Bu adaylar risk katmani tarafindan reddedildi - kendi hesabinizda acarsaniz riski siz yonetmelisiniz."}
        </span>
      </div>

      <div className="px-3 py-3">
        {entries.length === 0 ? (
          <EmptyState
            title="bugun reddedilen aday yok"
            hint="risk butcesi tum sinyalleri kabul etti ya da bugun hic sinyal yok"
          />
        ) : (
          <div className={clsx("grid grid-cols-1 gap-2", entries.length > 1 && "md:grid-cols-2 xl:grid-cols-3")}>
            {entries.map((e) => (
              <OpportunityCard key={`${e.symbol}::${e.strategy}`} entry={e} />
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
