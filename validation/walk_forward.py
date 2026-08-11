"""Rolling ve anchored walk-forward split'leri - Modul 3 (sistematik arastirma mimarisi).

Kaynak: quant2.md (R `quantstrat` konusmasi). Birebir alinti (kod
yorumlarinda da korunmali cunku bu bir tasarim kurali, sadece bir aciklama
degil):

    "anchored walk forward makes a lot of sense for risk metrics and very
    little sense for most indicators - most indicators have a built-in
    look-back period so you end up with a rolling walk forward window
    anyway."

Yani: RISK METRIKLERI (orn. portfolio-level drawdown/VaR gibi olcumler,
tum gecmisin birikimli davranisini yansitmasi gerekenler) icin ANCHORED
daha mantiklidir; COGU GOSTERGE/FAKTOR (kendi ic lookback penceresi olan,
"rejim degisince eski veri artik alakasiz" mantigiyla calisan seyler) icin
ROLLING daha mantiklidir. Bu modul ikisini de birinci sinif secenek olarak
sunar; hangisinin kullanilacagina cagiran kod (validation/alpha_evaluation.py)
karar verir, bu modul bir tercih dayatmaz.

NOT (mevcut kod ile iliski): validation/significance.py::rolling_walk_forward_splits
ismine ragmen ANCHORED (genisleyen pencereli) davranir - o fonksiyona
DOKUNULMADI (backtest/run.py onu kullaniyor), ama ismi yaniltici oldugu
icin burada DOGRU isimlendirilmis rolling_splits (sabit pencere) ve
anchored_splits (genisleyen pencere, significance.py'dekiyle ayni mantik
ama bagimsiz/parametrize edilebilir bir implementasyon) saglanir.

UYARI (aynı kaynaktan, birebir): walk-forward analizini kural eklendikten
SONRA tekrar tekrar calistirmak overfitting'e davetiye cikarir - "you
don't want to do it too often... if you go back and redo walk-forward
analysis after you've added rules, you're almost certainly overfitting."
Bu modul bunu ZORLAMAZ (calistirma sikligini izlemek cagiran kodun/
kullanicinin sorumlulugundadir), sadece bu docstring'de hatirlatir.
"""

from __future__ import annotations

import pandas as pd


def rolling_splits(
    df: pd.DataFrame,
    train_window: int,
    test_window: int,
    step: int | None = None,
) -> list[tuple[pd.DataFrame, pd.DataFrame]]:
    """SABIT boyutlu train penceresiyle ilerleyen (rolling) walk-forward kesimleri.

    Her adimda train penceresi AYNI boyutta kalir, sadece ileri kayar (bir
    onceki adimin train+test'inin bir kismini "unutur") - cogu gosterge/
    faktor icin daha mantikli (bkz. modul docstring'i).

    Args:
        df: Kronolojik sirali DataFrame.
        train_window: Sabit train penceresi uzunlugu (bar sayisi).
        test_window: Her adimdaki test penceresi uzunlugu (bar sayisi).
        step: Her adimda ileri kaydirma miktari (varsayilan: test_window,
            yani ardisik/ortusmeyen test pencereleri).

    Returns:
        (train_df, test_df) ciftleri listesi (kronolojik sirayla). df,
        en az bir tam (train+test) penceresi icin yetersizse bos liste doner.

    Raises:
        ValueError: train_window/test_window/step <= 0 ise.
    """
    if train_window <= 0 or test_window <= 0:
        raise ValueError("train_window ve test_window > 0 olmali")
    if step is None:
        step = test_window
    if step <= 0:
        raise ValueError("step > 0 olmali")

    n = len(df)
    splits: list[tuple[pd.DataFrame, pd.DataFrame]] = []
    train_start = 0
    while True:
        train_end = train_start + train_window
        test_end = train_end + test_window
        if test_end > n:
            break
        train_df = df.iloc[train_start:train_end].copy()
        test_df = df.iloc[train_end:test_end].copy()
        splits.append((train_df, test_df))
        train_start += step

    return splits


def anchored_splits(
    df: pd.DataFrame,
    min_train_window: int,
    test_window: int,
    step: int | None = None,
) -> list[tuple[pd.DataFrame, pd.DataFrame]]:
    """Baslangictan itibaren BUYUYEN (anchored/expanding) train penceresiyle walk-forward kesimleri.

    Train penceresi her zaman df'in BASINDAN baslar ve her adimda genisler
    (bir onceki test penceresini de icine alir) - risk metrikleri icin
    daha mantikli (bkz. modul docstring'i), cunku risk olculeri genelde
    TUM birikmis gecmisi yansitmasi gereken seylerdir.

    Args:
        df: Kronolojik sirali DataFrame.
        min_train_window: Ilk (en kucuk) train penceresinin uzunlugu (bar sayisi).
        test_window: Her adimdaki test penceresi uzunlugu (bar sayisi).
        step: Her adimda train sonunun ne kadar ileri kaydigi (varsayilan:
            test_window, yani ardisik/ortusmeyen test pencereleri).

    Returns:
        (train_df, test_df) ciftleri listesi (kronolojik sirayla, train
        her adimda buyur). df yetersizse bos liste doner.

    Raises:
        ValueError: min_train_window/test_window/step <= 0 ise.
    """
    if min_train_window <= 0 or test_window <= 0:
        raise ValueError("min_train_window ve test_window > 0 olmali")
    if step is None:
        step = test_window
    if step <= 0:
        raise ValueError("step > 0 olmali")

    n = len(df)
    splits: list[tuple[pd.DataFrame, pd.DataFrame]] = []
    train_end = min_train_window
    while True:
        test_end = train_end + test_window
        if test_end > n:
            break
        train_df = df.iloc[:train_end].copy()
        test_df = df.iloc[train_end:test_end].copy()
        splits.append((train_df, test_df))
        train_end += step

    return splits


def compare_rolling_vs_anchored(
    df: pd.DataFrame,
    metric_fn,
    train_window: int,
    test_window: int,
    step: int | None = None,
) -> dict:
    """Ayni df/pencere parametreleriyle rolling ve anchored sonuclarini yan yana raporlar.

    Args:
        df: Kronolojik sirali DataFrame.
        metric_fn: (train_df, test_df) -> float alan, cagiran kodun tanimladigi
            bir degerlendirme fonksiyonu (orn. bir IC ya da expectancy hesabi).
        train_window: rolling icin sabit / anchored icin min_train_window.
        test_window: Her iki mod icin de test penceresi uzunlugu.
        step: Her iki mod icin de ileri kaydirma miktari.

    Returns:
        {"rolling": [float, ...], "anchored": [float, ...],
         "rolling_mean": float|None, "anchored_mean": float|None}
    """
    rolling_results = [
        metric_fn(train_df, test_df)
        for train_df, test_df in rolling_splits(df, train_window, test_window, step=step)
    ]
    anchored_results = [
        metric_fn(train_df, test_df)
        for train_df, test_df in anchored_splits(df, train_window, test_window, step=step)
    ]
    return {
        "rolling": rolling_results,
        "anchored": anchored_results,
        "rolling_mean": (sum(rolling_results) / len(rolling_results)) if rolling_results else None,
        "anchored_mean": (sum(anchored_results) / len(anchored_results)) if anchored_results else None,
    }
