"""paper_trading/opportunities.py - "En Iyi N Firsat": paper trading'in
GUNLUK risk butcesi (M2 korelasyon kumeleri + M2-eki net yonlu maruziyet +
brut kaldirac) tarafindan REDDEDILEN (skip_risk_budget) ama Donchian'in
KENDI (dogrulanmis) kirilim-kalite olcusune gore GUCLU olan adaylari
kullaniciya gosterir - boylece kullanici, sistemin sanal defterinde
acmadigi ama kendi gercek sermayesiyle degerlendirmek isteyebilecegi
sinyalleri KAYBETMEZ (bkz. ilgili konusma, "En Iyi N Firsat" arastirma
talebi).

DURUSTLUK/GUVENLIK CERCEVESI (arastirma bulgularina dogrudan cevap):

1. KAPSAM: SADECE bugun REDDEDILEN adaylar (zaten acilanlar Action Sheet'te
   zaten gorunuyor, burada TEKRAR gosterilmez - ozelligin butun degeri
   "kaybolan" sinyalleri gostermekte, bkz. modul docstring'i "amac").
   SADECE etkin/dogrulanmis strateji (su an: donchian) - devre disi Kart 1/
   Kart 3 sinyalleri BURAYA ASLA girmez (bkz. build_opportunities).

2. SIRALAMA: research/opportunity_score.py'nin SUREKLI kirilim-kalite
   metrikleri (Donchian'in KENDI zaten dogrulanmis body/volume filtrelerinin
   surekli versiyonu) - gozcu'nun dikkat skoru KARISTIRILMAZ,
   research/ensemble.py::composite_score KULLANILMAZ (yetersiz veri, bkz.
   opportunity_score.py modul docstring'i).

3. HER KAYITTA ZORUNLU red nedeni (rejection_reason, bkz.
   paper_trading/runner.py::_classify_rejection_reason) - GIZLENEMEZ,
   dashboard'da HER karti gostermek ZORUNDADIR.

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

import pandas as pd

from config import OPPORTUNITIES_TOP_N, PAPER_TRADING_LOG_DIR, USER_CAN_SHORT
from research.opportunity_score import compute_donchian_breakout_quality

OPPORTUNITIES_JSON_PATH: Path = PAPER_TRADING_LOG_DIR / "opportunities.json"

RISK_WARNING: str = (
    "Bu adaylar RISK KATMANI TARAFINDAN REDDEDILDI (portfoy butcesi, korelasyon kumesi "
    "veya net yonlu maruziyet siniri) - paper trading'in KENDI sanal defterinde acilmadilar. "
    "Kendi gercek hesabinizda acarsaniz, korelasyon ve yon riskini SIZ yonetmelisiniz - bu "
    "kisitlar hesabiniza OTOMATIK UYGULANMAZ. 'Kalite' olcusu SADECE Donchian'in kendi "
    "kirilim gucu olcumudur (kirilim mesafesi/hacim/govde orani) - gelecekteki performansin "
    "GARANTISI DEGILDIR."
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
    direction: int
    applicable: bool  # config.USER_CAN_SHORT'a gore (bkz. action_sheet.py ile AYNI ilke)
    entry_price: float
    stop_price: float
    signal_date: str
    rejection_reason: str
    atr_distance: float | None
    volume_ratio: float | None
    body_ratio: float | None


def build_opportunities(
    candidates: list[RejectedCandidate],
    top_n: int = OPPORTUNITIES_TOP_N,
) -> list[OpportunityEntry]:
    """Reddedilen adaylardan, kirilim-kalitesine (atr_distance) gore
    sirali EN FAZLA top_n girdi uretir.

    Args:
        candidates: Bugun skip_risk_budget olan TUM adaylar (bkz.
            RejectedCandidate). SADECE strategy=="donchian" olanlar
            degerlendirilir (bkz. modul docstring'i madde 1).
        top_n: Donecek EN FAZLA aday sayisi (varsayilan
            config.OPPORTUNITIES_TOP_N).

    Returns:
        atr_distance'e gore AZALAN sirali, en fazla top_n OpportunityEntry.
        Kalitesi hesaplanamayan (yetersiz veri/ATR<=0) adaylar SESSIZCE
        atlanir (siralamaya giremezler - bkz. compute_donchian_breakout_quality).
    """
    scored: list[tuple[float, OpportunityEntry]] = []
    for c in candidates:
        if c.strategy != "donchian":
            continue
        quality = compute_donchian_breakout_quality(c.df, c.direction)
        if quality is None or quality["atr_distance"] is None:
            continue
        entry = OpportunityEntry(
            symbol=c.symbol,
            strategy=c.strategy,
            direction=c.direction,
            applicable=(c.direction == 1 or USER_CAN_SHORT),
            entry_price=c.entry_price,
            stop_price=c.stop_price,
            signal_date=c.signal_date.isoformat(),
            rejection_reason=c.reason,
            atr_distance=quality["atr_distance"],
            volume_ratio=quality["volume_ratio"],
            body_ratio=quality["body_ratio"],
        )
        scored.append((quality["atr_distance"], entry))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [entry for _, entry in scored[:top_n]]


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
