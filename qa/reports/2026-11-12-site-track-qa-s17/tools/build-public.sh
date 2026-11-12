#!/bin/bash
# The public build (HD_PUBLIC=1) with a DUMMY analytics token of the right shape (32 hex, not a real token), as
# `npm run build` runs it, step by step, in its own copy: prepare:data (supplier images from the cache with --offline: no
# network), the web build, the API build (check-config inside it), the budget, and the image-rights check. Then the
# check's JSON summary. QA_TOKEN= (empty) builds without a token.
set -o pipefail
source "$(dirname "$0")/noNet.sh"
QA=$(cd "$(dirname "$0")/.." && pwd)
cd "$QA/build-s17-pub/site"
export HD_PUBLIC=1 CF_ANALYTICS_TOKEN=${QA_TOKEN-a17a17a17a17a17a17a17a17a17a17a1}
date -u +"=== prepare:data %H:%M:%S (token: $([ -n "$CF_ANALYTICS_TOKEN" ] && echo "a dummy, 32 hex" || echo none))"
npm run catalog && npm run assets:temp && npx --no-install tsx tools/supplier-images.ts --offline && npm run test:page && npm run story || { echo "prepare:data FAILED"; exit 1; }
date -u +"=== build %H:%M:%S"
npm run build -w @hd/web && npm run build -w @hd/api && npm run budget && npm run check:rights || { echo "build FAILED $?"; exit 2; }
npx --no-install tsx tools/check-image-rights.ts --json="$QA/s17-data/rights-check-public.json" > /dev/null
date -u +"=== done %H:%M:%S"
