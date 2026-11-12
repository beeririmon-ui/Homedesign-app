#!/bin/bash
# Full regression, the CI's step order (.github/workflows/site-ci.yml at a988b099) on the clean copy (node_modules from the
# same lockfile): prepare:data (the steps of the script; supplier images from the cache with --offline, no network),
# typecheck, lint, format:check, vitest, check:config, then the build (web, api, budget, check:rights). Every npx with
# --no-install. The e2e and a11y run separately against my own server (serve.sh), as in the earlier rounds.
set -o pipefail
cd "$(dirname "$0")/../build-s17/site"
export PATH=/opt/node22/bin:$PATH npm_config_offline=true WRANGLER_SEND_METRICS=false NO_UPDATE_NOTIFIER=1
st() { echo "=== $1 $(date -u +%H:%M:%S)"; }
st prepare:data
npm run catalog && npm run assets:temp && npx --no-install tsx tools/supplier-images.ts --offline && npm run test:page && npm run story || { echo "prepare:data FAILED $?"; exit 1; }
st typecheck; npm run typecheck || { echo "typecheck FAILED"; exit 2; }
st lint; npm run lint || { echo "lint FAILED"; exit 3; }
st format; npm run format:check || { echo "format FAILED"; exit 4; }
st vitest; npx --no-install vitest run || { echo "vitest FAILED"; exit 5; }
st check:config; npm run check:config -w @hd/api || { echo "check:config FAILED"; exit 6; }
st build; npm run build -w @hd/web && npm run build -w @hd/api && npm run budget && npm run check:rights || { echo "build FAILED"; exit 7; }
st done
