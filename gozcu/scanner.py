"""gozcu/scanner.py - GOZCU orkestratoru: evreni tarar, metrik/skor/psikoloji/
korelasyon hesaplar, tek bir JSON snapshot'a yazar.

MIMARI KARAR (Bolum 0): Yuzlerce sembolu her acik dashboard sekmesi kendi
basina tarasaydi hem yfinance rate-limit'ine hizla takilir hem de gereksiz
yuk olusurdu. Bunun yerine bu script GitHub Actions'ta periyodik olarak
(bkz. .github/workflows/gozcu_scan.yml) TEK bir kaynaktan calisir ve
sonucu gozcu/data/snapshot.json'a yazar; dashboard/app/api/gozcu/route.ts
SADECE bu dosyayi okur, kendi basina yfinance'e HICBIR ZAMAN gitmez. Boylece
kac kullanici sekmesi acarsa acsin tek kaynak taranir.

Piyasa saati / DST: GitHub Actions cron'u UTC'dir ve DST'yi kendisi
kaydirmaz (ABD/NASDAQ DST uygular, TR uygulamaz). Cron'da iki ayri saat
satiri tutmak yerine, cron GENIS bir UTC penceresinde (06:00-21:00, hafta
ici) sik sik tetiklenir ve bu script gozcu/market_hours.py ile HANGI
piyasa(lar)in GERCEKTEN acik oldugunu (zoneinfo, DST-farkinda) kontrol
edip sadece onlari tarar. Piyasa kapaliyken o piyasa icin BOSUNA yfinance'e
gidilmez; snapshot'taki o piyasaya ait veri (bir onceki acik seanstan kalan)
oldugu gibi korunur, sadece "market_open" bayragi False'a cekilir - kullanici
"kapali piyasa" ile "veri bayat" durumunu ayirt edebilsin diye.

GOZCU, paper_trading/'den TAMAMEN bagimsizdir: hicbir sinyal/pozisyon
uretmez, paper trading state.db'sine dokunmaz.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
from pathlib import Path
from typing import Callable

import pandas as pd

from config import (
    GOZCU_BIST_REFERENCE_TICKER,
    GOZCU_BIST_REFERENCE_TICKER_FALLBACK,
    GOZCU_NASDAQ_REFERENCE_TICKER,
    GOZCU_SNAPSHOT_PATH,
    GOZCU_VOLUME_ZSCORE_LOOKBACK,
)
from gozcu import alerts, correlation, market_hours, metrics, psychology, scoring, universe
from gozcu.data_fetch import fetch_daily_batch, fetch_intraday_batch

log = logging.getLogger("gozcu.scanner")

MARKET_LABELS = {"bist": "BIST", "nasdaq": "NASDAQ"}


def _safe_float(value, ndigits: int = 6) -> float | None:
    """Metrik ciktilarini JSON-guvenli float'a cevirir (None/NaN -> None)."""
    if value is None:
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    if f != f:  # NaN
        return None
    return round(f, ndigits)


def _filter_today(intraday_df: pd.DataFrame) -> pd.DataFrame:
    """Gun-ici DataFrame'i, SON barin tarihiyle ayni gune ait barlara indirger."""
    if intraday_df.empty:
        return intraday_df
    last_date = intraday_df.index[-1].date()
    return intraday_df[intraday_df.index.date == last_date]


def _avg_daily_volume(daily_df: pd.DataFrame, lookback: int = GOZCU_VOLUME_ZSCORE_LOOKBACK) -> float | None:
    volume = daily_df["Volume"].dropna()
    if len(volume) < 2:
        return None
    window = volume.iloc[-(lookback + 1):-1] if len(volume) > lookback else volume.iloc[:-1]
    if window.empty:
        return None
    return float(window.mean())


def _intraday_series_payload(today_intraday_df: pd.DataFrame, vwap_series: pd.Series) -> dict:
    if today_intraday_df.empty:
        return {"times": [], "price": [], "vwap": []}
    vwap_aligned = vwap_series.reindex(today_intraday_df.index)
    return {
        "times": [ts.isoformat() for ts in today_intraday_df.index],
        "price": [_safe_float(v, 4) for v in today_intraday_df["Close"]],
        "vwap": [_safe_float(v, 4) for v in vwap_aligned],
    }


