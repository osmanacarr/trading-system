# trading-system

Faz 2 (`faz2_strateji_kartlari.md`) ve Faz 3.5 (`faz3.5_matematiksel_formalizasyon.md`)
dokümanlarındaki kurallara sadık, test edilebilir bir Python paketi. Colab'da
kazanan iki strateji burada üretim-kalitesinde kodlandı:

- **Donchian Channel Breakout (Kart 4)** — birincil hedef, uçtan uca çalışıyor.
- **Price Action Breakout, Model B (Kart 5)** — ikincil, sinyal + backtest
  mantığı hazır (Model A / pullback girişi kapsam dışı, bkz. "Kapsam Dışı").

Faz 4'te bunun üzerine bir **paper trading motoru** eklendi (`paper_trading/`):
gerçek para olmadan, gerçek piyasa verisiyle, günlük çalışan, kalıcı state'e
sahip bir simülasyon katmanı — backtest motoruyla (`backtest/engine.py`)
AYNI risk/stop/pozisyon-büyüklüğü formüllerini kullanır (kod tekrarı yok).

Evren: yalnızca **BIST** ve **BTC/USDT (yfinance üzerinden BTC-USD vekili)**.
S&P500 Faz 3.5'te askıya alındığı için bu iskelette yok.

## Kurulum

```bash
cd trading-system
pip install -r requirements.txt
```

## Kullanım

```bash
# Donchian, BIST evreni (13 likit BIST30 sembolü)
python -m backtest.run --strategy donchian --universe bist

# Donchian, kripto evreni (BTC-USD)
python -m backtest.run --strategy donchian --universe crypto

# Price Action (Model B), tarih aralığı belirterek
python -m backtest.run --strategy price_action --universe bist --start 2019-01-01 --end 2025-01-01
```

Her sembol için `win_rate`, `E[R]` (expectancy_R), medyan R, max drawdown ve
Sharpe yazdırılır; sonda tüm işlemler havuzlanıp t-istatistiği ve Sharpe için
%95 güven aralığı raporlanır (`validation/significance.py`).

### Paper trading (Faz 4)

```bash
# Gunluk calistirma (gercek state/log yazar)
python -m paper_trading.runner --strategy donchian

# Once ne yapacagini gormek icin (HICBIR state/log degisikligi yapmaz)
python -m paper_trading.runner --strategy donchian --dry-run

# Gecmis bir tarih icin simulasyon (test/hata ayiklama)
python -m paper_trading.runner --strategy donchian --date 2026-08-05

# Haftalik ozet raporu (stdout'a; --out ile dosyaya da yazar)
python -m paper_trading.report
python -m paper_trading.report --out paper_trading/logs/weekly_report.md
```

- **State:** `paper_trading/data/state.db` (SQLite) — açık pozisyonlar (sembol
  başına en fazla 1), sanal hesap sermayesi (başlangıç 10.000, `config.PAPER_TRADING_INITIAL_CAPITAL`)
  ve idempotency için sembol başına "son işlenen bar tarihi" burada tutulur.
  JSON değil SQLite seçildi: yarım kalan bir yazma (çökme, güç kesintisi)
  SQLite'ta atomik INSERT/UPDATE/DELETE + WAL modu sayesinde dosyayı
  bozmaz; tek büyük bir JSON dosyası bu garantiyi vermez.
- **Loglar:** `paper_trading/logs/` altında:
  - `trades.jsonl` / `trades.csv` — her giriş/çıkış olayı (tarih, fiyat,
    R-katı, sebep: stop/trailing/target)
  - `equity.jsonl` / `equity.csv` — her çalıştırmada bir günlük sermaye
    anlık görüntüsü (equity eğrisi için gerekli)
  - `summary.json` — dashboard'un doğrudan okuyabileceği küçük özet
    (güncel toplam equity, açık pozisyon sayısı, son 7 günün işlem sayısı)
- **İdempotency:** Aynı gün içinde `runner.py` birden fazla kez çalıştırılırsa,
  bir sembol için en son işlenen bar tarihi zaten güncel ise o sembol
  `skip_already_processed` olarak atlanır — aynı sinyal iki kez işlenmez.
- **Piyasa takvimi:** BIST sembolleri için hafta sonu (Cts/Paz) günlerinde
  hiç fetch denenmez (`skip_weekend`); kripto her gün çalışır. Tam resmi
  tatil takvimi bu sürümde yok (bkz. "Bilinen riskler").

### Testler

```bash
python -m pytest -q
```

`python -m pytest` / `python -m backtest.run` / `python -m paper_trading.runner`
şeklinde **`-m` ile ve proje kökünden (`trading-system/`)** çalıştırın —
modüller arası importlar (`from config import ...`, `from data.fetch import ...`)
buna göre kuruldu.

