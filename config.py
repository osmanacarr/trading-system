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

# Harvey & Liu (2014) "...and the Cross-Section of Expected Returns" - coklu
# test problemi: ayni strateji/faktor havuzunda ne kadar cok hipotez
# denenirse, sabit t>2.0 esigiyle sahte-pozitif (yanlislikla "anlamli"
# bulunan, aslinda sans eseri) bulma olasiligi o kadar artar. quant2.md bu
# referansla t-esiginin havuz buyudukce 3.0-3.5'e cikarilmasini onerir.
# Burada UC kademeli bir merdiven kullanilir (bkz.
# validation.significance.multi_test_t_threshold): tek/iki stratejilik kucuk
# bir havuzda orijinal 2.0 esigi kalir (Donchian + Price Action - ilk ikisi
# zaten bu esikle dogrulandi, geriye donuk sertlestirilmiyor); yeni bir
# strateji/faktor havuza EKLENDIGINDE (3-6 arasi) 3.0'a, havuz daha da
# buyudugunde (7+) 3.5'e cikar.
SIGNIFICANCE_T_THRESHOLD_MULTI_TEST: float = 3.0  # havuzda 3-6 strateji/faktor varken
SIGNIFICANCE_T_THRESHOLD_MULTI_TEST_STRICT: float = 3.5  # havuzda 7+ strateji/faktor varken
SIGNIFICANCE_MULTI_TEST_SINGLE_MAX: int = 2  # bu sayiya kadar orijinal 2.0 esigi kullanilir
SIGNIFICANCE_MULTI_TEST_MID_MAX: int = 6  # bu sayiya kadar 3.0, sonrasi 3.5

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

# ---------------------------------------------------------------------------
# Faktor kutuphanesi (research/factors.py) - Modul 1
# ---------------------------------------------------------------------------

RESEARCH_EMA_PERIOD: int = 20
RESEARCH_RSI_PERIOD: int = 14
RESEARCH_MACD_FAST: int = 12
RESEARCH_MACD_SLOW: int = 26
RESEARCH_MACD_SIGNAL: int = 9
RESEARCH_STOCH_K_PERIOD: int = 14
RESEARCH_STOCH_D_PERIOD: int = 3

# gozcu.metrics.volume_zscore ile ayni formul/varsayilan; burada BAGIMSIZ
# (vektorize) bir implementasyon var cunku GOZCU'nun mimarisi diger
# modullere bagimli olmamasini gerektiriyor (bkz. research/factors.py
# modul docstring'i).
RESEARCH_VOLUME_ZSCORE_LOOKBACK: int = 20
RESEARCH_VOLUME_RATIO_LOOKBACK: int = 20  # gunluk bar RVOL vekili

# Order-flow vekilleri (trade2.md / "trade 3.md" - gercek tick/L2 verisi
# YOK, bunlar GUNLUK OHLCV'den turetilen yaklasiklamalar):
RESEARCH_CVD_PIVOT_WINDOW: int = 10  # CVD/fiyat diverjansi icin pivot onay penceresi
RESEARCH_POC_LOOKBACK: int = 60  # Volume Profile POC icin trailing bar sayisi
RESEARCH_POC_N_BINS: int = 24  # POC histogram bin sayisi
RESEARCH_VALUE_AREA_PCT: float = 0.70  # trade2.md'de gecen standart deger

# Absorption sezgiseli SPEKULATIF bir yaklasiklamadir, dogrulanmis bir
# sinyal degildir (bkz. research/factors.py).
RESEARCH_ABSORPTION_RANGE_LOOKBACK: int = 20
RESEARCH_ABSORPTION_VOLUME_LOOKBACK: int = 20

# ---------------------------------------------------------------------------
# Faktor gecmisi biriktirme (research/factor_history.py) - Modul 2
# ---------------------------------------------------------------------------

RESEARCH_DATA_DIR: Path = PROJECT_ROOT / "research" / "data"
RESEARCH_FACTOR_HISTORY_PATH: Path = RESEARCH_DATA_DIR / "factor_history.parquet"

# ---------------------------------------------------------------------------
# Alpha dogrulama / IC / walk-forward / rule-burden (validation/
# alpha_evaluation.py, validation/walk_forward.py) - Modul 3 + 8
# ---------------------------------------------------------------------------

RESEARCH_IC_HORIZON_DAYS: int = 5  # IC icin "ileri getiri" ufku (N gun sonra)
RESEARCH_MIN_IC_SAMPLE_SIZE: int = 5  # bir tarihte cross-sectional IC icin min sembol sayisi

# quant2.md - "rule burden": ardisik olarak eklenen filtre/kural sayisi bu
# esigi gecerse overfitting riski uyarisi tetiklenir (KOR bir kisitlama
# DEGIL, sadece bir bayrak/log - bkz. validation/alpha_evaluation.py).
MAX_FILTER_COUNT: int = 4

# quant.md/quant2.md - trade istatistiklerinde agregatlarin yanilticili
# olabilecegi minimum islem sayisi esigi (bkz. backtest/metrics.py summarize).
MIN_TRADES_FOR_RELIABLE_STATS: int = 30

