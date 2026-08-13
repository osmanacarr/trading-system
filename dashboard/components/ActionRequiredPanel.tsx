"use client";

import { useState } from "react";
import { useDashboard } from "@/lib/dashboard-context";
import { ActionStepCard, useRealCapital } from "./ActionSheetPanel";
import { EmptyState } from "./ui/EmptyState";
import { Badge } from "./ui/Badge";

// "Günlük aktif trader" akışının 2. katmanı (bkz. ilgili konusma): Bugünün
// İşlem Formu (ActionSheetPanel) TÜM açık/uygulanabilir pozisyonları
// gösterir - bu panel ise SADECE aksiyon GEREKTIREN alt-kümeyi (bugün YENİ
// sinyal VEYA stop'a yaklaşan) öncelik sırasıyla (önce yeni sinyal) öne
// çıkarır. Aynı veriyi (data.actionSheet) FARKLI bir süzgeçle gösterir -
// ikinci bir veri kaynağı/route YOK.
export function ActionRequiredPanel() {
  const { data } = useDashboard();
  const [capital] = useRealCapital();
  const entries = (data?.actionSheet?.entries ?? []).filter(
    (e) => e.applicable && (e.is_new_today || e.is_near_stop)
  );
  // Once yeni sinyaller, sonra stop'a yaklasanlar (oncelik sirasi).
  const sorted = [...entries].sort((a, b) => {
    if (a.is_new_today !== b.is_new_today) return a.is_new_today ? -1 : 1;
    return 0;
  });

  if (sorted.length === 0) {
    return (
      <section className="rounded-sm border border-term-border bg-term-panel/60 px-3 py-2">
        <div className="flex items-center gap-2">
          <span className="label-xs text-[10px] text-term-text-dim">🎯 aksiyon gerektiren</span>
          <Badge tone="neutral">0</Badge>
        </div>
        <div className="mt-1">
          <EmptyState title="bugün aksiyon gerektiren bir şey yok" hint="yeni sinyal geldiğinde veya bir pozisyon stop'a yaklaştığında burada görünecek" />
        </div>
      </section>
    );
  }

  return (
    <section className="rounded-sm border border-term-green/40 bg-term-panel/60">
      <header className="flex items-center gap-2 border-b border-term-green/40 bg-term-green-dim px-3 py-1.5">
        <span className="label-xs text-[10px] font-semibold text-term-green">🎯 AKSİYON GEREKTİREN</span>
        <Badge tone="green">{sorted.length}</Badge>
      </header>
      <div className="grid grid-cols-1 gap-2 px-3 py-3 md:grid-cols-2 xl:grid-cols-3">
        {sorted.map((e) => (
          <ActionStepCard key={`${e.symbol}::${e.strategy}`} entry={e} capital={capital} />
        ))}
      </div>
    </section>
  );
}