## Proje yapısı

```
trading-system/
├── .github/
│   └── workflows/
│       └── paper_trading.yml  # gunluk otomatik paper trading (bkz. "Zamanlama")
├── .gitignore
├── data/
│   ├── fetch.py          # yfinance OHLCV çekme (fetch_ohlcv, fetch_universe)
│   ├── adjust.py         # %40+ fiyat sıçramalarını geriye dönük düzeltme
│   └── fx.py             # BIST TL -> USD dönüşümü (USDTRY)
├── signals/
│   ├── donchian.py       # Kart 4: giriş/trailing-çıkış sinyalleri + filtreler
│   └── price_action.py   # Kart 5 (Model B): kırılım + sabit R/R sinyalleri
├── backtest/
│   ├── engine.py         # ATR stop, %1 risk, komisyon+slipaj dahil simülasyon
│   │                      # (OpenPosition, apply_slippage, resolve_intrabar_exit,
│   │                      #  check_donchian_exit, plan_donchian_entry — paper_trading
│   │                      #  ile PAYLAŞILAN public fonksiyonlar)
│   ├── metrics.py        # win_rate, expectancy_R, medyan R, max DD, Sharpe
│   └── run.py             # CLI: python -m backtest.run --strategy ... --universe ...
├── validation/
│   └── significance.py   # t-istatistiği, walk-forward split, Sharpe-CI
├── paper_trading/         # Faz 4 - paper trading motoru
│   ├── state.py           # SQLite kalıcı state (pozisyonlar, equity, idempotency)
│   ├── runner.py          # gunluk calistirici (fetch->sinyal->giris/cikis->state)
│   ├── logger.py          # trade/equity logu (CSV+JSONL) + dashboard summary.json
│   ├── report.py          # haftalik markdown ozet raporu
│   ├── data/state.db      # (calisma zamaninda olusur) SQLite veritabani
│   └── logs/               # (calisma zamaninda olusur) trades/equity/summary
├── config.py              # BIST_TICKERS, CRYPTO_TICKERS, tüm strateji + paper trading parametreleri
├── tests/                 # her modül için sentetik veriyle pytest testleri (71 test)
├── requirements.txt
└── README.md
```

## Doğrulama durumu

- `python -m pytest -q` → **71/71 test geçiyor** (44 backtest/veri/sinyal/istatistik +
  27 paper trading; tamamı sentetik/deterministik veri, ağ bağlantısı gerektirmez).
- Donchian + BIST canlı veriyle uçtan uca doğrulandı (2019-01-01 -> bugün, 13 sembol,
  ATR(20)): havuzlanmış 594 işlem, t-stat ≈ 4.29 (anlamlı), Sharpe %95 GA ≈ [0.42, 0.59] —
  Faz 3.5 SS4.1'deki tahmini rakamlarla (t≈2.6, tek sembol) aynı yönde ve daha
  güçlü (havuzlama örneklem büyüklüğünü artırdığı için beklenen bir sonuç).
- Donchian + BTC-USD canlı veriyle doğrulandı (ATR(20)): 68 işlem, Sharpe ≈ 0.92.
- **ATR(14) → ATR(20) düzeltmesinin etkisi** (aynı tarih aralığı, aynı 13 BIST
  sembolü + BTC-USD üzerinde tekrar koşuldu): sonuçlar pratik olarak aynı kaldı —
  BIST işlem sayısı 597→594, t-stat 4.23→4.29, Sharpe GA [0.41,0.58]→[0.42,0.59];
  BTC-USD işlem sayısı değişmedi (68), Sharpe 0.92→0.92. Daha geniş ATR penceresi
  yalnızca ilk stop mesafesini hafifçe genişletiyor (stop biraz daha uzakta), bu da
  birkaç sınırda kalan işlemin farklı barda kapanmasına yol açtı ama genel istatistiksel
  tabloyu değiştirmedi.

## Zamanlama — günlük otomatik çalıştırma (Faz 4)

Kod içinde bir scheduler YOK (cron/Task Scheduler kurulmuyor) — `paper_trading.runner`'ı
her gün otomatik tetiklemek için üç seçenek var. **C seçeneği (GitHub Actions) bu
repoda gerçekten uygulandı** (`.github/workflows/paper_trading.yml`); A ve B
kendi makinenizde/sunucunuzda çalıştırmak isterseniz referans olarak duruyor.

### Seçenek A — cron (Linux/Mac)

