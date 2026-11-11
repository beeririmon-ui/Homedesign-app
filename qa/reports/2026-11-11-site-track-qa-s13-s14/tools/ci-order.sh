#!/bin/bash
# ת32: the CI's step order (.github/workflows/site-ci.yml at a8104956) on the clean copy, after npm ci (node_modules from the same lockfile):
# prepare:data (the steps of the script; supplier images from the cache with --offline, no network), then typecheck, lint, format:check, vitest.
set -o pipefail
cd "$(dirname "$0")/../build-s1314/site"
export PATH=/opt/node22/bin:$PATH
st() { echo "=== $1 $(date -u +%H:%M:%S)"; }
st prepare:data
npm run catalog && npm run assets:temp && npx tsx tools/supplier-images.ts --offline && npm run test:page && npm run story || { echo "prepare:data FAILED $?"; exit 1; }
st typecheck; npm run typecheck || { echo "typecheck FAILED"; exit 2; }
st lint; npm run lint || { echo "lint FAILED"; exit 3; }
st format; npm run format:check || { echo "format FAILED"; exit 4; }
st vitest; npx vitest run || { echo "vitest FAILED"; exit 5; }
st done
