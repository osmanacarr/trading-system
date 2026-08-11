"""Faktor kutuphanesi - Modul 1 (sistematik arastirma mimarisi).

Kaynak: quant.md/quant2.md (faktor/IC kavramlari) ve trade.md/trade2.md/
"trade 3.md" (order-flow kavramlari).

Iki katmanli arayuz:
    - `compute_<factor>(df, ...) -> pd.Series`: vektorize, df ile ayni
      index'e sahip TAM zaman serisi. Ic kullanim ve gecmis-veri IC
      hesaplamasi (validation/alpha_evaluation.py) icin - her tarihi tek
      tek yeniden hesaplamak yerine bir kez vektorize hesaplanir.
    - `<factor>_factor(df, date=None) -> float`: gorev tanimindaki
      `factor(df, date) -> float` arayuzu. Ic kullanim (research/
      factor_history.py) icin ince bir sarmalayicidir; date=None ise son
      bar donulur.

Lookahead-bias konvansiyonu: signals/donchian.py ile TUTARLI - bir
gostergenin GECMISE bakan kismi (ornegin rolling ortalama) `.shift(1)`
ile MEVCUT bari haric tutar. Standart osilatorler (RSI/MACD/Stokastik)
bu kuralin DISINDADIR: bunlar TA'nin standart tanimi geregi mevcut barin
kapanisini da dahil eder (donchian'daki gibi "mevcut kapanisi ONCEKI
kanalla karsilastirma" degil, "mevcut kapanisa kadarki seriyi ozetleme"
yapar) - bu bar kapandiginda okunmalari lookahead sayilmaz.

ATR: backtest.engine.compute_atr yeniden kullanilir, burada YENIDEN
YAZILMAZ (repo genelindeki "tek kaynak" prensibi).

ORDER-FLOW VEKILLERI HAKKINDA DURUSTCE NOT: bu depoda gercek L2/tick
(emir defteri, footprint) verisi YOK, sadece gunluk OHLCV var. Asagidaki
CVD/POC fonksiyonlari trade2.md/"trade 3.md" transkriptlerindeki
kavramlarin GUNLUK BARLARDAN turetilebilen YAKLASIKLAMALARIDIR - gercek
alis/satis emir hacmini yansitmazlar, sadece yon egilimini kaba bir
sekilde yakalamaya calisirlar. Footprint imbalance, order book/DOM gibi
gercekten tick/L2 verisi gerektiren kavramlar bu modulde YOKTUR (kaynak
transkriptlerde de bunlarin makul bir gunluk-bar vekili olmadigi tespit
edildi).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from backtest.engine import compute_atr
from config import (
    RESEARCH_ABSORPTION_RANGE_LOOKBACK,
    RESEARCH_ABSORPTION_VOLUME_LOOKBACK,
    RESEARCH_CVD_PIVOT_WINDOW,
    RESEARCH_EMA_PERIOD,
    RESEARCH_MACD_FAST,
    RESEARCH_MACD_SIGNAL,
    RESEARCH_MACD_SLOW,
    RESEARCH_POC_LOOKBACK,
    RESEARCH_POC_N_BINS,
    RESEARCH_RSI_PERIOD,
    RESEARCH_STOCH_D_PERIOD,
    RESEARCH_STOCH_K_PERIOD,
    RESEARCH_VALUE_AREA_PCT,
    RESEARCH_VOLUME_RATIO_LOOKBACK,
    RESEARCH_VOLUME_ZSCORE_LOOKBACK,
)

REQUIRED_COLUMNS: list[str] = ["Open", "High", "Low", "Close", "Volume"]


def _validate_columns(df: pd.DataFrame) -> None:
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"df icinde eksik kolon(lar): {missing}")


def _scalar_at(series: pd.Series, date: pd.Timestamp | str | None = None) -> float:
    """Bir Series'ten tek bir skaler deger cikarir (factor(df, date) arayuzu icin).

    date=None -> son (NaN olmayan) deger. date verilmis ama index'te yoksa
    ya da NaN ise -> nan.
    """
    if date is None:
        clean = series.dropna()
        if clean.empty:
            return float("nan")
        return float(clean.iloc[-1])
    if date not in series.index:
        return float("nan")
    value = series.loc[date]
    return float(value) if pd.notna(value) else float("nan")


# ---------------------------------------------------------------------------
# Standart teknik faktorler
# ---------------------------------------------------------------------------


def compute_ema(df: pd.DataFrame, period: int = RESEARCH_EMA_PERIOD) -> pd.Series:
    """Ustel hareketli ortalama (EMA) - kapanis fiyati uzerinden."""
    _validate_columns(df)
    return df["Close"].ewm(span=period, adjust=False).mean()


def ema_factor(df: pd.DataFrame, period: int = RESEARCH_EMA_PERIOD, date=None) -> float:
    return _scalar_at(compute_ema(df, period=period), date)


def compute_rsi(df: pd.DataFrame, period: int = RESEARCH_RSI_PERIOD) -> pd.Series:
    """Wilder'in RSI yontemi (backtest.engine.compute_atr ile ayni ewm-alpha=1/period yaklasimi)."""
    _validate_columns(df)
    delta = df["Close"].diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    # avg_loss==0 ve avg_gain>0 -> RSI=100 (sinirsiz yukselis, rs=inf durumu)
    rsi = rsi.where(~((avg_loss == 0.0) & (avg_gain > 0.0)), 100.0)
    return rsi