```cron
# Her is gunu (Pzt-Cum) 19:00'da calistir (BIST kapanisindan, kripto icin
# gun sonuna yakin bir saat secildi - istege gore degistirin)
0 19 * * 1-5 cd /path/to/trading-system && /path/to/venv/bin/python -m paper_trading.runner --strategy donchian >> paper_trading/logs/cron.log 2>&1
```

### Seçenek B — Windows Task Scheduler

```powershell
# PowerShell'den bir kez calistirarak gorevi olusturur (gunluk 19:00)
$action = New-ScheduledTaskAction -Execute "python.exe" `
    -Argument "-m paper_trading.runner --strategy donchian" `
    -WorkingDirectory "C:\path\to\trading-system"
$trigger = New-ScheduledTaskTrigger -Daily -At 19:00
Register-ScheduledTask -TaskName "PaperTradingDaily" -Action $action -Trigger $trigger
```

### Seçenek C — GitHub Actions (UYGULANDI, önerilen: ücretsiz, sunucu gerektirmez)

Dosya: [`.github/workflows/paper_trading.yml`](.github/workflows/paper_trading.yml).
Bu workflow `trading-system/`'ın repo KÖKÜ olduğunu varsayar.

Ne yapıyor, adım adım:

1. **İki zamanlanmış tetikleyici** (`on.schedule`, ikisi de aynı işi çalıştırır):
   - `0 16 * * 1-5` → her iş günü UTC 16:00 (TR saatiyle ~19:00, BIST kapanışından sonra)
   - `0 0 * * *` → her gün UTC 00:00 (BTC-USD günlük barının kapanışına yakın)

   Artı `workflow_dispatch: {}` ile Actions sekmesinden elle de tetiklenebilir.
2. **Tek bir iş (job), iki tetikleyici de aynı komutu çalıştırır** — ayrı
   "sadece BIST" / "sadece kripto" komutu YOK, çünkü `paper_trading.runner`
   zaten tüm evreni (BIST+kripto) işler ve **idempotent**tir: bir sembolün o
   günkü barı zaten işlenmişse (`skip_already_processed`) ikinci tetikleyici
   o sembol için hiçbir şey yapmaz. Yani BIST çalıştırması o gün henüz kapanmamış
   kripto barını atlar/bir kez işler, kripto çalıştırması zaten işlenmiş BIST'i
   atlar — iki ayrı workflow yerine tek workflow'u iki saatte tetiklemek yeterli.
3. **Testler önce çalışır** (`python -m pytest -q`) — başarısız olursa (varsayılan
   GitHub Actions davranışı gereği) sonraki adımlar (runner, commit, push)
   **hiç çalışmaz**; bozuk kod state'e/loglara asla dokunmaz.
4. `python -m paper_trading.runner --strategy donchian` — dry-run **DEĞİL**,
   gerçek state/log güncellemesi yapar.
5. `paper_trading/data/state.db` ve `paper_trading/logs/` altındaki değişiklikler
   otomatik commit'lenip aynı branch'e push'lanır (`permissions: contents: write`
   ile `GITHUB_TOKEN`'a yazma izni verilerek). Değişiklik yoksa (o gün hiçbir
   sembol yeni işlenmediyse) commit atlanır — ama `equity.jsonl`'a her gerçek
   çalıştırmada bir satır eklendiği için (bkz. `logger.py`), pratikte hemen
   hemen her çalıştırma bir commit üretir.

**Not:** `paper_trading/data/backups/` (yerel zaman-damgalı yedekler, bkz.
`state.backup()`) bilinçli olarak commit'lenmiyor (`.gitignore`'da) — git
commit geçmişinin kendisi zaten her çalıştırma için geri dönülebilir bir
"yedek" işlevi görüyor; ayrıca commit etmek repoyu gereksiz büyütürdü.

### Kurulum gereksinimleri (workflow'u aktif etmeden önce)

- **Secret gerekmiyor:** yfinance kimlik doğrulaması istemiyor, `GITHUB_TOKEN`
  GitHub tarafından her çalıştırmada otomatik sağlanıyor — ek bir secret
  eklemenize gerek yok.
- **`GITHUB_TOKEN` yazma izni:** Workflow dosyasında `permissions: contents: write`
  var, ama bu bazı organizasyon/repo ayarlarında YETMEYEBİLİR — repo
  **Settings → Actions → General → Workflow permissions**'ta "**Read and
  write permissions**" seçili olmalı (varsayılan bazı yeni repolarda
  "Read repository contents permission" = salt okunur gelir). İkisi de
  gerekli: dosyadaki `permissions:` bloğu üst sınırı yükseltemez, yalnızca
  repo ayarının izin verdiği kadarını "talep" edebilir.
