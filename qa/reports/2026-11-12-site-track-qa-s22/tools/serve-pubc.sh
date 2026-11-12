#!/bin/bash
# The public build (HD_PUBLIC=1, built with a test contact made at run time, tmp/wrangler-contact.jsonc, never in the repo)
# served on 127.0.0.1:8841 by serve.sh with its own D1, and the same contact values as --var (read from tmp/contact.env).
QA=$(cd "$(dirname "$0")/.." && pwd)
set -a; source "$QA/tmp/contact.env"; set +a
QA_COPY=$QA/build-s22-pubc/site QA_PORT=8841 exec bash "$(dirname "$0")/serve.sh" --var "CONTACT_EMAIL:$QA_CONTACT_EMAIL" --var "CONTACT_PHONE:$QA_CONTACT_PHONE" "$@"
