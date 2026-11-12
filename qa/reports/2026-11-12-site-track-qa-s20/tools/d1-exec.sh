#!/bin/bash
# One SQL statement on a copy's own local D1 (site/.wrangler-state), never the live tree's.
source "$(dirname "$0")/noNet.sh"
COPY=${QA_COPY:-$(dirname "$0")/../build-s20/site}
cd "$COPY/api"
exec node ../node_modules/wrangler/wrangler-dist/qasrv20.js d1 execute DB --local --persist-to ../.wrangler-state --json --command "$1"
