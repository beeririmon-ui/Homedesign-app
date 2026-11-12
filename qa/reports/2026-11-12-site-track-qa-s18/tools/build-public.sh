#!/bin/bash
# The public build (HD_PUBLIC=1) with a DUMMY analytics token of the right shape (32 hex, not a real token), as
# `npm run build` runs it, step by step, in its own copy: prepare:data (copy first; supplier images from the cache with
# --offline), the web build, the API build (check-config inside it), the budget, check:rights, check:promises (+ JSON).
set -o pipefail
source "$(dirname "$0")/noNet.sh"
QA=$(cd "$(dirname "$0")/.." && pwd)
cd "$QA/build-s18-pub/site"
export HD_PUBLIC=1 CF_ANALYTICS_TOKEN=a18a18a18a18a18a18a18a18a18a18a1
date -u +"=== prepare:data %H:%M:%S (token: a dummy, 32 hex)"
npm run copy && npm run catalog && npm run assets:temp && npx --no-install tsx tools/supplier-images.ts --offline && npm run test:page && npm run story || { echo "prepare:data FAILED"; exit 1; }
date -u +"=== build %H:%M:%S"
npm run build -w @hd/web && npm run build -w @hd/api && npm run budget && npm run check:rights && npm run check:promises -- --json="$QA/data/check-promises-public.json" || { echo "build FAILED $?"; exit 2; }
date -u +"=== done %H:%M:%S"
