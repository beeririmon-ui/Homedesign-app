#!/bin/bash
# The copy's Worker on 127.0.0.1:8799 with its own D1 (site/.wrangler-state), ENVIRONMENT=preview-local, and a dummy
# webhook secret on the command line only (no .dev.vars). Extra --var pairs can be passed as arguments.
cd "$(dirname "$0")/../build-s1112/site/api"
exec env PATH=/opt/node22/bin:$PATH node ../node_modules/wrangler/wrangler-dist/qasrv1112.js dev --port 8799 --ip 127.0.0.1 --local \
  --persist-to ../.wrangler-state --var ENVIRONMENT:preview-local --var PAYMENT_WEBHOOK_SECRET:qa-dummy-not-a-key-1111 "$@"
