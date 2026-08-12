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
python -m paper_trading.runner --strategies donchian

# Birden fazla strateji paralel calistirilabilir (M3 - coklu strateji destegi)
python -m paper_trading.runner --strategies donchian price_action

# Once ne yapacagini gormek icin (HICBIR state/log degisikligi yapmaz)
python -m paper_trading.runner --strategies donchian --dry-run

# Gecmis bir tarih icin simulasyon (test/hata ayiklama)
python -m paper_trading.runner --strategies donchian --date 2026-08-05

# Haftalik ozet raporu (stdout'a; --out ile dosyaya da yazar)
python -m paper_trading.report
python -m paper_trading.report --out paper_trading/logs/weekly_report.md
```

- **State:** `paper_trading/data/state.db` (SQLite) — açık pozisyonlar
  ((sembol, strateji) çifti başına en fazla 1 — M3'ten itibaren aynı sembolde
  birden fazla strateji PARALEL pozisyon tutabilir), sanal hesap sermayesi
  (başlangıç 10.000, `config.PAPER_TRADING_INITIAL_CAPITAL`) ve idempotency
  için (sembol, strateji) başına "son işlenen bar tarihi" burada tutulur.
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
  bir (sembol, strateji) çifti için en son işlenen bar tarihi zaten güncel ise
  o çift `skip_already_processed` olarak atlanır — aynı sinyal iki kez işlenmez.
- **Evren (M3 - evren genişletme):** BIST tarafı artık sabit 13 sembol değil,
  Gözcü'nün canlı evrenini (`gozcu.universe.get_bist_universe()`, dinamik
  Wikipedia çekimi, ~347 sembol — başarısız/boş dönerse 13 sembole düşer)
  kullanır. Bu, `risk/correlation_clusters.py` + `risk/portfolio.py` ile
  ATOMİK teslim edildi: yeni girişler önce mevcut açık pozisyonların
  tükettiği brüt kaldıraç bütçesi düşülerek, sonra getiri-korelasyonu
  kümelerine göre kısıtlanarak açılır (bkz. `paper_trading/runner.py`
  modül docstring'i "PORTFÖY TAHSİSİ").
- **Çoklu strateji (M3):** `--strategies` ile birden fazla strateji paralel
  çalıştırılabilir; aynı sembolde farklı stratejiler bağımsız pozisyon
  tutabilir (`paper_trading/state.py`'de pozisyon anahtarı artık
  (sembol, strateji) kompozit).
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
│       ├── paper_trading.yml  # gunluk otomatik paper trading (bkz. "Zamanlama")
│       └── gozcu_scan.yml     # 5 dakikada bir GOZCU taramasi (bkz. "GOZCU")
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
├── gozcu/                  # GOZCU - canli izleme paneli (paper trading'den BAGIMSIZ, bkz. "GOZCU")
│   ├── universe.py         # BIST/NASDAQ-100 evrenlerini Wikipedia'dan dinamik ceker
│   ├── data_fetch.py       # toplu (batched) yfinance veri cekme
│   ├── metrics.py          # RVOL, hacim z-skoru, VWAP, 52h yakinlik, ATR yuzdelik dilimi, ...
│   ├── scoring.py          # kompozit "Dikkat Skoru" + siralama
│   ├── psychology.py       # breadth bazli piyasa psikolojisi gauge'u
│   ├── correlation.py      # referans endekse gore ortalama korelasyon
│   ├── alerts.py           # gunde-bir-kez Telegram "dikkat" uyarisi (idempotent)
│   ├── market_hours.py     # BIST/NASDAQ acik-saat kontrolu (zoneinfo, DST-farkinda)
│   ├── scanner.py          # orkestratör + CLI (python -m gozcu.scanner --market all)
│   └── data/snapshot.json  # (calisma zamaninda olusur) tek kaynak - dashboard SADECE bunu okur
├── config.py              # BIST_TICKERS, CRYPTO_TICKERS, tüm strateji + paper trading + GOZCU parametreleri
├── tests/                 # her modül için sentetik veriyle pytest testleri
├── requirements.txt
└── README.md
```