def rsi_factor(df: pd.DataFrame, period: int = RESEARCH_RSI_PERIOD, date=None) -> float:
    return _scalar_at(compute_rsi(df, period=period), date)


def compute_macd(
    df: pd.DataFrame,
    fast: int = RESEARCH_MACD_FAST,
    slow: int = RESEARCH_MACD_SLOW,
    signal: int = RESEARCH_MACD_SIGNAL,
) -> pd.DataFrame:
    """MACD hatti, sinyal hatti ve histogram. Kolonlar: macd_line, signal_line, histogram."""
    _validate_columns(df)
    ema_fast = df["Close"].ewm(span=fast, adjust=False).mean()
    ema_slow = df["Close"].ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return pd.DataFrame(
        {"macd_line": macd_line, "signal_line": signal_line, "histogram": histogram}
    )


def macd_factor(
    df: pd.DataFrame,
    fast: int = RESEARCH_MACD_FAST,
    slow: int = RESEARCH_MACD_SLOW,
    signal: int = RESEARCH_MACD_SIGNAL,
    date=None,
) -> float:
    """MACD'nin tek-skaler ozeti olarak histogram (macd_line - signal_line) donulur."""
    macd_df = compute_macd(df, fast=fast, slow=slow, signal=signal)
    return _scalar_at(macd_df["histogram"], date)


def compute_stochastic(
    df: pd.DataFrame,
    k_period: int = RESEARCH_STOCH_K_PERIOD,
    d_period: int = RESEARCH_STOCH_D_PERIOD,
) -> pd.DataFrame:
    """Stokastik osilator. Kolonlar: percent_k, percent_d."""
    _validate_columns(df)
    low_min = df["Low"].rolling(k_period).min()
    high_max = df["High"].rolling(k_period).max()
    denom = (high_max - low_min).replace(0.0, np.nan)
    percent_k = 100.0 * (df["Close"] - low_min) / denom
    percent_d = percent_k.rolling(d_period).mean()
    return pd.DataFrame({"percent_k": percent_k, "percent_d": percent_d})


def stochastic_factor(
    df: pd.DataFrame,
    k_period: int = RESEARCH_STOCH_K_PERIOD,
    d_period: int = RESEARCH_STOCH_D_PERIOD,
    date=None,
) -> float:
    """Stokastigin tek-skaler ozeti olarak %K donulur."""
    stoch_df = compute_stochastic(df, k_period=k_period, d_period=d_period)
    return _scalar_at(stoch_df["percent_k"], date)


