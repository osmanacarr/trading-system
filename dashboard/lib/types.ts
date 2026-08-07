// paper_trading/logger.py TRADE_LOG_COLUMNS / EQUITY_LOG_COLUMNS ile birebir
// ayni alanlar. Sayisal alanlar exit event'inde dolu, entry'de null olabilir.
export interface TradeRecord {
  event_type: "entry" | "exit";
  date: string; // ISO YYYY-MM-DD
  symbol: string;
  strategy: string;
  direction: 1 | -1;
  price: number;
  stop_price: number;
  target_price: number | null;
  size: number;
  pnl: number | null;
  r_multiple: number | null;
  exit_reason: "stop" | "trailing" | "target" | null;
  equity_after: number;
}

export interface EquitySnapshot {
  date: string;
  realized_equity: number;
  unrealized_pnl: number;
  total_equity: number;
  open_positions: number;
}

// runner.py run_once()'un yazdigi summary.json - "error" alani BUGUN
// UretilMIYOR (runner.py'de yok); ileride eklenirse UI otomatik
// yakalasin diye opsiyonel olarak tanimlandi (bkz. StatusBar anomali rozeti).
export interface Summary {
  last_updated: string;
  strategy: string;
  total_equity: number;
  realized_equity: number;
  open_positions: number;
  trades_last_7_days: number;
  error?: string;
}

// paper_trading/state.py positions tablosu
export interface OpenPosition {
  symbol: string;
  strategy: string;
  direction: 1 | -1;
  entry_date: string;
  entry_price: number;
  stop_price: number;
  target_price: number | null;
  size: number;
}

export type Market = "bist" | "crypto";

// paper_trading/manual_log.py MANUAL_LOG_COLUMNS ile birebir ayni alanlar.
// Kullanicinin sistem sinyaline karsi GERCEKTEN actigi (kendi hesabindan,
// manuel) islemin kaydi - sistemin sanal trades.jsonl'inden bagimsiz.
export interface ManualEntryRecord {
  symbol: string;
  signal_date: string; // ISO YYYY-MM-DD, trades.jsonl'deki "date" ile eslesir
  system_entry_price: number | null;
  user_entry_price: number;
  user_size: number;
  note: string;
  marked_at: string; // ISO datetime (UTC)
}
