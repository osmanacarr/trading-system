"""paper_trading/action_sheet.py - Gunluk Islem Formu (Daily Action Sheet).

AMAC: Kullanici artik kucuk gercek sermayeyle MANUEL islem yapiyor - "sistem
ne yapti" (trades.jsonl/summary.json) yetmiyor, "YARIN TAM OLARAK NE
YAPMALIYIM" sorusuna somut cevap gerekiyor. Bu modul, runner.py'nin HER
calistirmasinin sonunda (bkz. runner.py::run_once, ayni fetch/mark_prices
tekrar KULLANILIR - ikinci bir veri cekimi YAPILMAZ), o anki acik
pozisyonlardan bir "eylem formu" uretir.

KAPSAM/FELSEFE:
- Yalnizca UYGULANABILIR (config.USER_CAN_SHORT'a gore LONG, varsayilan
  taki gibi SHORT icin ozel marjin hesabi yoksa SADECE LONG) pozisyonlar
  "eylem" sayilir; SHORT pozisyonlar ayri gosterilir ama acikca "SADECE
  IZLEME" etiketlenir (bkz. dashboard/lib/constants.ts::directionApplicability
  ile AYNI ilke - TEK KAYNAK config.USER_CAN_SHORT, iki tarafta da).
- GERCEK SERMAYE / "KAC ADET ALINMALI": bu modul MUTLAK bir adet SAYISI
  URETMEZ. Kullanicinin gercek sermayesi BILINCLI olarak yalnizca
  dashboard'da (tarayici localStorage, sunucuya HIC gonderilmez - gorev
  tanimindaki acik gizlilik kisiti) tutulur; bu yuzden ne bu modul ne de
  Telegram ozeti bir "adet" hesaplayabilir/hesaplamamalidir - onun yerine
  ORANSAL bilgi (stop mesafesi %) verilir, mutlak miktar icin dashboard'daki
  panele yonlendirilir (bkz. format_action_steps). Dashboard'daki panel
  AYNI backtest.engine.compute_position_size formulunu TypeScript'te
  mirror'lar (bkz. dashboard/components/ActionSheetPanel.tsx - repo'daki
  "Python config/formul TS'de mirror'lanir" mevcut deseniyle tutarli,
  bkz. dashboard/lib/constants.ts).

Donchian'in trailing (10 gunluk) cikisinin SABIT bir tarihi YOKTUR - bu
yuzden exit_mechanism_explanation() her strateji icin dogru mekanizmayi
(sabit hedef vs. trailing vs. sinyal-bazli) acikca anlatir, kullaniciyi HER
GUN formu tekrar kontrol etmeye yonlendirir.
"""

from __future__ import annotations

import datetime as dt
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

from config import PAPER_TRADING_LOG_DIR, STOP_PROXIMITY_WARNING_PCT, USER_CAN_SHORT
from paper_trading.state import PositionRecord

ACTION_SHEET_JSON_PATH: Path = PAPER_TRADING_LOG_DIR / "action_sheet.json"

DISCLAIMER: str = (
    "Bu form karar destegidir, yatirim tavsiyesi degildir. Fiyatlar sinyal "
    "aninda hesaplanan degerlerdir, gercek piyasa fiyati farkli olabilir. "
    "Emirlerinizi kendi sorumlulugunuzda verin."
)


@dataclass
class ActionSheetEntry:
    """Tek bir acik pozisyon icin gunluk eylem formu satiri."""

    symbol: str
    strategy: str
    direction: int  # +1 long, -1 short
    applicable: bool  # config.USER_CAN_SHORT'a gore (bkz. modul docstring'i)
    entry_price: float
    stop_price: float
    entry_date: str  # ISO YYYY-MM-DD
    days_open: int
    current_price: float | None
    stop_distance_pct: float | None  # guncel fiyattan stop'a, yuzde (None = guncel fiyat yok)
    is_near_stop: bool  # STOP_PROXIMITY_WARNING_PCT ile ayni esik (bkz. runner.py)
    is_new_today: bool  # "YENI FIRSAT" - bugun acilan pozisyon
    exit_explanation: str
    unrealized_pnl_pct: float | None  # (guncel-giris)/giris * yon * 100 - guncel fiyat yoksa None


