// gozcu/scanner.py'nin ürettiği gozcu/data/snapshot.json ile BİREBİR aynı şema.
// Alan isimleri Python tarafıyla (gozcu/scanner.py: _compute_symbol_metrics,
// scan_market) kasıtlı olarak snake_case tutuldu - iki taraf arasında manuel
// bir alan-adı çevirisi katmanı olmasın diye (bkz. dashboard/lib/tickers.ts
// yorumundaki "elle senkron tut" felsefesiyle aynı, burada isim eşleşmesiyle
// senkronu ucuzlaştırıyoruz).

export type VolatilityRegime = "normal" | "yuksek" | "asiri" | "bilinmiyor";

export interface GozcuIntradaySeries {
  times: string[];
  price: (number | null)[];
  vwap: (number | null)[];
}

export interface GozcuSymbolMetrics {
  symbol: string;
  score: number | null;
  last_price: number | null;
  daily_change_pct: number | null;
  weekly_change_pct: number | null;
  rvol: number | null;
  volume_zscore: number | null;
  momentum_candle: boolean;
  vwap: number | null;
  vwap_position_pct: number | null;
  vwap_slope: number | null;
  distance_from_52w_high: number | null;
  distance_from_52w_low: number | null;
  atr_percentile: number | null;
  intraday: GozcuIntradaySeries;
}

export interface GozcuPsychology {
  breadth_pct: number | null;
  volatility_regime: VolatilityRegime;
}

export interface GozcuCorrelation {
  average_correlation: number | null;
  reference_ticker: string | null;
}

export interface GozcuMarketSnapshot {
  market_open: boolean;
  scanned_at: string | null;
  universe_size: number;
  scanned_count: number;
  error_count: number;
  attention_list: GozcuSymbolMetrics[];
  psychology: GozcuPsychology;
  correlation: GozcuCorrelation;
}

export type GozcuMarketKey = "bist" | "nasdaq";

export interface GozcuSnapshot {
  generated_at: string;
  markets: Partial<Record<GozcuMarketKey, GozcuMarketSnapshot>>;
}

export const GOZCU_MARKET_LABELS: Record<GozcuMarketKey, string> = {
  bist: "BIST",
  nasdaq: "NASDAQ",
};
