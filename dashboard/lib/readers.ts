import fs from "node:fs";
import os from "node:os";
import path from "node:path";
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

export interface PositionsResult {
  positions: OpenPosition[];
  /**
   * null = MESRU bos durum (state.db henuz hic olusmamis, ilk trade oncesi).
   * string = dosya VAR ama okunamadi/acilamadi (native modul/bundling sorunu
   * gibi gercek bir hata) - bu iki durum ARTIK birbirine karistirilmiyor.
   * Onceki surumde her iki durum da sessizce [] donuyordu; bu da state.db'de
   * gercekten acik pozisyon varken (bkz. paper_trading/data/state.db)
   * dashboard'un "aktif pozisyon yok" gibi YANLIS bir bos-durum gostermesine
   * yol acmisti (Sistem Gunlugu'nde GIRIS kaydi varken Acik Pozisyonlar'da
   * 0 pozisyon gorunmesi - bkz. ilgili konusma).
   */
  error: string | null;
}

/**
 * state.db'den acik pozisyonlari SALT-OKUNUR okur.
 *
 * KOK NEDEN (bkz. ilgili konusma - Sistem Gunlugu'nde GIRIS kaydi varken
 * Acik Pozisyonlar panelinin 0 pozisyon gostermesi): state.py, state.db'yi
 * `PRAGMA journal_mode=WAL` ile aciyor; bu ayar dosyanin BASLIGINDA kalici
 * olarak saklanir. WAL modundaki bir SQLite dosyasi SALT-OKUNUR acilsa bile
 * SQLite, WAL indeksi icin bir "-shm" yardimci dosyasi olusturmaya/acmaya
 * calisir - bu, o dosyanin bulundugu DIZINE yazma izni gerektirir. Vercel'in
 * serverless fonksiyon dizini READ-ONLY'dir (yalniz /tmp yazilabilir), bu
 * yuzden bu deneme sessizce basarisiz olup better-sqlite3'un fırlattigi
 * hatayi eskiden readOpenPositions() yutuyordu (bkz. asagidaki catch).
 *
 * COZUM: dosyayi ONCE /tmp altinda benzersiz bir gecici dizine kopyalayip
 * ORADAN acmak - state.db kucuk (KB mertebesinde) oldugundan bu kopyalama
 * her istekte ihmal edilebilir maliyette. /tmp yazilabilir oldugundan
 * SQLite ihtiyac duydugu -shm/-wal yardimci dosyalarini sorunsuzca
 * olusturabilir.
 */
export function readOpenPositions(): PositionsResult {
  if (!fs.existsSync(STATE_DB_PATH)) return { positions: [], error: null };

  let tmpDir: string | undefined;
  let db: Database.Database | undefined;
  try {
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "paper-trading-state-"));
    const tmpDbPath = path.join(tmpDir, "state.db");
    fs.copyFileSync(STATE_DB_PATH, tmpDbPath);

    db = new Database(tmpDbPath, { readonly: true, fileMustExist: true });
    const rows = db
      .prepare(
        "SELECT symbol, strategy, direction, entry_date, entry_price, stop_price, target_price, size FROM positions ORDER BY symbol"
      )
      .all() as OpenPosition[];
    return { positions: rows, error: null };
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    // Vercel fonksiyon loglarinda gorunsun diye - dosya var ama acilamadi
    // demek ki gercek bir sorun var (bkz. yukaridaki KOK NEDEN notu).
    console.error("[readOpenPositions] state.db okunamadi:", message);
    return { positions: [], error: message };
  } finally {
    db?.close();
    if (tmpDir) fs.rmSync(tmpDir, { recursive: true, force: true });
  }
}
