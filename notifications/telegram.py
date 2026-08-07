"""notifications/telegram.py - Telegram Bot API'sine basit metin mesaji
gonderen, bagimliliksiz (yalnizca requests) bir yardimci.

Kasitli olarak minimal: mesaj GONDERMEK disinda hicbir sey yapmaz (mesaj
formatlama caller'in sorumlulugunda - bkz. paper_trading/runner.py). Bot
token/chat ID GitHub Secrets'tan environment degiskeni olarak gelir, KOD
ICINE hardcode edilmez (bkz. README "Telegram bot nasil kurulur").

Bu modul hicbir istisna FIRLATMAZ - cagiran (runner.py) Telegram bildirimi
basarisiz olsa bile (yanlis token, ag hatasi, Telegram API'nin gecici
erisilemez olmasi vb.) paper trading calismaya devam etmelidir (bkz. gorev
tanimi). Basarisizlik durumunda sadece loglanir ve False donulur.
"""

from __future__ import annotations

import logging
import os

import requests

log = logging.getLogger("notifications.telegram")

TELEGRAM_API_BASE = "https://api.telegram.org"
REQUEST_TIMEOUT_SECONDS = 10


def send_telegram_message(
    text: str,
    bot_token: str | None = None,
    chat_id: str | None = None,
) -> bool:
    """Verilen metni Telegram Bot API'si uzerinden chat_id'ye gonderir.

    Args:
        text: Gonderilecek mesaj metni.
        bot_token: Telegram bot token'i (None ise TELEGRAM_BOT_TOKEN
            environment degiskeninden okunur).
        chat_id: Hedef sohbet/grup ID'si (None ise TELEGRAM_CHAT_ID
            environment degiskeninden okunur).

    Returns:
        Mesaj basariyla gonderildiyse True; token/chat_id tanimli degilse,
        ag hatasi olusursa veya Telegram API basarisiz bir durum kodu
        donerse False. Hicbir kosulda istisna FIRLATMAZ.
    """
    token = bot_token if bot_token is not None else os.environ.get("TELEGRAM_BOT_TOKEN")
    chat = chat_id if chat_id is not None else os.environ.get("TELEGRAM_CHAT_ID")

    if not token or not chat:
        log.warning("Telegram bildirimi atlandi: TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID tanimli degil")
        return False

    url = f"{TELEGRAM_API_BASE}/bot{token}/sendMessage"
    try:
        response = requests.post(
            url,
            json={"chat_id": chat, "text": text},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        log.warning("Telegram bildirimi gonderilemedi (ag hatasi): %s", exc)
        return False

    if response.status_code != 200:
        log.warning("Telegram API basarisiz durum kodu dondu (%d): %s", response.status_code, response.text[:200])
        return False

    return True
