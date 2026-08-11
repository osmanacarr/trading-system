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

# Kullanicinin sistem sinyaline karsi GERCEKTEN (kendi hesabindan, manuel)
# actigi islemlerin kaydi - bkz. paper_trading/manual_log.py. Sistemin kendi
# (sanal) trades.jsonl'inden bagimsiz, sadece dashboard'da "sistem onerisi
# vs gercek giris" karsilastirmasi icin.
PAPER_TRADING_MANUAL_LOG_PATH: Path = PAPER_TRADING_LOG_DIR / "manual_trades.jsonl"

# Veri cekme hatalarina karsi yeniden deneme (rate limit / gecici ag hatasi)
FETCH_MAX_ATTEMPTS: int = 3
FETCH_RETRY_BASE_DELAY_SECONDS: float = 1.0  # exponential backoff: 1s, 2s, 4s, ...

# Gostergelerin (Donchian N=20, ATR N=20 vb.) isinmasi icin her calistirmada
# geriye dogru cekilecek takvim gunu sayisi (hafta sonu/tatil kaybini telafi
# etmek icin MIN_BARS_REQUIRED'in oldukca uzerinde).
PAPER_TRADING_LOOKBACK_DAYS: int = 400

# Acik bir pozisyonda guncel fiyatin stop'a olan mesafesi, orijinal
# giris-stop mesafesinin bu oranin altina duserse Telegram'a erken uyari
# mesaji gonderilir (karar/islem degistirmez, sadece bilgilendirme).
STOP_PROXIMITY_WARNING_PCT: float = 0.20

# ---------------------------------------------------------------------------
# GOZCU - surekli izleme paneli (gozcu/). Paper trading'den TAMAMEN bagimsiz:
# al-sat sinyali uretmez, sadece dikkat ceken piyasa hareketlerini gosterir.
# Bkz. gozcu/scanner.py modul docstring'i (mimari gerekce).
# ---------------------------------------------------------------------------

GOZCU_DATA_DIR: Path = PROJECT_ROOT / "gozcu" / "data"
GOZCU_SNAPSHOT_PATH: Path = GOZCU_DATA_DIR / "snapshot.json"
GOZCU_ALERT_STATE_PATH: Path = GOZCU_DATA_DIR / "alert_state.json"

# BIST evreni dinamik cekilir (gozcu/universe.py): Wikipedia'nin Borsa
# Istanbul'a kote TUM sirketleri listeleyen tablosu (BIST100 endeks
# bilesenlerinden daha genis bir kapsam - pd.read_html ile parse edilebilir
# tek uygun kaynak buydu). Cekme basarisiz/parse edilemez olursa mevcut
# BIST_TICKERS'a (13 sembol) dusulur.
GOZCU_BIST_WIKI_URL: str = "https://en.wikipedia.org/wiki/List_of_companies_listed_on_the_Borsa_Istanbul"

# NASDAQ-100 da dinamik cekilir (Wikipedia "List of NASDAQ-100 companies").
GOZCU_NASDAQ100_WIKI_URL: str = "https://en.wikipedia.org/wiki/List_of_NASDAQ-100_companies"

# Her iki dinamik kaynak da basarisiz olursa dusulecek statik yedek listeler.
GOZCU_NASDAQ100_FALLBACK: list[str] = [
    "AAPL", "MSFT", "AMZN", "NVDA", "GOOGL", "GOOG", "META", "TSLA", "AVGO",
    "COST", "PEP", "ADBE", "NFLX", "CSCO", "AMD", "INTC", "QCOM", "TXN",
    "AMGN", "HON", "INTU", "SBUX", "GILD", "MDLZ", "BKNG", "ADI", "REGN",
    "VRTX", "PYPL", "LRCX", "PANW", "MU", "SNPS", "CDNS", "KLAC", "MAR",
    "ORLY", "CSX", "ABNB",
]

# Referans endeks/ETF sembolleri (korelasyon ozeti icin, gozcu/correlation.py).
GOZCU_BIST_REFERENCE_TICKER: str = "XU100.IS"
GOZCU_BIST_REFERENCE_TICKER_FALLBACK: str = "^XU100"
GOZCU_NASDAQ_REFERENCE_TICKER: str = "QQQ"

# Veri cekme parametreleri
GOZCU_INTRADAY_INTERVAL: str = "5m"
GOZCU_DAILY_LOOKBACK_DAYS: int = 400  # ~252 islem gunu + tatil/haftasonu payi
GOZCU_INTRADAY_LOOKBACK_DAYS: int = 5  # sadece bugunku (+ haftasonu tamponu) barlar
GOZCU_ATR_PERIOD: int = 14
GOZCU_VOLUME_ZSCORE_LOOKBACK: int = 20
GOZCU_WEEKLY_LOOKBACK_TRADING_DAYS: int = 5
GOZCU_52W_LOOKBACK_TRADING_DAYS: int = 252

# Piyasa acik saatleri (yerel saat, basitlestirilmis - resmi tatil takvimi
# haric, bkz. dashboard/lib/market.ts: isBistOpen ile ayni felsefe).
GOZCU_BIST_TIMEZONE: str = "Europe/Istanbul"
GOZCU_BIST_OPEN_TIME: tuple[int, int] = (10, 0)
GOZCU_BIST_CLOSE_TIME: tuple[int, int] = (18, 10)
GOZCU_NASDAQ_TIMEZONE: str = "America/New_York"
GOZCU_NASDAQ_OPEN_TIME: tuple[int, int] = (9, 30)
GOZCU_NASDAQ_CLOSE_TIME: tuple[int, int] = (16, 0)

# Kompozit "Dikkat Skoru" agirliklari (gozcu/scoring.py). Skor =
# w1*|gunluk %degisim| + w2*hacim_zskoru + w3*RVOL + w4*(momentum mumu ise 1 else 0)
GOZCU_SCORE_WEIGHT_DAILY_CHANGE: float = 1.0
GOZCU_SCORE_WEIGHT_VOLUME_ZSCORE: float = 1.0
GOZCU_SCORE_WEIGHT_RVOL: float = 1.0
GOZCU_SCORE_MOMENTUM_BONUS: float = 2.0
GOZCU_ATTENTION_LIST_TOP_N: int = 20

# Piyasa psikolojisi gauge'u: ortalama |gunluk %degisim| bu esikleri asarsa
# oynaklik rejimi "yuksek"/"asiri" olarak etiketlenir (gauge'a karistirilmaz,
# ayri bir bayrak olarak gosterilir - bkz. gozcu/psychology.py).
GOZCU_VOLATILITY_REGIME_ELEVATED_PCT: float = 0.02
GOZCU_VOLATILITY_REGIME_EXTREME_PCT: float = 0.04

# Telegram "dikkat" uyarisi (opsiyonel, gozcu/alerts.py): dikkat skoru bu
# esigi gecen bir sembol icin GUNDE BIR KEZ bilgi mesaji gonderilir. Bu bir
# al-sat sinyali DEGILDIR.
GOZCU_ALERT_SCORE_THRESHOLD: float = 8.0
