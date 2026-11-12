#!/bin/bash
# The copy's Worker on 127.0.0.1:${QA_PORT:-8840} with its own D1 (site/.wrangler-state), ENVIRONMENT=preview-local, and a
# dummy webhook secret on the command line only. The copy's api/.dev.vars holds only a dummy ADMIN_DEV_TOKEN (the e2e
# helper reads it there); no webhook secret is written anywhere. QA_COPY picks another copy; extra args (e.g. --var
# CONTACT_EMAIL:…) go to wrangler.
source "$(dirname "$0")/noNet.sh"
COPY=${QA_COPY:-$(dirname "$0")/../build-s22/site}
cd "$COPY/api"
exec node ../node_modules/wrangler/wrangler-dist/qasrv22.js dev --port ${QA_PORT:-8840} --ip 127.0.0.1 --local \
  --persist-to ${QA_STATE:-../.wrangler-state} --var ENVIRONMENT:preview-local --var PAYMENT_WEBHOOK_SECRET:qa-dummy-not-a-key-22 "$@"
