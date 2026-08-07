# Paper Trading Terminal (dashboard/)

Donchian Breakout paper trading sisteminin canli izleme paneli. Next.js
(App Router, TypeScript, Tailwind v4) ile yazildi; veri kaynagi olarak
**yalnizca** repo kokundeki kalici dosyalari okur (agdan canli fiyat cekmez):

| Kaynak | Ne icin |
|---|---|
| `../paper_trading/logs/trades.jsonl` | islem gecmisi |
| `../paper_trading/logs/equity.jsonl` | equity zaman serisi |
| `../paper_trading/logs/summary.json` | ozet (son calisma, toplam equity, acik pozisyon) |
| `../paper_trading/data/state.db` | acik pozisyonlar (SQLite, **salt-okunur**) |

Bu dosyalar ilk gercek trade oncesi bos/mevcut degildir - her panel bu
durumu zarif bir "yetersiz veri / sinyal bekleniyor" mesajiyla karsilar,
hicbir zaman crash etmez.

## Yerel calistirma

```bash
cd dashboard
npm install
npm run dev
```

Tarayicida [http://localhost:3000](http://localhost:3000) adresini acin.
`lib/paths.ts`, `process.cwd()`'nin bir ust dizinini (yani repo kokunu)
baz alir - bu yuzden `npm run dev` **mutlaka `dashboard/` klasoru
icinden** calistirilmalidir (yukaridaki gibi).

Gercek veri gormek icin repo kokunde bir kez paper trading calistirin:

```bash
# repo kokunde (dashboard/ DEGIL)
python -m paper_trading.runner --strategy donchian
```

## Sorun giderme: "Sistem gunlugu bir trade gosteriyor ama acik pozisyonlar 0 diyor"

Bu, `/api/positions`'un state.db'yi okuyamadigi (native modul/bundling
sorunu) halde eskiden sessizce `{"positions":[]}` donmesinden kaynaklanan
bilinen bir hataydi - `state.db` OKUNAMADIGINDA da, gercekten pozisyon
YOKKEN de ayni bos sonuc donuyordu. Artik `readOpenPositions()` (bkz.
`lib/readers.ts`) bu iki durumu ayirt ediyor: dosya hic yoksa (mesru "ilk
trade oncesi") `error: null`, dosya var ama acilamiyorsa `error: "<mesaj>"`
doner. Ust cubukta "⚠ pozisyon verisi okunamadi" rozeti ve Acik Pozisyonlar
panelinde ayri bir hata mesaji gorurseniz:

1. `/api/positions`'u dogrudan acip `error` alanini okuyun - gercek native
   modul hata mesaji orada.
2. Vercel Project Settings → Functions'ta ilgili fonksiyonun loglarini
   kontrol edin (`console.error("[readOpenPositions] ...")` orada gorunur).
3. `next.config.ts`'teki `outputFileTracingIncludes` altinda
   `node_modules/better-sqlite3/prebuilds/**/*` satirinin hala orada
   oldugunu dogrulayin - better-sqlite3'un platform-bazli dinamik require'i
   @vercel/nft'in statik izlemesini bazen atlatiyor, bu satir bunun icin.

## Bilinen sinirlamalar (bilincli tasarim kararlari)

- **Guncel fiyat / anlik P&L (acik pozisyonlar tablosunda)**: bu surum
  hicbir canli fiyat akisi cagirmiyor (yalnizca kalici dosyalar okunuyor);
  bu yuzden acik pozisyonlar icin "guncel fiyat" ve "anlik P&L" sutunlari
  `n/a` gosterir. Giris fiyati, stop mesafesi ve pozisyon suresi dogru
  ve kalici veriden geliyor.
- **Canli-vs-backtest equity sapma egrisi**: repoda makine-okunur
  (JSON/CSV) bir backtest ciktisi commit'lenmedigi ve BIST+kripto
  birlesik bir `expectancy_R` sayisi hic yayinlanmadigi icin bu egri
  varsayilan olarak "referans backtest verisi eksik" mesaji gosterir.
  `lib/backtestBaseline.ts` dosyasina `expectancyRPerTrade` degeri
  eklendiginde panel otomatik olarak dolar (win-rate/Sharpe karsilastirmasi
  zaten faz3.5 dokumanindaki degerlerle simdiden calisiyor).
- **Veri butunlugu paneli**: `data/adjust.py`'deki `adjust_jumps()`
  sicrama duzeltmeleri su an hicbir yere kalici olarak loglanmiyor
  (yalnizca bellek icinde uygulaniyor). Panel bu yuzden yapisi hazir
  ama "duzeltme kaydi yok" gosteriyor; `runner.py`'ye bir
  `data_integrity.jsonl` logu eklenirse otomatik aktif olur.
- **BIST/Kripto ayri "son calisma" durumu**: `paper_trading/runner.py`
  tek bir job'da HER IKI evreni de isler (idempotent), bu yuzden
  `summary.json` piyasa bazinda ayri bir zaman damgasi tutmuyor. Ust
  cubuktaki iki nokta ayni `last_updated` degerini yansitir.

## Vercel'e deploy

Bu proje bir **monorepo alt klasoru**dur (`dashboard/`), ve API
route'lari kendi klasorunun DISINDAKI (`../paper_trading/`) dosyalari
okuyor. Bu yuzden standart "tek repo = tek proje" akisina iki ek adim
gerekiyor - asagidaki sira atlanirsa API route'lari prod'da bos veri
donmez, `ENOENT`/500 hatasi verir.

1. **GitHub reposunu Vercel'e bagla**: [vercel.com/new](https://vercel.com/new) →
   `osmanacarr/trading-system` reposunu sec → Import.
2. **Root Directory**: proje ayarlarinda **Root Directory** alanina
   `dashboard` yazin (Vercel bunu otomatik algilamayabilir, elle
   girin/degistirin).
3. **Monorepo disi dosyalari dahil et**: ayni ekranda (veya import
   sonrasi Project Settings → General → Build & Development Settings)
   **"Include files outside the root directory in the Build Step"**
   secenegini **acin**. Bu, `../paper_trading/` dosyalarinin build'e
   dahil edilmesi icin sarttir (next.config.ts'teki
   `outputFileTracingRoot`/`outputFileTracingIncludes` bu ayarla
   BIRLIKTE calisir, tek basina yeterli degildir).
4. Framework Preset otomatik "Next.js" olarak algilanir; Build/Install
   komutlarini degistirmenize gerek yok.
5. **Deploy**'a tiklayin. Ilk build'de `paper_trading/logs/` ve
   `paper_trading/data/` henuz repo'da bos/yoksa (ilk trade oncesi),
   dashboard yine de acilir - tum panellerin bos-durum haline dustugunu
   goreceksiniz.
6. **Otomatik yeniden deploy**: `.github/workflows/paper_trading.yml`
   her gunluk calistirmadan sonra `state.db` ve `logs/` degisikliklerini
   repoya commit+push eder (bkz. workflow dosyasi). Vercel'in GitHub
   entegrasyonu `main` branch'teki her push'ta otomatik yeniden build
   tetikler - yani paper trading her calistiginda dashboard bir sonraki
   build'de guncel veriyi gosterir (gercek zamanli degil, "gunde birkaç
   kez otomatik yenilenen" bir terminal).

### Ilk deploy sonrasi hizli dogrulama

- Deploy linkini acin, ust cubuktaki "son calisma" alaninin `henuz
  calismadi` gosterdigini (eger hic paper trading calismadiysa) veya
  gercek bir tarih gosterdigini kontrol edin.
- `/api/dashboard` adresini dogrudan acip JSON donduğunu (500 hatasi
  ALMADIGINI) dogrulayin - bu, adim 2-3'un dogru yapildiginin en hizli
  kanitidir.
