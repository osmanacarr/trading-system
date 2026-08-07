"""Merkezi konfigürasyon: enstrüman evrenleri ve strateji parametreleri.

Kaynak: faz2_strateji_kartlari.md (Kart 4, Kart 5) ve
faz3.5_matematiksel_formalizasyon.md (SS 2-3).

Not (ATR periyodu): Kart 4 metninde stop mesafesi "ATR(20)x2" olarak
geçiyor; formalizasyon dokümanının SS 2.3'undeki ATR_14(t) ifadesi ise
genel formülü illüstre eden bir örnekti, Colab'da test edilip doğrulanan
parametreyi geçersiz kılma amaçlı değildi. Bu paket, Colab'da gerçekten
test edilen ve doğrulanan Kart 4 parametresini esas alır
(ATR_PERIOD=20, ATR_STOP_MULT=2). Farklı bir varsayımla test etmek
isterseniz bu iki sabiti değiştirmeniz yeterli.
"""

from __future__ import annotations

from pathlib import Path

# Proje koku (bu dosyanin bulundugu dizin) - state/log yollari cagiran kodun
# calisma dizininden BAGIMSIZ olsun diye buna gore kurulur.
PROJECT_ROOT: Path = Path(__file__).resolve().parent

# ---------------------------------------------------------------------------
# Enstrüman evrenleri
# ---------------------------------------------------------------------------

# BIST30 icindeki likit, sik islem goren semboller (yfinance formati: ".IS")
BIST_TICKERS: list[str] = [
    "THYAO.IS",
    "GARAN.IS",
    "AKBNK.IS",
    "ISCTR.IS",
    "KCHOL.IS",
    "SAHOL.IS",
    "SISE.IS",
    "EREGL.IS",
    "BIMAS.IS",
    "ASELS.IS",
    "TUPRS.IS",
    "FROTO.IS",
    "TOASO.IS",
]

# Kripto evreni: yfinance BTC/USDT'yi dogrudan sunmuyor; USD paritesi
# (BTC-USD) Colab'daki BTC/USDT sonuclarina en yakin serbestce erisilebilir
# vekildir (fark, USDT/USD peg sapmasi kadar - genelde ihmal edilebilir).
CRYPTO_TICKERS: list[str] = [
    "BTC-USD",
]

# BIST icin TL -> USD donusumu istenirse kullanilacak FX sembolu (yfinance)
USDTRY_TICKER: str = "USDTRY=X"

# ---------------------------------------------------------------------------
# Ortak risk / maliyet varsayimlari (faz2_strateji_kartlari.md - "Ortak
# varsayimlar")
# ---------------------------------------------------------------------------

RISK_PER_TRADE: float = 0.01  # hesabin %1'i (E_t * rho)
MIN_RISK_REWARD: float = 2.0  # min R/R = 1:2
COMMISSION_PCT: float = 0.0005  # %0.05 komisyon (tek yon)
SLIPPAGE_PCT: float = 0.0005  # ~1 tick yerine fiyatin sabit bir orani
INITIAL_CAPITAL: float = 100_000.0
MIN_BARS_REQUIRED: int = 60  # gostergelerin (ATR20, Donchian20 vb.) isinmasi icin gereken min bar

# ---------------------------------------------------------------------------
# Kart 4 - Donchian Channel Breakout parametreleri
# ---------------------------------------------------------------------------

DONCHIAN_ENTRY_N: int = 20  # giris kanali (N gunluk ekstremum)
DONCHIAN_EXIT_N: int = 10  # cikis (trailing) kanali
DONCHIAN_ATR_PERIOD: int = 20  # bkz. modul docstring'i - Colab'da test edilen Kart 4 parametresi
DONCHIAN_ATR_STOP_MULT: float = 2.0  # k=2, ilk stop mesafesi
DONCHIAN_BODY_MULT: float = 1.5  # kirilim mumu >= onceki 5 mumun 1.5 katı
DONCHIAN_BODY_LOOKBACK: int = 5
DONCHIAN_VOLUME_MULT: float = 1.0  # hacim >= 20 gunluk ortalama
DONCHIAN_VOLUME_LOOKBACK: int = 20

# ---------------------------------------------------------------------------
# Kart 5 - Price Action Breakout parametreleri (Model B: hacim onayli
# dogrudan kirilim - formal dokuman SS3'te kodlanabilir sekilde tanimlanan
# versiyon; Model A (pullback) bu ilk surumde kapsam disi, bkz README)
# ---------------------------------------------------------------------------

PA_BREAKOUT_N: int = 20  # kirilim seviyesi icin lookback (n)
PA_BODY_MULT: float = 2.0  # beta
PA_BODY_LOOKBACK: int = 5
PA_VOLUME_MULT: float = 1.5  # gamma
PA_VOLUME_LOOKBACK: int = 20
PA_RISK_REWARD: float = 2.0  # sabit R/R cikis (2:1)

# ---------------------------------------------------------------------------
# Istatistiksel anlamlilik (validation/significance.py) varsayilan degerleri
# ---------------------------------------------------------------------------

SIGNIFICANCE_T_THRESHOLD: float = 2.0  # ~%95 guven esigi (faz3.5 SS4.1)
CONFIDENCE_LEVEL: float = 0.95

# ---------------------------------------------------------------------------
# Faz 4 - Paper Trading motoru (paper_trading/)
# ---------------------------------------------------------------------------

PAPER_TRADING_INITIAL_CAPITAL: float = 10_000.0  # sanal sermaye baslangici
PAPER_TRADING_DEFAULT_STRATEGY: str = "donchian"  # Faz 3'te dogrulanan birincil strateji

# Kalici state (SQLite) ve log dosyalarinin yolu - proje kokune gore sabit,
# calisma dizininden bagimsiz.
PAPER_TRADING_DATA_DIR: Path = PROJECT_ROOT / "paper_trading" / "data"
PAPER_TRADING_STATE_DB_PATH: Path = PAPER_TRADING_DATA_DIR / "state.db"
PAPER_TRADING_LOG_DIR: Path = PROJECT_ROOT / "paper_trading" / "logs"

# Veri cekme hatalarina karsi yeniden deneme (rate limit / gecici ag hatasi)
FETCH_MAX_ATTEMPTS: int = 3
FETCH_RETRY_BASE_DELAY_SECONDS: float = 1.0  # exponential backoff: 1s, 2s, 4s, ...

# Gostergelerin (Donchian N=20, ATR N=20 vb.) isinmasi icin her calistirmada
# geriye dogru cekilecek takvim gunu sayisi (hafta sonu/tatil kaybini telafi
# etmek icin MIN_BARS_REQUIRED'in oldukca uzerinde).
PAPER_TRADING_LOOKBACK_DAYS: int = 400