def _exit_mechanism_explanation(strategy: str, stop_price: float) -> str:
    """Strateji-bazli cikis mekanizmasini Turkce acik metinle anlatir.

    Donchian'in trailing (kanal) cikisinin SABIT bir tarihi YOK - stop
    seviyesi HER GUN yeniden hesaplanabilir; digger stratejiler (price_action,
    bollinger_fade) sabit hedef/stop kullanir, ma_voting ise oy sayisi
    donunce de kapanabilir. Yanlis strateji icin yanlis metin URETMEMEK
    icin (ornegin ileride Kart 1/Kart 3 canliya alinirsa) strateji-farkindali
    bir dict/if-zinciri kullanilir - tek bir "Donchian'a ozel" metin
    HARDCODE edilmez.
    """
    if strategy == "donchian":
        return (
            f"Bu pozisyon, fiyat {stop_price:.2f} seviyesine (10 gunluk takip stopu, "
            "HER GUN guncellenir) geri cekilirse KAPANACAK. Sabit bir cikis tarihi YOK - "
            "HER GUN bu formu tekrar kontrol edin."
        )
    if strategy == "ma_voting":
        return (
            f"Bu pozisyon, MA oy sayisi sifira/karsi yone donunce VEYA stop {stop_price:.2f} "
            "tetiklenince KAPANACAK. Sabit bir cikis tarihi YOK - HER GUN kontrol edin."
        )
    if strategy in ("price_action", "bollinger_fade"):
        return (
            f"Bu pozisyon SABIT hedef/stop ile calisir: stop {stop_price:.2f} veya hedef "
            "fiyat vurulunca KAPANACAK (trailing yok, ama yine de HER GUN kontrol edilmesi onerilir)."
        )
    return f"Cikis kosulu: stop {stop_price:.2f} tetiklenince kapanir."


def build_action_sheet(
    positions: list[PositionRecord],
    run_date: dt.date,
    mark_prices: dict[str, float] | None = None,
) -> list[ActionSheetEntry]:
    """Acik pozisyonlardan gunluk eylem formu satirlarini uretir.

    Args:
        positions: state.list_open_positions() ciktisi (TUM stratejiler).
        run_date: Bu formun "bugun" kabul ettigi tarih.
        mark_prices: {sembol: guncel/son kapanis fiyati} - runner.py'nin
            AYNI calistirmada zaten cektigi veri (bkz. modul docstring'i,
            ikinci bir veri cekimi YAPILMAZ). None/eksik sembol icin
            current_price/stop_distance_pct/is_near_stop hesaplanamaz (None/False
            donulur) - bu bir hata degil, sadece o an icin veri yok demektir
            (orn. standalone/offline cagrida).

    Returns:
        symbol'e gore sirali ActionSheetEntry listesi.
    """
    mark_prices = mark_prices or {}
    entries: list[ActionSheetEntry] = []
    for pos in sorted(positions, key=lambda p: (p.symbol, p.strategy)):
        applicable = pos.direction == 1 or USER_CAN_SHORT
        days_open = (run_date - pos.entry_date).days
        current_price = mark_prices.get(pos.symbol)

        stop_distance_pct: float | None = None
        is_near_stop = False
        unrealized_pnl_pct: float | None = None
        if current_price is not None and current_price > 0:
            stop_distance_pct = abs(current_price - pos.stop_price) / current_price * 100
            initial_risk = abs(pos.entry_price - pos.stop_price)
            distance_to_stop = abs(current_price - pos.stop_price)
            if initial_risk > 0:
                is_near_stop = distance_to_stop < STOP_PROXIMITY_WARNING_PCT * initial_risk
            if pos.entry_price > 0:
                unrealized_pnl_pct = (current_price - pos.entry_price) / pos.entry_price * pos.direction * 100

        entries.append(
            ActionSheetEntry(
                symbol=pos.symbol,
                strategy=pos.strategy,
                direction=pos.direction,
                applicable=applicable,
                entry_price=pos.entry_price,
                stop_price=pos.stop_price,
                entry_date=pos.entry_date.isoformat(),
                days_open=days_open,
                current_price=current_price,
                stop_distance_pct=stop_distance_pct,
                is_near_stop=is_near_stop,
                is_new_today=pos.entry_date == run_date,
                exit_explanation=_exit_mechanism_explanation(pos.strategy, pos.stop_price),
                unrealized_pnl_pct=unrealized_pnl_pct,
            )
        )
    return entries


