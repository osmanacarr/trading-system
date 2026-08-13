"""paper_trading/opportunities.py - "En Iyi N Firsat": paper trading'in
GUNLUK risk butcesi (M2 korelasyon kumeleri + M2-eki net yonlu maruziyet +
brut kaldirac) tarafindan REDDEDILEN (skip_risk_budget) ama stratejinin
KENDI (dogrulanmis/deneysel) sinyal-kalite olcusune gore GUCLU olan
adaylari kullaniciya gosterir - boylece kullanici, sistemin sanal
defterinde acmadigi ama kendi gercek sermayesiyle degerlendirmek
isteyebilecegi sinyalleri KAYBETMEZ (bkz. ilgili konusma, "En Iyi N
Firsat" arastirma talebi).

DURUSTLUK/GUVENLIK CERCEVESI (arastirma bulgularina dogrudan cevap):

1. KAPSAM: SADECE bugun REDDEDILEN adaylar (zaten acilanlar Action Sheet'te
   zaten gorunuyor, burada TEKRAR gosterilmez - ozelligin butun degeri
   "kaybolan" sinyalleri gostermekte, bkz. modul docstring'i "amac").
   DESTEKLENEN stratejiler: "donchian" (dogrulanmis) VE "mean_reversion"
   (DENEYSEL, bkz. config.STRATEGY_VALIDATION_STATUS) - devre disi Kart 1/
   Kart 3 sinyalleri BURAYA ASLA girmez (bkz. build_opportunities,
   STRATEGY_QUALITY_FN).

2. SIRALAMA STRATEJI-BAZINDA AYRI yapilir, ASLA HAVUZLANMAZ: Donchian'in
   atr_distance'i (ATR birimi) ile mean_reversion'in rsi_oversold_depth'i
   (RSI puani) FARKLI olcek/anlam tasir - bunlari TEK bir sayida
   birlestirmek/karsilastirmak sahte bir "hangisi daha iyi" izlenimi
   yaratirdi (research/opportunity_score.py'nin "tek opak skora
   sikistirma" karsitligi ile AYNI ilke). Her strateji KENDI top_n'ini alir.

3. HER KAYITTA ZORUNLU red nedeni (rejection_reason, bkz.
   paper_trading/runner.py::_classify_rejection_reason) VE
   validation_status ("dogrulanmis"/"deneysel", bkz. config.
   STRATEGY_VALIDATION_STATUS) - GIZLENEMEZ, dashboard'da HER karti
   gostermek ZORUNDADIR.

4. RISK_WARNING: bu adaylarin risk katmani TARAFINDAN REDDEDILDIGINI ve
   kullanicinin KENDI hesabinda bu riski KENDISININ yonetmesi gerektigini
   ACIKCA belirtir - action_sheet.DISCLAIMER'dan AYRI ve DAHA SERT (bkz.
   asagisi RISK_WARNING).
"""

from __future__ import annotations

import datetime as dt
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

import pandas as pd

from config import OPPORTUNITIES_TOP_N, PAPER_TRADING_LOG_DIR, STRATEGY_VALIDATION_STATUS, USER_CAN_SHORT
from research.opportunity_score import compute_donchian_breakout_quality, compute_mean_reversion_quality

OPPORTUNITIES_JSON_PATH: Path = PAPER_TRADING_LOG_DIR / "opportunities.json"

RISK_WARNING: str = (
    "Bu adaylar RISK KATMANI TARAFINDAN REDDEDILDI (portfoy butcesi, korelasyon kumesi "
    "veya net yonlu maruziyet siniri) - paper trading'in KENDI sanal defterinde acilmadilar. "
    "Kendi gercek hesabinizda acarsaniz, korelasyon ve yon riskini SIZ yonetmelisiniz - bu "
    "kisitlar hesabiniza OTOMATIK UYGULANMAZ. 'Kalite' olcusu SADECE stratejinin kendi sinyal "
    "gucu olcumudur - gelecekteki performansin GARANTISI DEGILDIR. DENEYSEL etiketli stratejiler "
    "(bkz. her kaydin validation_status alani) DOGRULANMIS stratejilerle AYNI guven duzeyinde DEGILDIR."
)


@dataclass
class RejectedCandidate:
    """opportunities.build_opportunities'e girdi - paper_trading/runner.py::EntryCandidate'in
    KUCUK bir alt kumesi (dairesel import'tan kacinmak icin runner.py'den
    dogrudan import EDILMEZ, bkz. modul docstring'i)."""

    symbol: str
    strategy: str
    direction: int
    entry_price: float
    stop_price: float
    signal_date: dt.date
    reason: str
    df: pd.DataFrame


@dataclass
class OpportunityEntry:
    symbol: str
    strategy: str
    validation_status: str  # "dogrulanmis" | "deneysel" (bkz. config.STRATEGY_VALIDATION_STATUS)
    direction: int
    applicable: bool  # config.USER_CAN_SHORT'a gore (bkz. action_sheet.py ile AYNI ilke)
    entry_price: float
    stop_price: float
    signal_date: str
    rejection_reason: str
    # Donchian icin (mean_reversion'da None):
    atr_distance: float | None
    volume_ratio: float | None
    body_ratio: float | None
    # mean_reversion icin (donchian'da None):
    rsi_oversold_depth: float | None
    ibs: float | None


