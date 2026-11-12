#!/bin/bash
# One SQL statement on the copy's own local D1 (site/.wrangler-state), never the live tree's.
source "$(dirname "$0")/noNet.sh"
COPY=${QA_COPY:-$(dirname "$0")/../build-s17/site}
cd "$COPY/api"
exec node ../node_modules/wrangler/wrangler-dist/qasrv17.js d1 execute DB --local --persist-to ../.wrangler-state --command "$1"
