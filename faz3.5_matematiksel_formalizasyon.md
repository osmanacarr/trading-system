# Faz 3.5 — Stratejilerin Matematiksel Formalizasyonu

> Kapsam: S&P500'ü şimdilik askıya aldık. Bu doküman **Donchian Breakout** (ana kazanan) ve **Price Action Breakout** (BIST'te ikinci en iyi) stratejilerini kaynaklarınızdaki kantitatif çerçeveye (zaman serisi tahmincisi, doğrusal indikatör, Sharpe-bazlı istatistiksel anlamlılık) göre biçimselleştiriyor. Amaç: "işe yarıyor gibi görünüyor"dan → "neden işe yaradığını matematiksel olarak ifade edebiliyoruz"a geçmek, sonra bunu Claude Code'da kodlanabilir bir modüle dönüştürmek.

---

## 1. Genel Çerçeve — Pozisyon Fonksiyonu ve Tahminci

Kaynaklarınızdaki kantitatif yaklaşımı takip ediyoruz: her strateji bir **pozisyon fonksiyonu** $b_t \in \{-1, 0, +1\}$ (yön) ve bir **büyüklük çarpanı** $s_t \in [0,1]$ olarak yazılabilir. Zamanı $t$ anındaki getiri:

$$r_t = b_t \cdot s_t \cdot \frac{P_{t+1} - P_t}{P_t}$$

Bir stratejinin "kantitatif" sayılması, $b_t$'nin gelişigüzel bir kural değil, **fiyat sürecinin bir tahmincisinden** (forecaster) türetilmiş olmasına bağlı — kaynaklarınızda MA crossover'ın bunu doğrusal zaman serisi tahmincisiyle aynı forma sahip olduğu için (ağırlıklı gecikme toplamı) kantitatif sayıldığı anlatılıyor. Donchian da benzer bir mantıkla savunulabilir: $N$-günlük ekstremum kırılımı, fiyatın **rejim değişikliği** sinyalidir — resmi olarak bir "değişim noktası testi" (change-point detection) yaklaşımının basit bir versiyonu.

---

## 2. Donchian Breakout — Formal Tanım

### 2.1 Sinyal

$$U_t = \max(H_{t-n}, \dots, H_{t-1}), \quad L_t = \min(L_{t-n}, \dots, L_{t-1})$$

$$b_t = \begin{cases} +1 & \text{if } C_t > U_t \text{ ve hacim/gövde filtreleri sağlanıyorsa} \\ -1 & \text{if } C_t < L_t \text{ ve filtreler sağlanıyorsa} \\ b_{t-1} & \text{aksi halde (pozisyon korunur)} \end{cases}$$

Çıkış (trailing): pozisyon $L^{exit}_t = \min(L_{t-m}, \dots, L_{t-1})$ seviyesine geri çekilene kadar korunur ($m < n$, bizim uygulamamızda $n=20, m=10$).

### 2.2 Neden İşe Yarayabilir — Matematiksel Gerekçe

Donchian, fiyatın $[L_t, U_t]$ aralığından **çıkışını** bir bilgi sinyali olarak yorumlar. Fiyat sürecini $P_t = \mu_t + \epsilon_t$ (yerel trend + gürültü) şeklinde düşünürsek, kırılım $C_t > U_t$, $\mu_t$'nin son $n$ barlık aralığın üstüne çıktığına dair bir **istatistiksel sinyal**dir — gürültü genliği $\sigma$ sabitken, kanal genişliği $n$ ile orantılı arttığı için, kırılımın "gerçek" bir rejim değişikliği olma olasılığı $n$ büyüdükçe artar (ama işlem sıklığı azalır — klasik hassasiyet/kesinlik dengesi, precision-recall trade-off).

### 2.3 Pozisyon Büyüklüğü

$$\text{size}_t = \frac{E_t \cdot \rho}{|C_t - \text{stop}_t|}, \quad \text{stop}_t = C_t - k \cdot \text{ATR}_{14}(t)$$

burada $E_t$ = güncel sermaye, $\rho = 0.01$ (risk fraksiyonu), $k=2$. Bu, **volatilite-bazlı pozisyon boyutlandırma** — ATR yüksekken pozisyon küçülür, düşükken büyür (kaynaklarınızdaki "volatility-based sizing" ile birebir örtüşüyor).

