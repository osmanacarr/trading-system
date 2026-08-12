// config.py ile birebir ayni (paper_trading sanal sermaye baslangici)
export const PAPER_TRADING_INITIAL_CAPITAL = 10_000.0;

// config.py GOZCU_DATA_STALENESS_ESTIMATE_MINUTES ile birebir ayni - turetme
// icin config.py'deki yorumu oku. Harici tetikleyici (cron-job.org) birkac
// gun calistiktan SONRA GERCEK araliklar olculup bu sayi GEREKIRSE
// guncellenmelidir (bkz. research/gozcu_timing.py) - bu sabit bir garanti
// DEGIL, yeniden kalibre edilecek bir tahmindir.
export const GOZCU_DATA_STALENESS_ESTIMATE_MINUTES = 6;

// config.py USER_CAN_SHORT ile birebir ayni: kullanicinin GERCEK hesabinda
// SHORT (acik satis) yapip yapamadigi - BIST'te ozel marjin izni gerekir,
// kullanicida su an YOK. Bu SADECE gorsel bir bayrak (asagidaki
// "uygulanabilirlik" rozetleri icin) - paper trading motoru SHORT
// sinyalleri uretmeye/test etmeye DEVAM EDER, bu deger bunu etkilemez.
// Kullanici ileride acik satis marjinli bir hesap acarsa iki tarafta da
// (config.py + burada) true yapilmali.
export const USER_CAN_SHORT = false;

// config.py RISK_PER_TRADE ile birebir ayni (hesabin %1'i, SS2.3 formulu:
// size = E_t*rho / |giris-stop|) - "Bugunun Islem Formu" panelinin (bkz.
// dashboard/components/ActionSheetPanel.tsx) kac adet alinmasi gerektigini
// GERCEK sermaye (yalnizca bu tarayicida, localStorage) ile hesaplayabilmesi
// icin client-side'da mirror'lanir - sunucu bu hesabi YAPMAZ/YAPAMAZ (bkz.
// paper_trading/action_sheet.py modul docstring'i, gizlilik kisiti).
export const RISK_PER_TRADE = 0.01;

export function directionApplicability(direction: 1 | -1): { label: string; hint: string; applicable: boolean } {
  if (direction === 1) {
    return { label: "UYGULANABILIR", hint: "Gercek hesabinizdan LONG olarak uygulayabilirsiniz", applicable: true };
  }
  return USER_CAN_SHORT
    ? { label: "UYGULANABILIR", hint: "Acik satis hesabiniz var - SHORT uygulanabilir", applicable: true }
    : {
        label: "SADECE IZLEME",
        hint: "Acik satis (SHORT) icin ozel marjin hesabi gerekir - gercek hesabinizdan uygulayamazsiniz",
        applicable: false,
      };
}