def format_action_steps(entry: ActionSheetEntry) -> str:
    """Uygulanabilir (LONG) bir pozisyon icin adim-adim eylem metnini uretir.

    Miktar/adet BILEREK bu metinde YOK (bkz. modul docstring'i - gercek
    sermaye yalnizca dashboard'un tarayici localStorage'inda tutulur, bu
    modul/Telegram sunucu tarafinda calisir ve o degere erisemez/erismemelidir).
    """
    yon = "LONG" if entry.direction == 1 else "SHORT"
    risk_pct = abs(entry.stop_price - entry.entry_price) / entry.entry_price * 100
    return (
        f"{entry.symbol} - {yon}\n"
        f"1. Kendi araci kurum uygulamanizda {entry.symbol} hissesini bulun\n"
        f"2. Guncel piyasa fiyatina yakin (sinyal fiyati: {entry.entry_price:.2f}) LIMIT EMIR ile alin\n"
        f"3. Stop-loss emrinizi {entry.stop_price:.2f} seviyesine koyun (bu, giris fiyatindan %{risk_pct:.1f} uzaklikta)\n"
        f"4. Miktar: dashboard'daki 'Bugunun Islem Formu' panelinde gercek sermayenize gore hesaplanir "
        "(bu ozette YOK - gercek sermaye yalnizca tarayicinizda tutulur, sunucuya gonderilmez)\n"
        f"5. HER GUN bu formu tekrar kontrol edin - stop seviyesi guncellenebilir\n"
        f"{entry.exit_explanation}"
    )


def format_daily_telegram_summary(entries: list[ActionSheetEntry], run_date: dt.date) -> str:
    """Gunluk Telegram ozet mesajini uretir.

    HER GUN gonderilmek uzere tasarlandi (bkz. gorev tanimi - sadece yeni
    sinyal geldiginde degil, cunku mevcut pozisyonlarin trailing stop'u
    sessizce degisebilir ve kullanicinin bunu HER GUN gormesi gerekir).
    Acik pozisyon HIC yoksa None doner (cagiran gondermeyi atlar - bos bir
    "0 pozisyon var" mesaji her gun spam olur).
    """
    if not entries:
        return ""

    actionable = [e for e in entries if e.applicable]
    watch_only = [e for e in entries if not e.applicable]

    lines = [f"📋 Gunluk Islem Formu - {run_date.isoformat()}", DISCLAIMER, ""]

    if actionable:
        lines.append(f"Bugun uygulanabilir {len(actionable)} pozisyon var:")
        for e in actionable:
            flag = " ⚠ STOP'A YAKIN" if e.is_near_stop else ""
            new_flag = " 🆕 YENI FIRSAT" if e.is_new_today else ""
            lines.append(
                f"- {e.symbol} [{e.strategy}] LONG | giris {e.entry_price:.2f} | "
                f"stop {e.stop_price:.2f}{flag}{new_flag}"
            )
    else:
        lines.append("Bugun uygulanabilir (LONG) pozisyon yok.")

    if watch_only:
        lines.append("")
        lines.append(f"SADECE IZLEME (SHORT, siz uygulayamiyorsunuz) - {len(watch_only)} pozisyon:")
        for e in watch_only:
            lines.append(f"- {e.symbol} [{e.strategy}] SHORT | giris {e.entry_price:.2f} | stop {e.stop_price:.2f}")

    lines.append("")
    lines.append("Miktar/adet icin dashboard'daki 'Bugunun Islem Formu' panelini kontrol edin (gercek sermayeniz orada, sadece tarayicinizda).")

    return "\n".join(lines)


def action_sheet_to_dict(entries: list[ActionSheetEntry], run_date: dt.date) -> dict:
    """Dashboard'un okuyacagi JSON-serilestirilebilir gosterimi uretir.

    "prices_updated_at" BILEREK "generated_at" ile AYNI baslar (tam olusturma
    aninda fiyatlar da tazedir - mark_prices runner.py'nin AYNI calistirmasindan
    gelir) ama SONRADAN refresh_live_prices() TARAFINDAN BAGIMSIZ guncellenir
    (bkz. o fonksiyonun docstring'i - formun geri kalani gunde bir, fiyatlar
    ~birkac dakikada bir yenilenir - iki ayri tazelik saati, dashboard'un
    ikisini de ayri ayri gosterebilmesi icin AYRI tutulur)."""
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    return {
        "generated_at": now,
        "prices_updated_at": now,
        "run_date": run_date.isoformat(),
        "disclaimer": DISCLAIMER,
        "entries": [asdict(e) for e in entries],
    }


