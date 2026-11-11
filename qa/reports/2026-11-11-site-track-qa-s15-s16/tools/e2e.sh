#!/bin/bash
# The full e2e and a11y projects of the copy, against my own server (serve.sh on 8799), as the CI runs them after the build.
cd "$(dirname "$0")/../build-s1516/site"
export PATH=/opt/node22/bin:$PATH HD_BASE_URL=http://127.0.0.1:${QA_PORT:-8799}
date -u +"=== e2e %H:%M:%S"
npx playwright test --project=e2e --reporter=list; echo "e2e exit $?"
date -u +"=== a11y %H:%M:%S"
npx playwright test --project=a11y --reporter=list; echo "a11y exit $?"
date -u +"=== done %H:%M:%S"
