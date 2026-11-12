#!/bin/bash
# QA S19 (2026-11-12): an isolated copy of commit f33cfe42, outside the live tree (session scratchpad).
# - git archive of site/, data/, status/, docs/, .github/ and the S19 evidence (qa/reports/2026-11-07-site-track/s19) at f33cfe42;
# - assets/manifest.json pinned from f33cfe42; the other assets dirs linked read-only to the live tree (the build reads only
#   committed render dirs: editorial-phase-b, living-room/nordic v7/v9, warm-modern pilot-phase1, hall/kitchen v7,
#   transitions/test; render-agent writes under living-room/warm-modern/phase2-2026-11-10 and products/: checked at the
#   start and the end, data/live-tree-at-*.txt);
# - the other qa/reports entries as links (read-only);
# - node_modules hard-linked from the S17 copy (package-lock.json unchanged a988b099..f33cfe42), read-only use;
# - the supplier-image cache hard-linked from the live tree (the build runs --offline, no network).
set -euo pipefail
COMMIT=f33cfe42
REPO=/home/user/homedesign-app
QA=$(cd "$(dirname "$0")/.." && pwd)
DST=$QA/build-s19
OLD=$QA/../qa/build-s17
[ -e "$DST" ] && { echo "exists: $DST"; exit 1; }
mkdir -p "$DST"
git -C "$REPO" archive "$COMMIT" site data status docs .github qa/reports/2026-11-07-site-track/s19 | tar -x -C "$DST"
mkdir -p "$DST/assets"
git -C "$REPO" show "$COMMIT:assets/manifest.json" > "$DST/assets/manifest.json"
for d in blockout brand prompts qa renders review; do ln -s "$REPO/assets/$d" "$DST/assets/$d"; done
ln -s "$REPO/studio" "$DST/studio"
for e in "$REPO"/qa/reports/*; do b=$(basename "$e"); [ -e "$DST/qa/reports/$b" ] || ln -s "$e" "$DST/qa/reports/$b"; done
cp -al "$OLD/site/node_modules" "$DST/site/node_modules"
for w in api web; do [ -d "$OLD/site/$w/node_modules" ] && cp -al "$OLD/site/$w/node_modules" "$DST/site/$w/node_modules"; done
# a private name for this round's wrangler, so I can stop my own servers without touching anyone else's
rm -f "$DST/site/node_modules/wrangler/wrangler-dist/qasrv17.js"
cp "$DST/site/node_modules/wrangler/wrangler-dist/cli.js" "$DST/site/node_modules/wrangler/wrangler-dist/qasrv19.js"
mkdir -p "$DST/site/.cache"
cp -al "$REPO/site/.cache/supplier-images" "$DST/site/.cache/supplier-images"
echo "commit $COMMIT -> $DST"