def write_action_sheet_json(
    entries: list[ActionSheetEntry],
    run_date: dt.date,
    path: str | Path = ACTION_SHEET_JSON_PATH,
) -> Path:
    """action_sheet.json'i (tamamen) UZERINE YAZAR - dashboard'un okuyacagi son durum
    (bkz. paper_trading/logger.py::update_summary ile AYNI desen - Python periyodik
    yazar, dashboard SADECE okur)."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(action_sheet_to_dict(entries, run_date), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return target


def refresh_live_prices(
    path: str | Path = ACTION_SHEET_JSON_PATH,
    fetch_batch_fn: Callable[[list[str]], dict] | None = None,
) -> bool:
    """Mevcut action_sheet.json'daki fiyat-bagimli alanlari (current_price,
    stop_distance_pct, is_near_stop, unrealized_pnl_pct) YERINDE gunceller -
    formun geri kalanini (giris/stop/exit_explanation/is_new_today/gunun
    sinyalleri) YENIDEN URETMEZ.

    NEDEN AYRI: gunluk formun tamami (build_action_sheet) SADECE runner.py'nin
    gunde-bir calistigi anda, TUM evreni tarayip sinyal uretirken zaten
    elindeki mark_prices ile olusturulur - bu PAHALI bir islemdir (yuzlerce
    sembol). Ama SADECE acik pozisyonlarin (tipik olarak ~5 sembol) GUNCEL
    fiyatini yenilemek COK UCUZDUR - gozcu/data_fetch.py::fetch_daily_batch
    (gozcu'nun KENDI "last_price"i icin kullandigi AYNI toplu yf.download
    yontemi - bkz. gozcu/scanner.py::_compute_symbol_metrics) TEK bir toplu
    cagriyla hepsini ceker. Bu fonksiyon gozcu_scan.yml'in ZATEN var olan
    ~2 dakikalik harici tetikleme dongusune (cron-job.org) eklenerek "gercek
    zamanli"ya yakin bir tazelik saglar - runner.py'nin gunde-bir sinyal
    uretme mantigina HIC dokunmadan (bkz. modul docstring'i, gorev tanimi).

    Args:
        path: Guncellenecek action_sheet.json yolu.
        fetch_batch_fn: {sembol: OHLCV df} donen toplu getirme fonksiyonu
            (varsayilan gozcu.data_fetch.fetch_daily_batch - testler icin
            enjekte edilebilir). Import LAZY yapilir (action_sheet.py'nin
            gozcu'ya sabit bir bagimliligi olmasin, sadece bu fonksiyon
            cagrildiginda gerekli olsun diye).

    Returns:
        Dosya var olup basariyla guncellendiyse True; action_sheet.json
        HENUZ hic olusturulmadiysa (ilk gunluk calistirma once gelmeli)
        False (sessizce atlanir, hata FIRLATILMAZ - bkz. bu depodaki genel
        "veri yoksa/hata olursa sessizce atla" felsefesi).
    """
    target = Path(path)
    if not target.exists():
        return False

    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False

    entries = data.get("entries", [])
    if not entries:
        return True

    if fetch_batch_fn is None:
        from gozcu.data_fetch import fetch_daily_batch as fetch_batch_fn  # lazy import, bkz. docstring

    symbols = sorted({e["symbol"] for e in entries})
    price_data = fetch_batch_fn(symbols)

    for entry in entries:
        df = price_data.get(entry["symbol"])
        if df is None or df.empty:
            continue  # bu sembol icin cekim basarisiz - ESKI degerler KORUNUR (sessizce atla)
        current_price = float(df["Close"].dropna().iloc[-1])
        if current_price <= 0:
            continue

        entry["current_price"] = current_price
        entry["stop_distance_pct"] = abs(current_price - entry["stop_price"]) / current_price * 100
        initial_risk = abs(entry["entry_price"] - entry["stop_price"])
        distance_to_stop = abs(current_price - entry["stop_price"])
        entry["is_near_stop"] = bool(initial_risk > 0 and distance_to_stop < STOP_PROXIMITY_WARNING_PCT * initial_risk)
        if entry["entry_price"] > 0:
            entry["unrealized_pnl_pct"] = (
                (current_price - entry["entry_price"]) / entry["entry_price"] * entry["direction"] * 100
            )

    data["entries"] = entries
    data["prices_updated_at"] = dt.datetime.now(dt.timezone.utc).isoformat()

    target.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return True


def _print_human_readable(entries: list[ActionSheetEntry], run_date: dt.date) -> None:
    print(f"Gunluk Islem Formu - {run_date.isoformat()}")
    print(DISCLAIMER)
    print("-" * 80)
    if not entries:
        print("Acik pozisyon yok.")
        return
    for e in entries:
        tag = "UYGULANABILIR" if e.applicable else "SADECE IZLEME"
        print(f"\n[{tag}] {e.symbol} [{e.strategy}] {'LONG' if e.direction == 1 else 'SHORT'}")
        print(f"  giris: {e.entry_price:.2f} | stop: {e.stop_price:.2f} | acik gunu: {e.days_open}")
        if e.current_price is not None:
            near = " (STOP'A YAKIN)" if e.is_near_stop else ""
            pnl = f" | P&L: %{e.unrealized_pnl_pct:+.2f}" if e.unrealized_pnl_pct is not None else ""
            print(f"  guncel: {e.current_price:.2f} | stop mesafesi: %{e.stop_distance_pct:.2f}{near}{pnl}")
        else:
            print("  guncel fiyat: bilinmiyor")
        if e.is_new_today:
            print("  >> YENI FIRSAT (bugun acildi)")
        print(f"  {e.exit_explanation}")
        if e.applicable:
            print("  " + format_action_steps(e).replace("\n", "\n  "))


def main(argv: list[str] | None = None) -> None:
    """CLI onizleme: gercek state.db'deki acik pozisyonlardan eylem formunu
    uretip STDOUT'a yazdirir - hicbir state/log/Telegram YAN ETKISI yoktur
    (bkz. run_once icindeki asil canli entegrasyon, bu sadece manuel
    onizleme/dogrulama icindir). --fetch-prices verilirse guncel fiyatlar
    (data.fetch.fetch_ohlcv ile, YENIDEN cekilir) de eklenir; verilmezse
    stop mesafesi hesaplanamaz (current_price=None).

    --refresh-live-prices FARKLI bir modu tetikler (YAN ETKILI - gercek
    action_sheet.json'i GUNCELLER): formu YENIDEN URETMEZ, sadece
    refresh_live_prices()'i cagirir (bkz. o fonksiyonun docstring'i -
    gozcu_scan.yml'in ~2 dakikalik dongusunden cagrilmak icin tasarlandi)."""
    import argparse

    from data.fetch import fetch_ohlcv
    from paper_trading.runner import fetch_symbol_bars
    from paper_trading.state import PaperTradingState

    parser = argparse.ArgumentParser(description="Gunluk Islem Formu onizleme (yan etkisiz)")
    parser.add_argument("--fetch-prices", action="store_true", help="Acik pozisyonlar icin guncel fiyati yeniden ceker")
    parser.add_argument("--date", default=None, help="YYYY-MM-DD (varsayilan: bugun)")
    parser.add_argument(
        "--refresh-live-prices", action="store_true",
        help="YAN ETKILI: mevcut action_sheet.json'daki fiyat alanlarini gozcu'nun toplu-fetch "
             "yontemiyle YERINDE gunceller (formu yeniden uretmez) - bkz. refresh_live_prices()",
    )
    args = parser.parse_args(argv)

    if args.refresh_live_prices:
        updated = refresh_live_prices()
        print("action_sheet.json fiyatlari guncellendi." if updated else "action_sheet.json henuz yok, atlandi.")
        return

    run_date = dt.date.fromisoformat(args.date) if args.date else dt.date.today()
    state = PaperTradingState(read_only=True)
    try:
        positions = state.list_open_positions()
    finally:
        state.close()

    mark_prices: dict[str, float] = {}
    if args.fetch_prices:
        for pos in positions:
            if pos.symbol in mark_prices:
                continue
            market = "bist" if pos.symbol.endswith(".IS") else "crypto"
            df, skip_reason = fetch_symbol_bars(pos.symbol, market, run_date, fetch_ohlcv)
            if df is not None:
                mark_prices[pos.symbol] = float(df["Close"].iloc[-1])
            else:
                print(f"[uyari] {pos.symbol} icin guncel fiyat cekilemedi ({skip_reason})")

    entries = build_action_sheet(positions, run_date, mark_prices)
    _print_human_readable(entries, run_date)


if __name__ == "__main__":
    main()
