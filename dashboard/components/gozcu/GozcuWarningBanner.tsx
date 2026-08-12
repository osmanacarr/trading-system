import { GOZCU_DATA_STALENESS_ESTIMATE_MINUTES } from "@/lib/constants";

// KALICI, kapatilamaz uyari seridi (bkz. gorev tanimi Bolum 9) - bilincli
// olarak bir kapatma/dismiss butonu YOK.
export function GozcuWarningBanner() {
  return (
    <div className="flex shrink-0 flex-col items-center justify-center gap-0.5 border-b border-term-amber/40 bg-term-amber-dim px-3 py-1.5 text-center">
      <div className="flex items-center gap-2">
        <span className="mono-tabular text-[11px] font-semibold text-term-amber">⚠ GÖZCÜ</span>
        <span className="label-xs text-[10px] text-term-amber">
          bu panel YATIRIM TAVSİYESİ DEĞİLDİR — sadece dikkat çeken piyasa hareketlerini gösterir
        </span>
      </div>
      <span className="label-xs text-[9px] text-term-amber/80">
        bu veri en fazla ~{GOZCU_DATA_STALENESS_ESTIMATE_MINUTES} dakika gecikmeli olabilir (ücretsiz/gerçek-zamanlı-olmayan
        veri kaynağı) — kesin zamanlama için kullanmayın
      </span>
    </div>
  );
}
