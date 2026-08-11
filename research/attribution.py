"""Performans attribution: common (piyasa) vs specific (secim becerisi) - Modul 7.

Her kapanmis islemin getirisi, referans endekse (GOZCU_BIST_REFERENCE_TICKER /
GOZCU_NASDAQ_REFERENCE_TICKER - config.py'den, YENIDEN TANIMLANMAZ) karsi
TEK-FAKTOR OLS regresyonuyla ikiye ayrilir:
    - common_return  (beta * referans getirisi): piyasa/beta'dan gelen kisim
    - specific_return (residual): gercek SECIM becerisinden gelen kisim

Bu, kurumsal performans attribution'daki standart tek-faktor (piyasa
modeli) yaklasimidir - coklu-faktor (sektor, stil vb.) versiyonlar bu
depoda YOK (referans veri/karmasiklik kapsamin disinda).

Fiyat verisi: data/fetch.py::fetch_ohlcv ile cekilir (mevcut fetch
katmani, yeniden yazilmaz).
"""

from __future__ import annotations

import pandas as pd
from scipy import stats


def compute_daily_returns(price_df: pd.DataFrame, start_date, end_date) -> pd.Series:
    """[start_date, end_date] (dahil) araligindaki basit gunluk getiri serisi (Close.pct_change())."""
    window = price_df.loc[start_date:end_date, "Close"]
    return window.pct_change().dropna()


def single_factor_attribution(position_returns: pd.Series, reference_returns: pd.Series) -> dict:
    """position_returns ~ beta*reference_returns + alpha + residual regresyonuyla common/specific ayrimi yapar.

    Args:
        position_returns: Pozisyonun (YON-AYARLANMIS - bkz. attribute_trade)
            gunluk getiri serisi.
        reference_returns: Referans endeks/ETF'in gunluk getiri serisi.

    Returns:
        {"beta","alpha","r_squared","common_return","specific_return","n_days"}.
        Ortak tarih sayisi < 2 ya da referans getirisinin varyansi 0 ise
        (regresyon tanimsiz) TUM getiri "specific" sayilir (piyasa hareketi
        izole EDILEMEDI, bu bir varsayilan/fallback'tir - "beceri" olarak
        yanlis yorumlanmamalidir, bkz. dashboard'da n_days uyarisi).
    """
    common_dates = position_returns.index.intersection(reference_returns.index)
    pos = position_returns.loc[common_dates].dropna()
    ref = reference_returns.loc[common_dates].dropna()
    common_dates = pos.index.intersection(ref.index)
    pos, ref = pos.loc[common_dates], ref.loc[common_dates]

    total_return = float(pos.sum()) if len(pos) else 0.0

    if len(common_dates) < 2 or ref.std() == 0:
        return {
            "beta": 0.0,
            "alpha": 0.0,
            "r_squared": 0.0,
            "common_return": 0.0,
            "specific_return": total_return,
            "n_days": len(common_dates),
        }

    slope, intercept, r_value, _p_value, _std_err = stats.linregress(ref.to_numpy(), pos.to_numpy())
    common_return = float(slope * ref.sum())
    specific_return = total_return - common_return

    return {
        "beta": float(slope),
        "alpha": float(intercept),
        "r_squared": float(r_value**2),
        "common_return": common_return,
        "specific_return": specific_return,
        "n_days": len(common_dates),
    }


def attribute_trade(
    price_df: pd.DataFrame,
    reference_df: pd.DataFrame,
    entry_date,
    exit_date,
    direction: int,
) -> dict:
    """Tek bir kapanmis islem icin common/specific getiri ayrimini hesaplar.

    Args:
        price_df: Pozisyonun sembolune ait OHLCV (["Close"] yeterli).
        reference_df: Referans endeks/ETF OHLCV (["Close"] yeterli).
        entry_date, exit_date: Islemin giris/cikis tarihleri.
        direction: +1 (long) / -1 (short). Pozisyonun gunluk getirisi buna
            gore ISARETLENIR (short pozisyon fiyat dusunce kazanir) -
            boylece regresyondaki beta, POZISYONUN (altta yatan sembolun
            DEGIL) piyasaya duyarliligini yansitir.

    Returns:
        single_factor_attribution() ciktisi.
    """
    position_returns = direction * compute_daily_returns(price_df, entry_date, exit_date)
    reference_returns = compute_daily_returns(reference_df, entry_date, exit_date)
    return single_factor_attribution(position_returns, reference_returns)


