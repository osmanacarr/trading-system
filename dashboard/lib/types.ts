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

// paper_trading/action_sheet.py::ActionSheetEntry (asdict ciktisi) ile
// birebir ayni alanlar - Python "tek kaynak", dashboard SADECE okur.
export interface ActionSheetEntry {
  symbol: string;
  strategy: string;
  direction: 1 | -1;
  applicable: boolean; // config.USER_CAN_SHORT'a gore (bkz. lib/constants.ts::directionApplicability)
  entry_price: number;
  stop_price: number;
  entry_date: string; // ISO YYYY-MM-DD
  days_open: number;
  current_price: number | null;
  stop_distance_pct: number | null;
  is_near_stop: boolean;
  is_new_today: boolean;
  exit_explanation: string;
  unrealized_pnl_pct: number | null;
}

// paper_trading/action_sheet.py::action_sheet_to_dict ciktisi.
export interface ActionSheetData {
  generated_at: string;
  // refresh_live_prices() TARAFINDAN generated_at'TEN BAGIMSIZ guncellenir
  // (bkz. o fonksiyonun docstring'i - form gunde bir, fiyatlar ~birkac
  // dakikada bir tazelenir, iki ayri tazelik saati).
  prices_updated_at: string;
  run_date: string;
  disclaimer: string;
  entries: ActionSheetEntry[];
}

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