---

## 3. Price Action Breakout — Formal Tanım

$$b_t = \mathbb{1}\left[C_t > \max(H_{t-n}, \dots, H_{t-1})\right] \cdot \mathbb{1}\left[|C_t - O_t| \geq \beta \cdot \overline{|C-O|}_{5}\right] \cdot \mathbb{1}\left[V_t \geq \gamma \cdot \overline{V}_{20}\right]$$

$\beta=2, \gamma=1.5$. Donchian'dan farkı: (i) **sabit R/R çıkışı** ($T_t = C_t + 2\cdot(C_t - \text{stop}_t)$, trailing değil), (ii) ek gövde/hacim filtresi — bu, kırılımın "gerçekliğini" (gerçek katılım var mı, yoksa düşük hacimli sahte kırılım mı) doğrudan teste sokuyor. Matematiksel olarak bu, sinyalin **koşullu olasılığını** iyileştirme girişimi: $P(\text{devam} \mid \text{kırılım}, V_t \geq \gamma\bar{V}) > P(\text{devam} \mid \text{kırılım})$ varsayımı.

---

## 4. İstatistiksel Anlamlılık — Backtest'i Gerçekten Sorgulamak

Kaynaklarınızdaki temel uyarı: **düşük Sharpe = düşük istatistiksel anlamlılık**, üretilen getiri şans olabilir. Formalize edelim.

### 4.1 Ortalama R'nin Standart Hatası

$n$ işlemlik bir örneklemde, R-katları $\{R_1, \dots, R_n\}$ için:

$$\text{SE}(\bar{R}) = \frac{\sigma_R}{\sqrt{n}}, \qquad t = \frac{\bar{R}}{\text{SE}(\bar{R})} = \frac{\bar{R}\sqrt{n}}{\sigma_R}$$

**Kural:** hata payı $n$'in kareköküyle küçülür — 4 kat daha fazla işlem, hatayı yalnızca yarıya indirir. Bu yüzden 5-10 işlemlik "harika expectancy" gösteren sonuçlara (MA Crossover'ın ilk halinde gördüğümüz gibi) güvenilmemeli.

**Uygulama — Donchian BIST örneği:** $n \approx 45$ işlem/sembol, $\bar{R} \approx 0.4$–$0.5$. R-katlarının standart sapması tipik olarak $\sigma_R \approx 1$–$1.3$ civarında olur (trend-takip dağılımlarında sağa çarpık, çoğu -1'e yakın kayıp + birkaç büyük kazanç). Bu varsayımla:

$$t \approx \frac{0.45 \times \sqrt{45}}{1.15} \approx 2.6$$

$t > 2$ genellikle **%95 güven** eşiği sayılır — yani BIST'teki Donchian sonucu şans eseri olma ihtimali düşük görünüyor (ama bu tahmini bir hesap; **gerçek $\sigma_R$'yi trade log'larınızdan hesaplamalıyız** — bir sonraki adım olarak öneriyorum).

### 4.2 Sharpe Oranı ve Zaman Ufku

Kaynaklarınızdaki formül: bir stratejinin getirisinin pozitif olduğuna belirli bir güvenle "garanti" verebileceğiniz süre yaklaşık $1/\text{Sharpe}^2$ yıldır. Donchian BIST ortalama Sharpe'ı ~0.5-0.6 civarında çıktı → $1/0.55^2 \approx 3.3$ yıl. Yani stratejinin gerçekten çalıştığından emin olmak için (istatistiksel olarak) yaklaşık 3+ yıllık canlı/paper-trade verisi gerekiyor — bu da Faz 4'ün neden kısa sürede bitmeyeceğinin matematiksel gerekçesi.

### 4.3 Walk-Forward'ın Bu Çerçevedeki Yeri

Yaptığımız train/test ayrımı, kaynaklarınızda geçen **"rolling walk-forward"**un basit bir versiyonu (biz "anchored" değil, tek bir sabit kesim kullandık). İleri seviye: parametreleri ($n=20$, $k=2$ gibi) sadece train'de optimize edip, her seferinde bir sonraki periyoda kaydırarak test etmek (gerçek rolling walk-forward) — bunu Claude Code fazında otomatikleştirebiliriz.

---

## 5. Pozisyon Boyutlandırma — Kelly Kriteri ile Karşılaştırma

Kelly formülü: $f^* = W - \frac{1-W}{R}$, $W$=kazanma oranı, $R$=ortalama kazanç/ortalama kayıp oranı.

**Donchian BIST için yaklaşık:** $W \approx 0.40$, kayıplar ortalama $\approx -1R$'ye yakın (stop'a takılanlar), kazançlar trend sürdükçe büyüyebiliyor (median negatif ama mean pozitif → sağa çarpık dağılım, R belirsiz/yüksek). Bu durumda klasik sabit-R/R Kelly formülü doğrudan uygulanamaz (R sabit değil) — bunun yerine **Kelly'nin genel beklenen-log-getiri versiyonu** kullanılmalı:

