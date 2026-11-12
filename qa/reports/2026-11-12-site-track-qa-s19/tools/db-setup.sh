#!/bin/bash
# The copy's own local D1 (site/.wrangler-state): the seed SQL (api `seed:sql`, from the copy's own .generated), then
# migrate (non-interactive) and seed. Never db:reset, never the live tree's state. QA_COPY picks another copy.
source "$(dirname "$0")/noNet.sh"
export CI=true
COPY=${QA_COPY:-$(dirname "$0")/../build-s19/site}
cd "$COPY/api"
W="node ../node_modules/wrangler/wrangler-dist/qasrv19.js"
npx --no-install tsx scripts/seed.ts && $W d1 migrations apply DB --local --persist-to ../.wrangler-state && $W d1 execute DB --local --persist-to ../.wrangler-state --file ../.generated/seed.sql