def compute_volume_zscore(
    df: pd.DataFrame, lookback: int = RESEARCH_VOLUME_ZSCORE_LOOKBACK
) -> pd.Series:
    """Gunluk hacmin, ONCEKI `lookback` gunun hacim dagilimina gore Z-skoru (vektorize).

    gozcu.metrics.volume_zscore ile AYNI formul (yalniz-son-bar/canli tarama
    icin), burada TAM zaman serisi olarak (ic hesaplama + IC analizi icin)
    yeniden uygulanmistir - GOZCU'nun diger modullere bagimli olmama
    mimarisini bozmamak icin bilerek bagimsiz birer implementasyon.
    """
    _validate_columns(df)
    volume = df["Volume"]
    mean = volume.shift(1).rolling(lookback).mean()
    std = volume.shift(1).rolling(lookback).std()
    return (volume - mean) / std.replace(0.0, np.nan)


def volume_zscore_factor(
    df: pd.DataFrame, lookback: int = RESEARCH_VOLUME_ZSCORE_LOOKBACK, date=None
) -> float:
    return _scalar_at(compute_volume_zscore(df, lookback=lookback), date)


def compute_daily_volume_ratio(
    df: pd.DataFrame, lookback: int = RESEARCH_VOLUME_RATIO_LOOKBACK
) -> pd.Series:
    """Gunluk RVOL vekili: bugunku hacim / ONCEKI `lookback` gunun ortalama hacmi.

    NOT: gozcu.metrics.relative_volume gun-ici (intraday) gercek RVOL'u
    hesaplar (seans ilerleme oranina gore olceklenmis) - bu fonksiyon onun
    YERINE gecmez, sadece GUNLUK bar backtesti/IC analizi icin (gun-ici veri
    olmadan) kullanilabilecek kaba bir vekildir.
    """
    _validate_columns(df)
    volume = df["Volume"]
    avg_volume = volume.shift(1).rolling(lookback).mean()
    return volume / avg_volume.replace(0.0, np.nan)


def daily_volume_ratio_factor(
    df: pd.DataFrame, lookback: int = RESEARCH_VOLUME_RATIO_LOOKBACK, date=None
) -> float:
    return _scalar_at(compute_daily_volume_ratio(df, lookback=lookback), date)


# ---------------------------------------------------------------------------
# Order-flow vekilleri (gunluk OHLCV'den turetilmis yaklasiklamalar)
# ---------------------------------------------------------------------------


def compute_cvd_proxy(df: pd.DataFrame, method: str = "graded") -> pd.Series:
    """Kumulatif Hacim Delta (CVD) VEKILI - trade2.md/"trade 3.md".

    Gercek CVD, tick-bazli alis/satis emir hacminin farkidir (footprint
    veri gerektirir). Bu depoda sadece gunluk OHLCV oldugu icin, her barin
    yonu/hacmi uzerinden bir yaklasiklama kullanilir:
        - method="sign": sign(Close-Open) * Volume (kaba, ikili yon)
        - method="graded": ((Close-Open)/(High-Low)) * Volume (Chaikin-tarzi,
          kapanisin bar araligindaki KONUMUNA gore kademeli agirlik - High==Low
          oldugu barlarda sign() yontemine duser)

    Sonuc, bar-bazinda "signed volume" degerlerinin kumulatif toplamidir.
    """
    _validate_columns(df)
    open_, high, low, close, volume = (
        df["Open"],
        df["High"],
        df["Low"],
        df["Close"],
        df["Volume"],
    )
    if method == "sign":
        signed_volume = np.sign(close - open_) * volume
    elif method == "graded":
        bar_range = (high - low).replace(0.0, np.nan)
        position = ((close - open_) / bar_range).clip(-1.0, 1.0)
        signed_volume = position * volume
        signed_volume = signed_volume.fillna(np.sign(close - open_) * volume)
    else:
        raise ValueError(f"bilinmeyen method: {method!r} (sign|graded)")
    return signed_volume.cumsum()


def cvd_proxy_factor(df: pd.DataFrame, method: str = "graded", date=None) -> float:
    return _scalar_at(compute_cvd_proxy(df, method=method), date)


