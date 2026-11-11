#!/bin/bash
# The copy's Worker on 127.0.0.1:${QA_PORT:-8799} with its own D1 (site/.wrangler-state), ENVIRONMENT=preview-local, and a
# dummy webhook secret on the command line only. The copy's api/.dev.vars holds only a dummy ADMIN_DEV_TOKEN (the e2e
# helper reads it there); no webhook secret is written anywhere. QA_COPY picks another copy (the public build's).
COPY=${QA_COPY:-$(dirname "$0")/../build-s1516/site}
cd "$COPY/api"
exec env PATH=/opt/node22/bin:$PATH node ../node_modules/wrangler/wrangler-dist/qasrv1516.js dev --port ${QA_PORT:-8799} --ip 127.0.0.1 --local \
  --persist-to ../.wrangler-state --var ENVIRONMENT:preview-local --var PAYMENT_WEBHOOK_SECRET:qa-dummy-not-a-key-1516 "$@"
