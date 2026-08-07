/**
 * Basit alt-dizi (subsequence) fuzzy eslesme: query'nin tum karakterleri
 * target icinde SIRAYLA (araya baska karakter girebilir) geciyorsa eslesir.
 * Bloomberg <GO> komut kutusunun hafif bir versiyonu icin yeterli - tam bir
 * fuzzy-search kutuphanesi gerektirmez.
 */
export function fuzzyMatch(query: string, target: string): boolean {
  if (query.length === 0) return true;
  const q = query.toLowerCase();
  const t = target.toLowerCase();
  let qi = 0;
  for (let ti = 0; ti < t.length && qi < q.length; ti++) {
    if (t[ti] === q[qi]) qi++;
  }
  return qi === q.length;
}

export function fuzzyScore(query: string, target: string): number {
  const q = query.toLowerCase();
  const t = target.toLowerCase();
  if (t.startsWith(q)) return 100 - t.length;
  const idx = t.indexOf(q);
  if (idx >= 0) return 50 - idx;
  return fuzzyMatch(q, t) ? 10 : -1;
}