## Doğrulama durumu

- `python -m pytest -q` → **319/319 test geçiyor** (backtest/veri/sinyal/istatistik/
  paper trading/risk/GÖZCÜ; tamamı sentetik/deterministik veri veya mock'lanmış
  yfinance/Telegram çağrılarıyla, gerçek ağ bağlantısı gerektirmez).
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
- **Kart 1 (MA-oylama, `signals/ma_voting.py`, M4) — KODLANDI ve BACKTEST EDİLDİ
  ama LIVE paper trading'e EKLENMEDİ.** BIST + 13 sembol (2018-01-01 -> bugün):
  havuzlanmış 467 işlem, t-stat ≈ 2.89. Bu, eski tekil-hipotez eşiğini (2.0)
  geçer ama Harvey & Liu çoklu-test eşiğini (havuzda 3 strateji ->
  `multi_test_t_threshold(3)` = 3.0, bkz. `validation/significance.py`) GEÇMEZ.
  Parametreler Kart 1 metnindeki örnek değerler ((10,50)/(20,100)/(50,200)) —
  bilinçli olarak eşiği geçmek için ayarlanmadı (bu tam olarak M1'in önlemeye
  çalıştığı p-hacking olurdu). Strateji `python -m paper_trading.runner
  --strategies donchian ma_voting` ile isteğe bağlı/deneysel olarak
  çalıştırılabilir ama varsayılan aktif strateji listesinde DEĞİL.

## Zamanlama — günlük otomatik çalıştırma (Faz 4)

Kod içinde bir scheduler YOK (cron/Task Scheduler kurulmuyor) — `paper_trading.runner`'ı
her gün otomatik tetiklemek için üç seçenek var. **C seçeneği (GitHub Actions) bu
repoda gerçekten uygulandı** (`.github/workflows/paper_trading.yml`); A ve B
kendi makinenizde/sunucunuzda çalıştırmak isterseniz referans olarak duruyor.

### Seçenek A — cron (Linux/Mac)

```cron
# Her is gunu (Pzt-Cum) 19:00'da calistir (BIST kapanisindan, kripto icin
# gun sonuna yakin bir saat secildi - istege gore degistirin)
0 19 * * 1-5 cd /path/to/trading-system && /path/to/venv/bin/python -m paper_trading.runner --strategies donchian >> paper_trading/logs/cron.log 2>&1
```

### Seçenek B — Windows Task Scheduler

