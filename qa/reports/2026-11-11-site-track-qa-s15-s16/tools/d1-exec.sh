#!/bin/bash
# One SQL statement on the copy's own local D1 (site/.wrangler-state), never the live tree's.
COPY=${QA_COPY:-$(dirname "$0")/../build-s1516/site}
cd "$COPY/api"
exec env PATH=/opt/node22/bin:$PATH node ../node_modules/wrangler/wrangler-dist/qasrv1516.js d1 execute DB --local --persist-to ../.wrangler-state --command "$1"