- **Actions etkin olmalı:** **Settings → Actions → General**'da "Allow all
  actions and reusable workflows" (veya en azından `actions/checkout` ve
  `actions/setup-python`'a izin veren bir politika) seçili olmalı.
- **Branch protection dikkat:** `main` (veya push edilen branch) üzerinde
  "Require a pull request before merging" gibi bir kural varsa, bot'un
  DOĞRUDAN push'u reddedilir. Ya bu repoda branch protection kurmayın, ya da
  kuralda "Allow specified actors to bypass required pull requests" ile
  `github-actions[bot]`'u (veya kullanacağınız token'ın sahibini) istisna
  olarak ekleyin.
- **Repo GitHub'a push edilmiş olmalı:** Bu workflow yalnızca repo GitHub'da
  barındığında ve Actions çalıştığında aktif olur — yerel makinede otomatik
  tetiklenmez.

### Otomatik çalışma nasıl doğrulanır

1. Repoyu push ettikten ve yukarıdaki ayarları yaptıktan sonra **Actions**
   sekmesine gidin; "Paper Trading Daily" workflow'unu görmelisiniz.
2. Zamanlanmış saati beklemeden test etmek için workflow'u açıp **"Run workflow"**
   (workflow_dispatch) ile elle tetikleyin.
3. Çalışan/tamamlanan run'a tıklayıp adım adım logları izleyin: `pytest`
   çıktısı (testler geçti mi), ardından `paper_trading.runner` çıktısı —
   her sembol için `no_signal` / `entry_long` / `exit` / `skip_weekend` vb.
   satırları ve sondaki toplam equity özetini burada görürsünüz.
4. Run yeşil (başarılı) bittiyse, repo'nun ana sayfasında **yeni bir commit**
   olmalı: `"paper trading: otomatik calistirma YYYY-MM-DD HH:MM UTC"`.
   Bu commit'i açıp diff'e bakın: `paper_trading/data/state.db` (binary,
   diff görünmez ama değişmiş olmalı) ve `paper_trading/logs/*` değişiklikleri.
5. Asıl doğrulama için GitHub üzerinde şu dosyaları açın:
   - `paper_trading/logs/summary.json` — dashboard-hazır özet: güncel toplam
     equity, açık pozisyon sayısı, son 7 günün işlem sayısı. Bu dosyanın
     `last_updated` alanı en son çalıştırmanın tarihiyle eşleşmeli.
   - `paper_trading/logs/trades.jsonl` (veya `.csv`) — o gün bir giriş/çıkış
     olduysa yeni bir satır eklenmiş olmalı.
   - `paper_trading/logs/equity.jsonl` (veya `.csv`) — her gerçek çalıştırmada
     bir satır eklenir (işlem olsun olmasın); satır sayısının çalıştırma
     sayısıyla orantılı arttığını görmek, motorun düzenli çalıştığının en
     basit kanıtıdır.
6. Bir şey ters giderse (run kırmızı/başarısız): önce `pytest` adımının mı
   yoksa `paper_trading.runner` adımının mı başarısız olduğuna bakın —
   `pytest` başarısızsa kod bozuktur (state'e dokunulmadı, güvenli); runner
   adımı başarısızsa (orn. yfinance geçici hata sonrası TÜM denemeler
   tükendi) o sembol zaten `skip_fetch_error` ile atlanmış olmalı ama
   process'in kendisi de çökmüşse (beklenmeyen bir istisna) logu inceleyin.

**Önemli:** Hangi seçenek kullanılırsa kullanılsın, `paper_trading/data/state.db`
çalıştırmalar arasında KALICI olmalı (aynı makine/disk, ya da GitHub Actions'ta
yukarıdaki gibi commit-back). State kaybolursa açık pozisyonlar ve idempotency
geçmişi de kaybolur (bkz. "Bilinen riskler").

## Bilinen riskler / öneriler

- **State dosyası kaybı/bozulması:** `state.db` tek bir dosyadır; disk arızası
  veya yanlışlıkla silinme açık pozisyon bilgisini tamamen kaybettirir. Öneri:
  `paper_trading/data/` dizinini düzenli olarak (GitHub Actions senaryosunda
  zaten her çalıştırmada) versiyon kontrolüne veya ayrı bir yedeğe alın. SQLite
  WAL modu yalnızca process çökmesine karşı korur, disk/insan hatasına karşı değil.
- **Veri gecikmesi / erken çalıştırma riski:** yfinance günlük barı, piyasa
  henüz kapanmadan çekilirse o günün Close'u NİHAİ olmayabilir (kısmi gün
  verisi). Runner'ı piyasa kapanışından sonra çalıştırmak (yukarıdaki
  zamanlama örneklerindeki saatler bunu hedefler) bu riski azaltır ama şu an
  kod içinde bir "piyasa kapandı mı" kontrolü YOK — yalnızca hafta sonu
  kontrolü var. Kritik ise `--dry-run` ile önce doğrulama önerilir.
  yfinance ayrıca ara sıra geriye dönük fiyat düzeltmeleri (auto_adjust)
  yayınlayabilir; bu, dünkü bir barın bugün hafifçe farklı gelmesine yol
  açabilir — Donchian/ATR gibi rolling göstergeler için pratikte ihmal
  edilebilir düzeyde ama sıfır değil.