$$f^* = \arg\max_f \, \mathbb{E}[\log(1 + f \cdot R)]$$

Bu, trade log'unuzdaki gerçek R dağılımı üzerinden sayısal olarak optimize edilir (kapalı form yok). **Önemli:** kaynaklarınızda da vurgulandığı gibi, tam Kelly çok agresiftir ve tahmin hatasına karşı kırılgandır — biz zaten sabit %1 risk (yaklaşık **çeyrek-Kelly veya daha az**) kullanıyoruz, bu muhafazakâr ve doğru bir seçim. Bunu değiştirmeyi önermiyorum; sadece neden doğru olduğunu formalize ediyoruz.

---

## 6. Portföy Seviyesi — Çoklu Sembol/Strateji Kombinasyonu

Kaynaklarınızdaki Markowitz/faktör-risk mantığı: $N$ sembolün getirileri $r^{(1)}, \dots, r^{(N)}$ ise, portföy varyansı:

$$\sigma_p^2 = \sum_i w_i^2 \sigma_i^2 + \sum_{i \neq j} w_i w_j \sigma_i \sigma_j \rho_{ij}$$

BIST'teki 13 "tutarlı" sembolün çoğu benzer makro faktörlere (TL, yerel faiz, BIST endeksi) maruz — yani $\rho_{ij}$ muhtemelen yüksek. Bu, çeşitlendirme faydasının göründüğünden az olabileceği anlamına gelir. **Claude Code fazında eklenecek:** sembol-sembol korelasyon matrisini gerçek veriden hesaplayıp, portföy risk bütçesini (kaynaklarınızdaki "risk constrained portfolio" kavramı) buna göre ayarlayan bir modül.

---

## 7. Ürüne Geçiş — Bu Matematiğin Kod Modüllerine Dönüşümü

Bu formaliazasyon, Claude Code'da şu somut modüllere karşılık gelecek:

| Matematik | Kod Modülü |
|---|---|
| §2-3 sinyal tanımları | `signals/donchian.py`, `signals/price_action.py` — zaten Colab'da yazıldı, üretime taşınacak |
| §4 istatistiksel anlamlılık | `validation/significance.py` — her yeni backtest sonrası otomatik t-stat/Sharpe-CI hesaplayan modül |
| §5 Kelly/pozisyon boyutu | `risk/position_sizing.py` — mevcut sabit %1 kuralın yanına, opsiyonel "fractional Kelly önerisi" gösteren bir yardımcı |
| §6 portföy/korelasyon | `risk/portfolio.py` — strateji ligi tablosundaki sembolleri korelasyona göre gruplandırıp risk bütçesi öneren modül |

Bu tablo, Faz 1'deki mimari planın "Araştırma Motoru" katmanının somutlaşmış hali. Bir sonraki adımda Claude Code'a geçip bu modülleri gerçek bir Python paketi olarak (Colab notebook'larından ziyade, tekrar kullanılabilir, test edilebilir kod) inşa etmeye başlayabiliriz — sonra bunun üzerine paper trading motoru ve dashboard'u koyarız.

⚠️ Bu doküman istatistiksel çerçeve sunar, getiri garantisi vermez; §4'teki hesaplamalar tahmini varsayımlarla yapıldı, kesin rakamlar için trade log'larınız üzerinde gerçek hesaplama gerekir.
