#!/bin/bash
# The public build (HD_PUBLIC=1) with a DUMMY analytics token of the right shape (32 hex, not a real token), as
# `npm run build` runs it, step by step, in its own copy: prepare:data (supplier images from the cache with --offline: no
# network), the web build, the API build (check-config inside it), the budget, check:rights and check:promises. Then the
# rights check's JSON summary. QA_TOKEN= (empty) builds without a token.
set -o pipefail
source "$(dirname "$0")/noNet.sh"
QA=$(cd "$(dirname "$0")/.." && pwd)
cd "$QA/build-s19-pub/site"
export HD_PUBLIC=1 CF_ANALYTICS_TOKEN=${QA_TOKEN-a19a19a19a19a19a19a19a19a19a19a1}
date -u +"=== prepare:data %H:%M:%S (token: $([ -n "$CF_ANALYTICS_TOKEN" ] && echo "a dummy, 32 hex" || echo none))"
npm run copy && npm run catalog && npm run assets:temp && npx --no-install tsx tools/supplier-images.ts --offline && npm run test:page && npm run story || { echo "prepare:data FAILED"; exit 1; }
date -u +"=== build %H:%M:%S"
npm run build -w @hd/web && npm run build -w @hd/api && npm run budget && npm run check:rights && npm run check:promises || { echo "build FAILED $?"; exit 2; }
npx --no-install tsx tools/check-image-rights.ts --json="$QA/data/rights-check-public.json" > /dev/null
date -u +"=== done %H:%M:%S"
