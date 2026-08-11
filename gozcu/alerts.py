"""gozcu/alerts.py - Asiri dikkat skorlari icin GUNDE BIR KEZ Telegram bilgi mesaji.

Bu bir AL-SAT sinyali DEGILDIR, sadece "dikkatini cek" mesajidir (mesaj
metninde de acikca belirtilir, bkz. gorev tanimi Bolum 7).

Idempotency deseni paper_trading/state.py'deki stop_warnings tablosuyla
AYNI mantik (sembol basina "son uyarilan tarih", < today karsilastirmasi)
ama paper trading state.db'sine DOKUNMAZ - GOZCU tamamen ayri, kendi JSON
dosyasinda (config.GOZCU_ALERT_STATE_PATH) tutar.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
from pathlib import Path

from config import GOZCU_ALERT_SCORE_THRESHOLD, GOZCU_ALERT_STATE_PATH
from notifications.telegram import send_telegram_message

log = logging.getLogger("gozcu.alerts")


def load_alert_state(path: Path = GOZCU_ALERT_STATE_PATH) -> dict[str, str]:
    """{sembol: "YYYY-MM-DD"} seklinde son-uyarilan-tarih haritasini okur.

    Dosya yoksa/bozuksa BOS sozluk doner, istisna firlatmaz.
    """
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {}
        return {str(k): str(v) for k, v in data.items()}
    except (OSError, json.JSONDecodeError):
        return {}


def save_alert_state(state: dict[str, str], path: Path = GOZCU_ALERT_STATE_PATH) -> None:
    """State'i atomik olarak yazar (tmp dosya + rename, yarim yazma riskine karsi)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2, sort_keys=True)
    tmp_path.replace(path)


def should_alert(symbol: str, today: dt.date, state: dict[str, str]) -> bool:
    """Bu sembol icin BUGUN daha once uyari gonderilmemisse True doner."""
    last_warned = state.get(symbol)
    if last_warned is None:
        return True
    return last_warned < today.isoformat()


def record_alert(symbol: str, today: dt.date, state: dict[str, str]) -> dict[str, str]:
    """State'in, bu sembol icin bugunku tarihle guncellenmis YENI bir kopyasini doner."""
    updated = dict(state)
    updated[symbol] = today.isoformat()
    return updated


def format_alert_message(market_label: str, symbol: str, rvol: float | None, score: float) -> str:
    """Kullaniciya gosterilecek Telegram mesajini uretir (bkz. gorev tanimi ornek format)."""
    rvol_str = f"{rvol:.1f}x" if rvol is not None else "N/A"
    return (
        f"[GOZCU] {market_label}: {symbol} olagandisi hacimle hareket ediyor "
        f"(RVOL {rvol_str}, dikkat skoru {score:.1f}) - bu bir AL sinyali "
        f"DEGILDIR, sadece dikkat ceken bir hareket."
    )


def maybe_send_attention_alert(
    symbol: str,
    market_label: str,
    score: float,
    rvol: float | None,
    state: dict[str, str],
    today: dt.date | None = None,
    threshold: float = GOZCU_ALERT_SCORE_THRESHOLD,
) -> dict[str, str]:
    """Skor esigi gecildiyse VE bugun daha once uyarilmadiysa Telegram'a gonderir.

    Gonderim basarisiz olsa bile (yanlis token, ag hatasi -
    send_telegram_message hicbir zaman istisna firlatmaz) state GUNCELLENIR:
    amac ayni eşik-asan sembol icin her 5 dakikada bir tekrar tekrar deneme
    yapmamak (stop_warnings ile ayni "gunde bir DENEME" felsefesi).

    Args:
        state: Cagiran (scanner.py) tarafindan yuklenen mevcut alert state'i.
        today: Test edilebilirlik icin enjekte edilebilir (varsayilan bugun).

    Returns:
        Guncellenmis state (esik/idempotency nedeniyle gonderim yapilmadiysa DEGISMEDEN aynen doner).
    """
    if score < threshold:
        return state
    resolved_today = today if today is not None else dt.date.today()
    if not should_alert(symbol, resolved_today, state):
        return state

    message = format_alert_message(market_label, symbol, rvol, score)
    send_telegram_message(message)
    return record_alert(symbol, resolved_today, state)
