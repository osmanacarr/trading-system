#!/usr/bin/env bash
# Vercel "Ignored Build Step" script (Project Settings -> Git -> Ignored Build Step).
#
# KOK NEDEN (bkz. ilgili konusma, 2026-08-13 Vercel deploy-kotasi tukenmesi):
# GitHub Actions (gozcu_scan / paper_trading / research_pipeline) yalnizca
# VERI dosyalari (paper_trading/logs, paper_trading/data, gozcu/data,
# research/data) uretip main'e commit/push ediyor. Vercel her push'ta otomatik
# deploy tetikledigi icin, gunde yuzlerce veri-commit'i = yuzlerce gereksiz
# deploy -> Hobby plan deploy kotasi tukendi. Bu script, degisen dosyalarin
# TAMAMI yukaridaki veri dizinlerinden ibaretse build'i ATLAR (exit 0);
# dashboard/ altinda gercek KOD degisikligi varsa build DEVAM EDER (exit 1).
#
# Exit code semantigi (Vercel dokumantasyonu): 0 = build ATLA, 1 (veya
# sifir-disi herhangi bir kod) = build'e DEVAM ET.
#
# NOT: bu script Vercel build container'inda calisir; repo tam olarak
# checkout edilmis olur ama calisma dizini Root Directory (= dashboard/)
# olabilir - bu yuzden ONCE repo kokune gecip git diff'i ORADAN calistiriyoruz,
# boylece degisen dosya yollari her zaman repo-koku-goreli oluyor.
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

# Vercel, onceki BASARIYLA deploy edilmis commit'i VERCEL_GIT_PREVIOUS_SHA
# olarak saglar. Ilk deploy'da (veya bu degisken bir sebeple bos gelirse)
# guvenli taraf: build'e devam et (exit 1) - "atla" varsayimini asla yapma.
PREV_SHA="${VERCEL_GIT_PREVIOUS_SHA:-}"
if [ -z "$PREV_SHA" ]; then
  echo "vercel-ignore-build: VERCEL_GIT_PREVIOUS_SHA yok (ilk deploy?) - guvenli tarafta kal, build'e devam."
  exit 1
fi

CHANGED_FILES="$(git diff --name-only "$PREV_SHA" HEAD || true)"
if [ -z "$CHANGED_FILES" ]; then
  echo "vercel-ignore-build: degisen dosya listesi bos - guvenli tarafta kal, build'e devam."
  exit 1
fi

# Sadece bu onekler altindaki degisiklikler "veri-only" sayilir.
DATA_PREFIXES="paper_trading/logs/ paper_trading/data/ gozcu/data/ research/data/"

echo "vercel-ignore-build: degisen dosyalar ($PREV_SHA -> HEAD):"
echo "$CHANGED_FILES"

while IFS= read -r file; do
  [ -z "$file" ] && continue
  matched=0
  for prefix in $DATA_PREFIXES; do
    case "$file" in
      "$prefix"*)
        matched=1
        break
        ;;
    esac
  done
  if [ "$matched" -eq 0 ]; then
    echo "vercel-ignore-build: '$file' veri-only oneklerle eslesmedi -> build'e devam (exit 1)."
    exit 1
  fi
done <<< "$CHANGED_FILES"

echo "vercel-ignore-build: tum degisiklikler veri-only -> build ATLANIYOR (exit 0)."
exit 0
