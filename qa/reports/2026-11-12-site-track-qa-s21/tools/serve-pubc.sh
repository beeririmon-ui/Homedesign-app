#!/bin/bash
# The public build (HD_PUBLIC=1, built with my test contact config through HD_WRANGLER) served on 127.0.0.1:8831 by
# serve.sh with its own D1, and the same test contact values as --var (as in QA S20).
QA=$(cd "$(dirname "$0")/.." && pwd)
QA_COPY=$QA/build-s21-pubc/site QA_PORT=8831 exec bash "$(dirname "$0")/serve.sh" --var CONTACT_EMAIL:info@hd-qa.co.il --var CONTACT_PHONE:04-8123456 "$@"
