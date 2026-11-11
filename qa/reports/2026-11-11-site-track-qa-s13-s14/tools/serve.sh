#!/bin/bash
# The copy's Worker on 127.0.0.1:8799 with its own D1 (site/.wrangler-state), ENVIRONMENT=preview-local, and a dummy
# webhook secret on the command line only. The copy's api/.dev.vars holds only a dummy ADMIN_DEV_TOKEN (the e2e helper
# reads it there); no webhook secret is written anywhere. Extra --var pairs can be passed as arguments.
cd "$(dirname "$0")/../build-s1314/site/api"
exec env PATH=/opt/node22/bin:$PATH node ../node_modules/wrangler/wrangler-dist/qasrv1314.js dev --port ${QA_PORT:-8799} --ip 127.0.0.1 --local \
  --persist-to ../.wrangler-state --var ENVIRONMENT:preview-local --var PAYMENT_WEBHOOK_SECRET:qa-dummy-not-a-key-1314 "$@"
