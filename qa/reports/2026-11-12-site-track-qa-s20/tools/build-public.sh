#!/bin/bash
# The public build (HD_PUBLIC=1) as `npm run build` runs it, in its own copy, with a DUMMY analytics token of the right
# shape (32 hex, not a real token). Supplier images from the cache with --offline (no network). QA_WRANGLER=<file> points
# build-copy and check-promises at a test config (HD_WRANGLER, S20; the repo's api/wrangler.jsonc otherwise).
#   bash build-public.sh <suffix> [json-out-name]
set -o pipefail
source "$(dirname "$0")/noNet.sh"
QA=$(cd "$(dirname "$0")/.." && pwd)
cd "$QA/build-s20-${1:-pub}/site"
export HD_PUBLIC=1 CF_ANALYTICS_TOKEN=a20a20a20a20a20a20a20a20a20a20a2
[ -n "${QA_WRANGLER:-}" ] && export HD_WRANGLER=$QA_WRANGLER
date -u +"=== prepare:data %H:%M:%S (HD_PUBLIC=1, token: a dummy, 32 hex; wrangler: ${HD_WRANGLER:-api/wrangler.jsonc})"
npm run copy && npm run catalog && npm run assets:temp && npx --no-install tsx tools/supplier-images.ts --offline && npm run test:page && npm run story || { echo "prepare:data FAILED $?"; exit 1; }
date -u +"=== build %H:%M:%S"
npm run build -w @hd/web && npm run build -w @hd/api && npm run budget && npm run check:rights && npm run check:promises -- --json="$QA/data/check-promises-${2:-public}.json" || { echo "build FAILED $?"; exit 2; }
date -u +"=== done %H:%M:%S"