# quant.md - "profit factor 1.2-2.6 makul, >5-10 asiri optimize edilmis
# olabilir" sezgiseli (SERT bir kural degil, bir kirmizi bayrak esigi).
PROFIT_FACTOR_OVERFIT_WARNING_THRESHOLD: float = 5.0

# ---------------------------------------------------------------------------
# Volatilite rejimi tespiti (research/regime.py) - Modul 4
# ---------------------------------------------------------------------------

# gozcu.metrics.atr_percentile ile AYNI varsayilan ATR periyodu/lookback -
# burada TAM ZAMAN SERISI (rolling) versiyonu icin bagimsiz implementasyon
# (bkz. research/regime.py modul docstring'i, ayni gerekce research/
# factors.py::compute_volume_zscore icin de gecerliydi).
RESEARCH_REGIME_ATR_PERIOD: int = 14
RESEARCH_REGIME_ATR_LOOKBACK: int = 252
RESEARCH_REGIME_LOW_PCT: float = 33.0  # bu yuzdelik dilimin ALTI -> "dusuk" rejim
RESEARCH_REGIME_HIGH_PCT: float = 67.0  # bu yuzdelik dilimin USTU -> "yuksek" rejim

# ---------------------------------------------------------------------------
# Model kombinasyonu / ensemble (research/ensemble.py) - Modul 5
# ---------------------------------------------------------------------------

# quant2.md - "you'll develop a supposedly new model but then you'll just
# find out that it's actually not that different from other stuff": bu
# esigi ASAN korelasyona sahip faktor ciftleri "redundant" (cesitlendirme
# saglamiyor) olarak isaretlenir.
RESEARCH_FACTOR_CORRELATION_REDUNDANCY_THRESHOLD: float = 0.8

# detect_decay() "decayed=True" donerse, o faktorun ensemble agirligi bu
# oranda AZALTILIR (0.3 = agirlik %30 kesilir) - quant2.md'nin "decay ==
# stratejiyi kapat degil, daha az guven" ilkesine uygun KADEMELI ceza.
RESEARCH_ENSEMBLE_DECAY_PENALTY: float = 0.3

# ---------------------------------------------------------------------------
# Risk-kisitli portfoy optimizasyonu (risk/portfolio.py) - Modul 6
# ---------------------------------------------------------------------------

# quant2.md - "we wouldn't use more than 100 percent of our available
# capital": brut maruziyet (sum(|w_i|)) bu esigi ASAMAZ.
RISK_MAX_GROSS_LEVERAGE: float = 1.0

# quant2.md - "we can't be more than 15 percent short any one thing and we
# can't be more than 30 percent long any one thing" (ornek deger) - bu
# depoda TEK BIR simetrik esik kullanilir (basitlik icin).
RISK_MAX_POSITION_SIZE: float = 0.2

# quant2.md - sektor maruziyeti kisiti: bir sektordeki NET agirlik
# (|sum(w_i in sektor)|) bu esigi asamaz. Sembol->sektor eslemesi bu
# depoda YOK (guvenilir bir kaynak olmadan UYDURULMAYACAK) - cagiran kod
# kendi sector_map'ini saglamalidir (bkz. risk/portfolio.py).
RISK_MAX_SECTOR_EXPOSURE: float = 0.4

# risk/correlation_clusters.py - gercek sektor verisi olmadigindan,
# sector_map'in YERINE ampirik getiri-korelasyonu kumeleri kullanilir
# (bkz. faz3.5_matematiksel_formalizasyon.md SS6: BIST sembolleri ortak
# makro faktore -TL, faiz, endeks- maruz, "sektor" bunu yakalamaz).
# Bu esigin USTUNDEKI (tek-baglantili/single-linkage) ciftler ayni kumeye
# konur, sonra mevcut RISK_MAX_SECTOR_EXPOSURE ile kume-basi maruziyet
# sinirlanir.
#
# NOT (gelecekte gozden gecirilecek - kullanici karari, 2026-08-12): 0.6 ile
# BASLANIYOR ama sabit degil. Birkac hafta paper trading + factor_history
# verisi biriktikten sonra, kumelere giren sembollerin GERCEKTEN ayni
# gunlerde ayni yonde hareket edip etmedigi (orn. ayni gun kume-ici birden
# fazla sembolde esbir giris sinyali sikligi) olculup, 0.6 BIST-geneli
# ortak faktoru yeterince yakalamiyorsa 0.5'e cekilmesi degerlendirilecek -
# kucuk sermayede fazla temkinli olmanin maliyeti, az temkinli olmaktan
# daha dusuktur.
RISK_CORRELATION_CLUSTER_THRESHOLD: float = 0.6
RISK_CORRELATION_CLUSTER_LOOKBACK_DAYS: int = 60

# ---------------------------------------------------------------------------
# Dashboard /research ozet yayinlama (research/publish_summary.py)
# ---------------------------------------------------------------------------

# paper_trading/logger.py::summary.json ile AYNI desen: Python periyodik
# yazar, dashboard SADECE okur (bkz. gozcu/scanner.py mimari prensibi).
RESEARCH_SUMMARY_PATH: Path = RESEARCH_DATA_DIR / "research_summary.json"
