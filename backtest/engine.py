"""Backtest motoru: ATR bazli stop, sabit %risk pozisyon boyutu, komisyon +
slipaj dahil, gunluk bar bazinda islem simulasyonu.

Kaynak: faz2_strateji_kartlari.md ("Ortak varsayimlar", Kart 4) ve
faz3.5_matematiksel_formalizasyon.md SS2.3 (pozisyon buyuklugu formulu):

    size_t = (E_t * rho) / |C_t - stop_t|,  stop_t = C_t - k*ATR_n(t)

n=20 (Colab'da test edilen Kart 4 parametresi, config.DONCHIAN_ATR_PERIOD;
formalizasyon dokumanindaki "ATR_14" ifadesi genel formulu illustre eden bir
ornekti, bkz. config.py docstring'i), k=2.

Uc strateji tipi desteklenir:
- "donchian": ilk ATR-bazli stop + trailing (kanal) cikis (Kart 4)
- "price_action": sabit stop + sabit R/R hedef, trailing yok (Kart 5)
- "ma_voting": ATR-bazli stop + sinyal-bazli (oy sayisi sifirlaninca) cikis,
  oy sayisina orantili pozisyon buyuklugu (Kart 1)

Basitlestirici varsayimlar (prototip asamasi icin, gunluk bar verisiyle
calisirken kacinilmaz):
- Giris/trailing-cikis fiyati bar KAPANISI'dir (Kart kurallari da kapanis
  bazli tanimliyor).
- Stop/hedef gibi gun ICI seviyeler o barin Low/High'i ile test edilir;
  ayni barda hem stop hem hedef "vurulabilir" durumda stop-loss ONCELIKLI
  sayilir (muhafazakar varsayim). Acilis (Open) stop/hedefin otesindeyse
  (gap), fiil Open fiyatindan gerceklesir.
- Komisyon, hem giris hem cikiste islem tutarinin COMMISSION_PCT'i kadar
  ayri ayri alinir. Slipaj, fiil fiyatini alici/satici aleyhine
  SLIPPAGE_PCT kadar kaydirir.

Bu moduldeki OpenPosition / apply_slippage / resolve_intrabar_exit /
close_position / check_donchian_exit / plan_donchian_entry / compute_atr /
compute_position_size fonksiyonlari BILINCLI OLARAK public'tir: ayni
formuller paper_trading/runner.py tarafindan da (tek bar, gunluk artimli
calisma icin) kullanilir - boylece backtest ve paper trading arasinda
risk/stop/pozisyon-buyuklugu mantigi TEK bir yerde tanimlanir.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

import numpy as np
import pandas as pd

from config import (
    COMMISSION_PCT,
    DONCHIAN_ATR_PERIOD,
    DONCHIAN_ATR_STOP_MULT,
    INITIAL_CAPITAL,
    MA_VOTING_PAIRS,
    RISK_PER_TRADE,
    SLIPPAGE_PCT,
)

TRADE_COLUMNS: list[str] = [
    "entry_date",
    "exit_date",
    "direction",
    "entry_price",
    "stop_price",
    "exit_price",
    "size",
    "pnl",
    "r_multiple",
    "exit_reason",
    "mae_r",
    "mfe_r",
]


@dataclass
class OpenPosition:
    """Acik bir pozisyonun durumu (backtest loop'u ve paper trading state'i
    arasinda paylasilan ortak temsil)."""

    direction: int  # +1 long, -1 short
    entry_date: pd.Timestamp
    entry_price: float
    stop_price: float
    size: float
    initial_risk: float = field(init=False)
    # MAE/MFE (quant2.md - blotter paketindeki "trade kapanmadan once ne
    # kadar aleyhte/lehte gitti" analizi): pozisyon acikken gorulen en kotu/
    # en iyi ANLIK fiyat sapmasi (R-oncesi, ham fiyat birimi). Giris barinin
    # kendisi SAYILMAZ (pozisyon o barin KAPANISINDA acilir, o gunun
    # High/Low'u pozisyon acikken gorulmedi) - bkz. update_excursion cagri
    # noktalari.
    max_adverse_price: float = field(init=False, default=0.0)
    max_favorable_price: float = field(init=False, default=0.0)

    def __post_init__(self) -> None:
        self.initial_risk = abs(self.entry_price - self.stop_price)

    def update_excursion(self, high: float, low: float) -> None:
        """Bu barin High/Low'una gore en kotu/en iyi ANLIK sapmayi gunceller."""
        if self.direction == 1:
            adverse = self.entry_price - low
            favorable = high - self.entry_price
        else:
            adverse = high - self.entry_price
            favorable = self.entry_price - low
        self.max_adverse_price = max(self.max_adverse_price, adverse)
        self.max_favorable_price = max(self.max_favorable_price, favorable)