def _confirmed_pivots(series: pd.Series, window: int, kind: str) -> pd.Series:
    """Trailing-onayli pivot (yerel tepe/dip) tespiti - LOOKAHEAD YOK.

    Bir bar, kendisinden `window` bar SONRAKI verilerle karsilastirilarak
    pivot olarak "onaylanir" (standart swing-tespit yontemi); bu yuzden
    donen Series, pivot ANINA degil pivotun ONAYLANDIGI (yani bilgi olarak
    mevcut oldugu) bara denk gelecek sekilde `window` kadar ILERI kaydirilir
    - boylece row t'deki deger yalnizca t anina kadar bilinen bilgiyi yansitir.

    kind="low" -> yerel dip, kind="high" -> yerel tepe.
    """
    centered_window = 2 * window + 1
    if kind == "low":
        extreme = series.rolling(centered_window, center=True).min()
    elif kind == "high":
        extreme = series.rolling(centered_window, center=True).max()
    else:
        raise ValueError("kind 'low' ya da 'high' olmali")
    is_pivot = series == extreme
    is_pivot = is_pivot.fillna(False)
    # pivot bilgisi ancak `window` bar sonra "bilinir" hale gelir -> ileri kaydir
    return is_pivot.shift(window).fillna(False)


def compute_cvd_divergence(
    df: pd.DataFrame,
    pivot_window: int = RESEARCH_CVD_PIVOT_WINDOW,
    cvd_method: str = "graded",
) -> pd.Series:
    """Fiyat/CVD-proxy diverjansi - trade2.md/"trade 3.md" mantigi.

    Ardisik iki onayli fiyat pivotu (dip-dip ya da tepe-tepe) arasinda:
        - Fiyat yeni bir DIP yapiyor AMA CVD-proxy'nin dip'i daha YUKSEKSE
          -> bullish diverjans (+1), satis bitkinligi.
        - Fiyat yeni bir TEPE yapiyor AMA CVD-proxy'nin tepesi daha
          DUSUKSE -> bearish diverjans (-1), alis bitkinligi.

    Kaynak transkriptte sayisal esik/lookback verilmiyor - pivot_window
    kendi secimimizdir (varsayilan config.RESEARCH_CVD_PIVOT_WINDOW).

    Donus: df ile ayni index'e sahip, çoğu deger 0 olan seyrek (sparse) bir
    Series (+1/-1 yalnizca diverjansin ONAYLANDIGI barda gorunur).
    """
    _validate_columns(df)
    cvd = compute_cvd_proxy(df, method=cvd_method)
    result = pd.Series(0, index=df.index, dtype=int)

    is_pivot_low = _confirmed_pivots(df["Low"], pivot_window, "low")
    is_pivot_high = _confirmed_pivots(df["High"], pivot_window, "high")

    low_pivot_positions = np.flatnonzero(is_pivot_low.to_numpy())
    high_pivot_positions = np.flatnonzero(is_pivot_high.to_numpy())

    close = df["Close"]
    for prev_pos, curr_pos in zip(low_pivot_positions[:-1], low_pivot_positions[1:]):
        price_lower_low = close.iloc[curr_pos] < close.iloc[prev_pos]
        cvd_higher_low = cvd.iloc[curr_pos] > cvd.iloc[prev_pos]
        if price_lower_low and cvd_higher_low:
            result.iloc[curr_pos] = 1

    for prev_pos, curr_pos in zip(high_pivot_positions[:-1], high_pivot_positions[1:]):
        price_higher_high = close.iloc[curr_pos] > close.iloc[prev_pos]
        cvd_lower_high = cvd.iloc[curr_pos] < cvd.iloc[prev_pos]
        if price_higher_high and cvd_lower_high:
            result.iloc[curr_pos] = -1

    return result


def cvd_divergence_factor(
    df: pd.DataFrame, pivot_window: int = RESEARCH_CVD_PIVOT_WINDOW, date=None
) -> float:
    return _scalar_at(compute_cvd_divergence(df, pivot_window=pivot_window).astype(float), date)


