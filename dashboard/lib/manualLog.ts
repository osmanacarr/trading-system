import type { ManualEntryRecord } from "./types";

/**
 * paper_trading/manual_log.py slippage_pct() ile BIREBIR ayni formul:
 * (user_entry_price - system_entry_price) / system_entry_price.
 * system_entry_price yoksa/0 ise None (TS'te null) doner.
 */
export function slippagePct(entry: ManualEntryRecord): number | null {
  const { system_entry_price, user_entry_price } = entry;
  if (system_entry_price === null || system_entry_price === 0) return null;
  return (user_entry_price - system_entry_price) / system_entry_price;
}
