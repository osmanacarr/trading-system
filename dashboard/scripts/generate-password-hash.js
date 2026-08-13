#!/usr/bin/env node
// Kendi giris sifrenizin bcrypt hash'ini uretir - SIFRENIN KENDISI hicbir
// yere (dosyaya, git'e, loglara) YAZILMAZ, sadece ekrana hash basilir ve
// SADECE SIZ gorursunuz (Claude'a hic gonderilmez/soylenmez).
//
// Kullanim (dashboard/ dizininden):
//   node scripts/generate-password-hash.js "sifreniz-burada"
// veya arguman vermeden calistirip terminalden girin:
//   node scripts/generate-password-hash.js
const bcrypt = require("bcryptjs");

function main() {
  const argPassword = process.argv[2];
  if (argPassword) {
    printHash(argPassword);
    return;
  }

  process.stdout.write("Şifrenizi girin ve Enter'a basın: ");
  process.stdin.resume();
  process.stdin.setEncoding("utf8");
  process.stdin.once("data", (data) => {
    printHash(data.toString().trim());
    process.exit(0);
  });
}

function printHash(password) {
  if (!password || password.length < 8) {
    console.error("\nŞifre en az 8 karakter olmalı.");
    process.exitCode = 1;
    return;
  }
  const hash = bcrypt.hashSync(password, 12);
  console.log("\n--- ADMIN_PASSWORD_HASH (bunu Vercel Environment Variables'a kopyalayın) ---\n");
  console.log(hash);
  console.log("\n--- (yukarıdaki satırı olduğu gibi kopyalayın) ---");
}

main();
