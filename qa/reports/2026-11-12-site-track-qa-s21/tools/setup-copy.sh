#!/bin/bash
# QA S21 (2026-11-12): an isolated copy of commit 7b42ddc1, outside the live tree (session scratchpad). frontend-dev works
# on S22 in the live tree at the same time, so nothing is read from the live site/.
# - git archive of site/, status/, docs/, .github/ and the S21 evidence (qa/reports/2026-11-07-site-track/s21) at 7b42ddc1;
# - data/: hard-linked from the S20 QA copy (data/ is unchanged 8828cab9..7b42ddc1: `git diff --stat` empty; checked again
#   with `git archive 7b42ddc1 data | tar -d` in data/data-dir-check.txt);
# - assets/manifest.json pinned from 7b42ddc1; the other assets dirs linked read-only to the live tree (the build reads
#   only committed render dirs; the live tree's renders are inventoried at the start and the end);
# - the other qa/reports entries as links (read-only);
# - node_modules hard-linked from the S20 QA copy (package-lock.json unchanged 8828cab9..7b42ddc1), read-only use;
# - the supplier-image cache hard-linked from the S20 QA copy (the build runs --offline, no network).
set -euo pipefail
COMMIT=7b42ddc1
REPO=/home/user/homedesign-app
QA=$(cd "$(dirname "$0")/.." && pwd)
OLD=$QA/../qa20/build-s20
DST=$QA/build-s21
[ -e "$DST" ] && { echo "exists: $DST"; exit 1; }
mkdir -p "$DST"
git -C "$REPO" archive "$COMMIT" site status docs .github qa/reports/2026-11-07-site-track/s21 | tar -x -C "$DST"
cp -al "$OLD/data" "$DST/data"
mkdir -p "$DST/assets"
git -C "$REPO" show "$COMMIT:assets/manifest.json" > "$DST/assets/manifest.json"
for d in blockout brand prompts qa renders review; do ln -s "$REPO/assets/$d" "$DST/assets/$d"; done
ln -s "$REPO/studio" "$DST/studio"
for e in "$REPO"/qa/reports/*; do b=$(basename "$e"); [ -e "$DST/qa/reports/$b" ] || ln -s "$e" "$DST/qa/reports/$b"; done
cp -al "$OLD/site/node_modules" "$DST/site/node_modules"
for w in api web shared tools; do [ -d "$OLD/site/$w/node_modules" ] && cp -al "$OLD/site/$w/node_modules" "$DST/site/$w/node_modules"; done
# a private name for this round's wrangler, so I can stop my own servers without touching anyone else's
rm -f "$DST/site/node_modules/wrangler/wrangler-dist/qasrv"*.js
cp "$DST/site/node_modules/wrangler/wrangler-dist/cli.js" "$DST/site/node_modules/wrangler/wrangler-dist/qasrv21.js"
mkdir -p "$DST/site/.cache"
cp -al "$OLD/site/.cache/supplier-images" "$DST/site/.cache/supplier-images"
echo "commit $COMMIT -> $DST"