def _rolling_poc_and_value_area(
    df: pd.DataFrame,
    lookback: int,
    n_bins: int,
    value_area_pct: float,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """POC fiyati + value-area alt/ust sinirlarini trailing pencerede hesaplar (iç yardimci)."""
    high, low, volume = df["High"].to_numpy(), df["Low"].to_numpy(), df["Volume"].to_numpy()
    n = len(df)
    poc = np.full(n, np.nan)
    va_low = np.full(n, np.nan)
    va_high = np.full(n, np.nan)

    for i in range(lookback, n):
        window_slice = slice(i - lookback, i)  # mevcut bar HARIC (shift(1) konvansiyonu)
        w_high, w_low, w_vol = high[window_slice], low[window_slice], volume[window_slice]

        price_min = w_low.min()
        price_max = w_high.max()
        if not np.isfinite(price_min) or not np.isfinite(price_max) or price_max <= price_min:
            continue

        bin_edges = np.linspace(price_min, price_max, n_bins + 1)
        bin_volumes = np.zeros(n_bins)

        lo_idx = np.clip(np.searchsorted(bin_edges, w_low, side="right") - 1, 0, n_bins - 1)
        hi_idx = np.clip(np.searchsorted(bin_edges, w_high, side="right") - 1, 0, n_bins - 1)

        for lo, hi, vol in zip(lo_idx, hi_idx, w_vol):
            if vol <= 0:
                continue
            span = hi - lo + 1
            bin_volumes[lo : hi + 1] += vol / span

        total_volume = bin_volumes.sum()
        if total_volume <= 0:
            continue

        # argsort + [::-1] hacme gore azalan sira verir; POC = bu siranin ILK
        # elemani (en yuksek hacimli bin) - value-area'nin de POC'tan disa
        # dogru genisletilmesiyle TUTARLI tek bir tie-break kuralini garantiler
        # (argmax kullanilsaydi esit-hacim durumunda farkli bir bin secilebilirdi).
        order = np.argsort(bin_volumes)[::-1]
        poc_bin = int(order[0])
        poc[i] = (bin_edges[poc_bin] + bin_edges[poc_bin + 1]) / 2.0

        # Value area: POC'tan disa dogru genisleyerek hedef hacim oranina ulas
        target = total_volume * value_area_pct
        cumulative = 0.0
        included = []
        for b in order:
            cumulative += bin_volumes[b]
            included.append(b)
            if cumulative >= target:
                break
        va_low[i] = bin_edges[min(included)]
        va_high[i] = bin_edges[max(included) + 1]

    index = df.index
    return (
        pd.Series(poc, index=index),
        pd.Series(va_low, index=index),
        pd.Series(va_high, index=index),
    )


def compute_volume_profile_poc(
    df: pd.DataFrame,
    lookback: int = RESEARCH_POC_LOOKBACK,
    n_bins: int = RESEARCH_POC_N_BINS,
) -> pd.Series:
    """Rolling Volume Profile POC (Point of Control) fiyat seviyesi - trade.md/trade2.md.

    NOT (vekil/proxy): gercek volume profile gun-ici (tick) hacim
    dagilimini kullanir; burada GUNLUK barlarin High-Low araligina, o
    gunun hacmi UNIFORM dagitilarak yaklasiklanir (gercek intrabar dagilim
    bilinmiyor).

    Her bar t icin, MEVCUT bar HARIC trailing `lookback` barlik pencere
    kullanilir (shift(1) konvansiyonu) - boylece POC[t], Close[t] ile
    karsilastirildiginda lookahead olusturmaz.
    """
    _validate_columns(df)
    poc, _, _ = _rolling_poc_and_value_area(df, lookback, n_bins, RESEARCH_VALUE_AREA_PCT)
    return poc


def compute_value_area(
    df: pd.DataFrame,
    lookback: int = RESEARCH_POC_LOOKBACK,
    n_bins: int = RESEARCH_POC_N_BINS,
    value_area_pct: float = RESEARCH_VALUE_AREA_PCT,
) -> pd.DataFrame:
    """Rolling Value Area alt/ust sinirlari (POC etrafinda hacmin %value_area_pct'ini iceren bolge)."""
    _validate_columns(df)
    poc, va_low, va_high = _rolling_poc_and_value_area(df, lookback, n_bins, value_area_pct)
    return pd.DataFrame({"poc": poc, "value_area_low": va_low, "value_area_high": va_high})


def poc_factor(
    df: pd.DataFrame,
    lookback: int = RESEARCH_POC_LOOKBACK,
    n_bins: int = RESEARCH_POC_N_BINS,
    date=None,
) -> float:
    return _scalar_at(compute_volume_profile_poc(df, lookback=lookback, n_bins=n_bins), date)


def compute_distance_from_poc(
    df: pd.DataFrame,
    lookback: int = RESEARCH_POC_LOOKBACK,
    n_bins: int = RESEARCH_POC_N_BINS,
    atr_period: int | None = None,
) -> pd.Series:
    """Guncel fiyatin POC'a uzakligi, ATR birimiyle normalize edilmis (fiyat - POC) / ATR.

    ATR icin backtest.engine.compute_atr yeniden kullanilir (varsayilan
    period ile - atr_period=None ise compute_atr'nin kendi varsayilani).
    """
    _validate_columns(df)
    poc = compute_volume_profile_poc(df, lookback=lookback, n_bins=n_bins)
    atr = compute_atr(df) if atr_period is None else compute_atr(df, period=atr_period)
    return (df["Close"] - poc) / atr.replace(0.0, np.nan)


def distance_from_poc_factor(
    df: pd.DataFrame,
    lookback: int = RESEARCH_POC_LOOKBACK,
    n_bins: int = RESEARCH_POC_N_BINS,
    date=None,
) -> float:
    return _scalar_at(compute_distance_from_poc(df, lookback=lookback, n_bins=n_bins), date)


def compute_absorption_heuristic(
    df: pd.DataFrame,
    range_lookback: int = RESEARCH_ABSORPTION_RANGE_LOOKBACK,
    volume_lookback: int = RESEARCH_ABSORPTION_VOLUME_LOOKBACK,
) -> pd.Series:
    """"Absorption" SEZGISELI (SPEKULATIF) - trade2.md.

    Kaynaktaki tanim: fiyat bir bolgeye carpip duruyorsa ve buyuk pasif
    likidite agresif emirleri "yutuyorsa" (absorbe ediyorsa) bu absorption'dir.
    Gercek absorption tespiti tick/order-book verisi gerektirir - bu
    fonksiyon SADECE kaba bir yaklasiklamadir (dogrulanmis bir sinyal
    DEGILDIR): yuksek hacim + dar bar araligi (normalize edilmis) -> yuksek
    skor. Yuksek skor = olasi "stall" (fiyatin hacme ragmen ilerleyememesi).
    """
    _validate_columns(df)
    high, low, volume = df["High"], df["Low"], df["Volume"]
    bar_range = high - low
    avg_range = bar_range.shift(1).rolling(range_lookback).mean()
    avg_volume = volume.shift(1).rolling(volume_lookback).mean()
    normalized_range = bar_range / avg_range.replace(0.0, np.nan)
    normalized_volume = volume / avg_volume.replace(0.0, np.nan)
    return normalized_volume - normalized_range


def absorption_factor(
    df: pd.DataFrame,
    range_lookback: int = RESEARCH_ABSORPTION_RANGE_LOOKBACK,
    volume_lookback: int = RESEARCH_ABSORPTION_VOLUME_LOOKBACK,
    date=None,
) -> float:
    return _scalar_at(
        compute_absorption_heuristic(
            df, range_lookback=range_lookback, volume_lookback=volume_lookback
        ),
        date,
    )


# ---------------------------------------------------------------------------
# Kayit: butun faktorlerin toplu hesaplanmasi (research/factor_history.py icin)
# ---------------------------------------------------------------------------

# {factor_adi: factor(df, date=None) -> float} - factor_history.py bu sozlugu
# gezerek her tarama sonunda TUM faktor degerlerini biriktirir.
FACTOR_REGISTRY: dict[str, callable] = {
    "ema": ema_factor,
    "rsi": rsi_factor,
    "macd_histogram": macd_factor,
    "stochastic_k": stochastic_factor,
    "volume_zscore": volume_zscore_factor,
    "daily_volume_ratio": daily_volume_ratio_factor,
    "cvd_proxy": cvd_proxy_factor,
    "cvd_divergence": cvd_divergence_factor,
    "poc": poc_factor,
    "distance_from_poc": distance_from_poc_factor,
    "absorption": absorption_factor,
}