```powershell
# PowerShell'den bir kez calistirarak gorevi olusturur (gunluk 19:00)
$action = New-ScheduledTaskAction -Execute "python.exe" `
    -Argument "-m paper_trading.runner --strategies donchian" `
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
4. `python -m paper_trading.runner --strategies donchian` — dry-run **DEĞİL**,
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

- **Zorunlu secret gerekmiyor:** yfinance kimlik doğrulaması istemiyor,
  `GITHUB_TOKEN` GitHub tarafından her çalıştırmada otomatik sağlanıyor.
  Telegram bildirimleri için **opsiyonel** iki secret eklenebilir (aşağıda
  "Telegram bot bildirimleri" bölümüne bakın) — eklenmezse runner normal
  çalışmaya devam eder, sadece bildirim adımı sessizce atlanır.
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

### Telegram bot bildirimleri (opsiyonel)

Her gerçek GİRİŞ/ÇIKIŞ işleminde (`no_signal`/`hold`/`skip_*` durumlarında
DEĞİL — bkz. `paper_trading/runner.py`, `notifications/telegram.py`), ekip
Telegram grubuna otomatik bir mesaj gider: `🔴 GIRIS: EREGL.IS SHORT @ 38.66
| Stop: 41.72 (+7.9%) | 2026-08-07` gibi. Kurulum tamamen opsiyoneldir —
aşağıdaki secret'lar tanımlı değilse bildirim adımı sessizce atlanır, paper
trading normal çalışmaya devam eder.

**1. BotFather ile bot oluşturun**

1. Telegram'da [@BotFather](https://t.me/BotFather) ile bir sohbet açın.
2. `/newbot` komutunu gönderin, botunuza bir isim ve kullanıcı adı verin
   (kullanıcı adı `bot` ile bitmelidir, örn. `bbtrade_alerts_bot`).
3. BotFather size bir **token** verecek (örn.
   `123456789:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw`) — bu, aşağıdaki
   `TELEGRAM_BOT_TOKEN` secret'ı olacak. Kimseyle paylaşmayın.

**2. Botu gruba ekleyin**

1. Bildirimlerin gitmesini istediğiniz Telegram grubunu açın (yoksa yeni bir
   grup oluşturun).
2. Grup üyelerine botunuzu (kullanıcı adıyla arayıp) ekleyin.
3. Botun mesaj gönderebilmesi için grup ayarlarında kısıtlı değilse ek bir
   işlem gerekmez (varsayılan olarak üyeler mesaj gönderebilir).

**3. Grubun chat ID'sini bulun**

En kolay yöntem:

1. Bota (veya gruba) herhangi bir mesaj gönderin (örn. "test").
2. Tarayıcıda şu adresi açın (TOKEN'ı kendi bot token'ınızla değiştirin):
   `https://api.telegram.org/bot<TOKEN>/getUpdates`
3. Dönen JSON'da `"chat":{"id": -1001234567890, ...}` gibi bir alan
   arayın — gruplar için bu ID genellikle **negatif** bir sayıdır. Bu değer
   `TELEGRAM_CHAT_ID` secret'ı olacak.

**4. GitHub Secrets'a ekleyin**

1. Repo sayfasında **Settings → Secrets and variables → Actions** açın.
2. **New repository secret** ile ikisini ayrı ayrı ekleyin:
   - `TELEGRAM_BOT_TOKEN` — 3. adımda BotFather'dan aldığınız token.
   - `TELEGRAM_CHAT_ID` — 3. adımda bulduğunuz chat ID (negatifse `-` işaretiyle birlikte).
3. Kod içinde bu değerler **hiçbir yerde hardcode edilmez** — workflow bunları
   `secrets.TELEGRAM_BOT_TOKEN` / `secrets.TELEGRAM_CHAT_ID` üzerinden
   environment değişkeni olarak `paper_trading.runner`'a geçirir (bkz.
   `.github/workflows/paper_trading.yml`, "Paper trading calistir" adımı).

**5. Doğrulama**

Workflow'u elle tetikleyin (`workflow_dispatch` / "Run workflow") ve o gün
gerçek bir giriş/çıkış sinyali varsa Telegram grubunuzda mesajı görmelisiniz.
Sinyal yoksa (çoğu gün böyle olur — trend-takip stratejileri seyrek işlem
yapar) test etmek için `--date` parametresiyle geçmişte sinyal ürettiğiniz
bilinen bir tarihi yerel makinenizde `--dry-run` OLMADAN deneyebilirsiniz
(dikkat: bu gerçek state/log yazar).

Bağlantı/token hatası olursa (`notifications/telegram.py` içinde
loglanır) workflow **KIRMIZI OLMAZ** — runner çalışmaya devam eder, sadece
o bildirim atlanmış olur.

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

## GÖZCÜ — NASDAQ + BIST canlı izleme paneli

`gozcu/` + `dashboard/app/gozcu`, `paper_trading/`'den **tamamen bağımsız**
bir gözetleme katmanıdır: hiçbir sinyal/pozisyon üretmez, sadece dikkat
çeken piyasa hareketlerini (hacim patlaması, momentum mumu, aşırı oynaklık)
gösterir. Dashboard'da sağ üstteki **GÖZCÜ** bağlantısından veya doğrudan
`/gozcu` adresinden erişilir.

### Mimari kararı — neden her saniye güncellenmiyor

