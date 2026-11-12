#!/bin/bash
# QA S18, question 4b: a test build with a VALID provider, to see the email lines come back. No provider exists, so in
# this copy only (never the repo): shared/src/email.ts lists a test provider `qa-test` (EMAIL_PROVIDERS = ['qa-test']),
# and api/wrangler.jsonc names it at the top level and in production. Same commit (3013d630), site/ re-extracted from git;
# node_modules, the supplier cache and the generated media hard-linked from the flag copy, .generated and web/story/test
# copied (prepare:data's output does not depend on EMAIL_PROVIDER, only build-copy's .generated/copy.he.json does, and
# it is rebuilt here). Then: build-copy, the web build, check-promises, check-config.
set -euo pipefail
QA=$(cd "$(dirname "$0")/.." && pwd)
bash "$QA/tools/setup-public-copy.sh" email
SRC=$QA/build-s18/site
DST=$QA/build-s18-email/site
cp -a "$SRC/.generated" "$DST/.generated"
mkdir -p "$DST/web/public" && cp -al "$SRC/web/public/media" "$DST/web/public/media"
cp -a "$SRC/web/story" "$DST/web/story"
cp -a "$SRC/web/test/story" "$DST/web/test/story" 2>/dev/null || true
cp -a "$SRC/web/test/index.html" "$DST/web/test/index.html"
cp "$SRC/api/.dev.vars" "$DST/api/.dev.vars"
cp "$SRC/node_modules/wrangler/wrangler-dist/qasrv18.js" "$DST/node_modules/wrangler/wrangler-dist/qasrv18.js" 2>/dev/null || true
sed -i "s/export const EMAIL_PROVIDERS: readonly string\[\] = \[\];/export const EMAIL_PROVIDERS: readonly string[] = ['qa-test'];/" "$DST/shared/src/email.ts"
grep -n "EMAIL_PROVIDERS: readonly" "$DST/shared/src/email.ts"
sed -i 's/"EMAIL_PROVIDER": "UNDECIDED"/"EMAIL_PROVIDER": "qa-test"/g' "$DST/api/wrangler.jsonc"
grep -n '"EMAIL_PROVIDER"' "$DST/api/wrangler.jsonc"
