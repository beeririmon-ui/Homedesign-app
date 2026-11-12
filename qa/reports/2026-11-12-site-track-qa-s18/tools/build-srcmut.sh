#!/bin/bash
# QA S18: the source-mutation build (setup-srcmut.sh): build-copy (UNDECIDED), the web build, check-promises; then where
# each marker landed in dist (which file, one string or split), so the gate's verdict can be read against it.
set -o pipefail
source "$(dirname "$0")/noNet.sh"
QA=$(cd "$(dirname "$0")/.." && pwd)
cd "$QA/build-s18-email/site"
date -u +"=== build-copy %H:%M:%S"; npm run copy || exit 1
date -u +"=== web build %H:%M:%S"; npm run build -w @hd/web > "$QA/data/srcmut-webbuild.log" 2>&1 || { echo "web build FAILED"; tail -20 "$QA/data/srcmut-webbuild.log"; exit 2; }
date -u +"=== check-promises %H:%M:%S"; npm run check:promises -- --json="$QA/data/check-promises-srcmut.json"; echo "check-promises exit $?"
date -u +"=== where the markers landed %H:%M:%S"
for m in סמ1 סמ2 סמ3 סמ4 סמ5 סמ6; do
  echo "-- $m"; grep -rl "$m" web/dist --include=*.html --include=*.js | sed 's|web/dist/||' | head -4
  grep -rhoE ".{0,90}$m.{0,10}" web/dist/assets/*.js web/dist/privacy/index.html 2>/dev/null | head -2
done
date -u +"=== done %H:%M:%S"
