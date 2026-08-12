// config.py ile birebir ayni (paper_trading sanal sermaye baslangici)
export const PAPER_TRADING_INITIAL_CAPITAL = 10_000.0;

// config.py USER_CAN_SHORT ile birebir ayni: kullanicinin GERCEK hesabinda
// SHORT (acik satis) yapip yapamadigi - BIST'te ozel marjin izni gerekir,
// kullanicida su an YOK. Bu SADECE gorsel bir bayrak (asagidaki
// "uygulanabilirlik" rozetleri icin) - paper trading motoru SHORT
// sinyalleri uretmeye/test etmeye DEVAM EDER, bu deger bunu etkilemez.
// Kullanici ileride acik satis marjinli bir hesap acarsa iki tarafta da
// (config.py + burada) true yapilmali.
export const USER_CAN_SHORT = false;

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
