#!/bin/bash
# The copy's own local D1 (site/.wrangler-state): migrate and seed (the seed SQL the build wrote), never db:reset, never
# the live tree's. QA_COPY picks another copy.
source "$(dirname "$0")/noNet.sh"
COPY=${QA_COPY:-$(dirname "$0")/../build-s22/site}
cd "$COPY/api"
W="node ../node_modules/wrangler/wrangler-dist/qasrv22.js"
npx --no-install tsx scripts/seed.ts && $W d1 migrations apply DB --local --persist-to ../.wrangler-state && $W d1 execute DB --local --persist-to ../.wrangler-state --file ../.generated/seed.sql