- **Resmi tatil takvimi eksik:** BIST resmi tatillerinde (hafta içi ama piyasa
  kapalı) runner yine de fetch dener; yfinance o gün için veri döndürmeyeceğinden
  (`fetch_ohlcv` boş/aynı son bar döner) pratik bir hata oluşmaz, ama gereksiz
  bir API çağrısı yapılır. Şu an bilinçli olarak basit tutuldu (gorev tanımı);
  ileride bir tatil takvimi kütüphanesi (`pandas_market_calendars` gibi)
  eklenebilir.
- **Çoklu-sembol equity ilişkisi:** Tüm semboller TEK bir paylaşılan hesap
  equity'sinden %1 risk alıyor (gerçekçi bir portföy davranışı), ancak
  semboller arası korelasyon (özellikle 13 BIST sembolü, bkz. Faz 3.5 §6)
  hesaba katılmıyor — aynı gün birden fazla korelasyonlu sembolde eşzamanlı
  giriş, göründüğünden daha yüksek gerçek risk anlamına gelebilir.
  `risk/portfolio.py` (Faz 3.5 §6, henüz kodlanmadı) bunu ele alacak modül.
- **Tek makine/tek process varsayımı:** SQLite dosya kilitleri aynı anda TEK
  bir yazan process'i güvenle destekler; runner'ı aynı state.db üzerinde
  paralel/çakışan zamanlamalarla çalıştırmayın (orn. hem cron hem manuel
  çalıştırma aynı dakikada).

## Önemli tasarım kararları / dokümanlarla farklar

- **ATR periyodu:** Kart 4 metni "ATR(20)×2" diyor; formalizasyon dokümanı SS2.3'teki
  "ATR_14(t)" ifadesi genel formülü illüstre eden bir örnekti, Colab'da test edilip
  doğrulanan parametreyi geçersiz kılma amaçlı değildi. Bu paket, Colab'da gerçekten
  test edilen Kart 4 parametresini esas alır: `DONCHIAN_ATR_PERIOD=20`,
  `DONCHIAN_ATR_STOP_MULT=2` (`config.py`'de). Farklı varsayımla test etmek
  isterseniz bu iki sabiti değiştirin.
- **Kripto sembolü:** yfinance BTC/USDT sunmuyor; `BTC-USD` (USD paritesi)
  kullanılıyor. USDT/USD sapması genelde ihmal edilebilir düzeydedir.
- **Slipaj:** "1 tick" yerine, evrenler arası genellenebilir olması için fiyatın
  sabit bir yüzdesi (`SLIPPAGE_PCT=0.0005`) olarak modellendi.
- **Aynı barda hem stop hem hedef tetiklenirse:** motor muhafazakâr davranır,
  stop-loss önceliklidir (bkz. `backtest/engine.py` docstring'i).
- **Sıçrama düzeltme eşiği (`data/adjust.py`):** %40+ günlük kapanış sıçraması
  tespit edilen barın ÖNCESİndeki tüm barlar, split-adjustment mantığıyla geriye
  dönük ölçeklenir (Volume ölçeklenmez).

## Kapsam dışı (sonraki iterasyon)

- **Price Action Model A (pullback girişi):** Kart 5'in yapısal seviye tespiti
  (üçgen, destek/direnç, swing high/low) gerektiren versiyonu; formalizasyon
  dokümanı SS3'te yalnızca Model B kapalı-form olarak verildi. Model A, otomatik
  swing/yapı tespiti eklendiğinde `signals/price_action.py`'ye eklenebilir.
- `risk/position_sizing.py` (Kelly) ve `risk/portfolio.py` (korelasyon bazlı risk
  bütçesi) — Faz 3.5 SS5-6'da tanımlanan, henüz kodlanmamış modüller.
- Kart 1 (MA oylama), Kart 2 (VWAP mean reversion), Kart 3 (Bollinger/Keltner
  fade) — Faz 2'de tanımlı ama bu iterasyonun kapsamı dışında.
