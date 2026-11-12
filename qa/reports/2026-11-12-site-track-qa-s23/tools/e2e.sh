#!/bin/bash
# The full e2e and a11y projects of a copy, against my own server (serve.sh), as the CI runs them after the build.
source "$(dirname "$0")/noNet.sh"
cd "${QA_COPY:-$(dirname "$0")/../build-s23/site}"
export HD_BASE_URL=http://127.0.0.1:${QA_PORT:-8850}
date -u +"=== e2e %H:%M:%S"
npx --no-install playwright test --project=e2e --reporter=list "$@"; echo "e2e exit $?"
date -u +"=== a11y %H:%M:%S"
npx --no-install playwright test --project=a11y --reporter=list; echo "a11y exit $?"
date -u +"=== done %H:%M:%S"
