import fs from "node:fs";
import Database from "better-sqlite3";
import { STATE_DB_PATH } from "./paths";
import type { OpenPosition } from "./types";

/** JSONL dosyasini okur; dosya yoksa (henuz ilk calistirma olmamis) bos dizi doner. */
export function readJsonl<T>(filePath: string): T[] {
  if (!fs.existsSync(filePath)) return [];
  const content = fs.readFileSync(filePath, "utf-8");
  const records: T[] = [];
  for (const line of content.split("\n")) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    try {
      records.push(JSON.parse(trimmed) as T);
    } catch {
      // Bozuk/yarim yazilmis son satiri sessizce atla (append sirasinda
      // crash olmus olabilir) - dashboard okurken hicbir zaman crash etmemeli.
    }
  }
  return records;
}

/** JSON dosyasini okur; dosya yoksa null doner (crash etmez). */
export function readJson<T>(filePath: string): T | null {
  if (!fs.existsSync(filePath)) return null;
  try {
    return JSON.parse(fs.readFileSync(filePath, "utf-8")) as T;
  } catch {
    return null;
  }
}

/**
 * state.db'den acik pozisyonlari SALT-OKUNUR okur.
 *
 * readonly:true + fileMustExist:true bilerek kullanildi: serverless (Vercel)
 * ortaminda dosya sistemi read-only'dir ve state.db henuz hic olusmamis
 * olabilir (ilk trade oncesi) - better-sqlite3 varsayilani (fileMustExist
 * false) olmayan dosyayi OLUSTURMAYA calisir ki bu hem gereksiz hem de
 * read-only FS'te patlar. Dosya yoksa/acilamiyorsa bos dizi donup dashboard
 * "aktif pozisyon yok" durumunu gosterir.
 */
export function readOpenPositions(): OpenPosition[] {
  if (!fs.existsSync(STATE_DB_PATH)) return [];
  let db: Database.Database | undefined;
  try {
    db = new Database(STATE_DB_PATH, { readonly: true, fileMustExist: true });
    const rows = db
      .prepare(
        "SELECT symbol, strategy, direction, entry_date, entry_price, stop_price, target_price, size FROM positions ORDER BY symbol"
      )
      .all() as OpenPosition[];
    return rows;
  } catch {
    return [];
  } finally {
    db?.close();
  }
}