def attribute_trades(
    trades: pd.DataFrame,
    price_df: pd.DataFrame,
    reference_df: pd.DataFrame,
) -> pd.DataFrame:
    """Bir trade log'una (backtest.engine.TRADE_COLUMNS semasi) common_return/specific_return kolonlari ekler.

    TUM satirlar AYNI sembole (price_df) ait olmalidir (backtest.engine
    ciktisi zaten tek-sembol bazlidir). Coklu-sembol trade log'lari (orn.
    paper_trading) icin sembol basina ayri ayri cagirip pd.concat ile
    birlestirin.

    Args:
        trades: "entry_date","exit_date","direction" kolonlarini iceren
            islem DataFrame'i.
        price_df: Pozisyonlarin sembolune ait OHLCV.
        reference_df: Referans endeks/ETF OHLCV.

    Returns:
        trades'in bir kopyasi + "common_return","specific_return" kolonlari.
    """
    if trades.empty:
        result = trades.copy()
        result["common_return"] = pd.Series(dtype=float)
        result["specific_return"] = pd.Series(dtype=float)
        return result

    records = []
    for _, trade in trades.iterrows():
        attribution = attribute_trade(
            price_df, reference_df, trade["entry_date"], trade["exit_date"], int(trade["direction"])
        )
        records.append(
            {"common_return": attribution["common_return"], "specific_return": attribution["specific_return"]}
        )
    attribution_df = pd.DataFrame(records, index=trades.index)
    return pd.concat([trades, attribution_df], axis=1)


def summarize_attribution(trades: pd.DataFrame) -> dict:
    """"Ne kadari gercek beceri (specific), ne kadari piyasa (common)" ozetini hesaplar.

    Args:
        trades: attribute_trades() ciktisi ("common_return","specific_return"
            kolonlarini icermeli).

    Returns:
        {"total_common_return","total_specific_return","pct_specific","n_trades"}.
        pct_specific = specific / (common+specific); toplam getiri 0 ise 0.0.
        n_trades: dashboard'un "N islem uzerinden hesaplandi" gibi somut bir
            ilerleme mesaji gosterebilmesi icin islem sayisi.
    """
    if trades.empty or "common_return" not in trades.columns or "specific_return" not in trades.columns:
        return {"total_common_return": 0.0, "total_specific_return": 0.0, "pct_specific": 0.0, "n_trades": 0}

    total_common = float(trades["common_return"].sum())
    total_specific = float(trades["specific_return"].sum())
    total = total_common + total_specific
    pct_specific = (total_specific / total) if total != 0 else 0.0

    return {
        "total_common_return": total_common,
        "total_specific_return": total_specific,
        "pct_specific": pct_specific,
        "n_trades": int(len(trades)),
    }


def pair_entry_exit_events(events: pd.DataFrame) -> pd.DataFrame:
    """paper_trading event-log'undaki (entry/exit) satirlari, sembol basina KRONOLOJIK eslestirerek (symbol, entry_date, exit_date, direction) ciftlerine donusturur.

    paper_trading/logger.py'nin TRADE_LOG_COLUMNS semasi olay-bazlidir
    (her satir bir "entry" ya da "exit" olayi) - attribute_trades() ise
    entry_date/exit_date CIFTI ister (backtest.engine.TRADE_COLUMNS gibi).
    Bu fonksiyon aradaki koprudur.

    paper_trading/state.py'nin "sembol basina EN FAZLA 1 acik pozisyon"
    kurali sayesinde, bir sembolun olaylari KRONOLOJIK sirada her zaman
    entry->exit->entry->exit... seklinde alternatif gelir - bu yuzden basit
    sirali eslestirme yeterlidir.

    Args:
        events: paper_trading.logger.PaperTradingLogger.read_trades()
            ciktisi ("event_type","date","symbol","direction" kolonlarini
            icermeli).

    Returns:
        ["symbol","entry_date","exit_date","direction"] kolonlarina sahip
        DataFrame - SADECE tamamlanmis (hem entry hem exit'i olan) islemler
        icerir; henuz kapanmamis (acik) son entry ATLANIR.
    """
    columns = ["symbol", "entry_date", "exit_date", "direction"]
    if events.empty:
        return pd.DataFrame(columns=columns)

    pairs: list[dict] = []
    for symbol, group in events.groupby("symbol"):
        group = group.sort_values("date")
        pending_entry = None
        for _, row in group.iterrows():
            if row["event_type"] == "entry":
                pending_entry = row
            elif row["event_type"] == "exit" and pending_entry is not None:
                pairs.append(
                    {
                        "symbol": symbol,
                        "entry_date": pd.Timestamp(pending_entry["date"]),
                        "exit_date": pd.Timestamp(row["date"]),
                        "direction": int(row["direction"]),
                    }
                )
                pending_entry = None

    return pd.DataFrame(pairs, columns=columns)
