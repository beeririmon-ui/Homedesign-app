#!/bin/bash
# The rest of `npm run build` after prepare:data (already run by ci-order.sh on this copy): the web build, the API build
# (check-config inside it), the budget. Offline: the supplier images came from the cache (--offline).
set -o pipefail
cd "$(dirname "$0")/../build-s1314/site"
export PATH=/opt/node22/bin:$PATH
date -u +%H:%M:%S
npm run build -w @hd/web && npm run build -w @hd/api && npm run budget
echo "build exit $?"
date -u +%H:%M:%S