def _donchian_quality(c: RejectedCandidate) -> tuple[float, dict] | None:
    quality = compute_donchian_breakout_quality(c.df, c.direction)
    if quality is None or quality["atr_distance"] is None:
        return None
    return quality["atr_distance"], {
        "atr_distance": quality["atr_distance"],
        "volume_ratio": quality["volume_ratio"],
        "body_ratio": quality["body_ratio"],
        "rsi_oversold_depth": None,
        "ibs": None,
    }


def _mean_reversion_quality(c: RejectedCandidate) -> tuple[float, dict] | None:
    quality = compute_mean_reversion_quality(c.df)
    if quality is None:
        return None
    return quality["rsi_oversold_depth"], {
        "atr_distance": None,
        "volume_ratio": None,
        "body_ratio": None,
        "rsi_oversold_depth": quality["rsi_oversold_depth"],
        "ibs": quality["ibs"],
    }


# Strateji -> (RejectedCandidate) -> (siralama_anahtari, ek_alanlar) | None.
# YENI bir strateji opportunities'e eklenecekse SADECE burada + config.
# STRATEGY_VALIDATION_STATUS'ta bir satir eklenir (bkz. modul docstring'i
# madde 1-2) - build_opportunities'in kendisi strateji-farkinda DEGILDIR.
STRATEGY_QUALITY_FN: dict[str, Callable[[RejectedCandidate], tuple[float, dict] | None]] = {
    "donchian": _donchian_quality,
    "mean_reversion": _mean_reversion_quality,
}


def build_opportunities(
    candidates: list[RejectedCandidate],
    top_n: int = OPPORTUNITIES_TOP_N,
) -> list[OpportunityEntry]:
    """Reddedilen adaylardan, HER STRATEJI ICIN AYRI ayRI (bkz. modul
    docstring'i madde 2) kendi kalite olcusune gore sirali EN FAZLA top_n
    girdi uretir; strateji listeleri sonda symbol'e gore BIRLESTIRILIR
    (dashboard/Telegram cagiran kod validation_status/strategy alanlarina
    gore kendi gruplamasini yapar).

    Args:
        candidates: Bugun skip_risk_budget olan TUM adaylar (bkz.
            RejectedCandidate). SADECE STRATEGY_QUALITY_FN'de kayitli
            stratejiler degerlendirilir (bkz. modul docstring'i madde 1).
        top_n: Her strateji icin AYRI donecek EN FAZLA aday sayisi
            (varsayilan config.OPPORTUNITIES_TOP_N).

    Returns:
        Strateji-basina en fazla top_n, toplamda len(STRATEGY_QUALITY_FN)*top_n
        OpportunityEntry. Kalitesi hesaplanamayan (yetersiz veri) adaylar
        SESSIZCE atlanir (siralamaya giremezler).
    """
    by_strategy: dict[str, list[tuple[float, RejectedCandidate, dict]]] = {}
    for c in candidates:
        quality_fn = STRATEGY_QUALITY_FN.get(c.strategy)
        if quality_fn is None:
            continue
        result = quality_fn(c)
        if result is None:
            continue
        score, extra_fields = result
        by_strategy.setdefault(c.strategy, []).append((score, c, extra_fields))

    entries: list[OpportunityEntry] = []
    for strategy, scored in by_strategy.items():
        scored.sort(key=lambda triple: triple[0], reverse=True)
        for _score, c, extra_fields in scored[:top_n]:
            entries.append(
                OpportunityEntry(
                    symbol=c.symbol,
                    strategy=c.strategy,
                    validation_status=STRATEGY_VALIDATION_STATUS.get(c.strategy, "deneysel"),
                    direction=c.direction,
                    applicable=(c.direction == 1 or USER_CAN_SHORT),
                    entry_price=c.entry_price,
                    stop_price=c.stop_price,
                    signal_date=c.signal_date.isoformat(),
                    rejection_reason=c.reason,
                    **extra_fields,
                )
            )
    return entries


def opportunities_to_dict(entries: list[OpportunityEntry], run_date: dt.date) -> dict:
    """Dashboard'un okuyacagi JSON-serilestirilebilir gosterimi uretir."""
    return {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "run_date": run_date.isoformat(),
        "risk_warning": RISK_WARNING,
        "entries": [asdict(e) for e in entries],
    }


def write_opportunities_json(
    entries: list[OpportunityEntry],
    run_date: dt.date,
    path: str | Path = OPPORTUNITIES_JSON_PATH,
) -> Path:
    """opportunities.json'i (tamamen) UZERINE YAZAR - paper_trading/logger.py::
    update_summary ile AYNI desen (Python periyodik yazar, dashboard SADECE okur)."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(opportunities_to_dict(entries, run_date), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return target