def compute_atr(df: pd.DataFrame, period: int = DONCHIAN_ATR_PERIOD) -> pd.Series:
    """Wilder'in ortalama gercek aralik (ATR) yontemiyle ATR hesaplar.

    Args:
        df: ["High","Low","Close"] kolonlarini iceren, kronolojik sirali
            DataFrame.
        period: ATR periyodu (varsayilan config.DONCHIAN_ATR_PERIOD, 20).

    Returns:
        df ile ayni index'e sahip ATR Series'i. Ilk `period` bar NaN'dir.
    """
    high, low, close = df["High"], df["Low"], df["Close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

    atr = tr.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    atr.iloc[: period - 1] = np.nan
    return atr


def compute_position_size(
    equity: float,
    risk_pct: float,
    entry_price: float,
    stop_price: float,
) -> float:
    """Sabit-yuzde risk pozisyon boyutunu hesaplar (SS2.3 formulu).

    Args:
        equity: Guncel sermaye (E_t).
        risk_pct: Islem basina riske edilecek sermaye orani (rho).
        entry_price: Planlanan giris fiyati.
        stop_price: Planlanan stop fiyati.

    Returns:
        Adet/birim cinsinden pozisyon buyuklugu. Giris/stop mesafesi 0 ise
        0.0 doner (islem acilamaz).
    """
    risk_distance = abs(entry_price - stop_price)
    if risk_distance <= 0:
        return 0.0
    return (equity * risk_pct) / risk_distance


def apply_slippage(price: float, direction: int, is_entry: bool, slippage_pct: float) -> float:
    """Fiil fiyatina alici/satici aleyhine slipaj uygular."""
    adverse = direction if is_entry else -direction
    return price * (1 + adverse * slippage_pct)


def plan_donchian_entry(
    close: float,
    direction: int,
    atr_value: float,
    atr_stop_mult: float = DONCHIAN_ATR_STOP_MULT,
    slippage_pct: float = SLIPPAGE_PCT,
) -> tuple[float, float]:
    """Donchian girisi icin fiil fiyati ve ilk ATR stop'unu hesaplar (SS2.3).

    Args:
        close: Sinyal barinin kapanis fiyati (giris tetikleyicisi).
        direction: +1 (long) veya -1 (short).
        atr_value: Giris barindaki ATR degeri.
        atr_stop_mult: ATR carpani (k, varsayilan 2).
        slippage_pct: Giris fiil fiyatina uygulanacak slipaj orani.

    Returns:
        (entry_price, stop_price). direction=+1 icin stop = entry - k*ATR;
        direction=-1 icin stop = entry + k*ATR (tek formulle, isaretle).
    """
    entry_price = apply_slippage(close, direction, is_entry=True, slippage_pct=slippage_pct)
    stop_price = entry_price - atr_stop_mult * atr_value * direction
    return entry_price, stop_price


def resolve_intrabar_exit(
    direction: int,
    open_: float,
    high: float,
    low: float,
    stop_price: float,
    target_price: float | None,
) -> tuple[float, str] | None:
    """Bir barin OHLC'sine gore stop/hedefin vurulup vurulmadigini cozer.

    Stop-loss, ayni barda hem stop hem hedef tetiklenebilecek durumlarda
    ONCELIKLIDIR (muhafazakar varsayim). Acilis fiyati seviyenin otesindeyse
    (gap), fiil Open'dan gerceklesir.

    Returns:
        (fiil_fiyati, sebep) veya bu barda cikis yoksa None. sebep in
        {"stop", "target"}.
    """
    if direction == 1:
        if open_ <= stop_price:
            return open_, "stop"
        if low <= stop_price:
            return stop_price, "stop"
        if target_price is not None:
            if open_ >= target_price:
                return open_, "target"
            if high >= target_price:
                return target_price, "target"
        return None
    else:
        if open_ >= stop_price:
            return open_, "stop"
        if high >= stop_price:
            return stop_price, "stop"
        if target_price is not None:
            if open_ <= target_price:
                return open_, "target"
            if low <= target_price:
                return target_price, "target"
        return None


def check_donchian_exit(
    direction: int,
    open_: float,
    high: float,
    low: float,
    close: float,
    stop_price: float,
    trailing_level: float | None,
) -> tuple[float, str] | None:
    """Donchian pozisyonu icin tek barlik cikis kontrolu (stop -> trailing).

    Once (gun ici, Low/High bazli) sabit ATR stop'u kontrol edilir; o
    tetiklenmediyse (kapanis bazli) trailing kanal ihlali kontrol edilir.
    Hem run_donchian_backtest'in ic dongusu hem de paper_trading/runner.py
    tarafindan gunluk artimli calisma icin kullanilir.

    Args:
        direction: +1 (long) veya -1 (short).
        open_, high, low, close: Bu barin OHLC degerleri.
        stop_price: Girişte sabitlenmis ATR stop fiyati.
        trailing_level: Bu bar icin trailing (m-gunluk) kanal seviyesi
            (signals.donchian exit_long_level / exit_short_level), NaN/None
            olabilir (henuz yeterli veri yoksa).

    Returns:
        (fiil_fiyati, sebep) veya bu barda cikis yoksa None. sebep in
        {"stop", "trailing"}.
    """
    exit_result = resolve_intrabar_exit(direction, open_, high, low, stop_price, target_price=None)
    if exit_result is not None:
        return exit_result

    if trailing_level is not None and pd.notna(trailing_level):
        breached = (direction == 1 and close < trailing_level) or (direction == -1 and close > trailing_level)
        if breached:
            return close, "trailing"

    return None


def close_position(
    pos: OpenPosition,
    exit_date: pd.Timestamp,
    raw_exit_price: float,
    exit_reason: str,
    commission_pct: float,
    slippage_pct: float,
) -> tuple[dict, float]:
    """Acik pozisyonu kapatir; islem kaydini ve net (komisyonlu) PnL'i dondurur."""
    fill_price = apply_slippage(raw_exit_price, pos.direction, is_entry=False, slippage_pct=slippage_pct)
    gross_pnl = (fill_price - pos.entry_price) * pos.direction * pos.size
    exit_commission = commission_pct * fill_price * pos.size
    net_pnl = gross_pnl - exit_commission
    r_multiple = ((fill_price - pos.entry_price) * pos.direction) / pos.initial_risk if pos.initial_risk > 0 else 0.0
    mae_r = pos.max_adverse_price / pos.initial_risk if pos.initial_risk > 0 else 0.0
    mfe_r = pos.max_favorable_price / pos.initial_risk if pos.initial_risk > 0 else 0.0

    trade = {
        "entry_date": pos.entry_date,
        "exit_date": exit_date,
        "direction": pos.direction,
        "entry_price": pos.entry_price,
        "stop_price": pos.stop_price,
        "exit_price": fill_price,
        "size": pos.size,
        "pnl": net_pnl,
        "r_multiple": r_multiple,
        "exit_reason": exit_reason,
        "mae_r": mae_r,
        "mfe_r": mfe_r,
    }
    return trade, net_pnl


def run_donchian_backtest(
    df: pd.DataFrame,
    signals: pd.DataFrame,
    initial_capital: float = INITIAL_CAPITAL,
    risk_pct: float = RISK_PER_TRADE,
    atr_period: int = DONCHIAN_ATR_PERIOD,
    atr_stop_mult: float = DONCHIAN_ATR_STOP_MULT,
    commission_pct: float = COMMISSION_PCT,
    slippage_pct: float = SLIPPAGE_PCT,
) -> tuple[pd.DataFrame, pd.Series]:
    """Donchian Breakout (Kart 4) icin islem simulasyonu calistirir.

    Giris kapanista, ilk stop ATR bazli (entry -+ k*ATR), sonrasinda cikis
    signals.exit_long_level / exit_short_level trailing seviyesine (kapanis
    bazli) veya ilk ATR stop'una (gun ici, Low/High bazli) gore belirlenir -
    hangisi once tetiklenirse.

    Args:
        df: ["Open","High","Low","Close","Volume"] kolonlarina sahip fiyat
            verisi.
        signals: signals.donchian.generate_signals ciktisi (ayni index).
        initial_capital: Baslangic sermayesi.
        risk_pct: Islem basina risk orani (rho).
        atr_period: ATR periyodu.
        atr_stop_mult: Ilk stop icin ATR carpani (k).
        commission_pct: Tek yonlu komisyon orani.
        slippage_pct: Fiil fiyatina uygulanan slipaj orani.

    Returns:
        (trades, equity_curve): trades -> TRADE_COLUMNS kolonlarina sahip
        DataFrame (islem yoksa bos); equity_curve -> df.index'e hizali,
        gunluk mark-to-market sermaye Series'i.
    """
    atr = compute_atr(df, period=atr_period)

    equity = initial_capital
    equity_curve = pd.Series(index=df.index, dtype=float)
    trades: list[dict] = []
    pos: OpenPosition | None = None

    for t in df.index:
        row = df.loc[t]
        sig = signals.loc[t]

        if pos is not None and pos.entry_date != t:
            pos.update_excursion(row["High"], row["Low"])

        if pos is not None:
            trailing_level = sig["exit_long_level"] if pos.direction == 1 else sig["exit_short_level"]
            exit_result = check_donchian_exit(
                pos.direction, row["Open"], row["High"], row["Low"], row["Close"], pos.stop_price, trailing_level
            )
            if exit_result is not None:
                raw_price, reason = exit_result
                trade, net_pnl = close_position(pos, t, raw_price, reason, commission_pct, slippage_pct)
                trades.append(trade)
                equity += net_pnl
                pos = None

        if pos is None:
            current_atr = atr.loc[t]
            if pd.notna(current_atr) and current_atr > 0:
                direction = 1 if bool(sig["entry_long"]) else (-1 if bool(sig["entry_short"]) else 0)
                if direction != 0:
                    entry_price, stop_price = plan_donchian_entry(
                        row["Close"], direction, current_atr, atr_stop_mult, slippage_pct
                    )
                    size = compute_position_size(equity, risk_pct, entry_price, stop_price)
                    if size > 0:
                        equity -= commission_pct * entry_price * size
                        pos = OpenPosition(direction, t, entry_price, stop_price, size)

        if pos is not None:
            unrealized = (row["Close"] - pos.entry_price) * pos.direction * pos.size
            equity_curve.loc[t] = equity + unrealized
        else:
            equity_curve.loc[t] = equity

    trades_df = pd.DataFrame(trades, columns=TRADE_COLUMNS)
    return trades_df, equity_curve


def run_price_action_backtest(
    df: pd.DataFrame,
    signals: pd.DataFrame,
    initial_capital: float = INITIAL_CAPITAL,
    risk_pct: float = RISK_PER_TRADE,
    commission_pct: float = COMMISSION_PCT,
    slippage_pct: float = SLIPPAGE_PCT,
) -> tuple[pd.DataFrame, pd.Series]:
    """Price Action Breakout (Kart 5, Model B) icin islem simulasyonu calistirir.

    Giris kapanista, stop = kirilim barinin en dusuk/yuksek noktasi, hedef =
    sabit R/R (signals.price_action.generate_signals icinde onceden
    hesaplanmis). Trailing cikis YOK; pozisyon stop veya hedefe carpana
    kadar tutulur.

    Args:
        df: ["Open","High","Low","Close","Volume"] kolonlarina sahip fiyat
            verisi.
        signals: signals.price_action.generate_signals ciktisi (ayni index).
        initial_capital: Baslangic sermayesi.
        risk_pct: Islem basina risk orani.
        commission_pct: Tek yonlu komisyon orani.
        slippage_pct: Fiil fiyatina uygulanan slipaj orani.

    Returns:
        (trades, equity_curve): bkz. run_donchian_backtest.
    """
    equity = initial_capital
    equity_curve = pd.Series(index=df.index, dtype=float)
    trades: list[dict] = []
    pos: OpenPosition | None = None
    target_price: float | None = None

    for t in df.index:
        row = df.loc[t]
        sig = signals.loc[t]

        if pos is not None and pos.entry_date != t:
            pos.update_excursion(row["High"], row["Low"])

        if pos is not None:
            exit_result = resolve_intrabar_exit(
                pos.direction, row["Open"], row["High"], row["Low"], pos.stop_price, target_price
            )
            if exit_result is not None:
                raw_price, reason = exit_result
                trade, net_pnl = close_position(pos, t, raw_price, reason, commission_pct, slippage_pct)
                trades.append(trade)
                equity += net_pnl
                pos = None
                target_price = None

        if pos is None:
            direction = 1 if bool(sig["entry_long"]) else (-1 if bool(sig["entry_short"]) else 0)
            if direction != 0:
                entry_price = apply_slippage(row["Close"], direction, is_entry=True, slippage_pct=slippage_pct)
                stop_price = sig["stop_long"] if direction == 1 else sig["stop_short"]
                size = compute_position_size(equity, risk_pct, entry_price, stop_price)
                valid_stop = (direction == 1 and stop_price < entry_price) or (
                    direction == -1 and stop_price > entry_price
                )
                if size > 0 and valid_stop:
                    equity -= commission_pct * entry_price * size
                    pos = OpenPosition(direction, t, entry_price, stop_price, size)
                    target_price = sig["target_long"] if direction == 1 else sig["target_short"]

        if pos is not None:
            unrealized = (row["Close"] - pos.entry_price) * pos.direction * pos.size
            equity_curve.loc[t] = equity + unrealized
        else:
            equity_curve.loc[t] = equity

    trades_df = pd.DataFrame(trades, columns=TRADE_COLUMNS)
    return trades_df, equity_curve


def run_ma_voting_backtest(
    df: pd.DataFrame,
    signals: pd.DataFrame,
    initial_capital: float = INITIAL_CAPITAL,
    risk_pct: float = RISK_PER_TRADE,
    commission_pct: float = COMMISSION_PCT,
    slippage_pct: float = SLIPPAGE_PCT,
    n_pairs: int = len(MA_VOTING_PAIRS),
) -> tuple[pd.DataFrame, pd.Series]:
    """MA-oylama (Kart 1) icin islem simulasyonu calistirir.

    Giris kapanista; stop = ATR bazli (signals.ma_voting.generate_signals
    icinde onceden hesaplanmis stop_long/stop_short); pozisyon buyuklugu
    oy sayisina ORANTILI kucultulur (Kart 1 - "3 oy = tam pozisyon, 1 oy =
    1/3 pozisyon", bkz. signals/ma_voting.py). Cikis: stop (gun ici,
    Low/High bazli) VEYA oy sayisi 0'a/karsi isarete dondugunde
    (sinyal-bazli, kapanis bazli) - trailing YOK, Price Action gibi sabit
    hedef de YOK (acik-uclu, sinyal/stop'a kadar tutulur).

    Args:
        df: ["Open","High","Low","Close","Volume"] kolonlarina sahip fiyat
            verisi.
        signals: signals.ma_voting.generate_signals ciktisi (ayni index).
        initial_capital: Baslangic sermayesi.
        risk_pct: Islem basina risk orani (rho) - vote-carpanindan ONCEKI
            taban oran.
        commission_pct: Tek yonlu komisyon orani.
        slippage_pct: Fiil fiyatina uygulanan slipaj orani.
        n_pairs: Oy carpani icin payda (MA_VOTING_PAIRS uzunlugu).

    Returns:
        (trades, equity_curve): bkz. run_donchian_backtest.
    """
    equity = initial_capital
    equity_curve = pd.Series(index=df.index, dtype=float)
    trades: list[dict] = []
    pos: OpenPosition | None = None

    for t in df.index:
        row = df.loc[t]
        sig = signals.loc[t]

        if pos is not None and pos.entry_date != t:
            pos.update_excursion(row["High"], row["Low"])

        if pos is not None:
            exit_result = resolve_intrabar_exit(
                pos.direction, row["Open"], row["High"], row["Low"], pos.stop_price, target_price=None
            )
            if exit_result is None:
                exit_flag = sig["exit_long_signal"] if pos.direction == 1 else sig["exit_short_signal"]
                if bool(exit_flag):
                    exit_result = (float(row["Close"]), "signal")
            if exit_result is not None:
                raw_price, reason = exit_result
                trade, net_pnl = close_position(pos, t, raw_price, reason, commission_pct, slippage_pct)
                trades.append(trade)
                equity += net_pnl
                pos = None

        if pos is None:
            direction = 1 if bool(sig["entry_long"]) else (-1 if bool(sig["entry_short"]) else 0)
            if direction != 0:
                entry_price = apply_slippage(row["Close"], direction, is_entry=True, slippage_pct=slippage_pct)
                stop_price = sig["stop_long"] if direction == 1 else sig["stop_short"]
                valid_stop = (direction == 1 and stop_price < entry_price) or (
                    direction == -1 and stop_price > entry_price
                )
                if valid_stop:
                    size_multiplier = abs(int(sig["vote_count"])) / n_pairs
                    size = compute_position_size(equity, risk_pct, entry_price, stop_price) * size_multiplier
                    if size > 0:
                        equity -= commission_pct * entry_price * size
                        pos = OpenPosition(direction, t, entry_price, stop_price, size)

        if pos is not None:
            unrealized = (row["Close"] - pos.entry_price) * pos.direction * pos.size
            equity_curve.loc[t] = equity + unrealized
        else:
            equity_curve.loc[t] = equity

    trades_df = pd.DataFrame(trades, columns=TRADE_COLUMNS)
    return trades_df, equity_curve


def run_backtest(
    df: pd.DataFrame,
    signals: pd.DataFrame,
    strategy: Literal["donchian", "price_action", "ma_voting"],
    **kwargs,
) -> tuple[pd.DataFrame, pd.Series]:
    """Strateji adina gore uygun backtest fonksiyonuna yonlendirir.

    Args:
        df: OHLCV fiyat verisi.
        signals: Ilgili signals modulunun generate_signals ciktisi.
        strategy: "donchian", "price_action" veya "ma_voting".
        **kwargs: Ilgili run_*_backtest fonksiyonuna aktarilan ek parametreler.

    Returns:
        (trades, equity_curve).

    Raises:
        ValueError: Bilinmeyen strateji adi verilirse.
    """
    if strategy == "donchian":
        return run_donchian_backtest(df, signals, **kwargs)
    if strategy == "price_action":
        return run_price_action_backtest(df, signals, **kwargs)
    if strategy == "ma_voting":
        return run_ma_voting_backtest(df, signals, **kwargs)
    raise ValueError(f"Bilinmeyen strateji: {strategy!r}")
