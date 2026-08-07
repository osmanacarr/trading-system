// Faz 3.5 dokumaninda (faz3.5_matematiksel_formalizasyon.md SS4.2, SS4.3)
// GECEN, elle girilmis referans backtest metrikleri - "canli vs backtest
// sapma" panelinin karsilastirma temeli.
//
// BILINCLI SINIRLAMA: bu degerler yalnizca Donchian/BIST icin nitel olarak
// raporlanmis (~0.40 win-rate, ~0.5-0.6 Sharpe); repo icinde makine-okunur
// (JSON/CSV) bir backtest ciktisi commit'lenmemis, ve BIST+kripto birlesik
// bir expectancy_R sayisi hic yayinlanmamis. Bu yuzden expectancyRPerTrade
// BILEREK null birakildi - panel bunu "referans expectancy tanimli degil"
// olarak gosterip YANLIS/UYDURMA bir karsilastirma egrisi CIZMEZ. Gercek
// bir backtest.run ciktisi (orn. backtest/run.py'nin urettigi summarize()
// sozlugu) makine-okunur olarak commit'lenirse, buraya expectancyRPerTrade
// ve tradesPerMonth degerleri eklenerek panel otomatik aktif hale gelir.
export const BACKTEST_BASELINE = {
  source: "faz3.5_matematiksel_formalizasyon.md SS4.2-4.3 (Donchian, BIST)",
  winRate: 0.40,
  sharpe: 0.55,
  expectancyRPerTrade: null as number | null,
  tradesPerMonth: null as number | null,
};