Yüzlerce sembolü (BIST + NASDAQ-100 evreni) her açık dashboard sekmesi kendi
başına tarasaydı hem yfinance/Yahoo rate-limit'ine hızla takılırdık hem de
gereksiz yük oluşurdu. Bunun yerine üç katmanlı bir ayrım var:

1. **`gozcu/scanner.py`** — GitHub Actions'ta periyodik çalışan, TEK
   kaynaktan (Actions runner'ı) yfinance'e giden bağımsız bir script. Tüm
   evreni tarar, metrik/skor/psikoloji/korelasyon hesaplar, sonucu tek bir
   JSON'a (`gozcu/data/snapshot.json`) atomik olarak yazar.
2. **`dashboard/app/api/gozcu/route.ts`** — **SADECE** bu snapshot.json'ı
   okur, kendi başına yfinance'e hiçbir zaman gitmez. Kaç kullanıcı sekmesi
   açarsa açsın tek kaynak taranmış olur.
3. **Client (`dashboard/lib/gozcu-context.tsx`)** — bu API'yi 45 saniyede
   bir polleyerek (gerçek veri ~5 dakikada bir yenilendiği için daha sık
   pollemek anlamsız) "son güncelleme: X dakika önce" bilgisini açıkça
   gösterir — sahte "her saniye canlı" hissi VERİLMEZ. Sekme arka plana
   alınırsa (`document.visibilitychange`) polling durur.

**Zamanlama / DST notu:** GitHub Actions cron'u UTC'dir ve yaz/kış saatini
kendisi kaydırmaz (TR'de DST yok, ABD/NASDAQ'ta var). Bunu cron'da iki ayrı
satırla yönetmek yerine, `.github/workflows/gozcu_scan.yml` GENİŞ bir UTC
penceresinde (`06:00-21:00`, hafta içi, 5 dakikada bir — GitHub Actions'ın
pratik minimum cron aralığı) tetiklenir; `gozcu/market_hours.py` (Python
`zoneinfo`, DST-farkında) HANGİ piyasa(lar)ın GERÇEKTEN açık olduğunu
kontrol edip sadece onları tarar. Piyasa kapalıyken boşuna yfinance'e
gidilmez; o piyasaya ait önceki (açık seanstan kalan) veri snapshot'ta
korunur, sadece "piyasa kapalı" bayrağı güncellenir — "piyasa kapalı" ile
"veri bayat/hatalı" durumu kullanıcıya karışmasın diye.

### Evrenler

- **BIST**: Wikipedia'nın Borsa İstanbul'a kote şirketleri listeleyen
  tablosundan (`List_of_companies_listed_on_the_Borsa_Istanbul`) dinamik
  çekilir — gerçek "BIST100 endeks bileşenleri" için `pd.read_html` ile
  parse edilebilir bir kaynak bulunamadığından, bu daha geniş (BIST100'den
  fazla) ama tek uygun kaynak kullanıldı. Çekme/parse başarısız olursa
  `config.BIST_TICKERS` (13 likit sembol) yedeğine düşülür. Wikipedia,
  User-Agent'sız istekleri 403 ile reddettiği için sayfa `requests` ile
  tarayıcı benzeri bir header'la çekilir (`gozcu/universe._fetch_tables`).
- **NASDAQ-100**: Wikipedia `List_of_NASDAQ-100_companies` sayfasından
  dinamik çekilir; başarısız olursa `config.GOZCU_NASDAQ100_FALLBACK`
  (~38 büyük isim) yedeğine düşülür.
- **BIST evren gürültüsü**: Wikipedia tablosundaki alfabetik BÖLÜM
  BAŞLIKLARI ("A", "B", ... "Z") bazen gerçek bir şirketin "Symbol" hücresi
  gibi parse ediliyor (canlı testte 18 tane tek harfli sahte sembol
  gözlemlendi: `A.IS`, `B.IS`, ...) — `gozcu/universe._clean_symbol`'e
  BIST için `min_length=3` filtresi eklendi (gerçek BIST sembolleri en az 3
  karakterdir; NASDAQ tarafı `min_length=1` kalır çünkü "ON" gibi geçerli
  2 harfli tikerlar var). Kalan hata oranı (~%31, 347 sembolden ~109'u)
  **rate-limit değil** — canlı loglarda `429`/`Too Many Requests`/timeout
  sinyali SIFIR, tamamı `"possibly delisted; no price data found"`: bu,
  BIST100'ün çok ötesine geçen bilinçli geniş evren tercihinin doğal
  sonucu (küçük/durgun/fiilen işlem görmeyen ama Wikipedia'da hâlâ listeli
  şirketler). Bu yüzden istekler arasına yapay bir bekleme EKLENMEDİ —
  gereksiz yavaşlatma olurdu, sorunu çözmezdi.

### Metrikler, skor, psikoloji, korelasyon

`gozcu/metrics.py` her sembol için günlük/haftalık %değişim, RVOL, hacim
Z-skoru, momentum mumu (mevcut `signals.donchian.compute_breakout_filters`
yeniden kullanılır), VWAP + eğimi, 52 haftalık zirve/dip yakınlığı ve ATR
yüzdelik dilimini (`backtest.engine.compute_atr` yeniden kullanılır) hesaplar.
`gozcu/scoring.py` bunları ağırlıklı bir "Dikkat Skoru"na birleştirir
(ağırlıklar `config.py`'de `GOZCU_SCORE_WEIGHT_*`) — **bu bir al-sat
tavsiyesi DEĞİLDİR**, sadece "en çok hareket eden" sıralamasıdır.
`gozcu/psychology.py` breadth (% pozitif kapanan) bazlı bir 0-100 gauge
üretir (oynaklık rejimi bilinçli olarak AYRI bir etiket olarak gösterilir,
tek sayıya karıştırılmaz). `gozcu/correlation.py` evrenin referans endekse
(BIST: `XU100.IS`/`^XU100`, NASDAQ: `QQQ`) göre ortalama korelasyonunu
hesaplar (tam NxN matris yerine, performans için).

### RVOL yaklaşıklığı (bilinçli basitleştirme)

"Son 20 günün aynı saatteki ortalama hacmi" için her sembolde 20 gün geriye
dönük 5 dakikalık bar çekmek, yüzlerce sembolde Actions'ın ~5 dakikalık
tarama bütçesini aşar. Bunun yerine `gozcu/metrics.relative_volume()`,
20 günlük ortalama GÜNLÜK hacmi seans içinde GEÇEN süre oranıyla ölçekler —
aynı niyeti ("bugünkü hacim normale kıyasla ne kadar öne çıktı") çok daha
ucuz bir şekilde yaklaşıklar.

**Seans-ilerleme oranı SEMBOL BAŞINA, o sembolün KENDİ son gün-içi barının
zaman damgasından hesaplanır** (`gozcu/market_hours.py`'deki
`bist_elapsed_fraction`/`nasdaq_elapsed_fraction`, `gozcu/scanner.py` içinde
her sembolün son barına ayrı ayrı uygulanır) — tek bir "şu an" (wall-clock)
değeri TÜM piyasa için kullanılmaz. Bu bilinçli bir tasarım: piyasa
kapalıyken gün-içi veri bir önceki TAMAMLANMIŞ seansa ait olur; "şu an"ı o
tamamlanmış seansla kıyaslamak anlamsız/yanlış bir RVOL üretirdi (canlı
testte NASDAQ kapalıyken RVOL sütununun tamamen boş görünmesine yol açan kök
neden buydu — düzeltilmiş halde RVOL, kapalı bir piyasa için "son seansın
kapanışındaki RVOL"nu doğru şekilde gösterir). Aynı nedenle
`gozcu/scanner.py: scan_market()`'ın döndürdüğü `market_open` alanı da artık
taramanın NEDEN tetiklendiğinden (gerçek açık saat mi, `--force` mi)
BAĞIMSIZ olarak piyasanın gerçek anlık durumunu yansıtır.

### Telegram uyarısı (opsiyonel)

Bir sembolün dikkat skoru `config.GOZCU_ALERT_SCORE_THRESHOLD` eşiğini
geçerse, **o sembol için günde bir kez**, mevcut `notifications.telegram`
ile "[GÖZCÜ] ... bu bir AL sinyali DEĞİLDİR" formatında bilgi mesajı
gönderilir. İdempotency, paper trading'in `stop_warnings` tablosuyla aynı
mantıkla (`gozcu/alerts.py`) ama **ayrı** bir dosyada (`gozcu/data/alert_state.json`)
tutulur — paper trading `state.db`'sine dokunulmaz.

### Kurulum / yapman gerekenler

- **Yeni secret gerekmiyor** — `TELEGRAM_BOT_TOKEN`/`TELEGRAM_CHAT_ID` aynı
  mevcut GitHub Secrets'lar yeniden kullanılıyor (bkz. yukarıdaki "Telegram
  bot nasıl kurulur").
- GitHub Actions'ta **Read and write permissions** zaten `paper_trading.yml`
  için açık olmalı (aynı repo, `.github/workflows/gozcu_scan.yml` de aynı
  izni kullanır).
- Cron zamanlaması (`*/5 6-21 * * 1-5`, UTC) onayınla aktif; farklı bir
  pencere/aralık istersen `.github/workflows/gozcu_scan.yml`'deki `cron:`
  satırını değiştirmen yeterli.
- Vercel bu repoya bağlıysa her `gozcu_scan.yml` commit'i otomatik yeni bir
  deploy tetikler (mevcut `paper_trading.yml` deseniyle aynı) — piyasa açık
  saatlerinde günde onlarca-yüzlerce deploy anlamına gelir; Hobby planda
  genelde sorun değildir ama build-minutes kotasını tüketebilir.

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
- **Çoklu-sembol equity ilişkisi (M3'te ele alındı):** Tüm semboller TEK bir
  paylaşılan hesap equity'sinden %1 risk alıyor; artık `risk/portfolio.py` +
  `risk/correlation_clusters.py` günün TÜM yeni giriş adaylarını, mevcut açık
  pozisyonların tükettiği brüt kaldıraç bütçesi ve getiri-korelasyonu
  kümelerine göre kısıtlayarak açıyor (bkz. yukarıdaki "Evren" notu). Bilinen
  sınır: mevcut açık pozisyonların küme maruziyeti, YENİ adaylara karşı ayrı
  ayrı (güne özel değil, kalıcı olarak) sınırlanmıyor — sadece toplam brüt
  kaldıraç bütçesi düşülüyor; kümesel çapraz-gün takibi ileride genişletilebilir.
  Korelasyon eşiği (0.6) sabit değil — bkz. `config.py`
  `RISK_CORRELATION_CLUSTER_THRESHOLD` yorumu (birkaç hafta veri sonrası
  0.5'e çekilmesi değerlendirilecek).
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
- `risk/position_sizing.py` (Kelly) — Faz 3.5 SS5'te tanımlanan, henüz
  kodlanmamış modül (`risk/portfolio.py` M2/M3'te kodlanıp paper trading'e
  bağlandı, bkz. yukarıdaki "Evren" ve "Çoklu-sembol equity ilişkisi" notları).
- **Kart 1 (MA oylama):** kodlandı (`signals/ma_voting.py`, M4) ama LIVE paper
  trading'e eklenmedi — çoklu-test anlamlılık eşiğini geçemedi (bkz. yukarıdaki
  "Doğrulama durumu"). Kart 3 (Bollinger/Keltner fade) kodlanma sırasında (bkz.
  proje kökündeki mimari genişletme planı). Kart 2 (VWAP mean reversion,
  gün-içi) daha düşük öncelikli, henüz planlanmadı.
