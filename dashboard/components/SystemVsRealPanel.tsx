"use client";

import clsx from "clsx";
import { useDashboard } from "@/lib/dashboard-context";
import { slippagePct } from "@/lib/manualLog";
import { formatNumber, formatPercent } from "@/lib/format";
import { Panel } from "./ui/Panel";
import { EmptyState } from "./ui/EmptyState";

export function SystemVsRealPanel() {
  const { data } = useDashboard();
  const entries = data?.manualEntries ?? [];

  return (
    <Panel title="sistem vs gercek" right={<span className="label-xs text-[9px]">{entries.length} isaretlenmis islem</span>}>
      {entries.length === 0 ? (
        <EmptyState
          title="henuz isaretlenmis islem yok"
          hint='sistem gunlugundeki bir giris sinyalinde "bu sinyali aldim" ile isaretleyin'
        />
      ) : (
        <div className="overflow-x-auto scroll-thin">
          <table className="w-full min-w-[640px] text-[11px]">
            <thead>
              <tr className="border-b border-term-border-soft">
                <th className="px-3 py-1.5 text-left label-xs text-[9px]">sembol</th>
                <th className="px-3 py-1.5 text-left label-xs text-[9px]">sinyal tarihi</th>
                <th className="px-3 py-1.5 text-left label-xs text-[9px]">sistem fiyati</th>
                <th className="px-3 py-1.5 text-left label-xs text-[9px]">gercek fiyat</th>
                <th className="px-3 py-1.5 text-left label-xs text-[9px]">slipaj</th>
                <th className="px-3 py-1.5 text-left label-xs text-[9px]">gercek miktar</th>
                <th className="px-3 py-1.5 text-left label-xs text-[9px]">not</th>
              </tr>
            </thead>
            <tbody>
              {[...entries].reverse().map((entry, i) => {
                const slip = slippagePct(entry);
                return (
                  <tr key={`${entry.symbol}-${entry.signal_date}-${i}`} className="border-b border-term-border-soft/60">
                    <td className="mono-tabular px-3 py-1.5 font-medium text-term-text">{entry.symbol}</td>
                    <td className="mono-tabular px-3 py-1.5 text-term-text-dim">{entry.signal_date}</td>
                    <td className="mono-tabular px-3 py-1.5 text-term-text-dim">
                      {entry.system_entry_price !== null ? formatNumber(entry.system_entry_price, 4) : "—"}
                    </td>
                    <td className="mono-tabular px-3 py-1.5 text-term-cyan">{formatNumber(entry.user_entry_price, 4)}</td>
                    <td
                      className={clsx(
                        "mono-tabular px-3 py-1.5",
                        slip === null ? "text-term-text-faint" : slip >= 0 ? "text-term-amber" : "text-term-green"
                      )}
                      title="Gercek giris fiyatinin sistem onerisinden farki (pozitif = daha pahaliya alindi)"
                    >
                      {slip === null ? "—" : formatPercent(slip, 2)}
                    </td>
                    <td className="mono-tabular px-3 py-1.5 text-term-text-dim">{formatNumber(entry.user_size, 4)}</td>
                    <td className="max-w-[220px] truncate px-3 py-1.5 text-term-text-faint" title={entry.note}>
                      {entry.note || "—"}
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
