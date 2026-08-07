# Faz 2 — Strateji Kural Kartları

Her kart, Colab'da doğrudan koda dökülebilecek netlikte yazıldı: kesin sayısal kurallar, belirsiz yorum yok. Parametreler backtest'te taranacak (grid search) — burada verilen sayılar başlangıç noktası, "doğru" değerler değil.

Ortak varsayımlar (tüm stratejiler için):
- **Risk/işlem:** Hesabın %1'i (backtest'te %0.5–2 aralığı taranacak)
- **Min Risk/Ödül:** 1:2
- **Komisyon/slipaj:** Backtest'te gerçekçi maliyet varsayımı eklenecek (örn. %0.05 komisyon + 1 tick slipaj) — kaynaklarınızdaki "gross expectancy costs'u zar zor karşılıyor" uyarısı ciddiye alınacak
- **Pozisyon büyüklüğü:** (Hesap riski) / (Giriş − Stop mesafesi)

---

## Kart 1 — Çoklu Zaman Dilimi MA Crossover (Oylama Sistemi)

**Tipi:** Trend takibi / momentum
**Zaman dilimi:** Günlük (backtest sonrası 4H'de de denenecek)

**Göstergeler:** 3 farklı hızlı/yavaş MA çifti, örn: (10,50), (20,100), (50,200)

**Sinyal mantığı:**
- Her çift için: `hızlı_MA > yavaş_MA` → +1 oy (boğa), aksi halde 0
- Toplam oy = 0, 1, 2 veya 3
- Pozisyon büyüklüğü oy sayısıyla orantılı (3 oy = tam pozisyon, 1 oy = 1/3 pozisyon)

**Giriş:** Oy sayısı önceki barda daha düşükken bu barda artınca (yeni crossover oluşunca)
**Çıkış:** Oy sayısı 0'a düşünce (tüm MA'lar altına geçince) veya stop/hedef vurunca
**Stop-loss:** Son 20 barın en düşüğü / ATR(14) × 2
**Not:** Kaynaklarda bu strateji "matematiksel olarak gerekçeli" (zaman serisi tahmincisi ile aynı form) olarak işaretleniyor — teknik analiz yorumundan bağımsız, kantitatif bir temeli var.

---

## Kart 2 — VWAP Mean Reversion (Bant Dokunuşu + Onay)

**Tipi:** Ortalamaya dönüş
**Zaman dilimi:** 5m–1H (gün içi)
**Koşul:** Piyasa yatay/range'de olmalı (VWAP eğimi düşük) — trend güçlüyse bu strateji devre dışı bırakılmalı

**Göstergeler:** Günlük VWAP + 2. standart sapma bandı (üst/alt)

