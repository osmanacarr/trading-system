"""Dashboard /research sayfasi icin ozet JSON uretici.

Python -> dashboard hicbir CANLI cagri YAPMAZ (repo mimarisi - bkz. gozcu/
scanner.py'nin ayni prensibi, modul docstring'i "Bolum 0"): bu script
periyodik calisir (CLI/GitHub Actions), research/data/research_summary.json'a
YAZAR; dashboard SADECE bu dosyayi okur.

Bu modul, ONCEKI modullerin (research/factors.py, research/factor_history.py,
validation/alpha_evaluation.py, research/regime.py, research/ensemble.py,
research/attribution.py) ciktilarini TEK bir JSON'da toplar - hicbirinin
HESAPLAMA mantigini burada TEKRAR YAZMAZ. Saf (I/O'suz, test edilebilir)
`build_*`/`assemble_summary` fonksiyonlari ile canli veri ceken/dosyaya
yazan `run_publish_summary` orkestrasyonu AYRI tutulur (gozcu/scanner.py'deki
run_scan/main ayrimiyla ayni desen).
"""

from __future__ import annotations

import datetime as dt
import json
import logging
from pathlib import Path

import pandas as pd

from config import (
    BIST_TICKERS,
    CRYPTO_TICKERS,
    MAX_FILTER_COUNT,
    RESEARCH_IC_HORIZON_DAYS,
    RESEARCH_SUMMARY_PATH,
)
from data.fetch import fetch_universe
from research import ensemble as ensemble_mod
from research import regime as regime_mod
from research.factor_history import load_factor_history
from validation.alpha_evaluation import check_rule_burden, compute_forward_returns, detect_decay, ic_time_series

log = logging.getLogger("research.publish_summary")


def _safe_float(value, ndigits: int = 6) -> float | None:
    """Dashboard'a JSON-guvenli float dondurur (None/NaN -> None) - gozcu/scanner.py::_safe_float ile AYNI desen."""
    if value is None:
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    if f != f:  # NaN
        return None
    return round(f, ndigits)


def build_factor_ic_summary(
    factor_long_df: pd.DataFrame, forward_returns_long_df: pd.DataFrame
) -> list[dict]:
    """Her faktor icin IC zaman serisi ozetini (ortalama IC + decay) hesaplar."""
    if factor_long_df.empty:
        return []
    rows = []
    for factor_name in sorted(factor_long_df["factor_name"].unique()):
        ic_series = ic_time_series(factor_long_df, forward_returns_long_df, factor_name)
        decay = detect_decay(ic_series)
        rows.append(
            {
                "factor_name": factor_name,
                "mean_ic": _safe_float(ic_series.mean()) if not ic_series.empty else None,
                "n_dates": int(len(ic_series)),
                "decayed": bool(decay["decayed"]),
                "first_half_mean_ic": _safe_float(decay["first_half_mean_ic"]),
                "second_half_mean_ic": _safe_float(decay["second_half_mean_ic"]),
            }
        )
    return rows


def build_regime_summary(regime_label_by_symbol: dict[str, str | None]) -> dict:
    """Sembol basina rejim etiketlerinden evren-genelinde bir ozet cikarir (cogunluk + dagilim).

    Args:
        regime_label_by_symbol: {sembol: "low"|"normal"|"high"|None} -
            HER sembolun EN SON barindaki rejim etiketi (bkz. research.
            regime.compute_regime_labels).
    """
    counts = {"low": 0, "normal": 0, "high": 0}
    for label in regime_label_by_symbol.values():
        if label in counts:
            counts[label] += 1
    total = sum(counts.values())
    majority = max(counts, key=lambda k: counts[k]) if total > 0 else None
    return {"counts": counts, "majority_label": majority, "n_symbols": total}


