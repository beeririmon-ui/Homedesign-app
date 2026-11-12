#!/bin/bash
# QA S18: full regression in the CI's step order (.github/workflows/site-ci.yml at 3013d630) on the clean copy:
# prepare:data (the steps of the script, copy first; supplier images from the cache with --offline: no network),
# typecheck, lint, format:check, vitest, check:config, then the build as `npm run build` runs it (prepare:data again,
# web, api, budget, check:rights, check:promises). Every npx with --no-install. The e2e and a11y run separately against
# my own server (serve.sh), with a dummy webhook secret on the command line only.
set -o pipefail
source "$(dirname "$0")/noNet.sh"
QA=$(cd "$(dirname "$0")/.." && pwd)
cd "$QA/build-s18/site"
st() { echo "=== $1 $(date -u +%H:%M:%S)"; }
prep() { npm run copy && npm run catalog && npm run assets:temp && npx --no-install tsx tools/supplier-images.ts --offline && npm run test:page && npm run story; }
st prepare:data; prep || { echo "prepare:data FAILED $?"; exit 1; }
st typecheck; npm run typecheck || { echo "typecheck FAILED"; exit 2; }
st lint; npm run lint || { echo "lint FAILED"; exit 3; }
st format; npm run format:check || { echo "format FAILED"; exit 4; }
st vitest; npx --no-install vitest run || { echo "vitest FAILED"; exit 5; }
st check:config; npm run check:config -w @hd/api || { echo "check:config FAILED"; exit 6; }
st build; prep && npm run build -w @hd/web && npm run build -w @hd/api && npm run budget && npm run check:rights && npm run check:promises -- --json="$QA/data/check-promises-flag.json" || { echo "build FAILED"; exit 7; }
st done
