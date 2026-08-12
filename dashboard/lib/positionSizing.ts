// backtest/engine.py::compute_position_size ile BIREBIR ayni formul (SS2.3:
// size = E_t*rho / |giris-stop|) - AYNEN mirror'lanir, farkli bir mantik
// EKLENMEZ. Bu hesap MUTLAKA client-side (tarayici) calismali: gercek
// sermaye yalnizca localStorage'da tutulur, sunucuya hic gonderilmez (bkz.
// paper_trading/action_sheet.py modul docstring'i - Telegram/JSON ozeti
// bilerek bir "adet" sayisi URETMEZ).
export function computePositionSize(equity: number, riskPct: number, entryPrice: number, stopPrice: number): number {
  const riskDistance = Math.abs(entryPrice - stopPrice);
  if (riskDistance <= 0) return 0;
  return (equity * riskPct) / riskDistance;
}
