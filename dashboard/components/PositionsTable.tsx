"use client";

import { useMemo, useState } from "react";
import clsx from "clsx";
import { useDashboard } from "@/lib/dashboard-context";
import { formatDaysSince, formatNumber } from "@/lib/format";
import { classifyMarket } from "@/lib/market";
import { directionApplicability } from "@/lib/constants";
import { estimateRemainingHold } from "@/lib/holdingEstimate";
import { Panel } from "./ui/Panel";
import { EmptyState } from "./ui/EmptyState";
import { Badge } from "./ui/Badge";
import { FlashNumber } from "./ui/FlashNumber";
import type { PricedOpenPosition } from "@/lib/types";

type SortKey = "symbol" | "direction" | "entry_price" | "stop_dist" | "entry_date" | "pnl";

const COLUMNS: { key: SortKey; label: string }[] = [
  { key: "symbol", label: "sembol" },
  { key: "direction", label: "yon" },
  { key: "entry_price", label: "giris fiyati" },
  { key: "stop_dist", label: "stop mesafesi" },
  { key: "entry_date", label: "sure" },
];

function stopDistancePct(pos: PricedOpenPosition): number {
  return ((pos.stop_price - pos.entry_price) / pos.entry_price) * pos.direction * -1;
}

export function PositionsTable() {
  const { data, selectedSymbol, setSelectedSymbol } = useDashboard();
  const positions = data?.positions ?? [];
  const positionsError = data?.positionsError ?? null;
  // summary.json (runner.py'nin kendi yazdigi open_positions sayisi) ile
  // state.db'den okunan liste uyusmuyorsa - positionsError null olsa bile -
  // bu, state.db'nin BASKA bir nedenle (ornegin gelecekte farkli bir
  // native-modul/bundling sorunu) sessizce eksik okundugunun isaretidir.
  // "Sistem Gunlugu'nde GIRIS var ama Acik Pozisyonlar 0 pozisyon diyor"
  // celiskisi tam olarak boyle ortaya cikmisti (bkz. ilgili konusma) -
  // bu kontrol ayni sinif hatanin sessizce tekrarlanmasini engeller.
  const expectedCount = data?.summary?.open_positions ?? null;
  const mismatch = !positionsError && expectedCount !== null && expectedCount !== positions.length;
  const [sortKey, setSortKey] = useState<SortKey>("symbol");
  const [sortDir, setSortDir] = useState<1 | -1>(1);

  const sorted = useMemo(() => {
    const copy = [...positions];
    copy.sort((a, b) => {
      let cmp = 0;
      if (sortKey === "symbol") cmp = a.symbol.localeCompare(b.symbol);
      else if (sortKey === "direction") cmp = a.direction - b.direction;
      else if (sortKey === "entry_price") cmp = a.entry_price - b.entry_price;
      else if (sortKey === "stop_dist") cmp = stopDistancePct(a) - stopDistancePct(b);
      else if (sortKey === "entry_date") cmp = a.entry_date.localeCompare(b.entry_date);
      else if (sortKey === "pnl") cmp = (a.unrealized_pnl_pct ?? -Infinity) - (b.unrealized_pnl_pct ?? -Infinity);
      return cmp * sortDir;
    });
    return copy;
  }, [positions, sortKey, sortDir]);

  function toggleSort(key: SortKey) {
    if (key === sortKey) setSortDir((d) => (d === 1 ? -1 : 1));
    else {
      setSortKey(key);
      setSortDir(1);
    }
  }

  return (
    <Panel
      title="açık pozisyonlarım — canlı"
      right={
        <span className="flex items-center gap-1.5">
          {(positionsError || mismatch) && (
            <Badge tone="amber">⚠ {positionsError ? "okuma hatasi" : "tutarsizlik"}</Badge>
          )}
          <span className="label-xs text-[9px]">{positions.length} pozisyon</span>
        </span>
      }
    >
      {positionsError ? (
        <EmptyState
          title="pozisyon verisi okunamadi"
          hint={`state.db acilamadi/okunamadi - bu bir "acik pozisyon yok" degil, bir okuma hatasi (${positionsError})`}
        />
      ) : mismatch ? (
        <EmptyState
          title="veri tutarsizligi"
          hint={`summary.json ${expectedCount} acik pozisyon diyor ama state.db'den ${positions.length} okundu - sayfa yenilendiginde duzelmezse dashboard/README "Vercel'e deploy" adimlarini kontrol edin`}
        />
      ) : positions.length === 0 ? (
        <EmptyState title="aktif pozisyon yok, sinyal bekleniyor" />
      ) : (
        <div className="overflow-x-auto scroll-thin">
          <table className="w-full min-w-[560px] text-[11px]">
            <thead>
              <tr className="border-b border-term-border-soft">
                {COLUMNS.map((col) => (
                  <th
                    key={col.key}
                    onClick={() => toggleSort(col.key)}
                    className="cursor-pointer select-none px-3 py-1.5 text-left label-xs text-[9px] hover:text-term-cyan"
                  >
                    {col.label}
                    {sortKey === col.key && <span className="ml-1 text-term-cyan">{sortDir === 1 ? "↑" : "↓"}</span>}
                  </th>
                ))}
                <th className="px-3 py-1.5 text-left label-xs text-[9px]">guncel fiyat</th>
                <th
                  onClick={() => toggleSort("pnl")}
                  className="cursor-pointer select-none px-3 py-1.5 text-left label-xs text-[9px] hover:text-term-cyan"
                >
                  p&amp;l{sortKey === "pnl" && <span className="ml-1 text-term-cyan">{sortDir === 1 ? "↑" : "↓"}</span>}
                </th>
                <th className="px-3 py-1.5 text-left label-xs text-[9px]">ne zaman kapanabilir</th>
                <th className="px-3 py-1.5 text-left label-xs text-[9px]">piyasa</th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((pos) => {
                const isSelected = selectedSymbol === pos.symbol;
                const eta = estimateRemainingHold(pos.strategy, pos.direction, pos.entry_date);
                return (
                  <tr
                    key={`${pos.symbol}::${pos.strategy}`}
                    onClick={() => setSelectedSymbol(isSelected ? null : pos.symbol)}
                    className={clsx(
                      "cursor-pointer border-b border-term-border-soft/60 transition-colors hover:bg-white/[0.02]",
                      isSelected && "bg-term-cyan-dim",
                      pos.is_near_stop && !isSelected && "bg-term-amber-dim/30"
                    )}
                  >
                    <td className="px-3 py-1.5 font-medium text-term-text mono-tabular">
                      {pos.symbol}
                      {pos.is_near_stop && (
                        <span className="ml-1.5" title="Stop'a yaklasiyor">
                          <Badge tone="amber">⚠ STOP&apos;A YAKIN</Badge>
                        </span>
                      )}
                    </td>
                    <td className="px-3 py-1.5">
                      <span className="flex items-center gap-1">
                        <Badge tone={pos.direction === 1 ? "green" : "red"}>{pos.direction === 1 ? "LONG" : "SHORT"}</Badge>
                        {(() => {
                          const app = directionApplicability(pos.direction);
                          return (
                            <span title={app.hint}>
                              <Badge tone={app.applicable ? "green" : "amber"}>{app.label}</Badge>
                            </span>
                          );
                        })()}
                      </span>
                    </td>
                    <td className="px-3 py-1.5 mono-tabular text-term-text-dim">{formatNumber(pos.entry_price, 4)}</td>
                    <td className="px-3 py-1.5 mono-tabular text-term-amber">{(stopDistancePct(pos) * 100).toFixed(2)}%</td>
                    <td className="px-3 py-1.5 mono-tabular text-term-text-dim" title="Acilis tarihinden bu yana">
                      {formatDaysSince(pos.entry_date)}
                    </td>
                    <td className="px-3 py-1.5">
                      {pos.current_price !== null ? (
                        <FlashNumber value={pos.current_price} format={(v) => formatNumber(v, 4)} className="text-term-text" />
                      ) : (
                        <span className="text-term-text-faint" title="action_sheet.json henuz bu sembol icin fiyat icermiyor (ilk gunluk calistirma bekleniyor)">
                          fiyat bekleniyor
                        </span>
                      )}
                    </td>
                    <td className="px-3 py-1.5">
                      {pos.unrealized_pnl_pct !== null ? (
                        <FlashNumber
                          value={pos.unrealized_pnl_pct}
                          format={(v) => `${v >= 0 ? "+" : ""}${v.toFixed(2)}%`}
                          colorByValue
                          pulse
                        />
                      ) : (
                        <span className="text-term-text-faint">—</span>
                      )}
                    </td>
                    <td className="px-3 py-1.5 text-[10px] leading-snug text-term-text-dim" style={{ maxWidth: 220 }}>
                      {eta ?? <span className="text-term-text-faint">—</span>}
                    </td>
                    <td className="px-3 py-1.5">
                      <span className="label-xs text-[9px]">{classifyMarket(pos.symbol)}</span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </Panel>
  );
}