def build_ensemble_summary(factor_ic_rows: list[dict], factor_long_df: pd.DataFrame) -> dict:
    """IC-agirlikli kompozit agirliklari ve redundant faktor ciftlerini uretir."""
    ic_by_factor = {row["factor_name"]: row["mean_ic"] for row in factor_ic_rows if row["mean_ic"] is not None}
    decay_by_factor = {row["factor_name"]: {"decayed": row["decayed"]} for row in factor_ic_rows}
    weights = ensemble_mod.compute_ic_weights(ic_by_factor, decay_by_factor)

    corr_matrix = ensemble_mod.factor_correlation_matrix(factor_long_df)
    redundant_pairs = ensemble_mod.flag_redundant_factors(corr_matrix)

    return {
        "weights": [
            {"factor_name": name, "weight": _safe_float(weight)} for name, weight in sorted(weights.items())
        ],
        "redundant_pairs": [
            {"factor_a": a, "factor_b": b, "correlation": _safe_float(c)} for a, b, c in redundant_pairs
        ],
    }


def write_summary_atomic(summary: dict, path: Path = RESEARCH_SUMMARY_PATH) -> None:
    """Ozeti atomik yazar (tmp dosya + rename) - gozcu/scanner.py::_write_snapshot_atomic ile AYNI desen."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    tmp_path.replace(path)


def assemble_summary(
    factor_long_df: pd.DataFrame,
    forward_returns_long_df: pd.DataFrame,
    regime_label_by_symbol: dict[str, str | None],
    attribution_summary: dict | None = None,
    n_active_filters: int = 0,
    now: dt.datetime | None = None,
) -> dict:
    """Tum parcalari TEK bir ozet sozlukte birlestirir (saf/test edilebilir - dosya/ag I/O YOK)."""
    now = now or dt.datetime.now(dt.timezone.utc)
    factor_ic_rows = build_factor_ic_summary(factor_long_df, forward_returns_long_df)
    return {
        "generated_at": now.isoformat(),
        "factor_ic": factor_ic_rows,
        "regime": build_regime_summary(regime_label_by_symbol),
        "ensemble": build_ensemble_summary(factor_ic_rows, factor_long_df),
        "attribution": attribution_summary
        or {"total_common_return": 0.0, "total_specific_return": 0.0, "pct_specific": 0.0},
        "rule_burden": check_rule_burden(n_active_filters, max_filters=MAX_FILTER_COUNT),
    }


def run_publish_summary(
    universe: list[str] | None = None,
    lookback_days: int = 400,
    path: Path = RESEARCH_SUMMARY_PATH,
) -> dict:
    """CLI/scheduled-run giris noktasi: canli veri ceker, ozetler, dosyaya yazar.

    Args:
        universe: Sembol listesi (varsayilan: config.BIST_TICKERS +
            config.CRYPTO_TICKERS - backtest/paper trading ile AYNI stabil
            evren, research/factor_history.py::run_daily_collection ile
            TUTARLI).
        lookback_days: Fiyat verisi cekimi icin geriye donuk gun sayisi.
        path: Ciktinin yazilacagi yol.
    """
    symbols = universe if universe is not None else list(BIST_TICKERS) + list(CRYPTO_TICKERS)
    end = pd.Timestamp.today().normalize()
    start = (end - pd.Timedelta(days=lookback_days)).strftime("%Y-%m-%d")
    price_data = fetch_universe(symbols, start=start)

    factor_long_df = load_factor_history()
    forward_returns_long_df = compute_forward_returns(price_data, horizon_days=RESEARCH_IC_HORIZON_DAYS)

    regime_label_by_symbol: dict[str, str | None] = {}
    for symbol, df in price_data.items():
        if df.empty:
            continue
        labels = regime_mod.compute_regime_labels(df)
        regime_label_by_symbol[symbol] = labels.iloc[-1] if not labels.empty else None

    summary = assemble_summary(factor_long_df, forward_returns_long_df, regime_label_by_symbol)
    write_summary_atomic(summary, path=path)
    return summary


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = run_publish_summary()
    log.info(
        "research_summary.json guncellendi: %d faktor, rejim=%s",
        len(result["factor_ic"]),
        result["regime"]["majority_label"],
    )
