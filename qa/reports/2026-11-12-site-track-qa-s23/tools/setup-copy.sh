#!/bin/bash
# QA S23 (2026-11-12): an isolated copy of commit bd5ac86a, outside the live tree (session scratchpad). Nothing is read
# from the live site/ and nothing is written to it.
# - git archive of site/, status/, docs/, briefs/, .github/, scripts/ and the S23 evidence at bd5ac86a;
# - data/: hard-linked from the S22 QA copy (9b6c6746), then the 2 files that changed 9b6c6746..bd5ac86a are replaced (rm
#   first, so the S22 inode is never written) from git; checked with `git archive bd5ac86a data | tar -d` afterwards;
# - assets/manifest.json pinned from bd5ac86a; the other assets dirs linked read-only to the live tree (clean at bd5ac86a);
# - the other qa/reports entries as links (read-only);
# - node_modules hard-linked from the S22 QA copy (package-lock.json unchanged 9b6c6746..bd5ac86a), read-only use;
# - the supplier-image cache hard-linked from the S22 QA copy (the build runs --offline, no network).
set -euo pipefail
COMMIT=bd5ac86a
PREV=9b6c6746
REPO=/home/user/homedesign-app
QA=$(cd "$(dirname "$0")/.." && pwd)
OLD=$QA/../qa22/build-s22
DST=$QA/build-s23
[ -e "$DST" ] && { echo "exists: $DST"; exit 1; }
git -C "$REPO" diff --quiet "$PREV" "$COMMIT" -- site/package-lock.json || { echo "lockfile changed"; exit 1; }
mkdir -p "$DST"
git -C "$REPO" archive "$COMMIT" site status docs briefs .github scripts qa/reports/2026-11-07-site-track/s23 | tar -x -C "$DST"
cp -al "$OLD/data" "$DST/data"
for f in $(git -C "$REPO" diff --name-only "$PREV" "$COMMIT" -- data); do
  rm -f "$DST/$f"; mkdir -p "$(dirname "$DST/$f")"; git -C "$REPO" show "$COMMIT:$f" > "$DST/$f"; echo "data updated: $f"
done
mkdir -p "$DST/assets"
git -C "$REPO" show "$COMMIT:assets/manifest.json" > "$DST/assets/manifest.json"
for d in blockout brand prompts qa renders review; do ln -s "$REPO/assets/$d" "$DST/assets/$d"; done
ln -s "$REPO/studio" "$DST/studio"
for e in "$REPO"/qa/reports/*; do b=$(basename "$e"); [ -e "$DST/qa/reports/$b" ] || ln -s "$e" "$DST/qa/reports/$b"; done
cp -al "$OLD/site/node_modules" "$DST/site/node_modules"
for w in api web shared tools; do [ -d "$OLD/site/$w/node_modules" ] && cp -al "$OLD/site/$w/node_modules" "$DST/site/$w/node_modules"; done
# a private name for this round's wrangler, so I stop only my own servers
rm -f "$DST/site/node_modules/wrangler/wrangler-dist/qasrv"*.js
cp "$DST/site/node_modules/wrangler/wrangler-dist/cli.js" "$DST/site/node_modules/wrangler/wrangler-dist/qasrv23.js"
mkdir -p "$DST/site/.cache"
cp -al "$OLD/site/.cache/supplier-images" "$DST/site/.cache/supplier-images"
echo "commit $COMMIT -> $DST"