def _compute_symbol_metrics(
    symbol: str,
    daily_df: pd.DataFrame,
    intraday_df: pd.DataFrame,
    session_progress_fn: Callable[[dt.datetime], float],
) -> dict | None:
    """Tek bir sembol icin Bolum 2'deki tum metrikleri hesaplar.

    Veri yetersizse (gunluk bar yoksa) None doner - cagiran sembolu "hata"
    sayip atlar (tarama bir sembolde takilmaz).

    RVOL icin "seans ilerleme orani" ARTIK sembol basina, o sembolun SON
    gun-ici barinin KENDI zaman damgasindan hesaplanir (session_progress_fn
    ile) - tek bir "su an" (wall-clock) degeri TUM piyasa icin kullanilmiyor.
    Onceki tasarim, piyasa kapaliyken (dolayisiyla gun-ici veri bir onceki
    TAMAMLANMIS seansa ait oldugunda) "su an"in o tamamlanmis seansla hicbir
    ilgisi olmadigi icin RVOL'u sistematik olarak None yapiyordu (NASDAQ
    kapaliyken RVOL sutununun tamamen bos gorunmesi buradan kaynaklaniyordu -
    bkz. ilgili hata raporu). session_progress_fn == market_hours.bist_
    elapsed_fraction / nasdaq_elapsed_fraction (asagida run_scan()'da
    baglanir) - AYNI fonksiyon, sadece "su an" yerine barin kendi zaman
    damgasiyla cagrilir.
    """
    if daily_df.empty:
        return None

    today_intraday = _filter_today(intraday_df)
    elapsed_fraction = session_progress_fn(today_intraday.index[-1]) if not today_intraday.empty else 0.0
    vwap_series = metrics.compute_vwap(today_intraday)
    vwap_last = vwap_series.iloc[-1] if not vwap_series.empty else None
    last_price = float(daily_df["Close"].dropna().iloc[-1])

    daily_change = metrics.daily_change_pct(daily_df)
    weekly_change = metrics.weekly_change_pct(daily_df)
    vol_z = metrics.volume_zscore(daily_df)
    avg_vol = _avg_daily_volume(daily_df)
    rvol = metrics.relative_volume(today_intraday, avg_vol, elapsed_fraction)
    momentum = metrics.momentum_candle_flag(daily_df)
    momentum_flag = momentum["body_ok"] and momentum["volume_ok"]

    score = scoring.compute_attention_score(daily_change, vol_z, rvol, momentum_flag)
    vwap_pos_pct = metrics.vwap_position_pct(last_price, vwap_last)
    lateness = metrics.compute_lateness_warning(daily_change, vwap_pos_pct, elapsed_fraction)

    return {
        "symbol": symbol,
        "score": _safe_float(score, 2),
        "last_price": _safe_float(last_price, 4),
        "daily_change_pct": _safe_float(daily_change),
        "weekly_change_pct": _safe_float(weekly_change),
        "rvol": _safe_float(rvol, 2),
        "volume_zscore": _safe_float(vol_z, 2),
        "momentum_candle": bool(momentum_flag),
        "vwap": _safe_float(vwap_last, 4),
        "vwap_position_pct": _safe_float(vwap_pos_pct),
        "vwap_slope": _safe_float(metrics.vwap_slope(vwap_series), 4),
        "distance_from_52w_high": _safe_float(metrics.distance_from_52w_high(daily_df)),
        "distance_from_52w_low": _safe_float(metrics.distance_from_52w_low(daily_df)),
        "atr_percentile": _safe_float(metrics.atr_percentile(daily_df), 1),
        # "Gec kalma" uyarisi (bkz. metrics.compute_lateness_warning docstring'i) -
        # her karta OZEL, SAYISAL - genel GozcuWarningBanner'in YANINDA, YERINE DEGIL.
        "session_elapsed_pct": lateness["session_elapsed_pct"],
        "vwap_distance_pct": lateness["vwap_distance_pct"],
        "lateness_warning": lateness["warning_text"],
        "_vwap_series": vwap_series,
        "_intraday_today": today_intraday,
    }


