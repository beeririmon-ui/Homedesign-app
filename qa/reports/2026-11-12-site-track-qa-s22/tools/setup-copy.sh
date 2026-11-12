#!/bin/bash
# QA S22 (2026-11-12): an isolated copy of commit 9b6c6746, outside the live tree (session scratchpad). frontend-dev works
# on S23 in the live tree at the same time, so nothing is read from the live site/.
# - git archive of site/, status/, docs/, briefs/, .github/ and the S22 evidence (qa/reports/2026-11-07-site-track/s22) at
#   9b6c6746;
# - data/: hard-linked from the S21 QA copy (7b42ddc1), then the 7 files that changed 7b42ddc1..9b6c6746 are replaced (rm
#   first, so the S21 inode is never written) from git; checked with `git archive 9b6c6746 data | tar -d` afterwards;
# - assets/manifest.json pinned from 9b6c6746 (unchanged since 7b42ddc1); the other assets dirs linked read-only to the live
#   tree (the build reads only the committed render dirs; 7b42ddc1..9b6c6746 only ADDS r9 files there);
# - the other qa/reports entries as links (read-only);
# - node_modules hard-linked from the S21 QA copy (package-lock.json unchanged 7b42ddc1..9b6c6746), read-only use;
# - the supplier-image cache hard-linked from the S21 QA copy (the build runs --offline, no network).
set -euo pipefail
COMMIT=9b6c6746
REPO=/home/user/homedesign-app
QA=$(cd "$(dirname "$0")/.." && pwd)
OLD=$QA/../qa21/build-s21
DST=$QA/build-s22
[ -e "$DST" ] && { echo "exists: $DST"; exit 1; }
mkdir -p "$DST"
git -C "$REPO" archive "$COMMIT" site status docs briefs .github qa/reports/2026-11-07-site-track/s22 | tar -x -C "$DST"
cp -al "$OLD/data" "$DST/data"
for f in $(git -C "$REPO" diff --name-only 7b42ddc1 "$COMMIT" -- data); do
  rm -f "$DST/$f"; mkdir -p "$(dirname "$DST/$f")"; git -C "$REPO" show "$COMMIT:$f" > "$DST/$f"; echo "data updated: $f"
done
mkdir -p "$DST/assets"
git -C "$REPO" show "$COMMIT:assets/manifest.json" > "$DST/assets/manifest.json"
for d in blockout brand prompts qa renders review; do ln -s "$REPO/assets/$d" "$DST/assets/$d"; done
ln -s "$REPO/studio" "$DST/studio"
for e in "$REPO"/qa/reports/*; do b=$(basename "$e"); [ -e "$DST/qa/reports/$b" ] || ln -s "$e" "$DST/qa/reports/$b"; done
cp -al "$OLD/site/node_modules" "$DST/site/node_modules"
for w in api web shared tools; do [ -d "$OLD/site/$w/node_modules" ] && cp -al "$OLD/site/$w/node_modules" "$DST/site/$w/node_modules"; done
# a private name for this round's wrangler, so I can stop my own servers without touching anyone else's
rm -f "$DST/site/node_modules/wrangler/wrangler-dist/qasrv"*.js
cp "$DST/site/node_modules/wrangler/wrangler-dist/cli.js" "$DST/site/node_modules/wrangler/wrangler-dist/qasrv22.js"
mkdir -p "$DST/site/.cache"
cp -al "$OLD/site/.cache/supplier-images" "$DST/site/.cache/supplier-images"
echo "commit $COMMIT -> $DST"