**Giriş (long örneği, short simetrik):**
1. Fiyat 2. bandın altına dokunur/kısa süreliğine kırar
2. Dönüş mumu formasyonu oluşur (bullish engulfing / hammer / morning star)
3. Aynı anda VWAP kendisi düz/yatay seyrediyor (son 20 barlık VWAP eğimi ~0'a yakın)

Üçü birden sağlanınca giriş → **çoklu sinyal çakışması kuralı** (kaynaklardaki "3 bullish şey aynı anda" prensibi)

**Stop-loss:** Dönüş mumunun dip noktasının hemen altı
**Take-profit:** VWAP orta çizgisi (ilk hedef) → kısmi kâr al, kalan pozisyon karşı banda kadar taşınır
**Filtre:** Sadece VWAP eğimi düşükken aktif (trend günlerinde bu strateji otomatik kapanmalı)

---

## Kart 3 — Bollinger / Keltner Fade

**Tipi:** Ortalamaya dönüş (Kart 2'ye benzer ama günlük/swing için)
**Zaman dilimi:** 1H–Günlük

**Göstergeler:** Bollinger Bands (20, 2 std) VEYA Keltner Channel (20 EMA, ATR×2) — ikisi ayrı ayrı backtest edilip karşılaştırılacak (Keltner'in ATR bazlı olması yüksek volatilite dönemlerinde daha stabil olabilir)

**Giriş:** Fiyat üst/alt banda dokunur + RSI(14) aşırı alım(>70)/aşırı satım(<30) bölgesinde + mum onayı
**Stop-loss:** Bandın dışına ATR×0.5 mesafe
**Take-profit:** Orta bant (basit ortalama)
**Filtre:** ADX(14) < 20 (trend gücü düşükken aktif — güçlü trendde fade stratejisi devre dışı)

---

## Kart 4 — Donchian Channel Breakout

**Tipi:** Kırılım / trend başlangıcı
**Zaman dilimi:** Günlük

**Göstergeler:** Donchian Channel (N=20 gün üst/alt, N=10 çıkış kanalı — Turtle sistemine benzer çift kanal mantığı)

**Giriş:** Kapanış, son 20 günün en yükseğini kırınca long / en düşüğünü kırınca short
**Çıkış:** Kapanış, son 10 günün tersi ucunu kırınca (trailing exit — sabit hedef yok, trend sürdükçe pozisyonda kal)
**Stop-loss:** Giriş fiyatından ATR(20)×2 uzaklıkta (ilk koruma), sonra trailing exit devreye girer
**Not:** Kaynaklarda geçen "sahte kırılımlardan kaçınmak için mum büyüklüğü ve hacim onayı" filtresi eklenecek: kırılım mumu, önceki 5 mumun ortalama boyutunun en az 1.5 katı VE hacim 20 günlük ortalamanın üzerinde olmalı

---

## Kart 5 — Price Action Breakout + Hacim Onayı (Pullback Modeli)

**Tipi:** Trend devamı / kırılım
**Zaman dilimi:** 1H–Günlük

**Kurulum:** Önceden tanımlı bir yapı (üçgen, destek/direnç, önceki swing high/low)

**Giriş — İki model, her ikisi ayrı ayrı test edilecek:**
- **Model A (Pullback girişi):** Kırılım sonrası fiyat kırılan seviyeye geri çekilir, o seviyede güçlü bir onay mumu (momentum candle) oluşunca gir
- **Model B (Kırılım girişi):** Fiyat direnci güçlü hacimle ve büyük gövdeli mumla (önceki mumların ort. boyutunun ≥2 katı) kırınca doğrudan gir

**Stop-loss:** Pullback'in/kırılımın en düşük noktasının altı
**Take-profit:** Sabit R/R (2:1 başlangıç) VEYA "measured move" (önceki hareketin boyutu kırılım noktasından itibaren yukarı taşınır) — ikisi karşılaştırılacak
**Filtre:** FOMO'yu önlemek için kesin kurulum kriterleri karşılanmadan giriş yasak (bu bir kod kısıtı olarak da uygulanacak — sistemde "kurulum yok" durumunda sinyal üretilmeyecek)

---

## Backtest Sırası (Faz 3 için öneri)

1. **Kart 4 (Donchian)** ile başlıyorum — kuralları en net, en az sübjektif yorum gerektiren strateji, ilk Colab notebook'u için ideal
2. Ardından Kart 1 (MA oylama) — benzer şekilde tamamen kural bazlı, kodlaması kolay
3. Kart 2/3 (mean reversion) ve Kart 5 (price action) — mum formasyonu tanıma gerektirdiği için biraz daha fazla kod işi, sıradaki adım

## Sonraki Adım

Colab notebook'unu hazırlayıp **Donchian Breakout (Kart 4)** ile ilk backtest'i başlatabilirim: veri çekme (yfinance/ccxt), gösterge hesaplama, sinyal üretimi, işlem simülasyonu, ve sonuç metrikleri (win rate, expectancy, max DD, equity curve grafiği). Hangi enstrüman ve tarih aralığıyla başlamak istersiniz (örn. BTC/USDT 2019–2025 günlük, ya da S&P 500 hisseleri)?
