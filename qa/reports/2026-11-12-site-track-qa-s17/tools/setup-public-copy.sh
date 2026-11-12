#!/bin/bash
# The public build's own copy (HD_PUBLIC=1), so the flag build in build-s17 keeps serving the e2e. Same commit: site/ is
# copied from the clean copy (node_modules and the supplier-image cache hard-linked, read-only use), the repo dirs the
# build reads are links to the clean copy's (data/, status/, docs/, .github/, assets/, qa/: the build never writes there).
set -euo pipefail
QA=$(cd "$(dirname "$0")/.." && pwd)
SRC=$QA/build-s17
DST=$QA/build-s17-pub
[ -e "$DST" ] && { echo "exists: $DST"; exit 1; }
mkdir -p "$DST/site"
( cd "$SRC/site" && tar --exclude=./node_modules --exclude=./api/node_modules --exclude=./web/node_modules --exclude=./test-results --exclude=./web/dist --exclude=./.cache --exclude=./.wrangler-state --exclude=./web/public/media --exclude=./.generated -cf - . ) | tar -xf - -C "$DST/site"
cp -al "$SRC/site/node_modules" "$DST/site/node_modules"
for w in api web; do [ -d "$SRC/site/$w/node_modules" ] && cp -al "$SRC/site/$w/node_modules" "$DST/site/$w/node_modules"; done
mkdir -p "$DST/site/.cache" && cp -al "$SRC/site/.cache/supplier-images" "$DST/site/.cache/supplier-images"
for d in data status docs .github assets qa studio; do ln -s "$SRC/$d" "$DST/$d"; done
echo "public copy -> $DST"
