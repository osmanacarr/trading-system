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
// paper_trading/action_sheet.py (ACTION_SHEET_JSON_PATH) ile BIREBIR ayni yol.
// runner.py'nin HER calistirmasi (dry_run=False) sonunda UZERINE yazilir.
export const ACTION_SHEET_JSON_PATH = path.join(PAPER_TRADING_LOG_DIR, "action_sheet.json");
// paper_trading/manual_log.py (PAPER_TRADING_MANUAL_LOG_PATH) ile BIREBIR ayni yol.
export const MANUAL_LOG_PATH = path.join(PAPER_TRADING_LOG_DIR, "manual_trades.jsonl");

// GOZCU (izleme paneli, paper trading'den BAGIMSIZ) - config.py: GOZCU_SNAPSHOT_PATH
// ile BIREBIR ayni yol. gozcu/scanner.py (GitHub Actions) tarafindan yazilir,
// bu dosya SADECE OKUNUR - hicbir API route buraya yazmaz.
export const GOZCU_DATA_DIR = path.join(REPO_ROOT, "gozcu", "data");
export const GOZCU_SNAPSHOT_PATH = path.join(GOZCU_DATA_DIR, "snapshot.json");

// Arastirma ozeti (/research sayfasi) - config.py: RESEARCH_SUMMARY_PATH ile
// BIREBIR ayni yol. research/publish_summary.py (periyodik CLI/GitHub
// Actions) tarafindan yazilir, bu dosya SADECE OKUNUR.
export const RESEARCH_DATA_DIR = path.join(REPO_ROOT, "research", "data");
export const RESEARCH_SUMMARY_PATH = path.join(RESEARCH_DATA_DIR, "research_summary.json");