def _resolve_reference_returns(primary: str, fallback: str | None) -> tuple[pd.Series, str | None]:
    candidates = [primary] + ([fallback] if fallback else [])
    data = fetch_daily_batch(candidates)
    for ticker in candidates:
        df = data.get(ticker)
        if df is not None and not df.empty:
            return correlation.compute_returns(df), ticker
    return pd.Series(dtype=float), None


def _empty_market_payload() -> dict:
    return {
        "market_open": False,
        "scanned_at": None,
        "universe_size": 0,
        "scanned_count": 0,
        "error_count": 0,
        "attention_list": [],
        "psychology": {"breadth_pct": None, "volatility_regime": "bilinmiyor"},
        "correlation": {"average_correlation": None, "reference_ticker": None},
    }


def scan_market(
    market_key: str,
    symbols: list[str],
    reference_ticker: str,
    reference_ticker_fallback: str | None,
    session_progress_fn: Callable[[dt.datetime], float],
    now: dt.datetime,
    actually_open: bool,
) -> dict:
    """Tek bir piyasayi (evreni) tarar, Bolum 2-5'teki tum ciktilari uretir.

    Args:
        session_progress_fn: Bir zaman damgasi alip o zamana kadar piyasa
            seansinin ne kadarinin gectigini (0-1) donen fonksiyon (bkz.
            market_hours.bist_elapsed_fraction / nasdaq_elapsed_fraction).
            Her sembol icin KENDI son gun-ici barinin zaman damgasiyla
            cagrilir (bkz. _compute_symbol_metrics).
        actually_open: Piyasanin GERCEKTEN acik olup olmadigi (force ile
            zorlanmis bir tarama da olsa dogru deger) - donen "market_open"
            alani buna esitlenir, boylece zorlanmis/test taramalari
            piyasayi yanlislikla "acik" gibi gostermez.
    """
    daily_data = fetch_daily_batch(symbols)
    intraday_data = fetch_intraday_batch(symbols)

    per_symbol: dict[str, dict] = {}
    daily_changes: list[float | None] = []
    returns_by_symbol: dict[str, pd.Series] = {}
    error_count = 0

    for symbol in symbols:
        daily_df = daily_data.get(symbol, pd.DataFrame())
        intraday_df = intraday_data.get(symbol, pd.DataFrame())
        try:
            computed = _compute_symbol_metrics(symbol, daily_df, intraday_df, session_progress_fn)
        except Exception:
            log.exception("Sembol metrikleri hesaplanamadi: %s", symbol)
            computed = None
        if computed is None:
            error_count += 1
            continue
        per_symbol[symbol] = computed
        daily_changes.append(computed["daily_change_pct"])
        returns_by_symbol[symbol] = correlation.compute_returns(daily_df)

    scores = {s: m["score"] for s, m in per_symbol.items() if m["score"] is not None}
    top = scoring.rank_by_attention(scores)

    attention_list = []
    for symbol, _score in top:
        entry = dict(per_symbol[symbol])
        vwap_series = entry.pop("_vwap_series")
        today_intraday = entry.pop("_intraday_today")
        entry["intraday"] = _intraday_series_payload(today_intraday, vwap_series)
        attention_list.append(entry)

    reference_returns, resolved_ticker = _resolve_reference_returns(reference_ticker, reference_ticker_fallback)
    avg_correlation = correlation.average_correlation_to_reference(returns_by_symbol, reference_returns)

    return {
        "market_open": actually_open,
        "scanned_at": now.isoformat(),
        "universe_size": len(symbols),
        "scanned_count": len(per_symbol),
        "error_count": error_count,
        "attention_list": attention_list,
        "psychology": {
            "breadth_pct": _safe_float(psychology.compute_breadth_pct(daily_changes), 1),
            "volatility_regime": psychology.compute_volatility_regime(daily_changes),
        },
        "correlation": {
            "average_correlation": _safe_float(avg_correlation, 3),
            "reference_ticker": resolved_ticker,
        },
    }


