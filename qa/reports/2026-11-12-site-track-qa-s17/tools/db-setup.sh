#!/bin/bash
# The copy's own local D1 (site/.wrangler-state): migrate and seed (the seed SQL the build wrote), never db:reset, never
# the live tree's. QA_COPY picks another copy (the public build's).
source "$(dirname "$0")/noNet.sh"
COPY=${QA_COPY:-$(dirname "$0")/../build-s17/site}
cd "$COPY/api"
W="node ../node_modules/wrangler/wrangler-dist/qasrv17.js"
$W d1 migrations apply DB --local --persist-to ../.wrangler-state && $W d1 execute DB --local --persist-to ../.wrangler-state --file ../.generated/seed.sql
