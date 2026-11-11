#!/bin/bash
# The build of `npm run build`, step by step, with the supplier images from the cache only (--offline).
set -o pipefail
cd "$(dirname "$0")/../build-s1112/site"
date -u +%H:%M:%S
npm run catalog && npm run assets:temp && npx tsx tools/supplier-images.ts --offline && npm run test:page && npm run story \
  && npm run build -w @hd/web && npm run build -w @hd/api && npm run budget
echo "build exit $?"
date -u +%H:%M:%S
