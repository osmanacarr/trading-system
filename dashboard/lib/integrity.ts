export interface DataIntegrityCorrection {
  symbol: string;
  date: string;
  ratio: number;
}

export interface DataIntegrityStatus {
  status: "insufficient_data" | "ok";
  reason: string;
  corrections: DataIntegrityCorrection[];
}

// data/adjust.py (adjust_jumps) sicrama duzeltmelerini calisma aninda
// bellek icinde uygular ve SONUCUNU HICBIR YERE KALICI OLARAK LOGLAMAZ -
// bkz. app/api/integrity/route.ts icin ayni aciklama.
export const DATA_INTEGRITY_STATUS: DataIntegrityStatus = {
  status: "insufficient_data",
  reason: "adjust_jumps() sonuclari henuz kalici olarak loglanmiyor (runner.py tarafinda eklenmesi gerekir).",
  corrections: [],
};
