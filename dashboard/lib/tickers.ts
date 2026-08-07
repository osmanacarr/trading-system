// config.py BIST_TICKERS / CRYPTO_TICKERS ile birebir ayni (evren degisirse
// burasi da guncellenmeli - komut paletinin sembol arama listesi icin).
export const BIST_TICKERS: string[] = [
  "THYAO.IS",
  "GARAN.IS",
  "AKBNK.IS",
  "ISCTR.IS",
  "KCHOL.IS",
  "SAHOL.IS",
  "SISE.IS",
  "EREGL.IS",
  "BIMAS.IS",
  "ASELS.IS",
  "TUPRS.IS",
  "FROTO.IS",
  "TOASO.IS",
];

export const CRYPTO_TICKERS: string[] = ["BTC-USD"];

export const ALL_TICKERS: string[] = [...BIST_TICKERS, ...CRYPTO_TICKERS];
