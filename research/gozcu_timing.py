"""research/gozcu_timing.py - GOZCU dikkat listesinin ZAMANLAMASINI olcer.

Kaynak: kullanici sikayeti (2026-08-12) - "GOZCU hareketleri genelde
OLDUKTAN SONRA gosteriyor". Bu modul o sikayeti VERIYLE sinamak icin
yazildi (once olc, sonra cozum onerme ilkesi - bkz. research/regime.py'nin
ayni felsefesi).

SORU: bir sembol ilk kez dikkat listesinin ilk-20'sine girdigi andaki
gunluk_degisim% ile, o gun icin SON GOZLEMLENEN gunluk_degisim% arasinda
ne kadar fark var? Fark KUCUKSE (ya da SIFIRSA), sistem hareketin
BASLANGICINI degil SONUNU/PLATOSUNU yakaliyor demektir.

VERI KAYNAGI: gozcu/data/snapshot.json'in GIT GECMISI. snapshot her
tarama sonrasi otomatik commit'lendigi icin (bkz. .github/workflows/
gozcu_scan.yml), git log FIILEN bir zaman serisi olusturur - YAPAY bir
veri degil, her commit gercek bir tarama anini temsil eder.

BILINEN SINIRLAMA (bu modul ilk yazildiginda, 2026-08-12): veri yalnizca
~1.5 gun, ~21 BIST-acik-saatlerinde tarama iceriyor - COK KUCUK bir
orneklem. main() bu durumda ACIKCA bir uyari basar. Birkac hafta
biriktikten sonra `python -m research.gozcu_timing` tekrar calistirilmali.

AYRICA NOT: .github/workflows/gozcu_scan.yml cron'u "*/5 6-21 * * 1-5"
(5 dakikada bir) ama GERCEKLESEN commit araligi GOZLEMLENEN veride
~1 SAATE yakin (GitHub Actions'in yuksek frekansli zamanlanmis
workflow'lari guvenilir sekilde tetiklememesi bilinen bir sinirlamadir).
Bu, "ilk-gorulme" zamanlamasinin KENDISININ neden gec kaldigini kismen
aciklar - metrik formulunden BAGIMSIZ, yapisal bir kisit.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Callable

import pandas as pd

from config import PROJECT_ROOT

SNAPSHOT_RELATIVE_PATH = "gozcu/data/snapshot.json"

SnapshotLoader = Callable[[str, Path], dict]


def list_snapshot_commits(repo_root: Path = PROJECT_ROOT) -> list[tuple[str, str]]:
    """gozcu/data/snapshot.json'a dokunan TUM commit'leri (hash, ISO-8601 tarih) olarak dondurur.

    Returns:
        (commit_hash, timestamp) ciftleri listesi, en YENIDEN en ESKIYE.
        git gecmisi yoksa (orn. repo henuz push edilmemis) bos liste doner.
    """
    try:
        raw = subprocess.run(
            ["git", "log", "--follow", "--format=%H|%aI", "--", SNAPSHOT_RELATIVE_PATH],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    except subprocess.CalledProcessError:
        return []

    commits = []
    for line in raw.strip().splitlines():
        if not line:
            continue
        commit_hash, ts = line.split("|", 1)
        commits.append((commit_hash, ts))
    return commits


def load_snapshot_at_commit(commit_hash: str, repo_root: Path = PROJECT_ROOT) -> dict:
    """Belirli bir commit'teki snapshot.json icerigini yukler (git show ile, checkout YAPMADAN)."""
    raw = subprocess.run(
        ["git", "show", f"{commit_hash}:{SNAPSHOT_RELATIVE_PATH}"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=True,
        encoding="utf-8",
    ).stdout
    return json.loads(raw)


def extract_attention_records(snapshot: dict, timestamp: str, market: str = "bist") -> list[dict]:
    """Bir snapshot'tan (tek bir tarama ani) dikkat listesi kayitlarini cikarir.

    Piyasa KAPALIYSA (market_open=False) bos liste doner - o anki veri
    gercek bir tarama degil, onceki acik seanstan KALAN veridir (bkz.
    gozcu/scanner.py mimari karari) ve "ilk gorulme" analizini bozar.

    Args:
        snapshot: load_snapshot_at_commit (veya gozcu/data/snapshot.json'un
            dogrudan yuklenmis hali) ciktisi.
        timestamp: Bu snapshot'in olusturuldugu an (ISO-8601 string).
        market: "bist" veya "nasdaq".

    Returns:
        Her biri {"ts","symbol","rank","daily_change_pct","score"}
        anahtarlarina sahip kayit listesi (attention_list sirasi = rank).
    """
    market_data = snapshot.get("markets", {}).get(market, {})
    if not market_data.get("market_open", False):
        return []
    records = []
    for rank, entry in enumerate(market_data.get("attention_list", []), start=1):
        records.append(
            {
                "ts": timestamp,
                "symbol": entry.get("symbol"),
                "rank": rank,
                "daily_change_pct": entry.get("daily_change_pct"),
                "score": entry.get("score"),
            }
        )
    return records


def build_attention_history(
    repo_root: Path = PROJECT_ROOT,
    market: str = "bist",
    commits: list[tuple[str, str]] | None = None,
    snapshot_loader: SnapshotLoader = load_snapshot_at_commit,
) -> pd.DataFrame:
    """git gecmisindeki TUM snapshot'lari tarayip dikkat-listesi kayitlarinin TAM zaman serisini olusturur.

    Args:
        repo_root: Git deposunun koku.
        market: "bist" veya "nasdaq".
        commits: Opsiyonel - verilmezse list_snapshot_commits ile gercek
            git gecmisinden cekilir (testlerde sentetik bir liste enjekte
            edilebilir).
        snapshot_loader: Opsiyonel - verilmezse gercek git'ten okur
            (testlerde sahte bir yukleyici enjekte edilebilir).

    Returns:
        ["ts","symbol","rank","daily_change_pct","score"] kolonlarina
        sahip, kronolojik sirali DataFrame (piyasa KAPALI barlar HARIC).
        Veri yoksa bos (ama dogru kolonlu) DataFrame doner.
    """
    if commits is None:
        commits = list_snapshot_commits(repo_root)

    all_records: list[dict] = []
    for commit_hash, ts in commits:
        try:
            snapshot = snapshot_loader(commit_hash, repo_root)
        except Exception:
            continue
        all_records.extend(extract_attention_records(snapshot, ts, market=market))

    columns = ["ts", "symbol", "rank", "daily_change_pct", "score"]
    if not all_records:
        return pd.DataFrame(columns=columns)

    df = pd.DataFrame(all_records)
    df["ts"] = pd.to_datetime(df["ts"], utc=True)
    return df.sort_values("ts").reset_index(drop=True)


def first_vs_last_daily_change(history: pd.DataFrame, min_observations: int = 2) -> pd.DataFrame:
    """Her (takvim_gunu, sembol) icin ILK ve SON gozlemlenen gunluk_degisim%'i karsilastirir.

    "Takvim gunu" ts'nin (UTC) tarih kismina gore gruplanir - kaba ama
    BIST'in tek zaman diliminde calismasi nedeniyle yeterli. En az
    `min_observations` gozlemi OLMAYAN (gun,sembol) ciftleri DISLANIR
    ("ilk vs son" karsilastirmasi tek gozlemle anlamsiz olurdu).

    Args:
        history: build_attention_history ciktisi.
        min_observations: Bir (gun,sembol) ciftinin dahil edilmesi icin
            gereken minimum gozlem sayisi (varsayilan 2).

    Returns:
        ["day","symbol","n_observations","first_ts","first_pct","last_ts",
        "last_pct","diff_pct_points"] kolonlarina sahip DataFrame
        (first_pct/last_pct/diff_pct_points YUZDE PUANI cinsinden, orn.
        5.2 = %5.2).
    """
    columns = ["day", "symbol", "n_observations", "first_ts", "first_pct", "last_ts", "last_pct", "diff_pct_points"]
    if history.empty:
        return pd.DataFrame(columns=columns)

    working = history.dropna(subset=["daily_change_pct"]).copy()
    if working.empty:
        return pd.DataFrame(columns=columns)
    working["day"] = working["ts"].dt.date

    rows = []
    for (day, symbol), group in working.groupby(["day", "symbol"]):
        group = group.sort_values("ts")
        if len(group) < min_observations:
            continue
        first_row = group.iloc[0]
        last_row = group.iloc[-1]
        first_pct = float(first_row["daily_change_pct"]) * 100
        last_pct = float(last_row["daily_change_pct"]) * 100
        rows.append(
            {
                "day": day,
                "symbol": symbol,
                "n_observations": len(group),
                "first_ts": first_row["ts"],
                "first_pct": first_pct,
                "last_ts": last_row["ts"],
                "last_pct": last_pct,
                "diff_pct_points": last_pct - first_pct,
            }
        )
    return pd.DataFrame(rows, columns=columns)


def summarize_timing(comparison: pd.DataFrame) -> dict:
    """first_vs_last_daily_change ciktisini tek bir ozet sozluge indirger.

    "already_moved_ratio_pct": ilk-gorulme anindaki gunluk-degisimin, o
    gunun SON GOZLEMLENEN degisimine orani - YALNIZCA yon degistirmeyen
    (first/last AYNI isaretli) ciftlerde anlamlidir, digerleri HARIC
    tutulur (aksi halde oran anlamsiz/yaniltici olurdu).

    Args:
        comparison: first_vs_last_daily_change ciktisi.

    Returns:
        {"n_pairs","n_same_sign_pairs","mean_diff_pct_points",
        "median_diff_pct_points","mean_already_moved_ratio_pct",
        "median_already_moved_ratio_pct"}. comparison bossa n_pairs=0,
        digerleri None.
    """
    if comparison.empty:
        return {
            "n_pairs": 0,
            "n_same_sign_pairs": 0,
            "mean_diff_pct_points": None,
            "median_diff_pct_points": None,
            "mean_already_moved_ratio_pct": None,
            "median_already_moved_ratio_pct": None,
        }

    same_sign = comparison[
        (comparison["first_pct"] != 0) & ((comparison["first_pct"] > 0) == (comparison["last_pct"] > 0))
    ]
    ratios = (same_sign["first_pct"] / same_sign["last_pct"] * 100) if not same_sign.empty else pd.Series(dtype=float)

    return {
        "n_pairs": int(len(comparison)),
        "n_same_sign_pairs": int(len(same_sign)),
        "mean_diff_pct_points": float(comparison["diff_pct_points"].mean()),
        "median_diff_pct_points": float(comparison["diff_pct_points"].median()),
        "mean_already_moved_ratio_pct": float(ratios.mean()) if not ratios.empty else None,
        "median_already_moved_ratio_pct": float(ratios.median()) if not ratios.empty else None,
    }


def main() -> None:
    """CLI giris noktasi: python -m research.gozcu_timing"""
    for market in ("bist", "nasdaq"):
        print(f"=== {market.upper()} ===")
        history = build_attention_history(market=market)
        if history.empty:
            print("  Veri yok (henuz hic acik-piyasa taramasi commit'lenmemis).\n")
            continue

        n_days = history["ts"].dt.date.nunique()
        n_snapshots = history["ts"].nunique()
        print(f"  {n_snapshots} tarama, {n_days} takvim gunu, {history['symbol'].nunique()} benzersiz sembol")
        if n_days < 10:
            print(f"  UYARI: veri COK az ({n_days} gun) - sonuclar KESIN degil, sadece EGILIM olarak okunmali.")

        comparison = first_vs_last_daily_change(history)
        summary = summarize_timing(comparison)
        print(f"  Karsilastirilabilir (gun,sembol) cifti: {summary['n_pairs']}")
        if summary["n_pairs"] > 0:
            print(f"  Ortalama fark (son-ilk): {summary['mean_diff_pct_points']:+.2f} puan")
            print(f"  Medyan fark (son-ilk): {summary['median_diff_pct_points']:+.2f} puan")
            if summary["mean_already_moved_ratio_pct"] is not None:
                print(
                    f"  Ilk-gorulme aninda hareketin ortalama %{summary['mean_already_moved_ratio_pct']:.1f}'i "
                    f"zaten gerceklesmisti (n={summary['n_same_sign_pairs']}, yon-degistirmeyen ciftler)"
                )
        print()


if __name__ == "__main__":
    main()
