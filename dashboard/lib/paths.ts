// Veri kaynagi yollari - config.py (repo koku) ile BIREBIR ayni mantik:
// dashboard/ repo kokunun dogrudan altinda oldugundan, process.cwd()'nin
// bir ust dizini repo kokudur (bkz. ../config.py: PROJECT_ROOT).
import path from "node:path";

export const REPO_ROOT = path.join(process.cwd(), "..");

export const PAPER_TRADING_DATA_DIR = path.join(REPO_ROOT, "paper_trading", "data");
export const PAPER_TRADING_LOG_DIR = path.join(REPO_ROOT, "paper_trading", "logs");

export const STATE_DB_PATH = path.join(PAPER_TRADING_DATA_DIR, "state.db");
export const TRADES_JSONL_PATH = path.join(PAPER_TRADING_LOG_DIR, "trades.jsonl");
export const EQUITY_JSONL_PATH = path.join(PAPER_TRADING_LOG_DIR, "equity.jsonl");
export const SUMMARY_JSON_PATH = path.join(PAPER_TRADING_LOG_DIR, "summary.json");
// paper_trading/manual_log.py (PAPER_TRADING_MANUAL_LOG_PATH) ile BIREBIR ayni yol.
export const MANUAL_LOG_PATH = path.join(PAPER_TRADING_LOG_DIR, "manual_trades.jsonl");
