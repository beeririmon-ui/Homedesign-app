#!/bin/bash
# The public build (HD_PUBLIC=1), as `npm run build` runs it, step by step, in its own copy: prepare:data (supplier images
# from the cache with --offline: no network), the web build, the API build (check-config inside it), the budget, and the
# image-rights check. Then the check's JSON summary.
set -o pipefail
cd "$(dirname "$0")/../build-s1516-pub/site"
export PATH=/opt/node22/bin:$PATH HD_PUBLIC=1 WRANGLER_SEND_METRICS=false NO_UPDATE_NOTIFIER=1
date -u +"=== prepare:data %H:%M:%S"
npm run catalog && npm run assets:temp && npx tsx tools/supplier-images.ts --offline && npm run test:page && npm run story || { echo "prepare:data FAILED"; exit 1; }
date -u +"=== build %H:%M:%S"
npm run build -w @hd/web && npm run build -w @hd/api && npm run budget && npm run check:rights || { echo "build FAILED $?"; exit 2; }
npx tsx tools/check-image-rights.ts --json=../../s1516-data/rights-check-public.json > /dev/null
date -u +"=== done %H:%M:%S"
