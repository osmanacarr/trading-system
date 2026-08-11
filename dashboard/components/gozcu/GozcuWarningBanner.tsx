// KALICI, kapatilamaz uyari seridi (bkz. gorev tanimi Bolum 9) - bilincli
// olarak bir kapatma/dismiss butonu YOK.
export function GozcuWarningBanner() {
  return (
    <div className="flex shrink-0 items-center justify-center gap-2 border-b border-term-amber/40 bg-term-amber-dim px-3 py-1.5 text-center">
      <span className="mono-tabular text-[11px] font-semibold text-term-amber">⚠ GÖZCÜ</span>
      <span className="label-xs text-[10px] text-term-amber">
        bu panel YATIRIM TAVSİYESİ DEĞİLDİR — sadece dikkat çeken piyasa hareketlerini gösterir
      </span>
    </div>
  );
}
