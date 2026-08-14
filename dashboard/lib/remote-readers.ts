// SECENEK 2 (runtime-fetch): API route'larinin repoya GOMULU dosyalari
// (build-time'da paketlenmis) okumasi yerine, request aninda GitHub'daki
// GUNCEL icerigi cekmesi icin - bkz. ilgili konusma (Vercel deploy-kotasi
// tukenmesi, veri guncellemesinin git push+deploy'a bagimli olmasi kok
// nedeni). lib/readers.ts'teki readJson/readJsonl ile AYNI imza ve AYNI
// "hicbir zaman crash etme" felsefesi korunur - tek fark veri kaynagi.
//
// raw.githubusercontent.com DEGIL, api.github.com Contents API kullanilir:
// raw content Fastly CDN'de ~5dk cache'leniyor, bu da asagidaki kendi TTL
// cache'imizin ustune binip tazeligi gereksiz yere geciktirir. Contents API
// dinamik (CDN cache yok) ve repo public oldugundan token'siz da calisir,
// ama rate limit 60/saat'e dusuyor - GITHUB_TOKEN ile 5000/saat'e cikariyoruz.
import { Buffer } from "node:buffer";

const REPO_OWNER = "osmanacarr";
const REPO_NAME = "trading-system";
const REPO_REF = "main";

// Route'larin tumu "force-dynamic" (bkz. her route.ts'nin basi) - bu, Next'in
// KENDI fetch cache'ini { cache: "no-store", next: { revalidate: 0 } } ile
// TAMAMEN devre disi birakiyor (bkz. node_modules/next/dist/docs/01-app/
// 02-guides/caching-without-cache-components.md, "dynamic" bolumu). Yani
// fetch()'e next.revalidate versek bile GitHub'a HER request'te gidilirdi.
// Bu yuzden kendi basit, module-scope TTL cache'imizi tutuyoruz - ayni
// serverless instance'in ardisik sicak (warm) cagrilarinda GitHub'a gereksiz
// istek atilmasini engeller (cold start'ta sifirlanir, bu kabul edilebilir).
interface CacheEntry {
  text: string | null;
  fetchedAt: number;
}
const textCache = new Map<string, CacheEntry>();

/**
 * GitHub Contents API'den bir dosyanin ham metin icerigini ceker.
 * Dosya yoksa (404) null doner (readJson/readJsonl'daki "meşru bos durum"
 * ile ayni anlam). Ag hatasi / 1MB ustu dosya (Contents API sinirlamasi -
 * ileride buyuk JSONL dosyalari icin ayrica ele alinmali) / beklenmedik
 * yanit gibi durumlarda da null doner, hata console.error'a yazilir -
 * dashboard okurken hicbir zaman crash etmemeli (bkz. lib/readers.ts ayni
 * felsefe).
 */
async function fetchRemoteText(relPath: string, ttlMs: number): Promise<string | null> {
  const cached = textCache.get(relPath);
  if (cached && Date.now() - cached.fetchedAt < ttlMs) {
    return cached.text;
  }

  try {
    const token = process.env.GITHUB_TOKEN;
    const res = await fetch(
      `https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/contents/${relPath}?ref=${REPO_REF}`,
      {
        headers: {
          Accept: "application/vnd.github+json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        cache: "no-store",
      }
    );

    if (res.status === 404) {
      textCache.set(relPath, { text: null, fetchedAt: Date.now() });
      return null;
    }
    if (!res.ok) {
      console.error(`[fetchRemoteText] ${relPath}: GitHub API ${res.status} ${res.statusText}`);
      return cached?.text ?? null;
    }

    const body = (await res.json()) as { content?: string; encoding?: string };
    if (!body.content || body.encoding !== "base64") {
      console.error(`[fetchRemoteText] ${relPath}: beklenmedik yanit sekli (content/encoding eksik)`);
      return cached?.text ?? null;
    }

    const text = Buffer.from(body.content, "base64").toString("utf-8");
    textCache.set(relPath, { text, fetchedAt: Date.now() });
    return text;
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    console.error(`[fetchRemoteText] ${relPath}: fetch basarisiz - ${message}`);
    // Gecici bir ag hatasinda, elimizde eski (stale) bir kopya varsa onu
    // donduruyoruz - dashboard'un aninda bos gorunmesindense birkac dakika
    // eski veri gostermesi tercih edilir.
    return cached?.text ?? null;
  }
}

/** GitHub'daki bir JSON dosyasini okur; yoksa/parse edilemezse null doner. */
export async function fetchRemoteJson<T>(relPath: string, ttlMs: number): Promise<T | null> {
  const text = await fetchRemoteText(relPath, ttlMs);
  if (text === null) return null;
  try {
    return JSON.parse(text) as T;
  } catch {
    console.error(`[fetchRemoteJson] ${relPath}: JSON parse hatasi`);
    return null;
  }
}

/** GitHub'daki bir JSONL dosyasini okur; yoksa bos dizi, bozuk satirlar sessizce atlanir. */
export async function fetchRemoteJsonl<T>(relPath: string, ttlMs: number): Promise<T[]> {
  const text = await fetchRemoteText(relPath, ttlMs);
  if (text === null) return [];
  const records: T[] = [];
  for (const line of text.split("\n")) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    try {
      records.push(JSON.parse(trimmed) as T);
    } catch {
      // readJsonl ile ayni davranis: bozuk/yarim son satiri sessizce atla.
    }
  }
  return records;
}