def _load_previous_snapshot(path: Path) -> dict:
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def _write_snapshot_atomic(data: dict, path: Path = GOZCU_SNAPSHOT_PATH) -> None:
    """Snapshot'i atomik yazar (tmp dosya + rename - yarim yazma riskine karsi)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    tmp_path.replace(path)


def run_scan(markets: list[str] | None = None, now: dt.datetime | None = None, force: bool = False) -> dict:
    """Verilen piyasa(lar)i tarar ve tam snapshot sozlugunu doner (dosyaya yazmaz).

    Kapali/istenmeyen piyasalar icin ONCEKI snapshot'taki veri korunur
    (market_open bayragi guncellenerek) - "piyasa kapali" ile "veri bayat/
    hatali" ayrimi kullaniciya net kalsin diye.

    Args:
        force: True ise piyasa-acik kontrolunu ATLAR, her zaman tarar (manuel
            test/hata ayiklama icin - CLI'da --force, bkz. main()).
    """
    resolved_markets = markets if markets is not None else ["bist", "nasdaq"]
    resolved_now = now if now is not None else dt.datetime.now(dt.timezone.utc)

    previous = _load_previous_snapshot(GOZCU_SNAPSHOT_PATH)
    previous_markets = previous.get("markets", {})

    result_markets: dict[str, dict] = dict(previous_markets)
    alert_state = alerts.load_alert_state()
    today = resolved_now.date()

    if "bist" in resolved_markets:
        bist_really_open = market_hours.is_bist_open(resolved_now)
        if force or bist_really_open:
            try:
                payload = scan_market(
                    "bist",
                    universe.get_bist_universe(),
                    GOZCU_BIST_REFERENCE_TICKER,
                    GOZCU_BIST_REFERENCE_TICKER_FALLBACK,
                    market_hours.bist_elapsed_fraction,
                    resolved_now,
                    actually_open=bist_really_open,
                )
            except Exception:
                log.exception("BIST taramasi basarisiz, onceki snapshot korunuyor")
                payload = previous_markets.get("bist", _empty_market_payload())
                payload["market_open"] = bist_really_open
        else:
            payload = previous_markets.get("bist", _empty_market_payload())
            payload["market_open"] = False
        result_markets["bist"] = payload
        alert_state = _apply_alerts("bist", payload, alert_state, today)

    if "nasdaq" in resolved_markets:
        nasdaq_really_open = market_hours.is_nasdaq_open(resolved_now)
        if force or nasdaq_really_open:
            try:
                payload = scan_market(
                    "nasdaq",
                    universe.get_nasdaq100_universe(),
                    GOZCU_NASDAQ_REFERENCE_TICKER,
                    None,
                    market_hours.nasdaq_elapsed_fraction,
                    resolved_now,
                    actually_open=nasdaq_really_open,
                )
            except Exception:
                log.exception("NASDAQ taramasi basarisiz, onceki snapshot korunuyor")
                payload = previous_markets.get("nasdaq", _empty_market_payload())
                payload["market_open"] = nasdaq_really_open
        else:
            payload = previous_markets.get("nasdaq", _empty_market_payload())
            payload["market_open"] = False
        result_markets["nasdaq"] = payload
        alert_state = _apply_alerts("nasdaq", payload, alert_state, today)

    alerts.save_alert_state(alert_state)

    return {"generated_at": resolved_now.isoformat(), "markets": result_markets}


def _apply_alerts(market_key: str, market_payload: dict, alert_state: dict[str, str], today: dt.date) -> dict[str, str]:
    if not market_payload.get("market_open"):
        return alert_state
    label = MARKET_LABELS.get(market_key, market_key.upper())
    state = alert_state
    for entry in market_payload.get("attention_list", []):
        state = alerts.maybe_send_attention_alert(
            entry["symbol"],
            label,
            entry["score"] or 0.0,
            entry.get("rvol"),
            state,
            today=today,
        )
    return state


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="GOZCU: NASDAQ + BIST canli izleme taramasi")
    parser.add_argument("--market", choices=["bist", "nasdaq", "all"], default="all")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Piyasa-acik kontrolunu atlar, her zaman tarar (manuel test/hata ayiklama icin).",
    )
    args = parser.parse_args(argv)

    markets = ["bist", "nasdaq"] if args.market == "all" else [args.market]
    snapshot = run_scan(markets, force=args.force)
    _write_snapshot_atomic(snapshot)
    log.info("GOZCU tarama tamamlandi: %s", snapshot["generated_at"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
