import { Badge } from "./Badge";
import type { ValidationStatus } from "@/lib/types";

// Gozcu'nun "YATIRIM TAVSIYESI DEGILDIR" panelinden gorsel VE isimsel
// AYRIK tutmak icin (bkz. config.STRATEGY_VALIDATION_STATUS, README
// "Dogrulama durumu") - dogrulanmis (donchian, canli varsayilan) ile
// deneysel (mean_reversion, --strategies ile istege bagli) HER pozisyon/
// firsat kartinda ayirt edilir, hicbir yerde gizlenmez.
export function ValidationBadge({ status }: { status: ValidationStatus }) {
  if (status === "dogrulanmis") {
    return <Badge tone="cyan">✅ DOĞRULANMIŞ</Badge>;
  }
  return <Badge tone="neutral">🧪 DENEYSEL</Badge>;
}
