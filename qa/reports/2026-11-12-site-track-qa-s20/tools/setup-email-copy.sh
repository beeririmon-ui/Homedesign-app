#!/bin/bash
# QA S20, ת62: a test build with a provider that declares ONLY `order_confirmation`. No provider exists, so in this copy
# only (never the repo): shared/src/email.ts lists test providers, each with what it declares (qa-oc: order_confirmation;
# qa-ship, qa-delay, qa-inv, qa-bis, qa-mkt: one each; qa-all: all six), and api/wrangler.jsonc names qa-oc at the top
# level (the flag build's environment). Same commit (8828cab9), site/ re-extracted from git; node_modules, the supplier
# cache and the generated media hard-linked from the flag copy, .generated / web/story / web/test copied (prepare:data's
# output does not depend on EMAIL_PROVIDER; build-copy's .generated/copy.he.json does, and it is rebuilt here).
set -euo pipefail
QA=$(cd "$(dirname "$0")/.." && pwd)
bash "$QA/tools/setup-public-copy.sh" email
SRC=$QA/build-s20/site
DST=$QA/build-s20-email/site
cp -a "$SRC/.generated" "$DST/.generated"
mkdir -p "$DST/web/public" && cp -al "$SRC/web/public/media" "$DST/web/public/media"
cp -a "$SRC/web/story" "$DST/web/story"
mkdir -p "$DST/web/test" && cp -a "$SRC/web/test/story" "$DST/web/test/story" && cp -a "$SRC/web/test/index.html" "$DST/web/test/index.html"
cp "$SRC/api/.dev.vars" "$DST/api/.dev.vars"
cp "$SRC/node_modules/wrangler/wrangler-dist/qasrv20.js" "$DST/node_modules/wrangler/wrangler-dist/qasrv20.js" 2>/dev/null || true
node -e '
const fs=require("fs");const f=process.argv[1];let s=fs.readFileSync(f,"utf8");
const a="export const EMAIL_PROVIDERS: EmailProviders = {};";
if(!s.includes(a)){console.error("anchor missing");process.exit(3)}
s=s.replace(a,"export const EMAIL_PROVIDERS: EmailProviders = { \"qa-oc\": [\"order_confirmation\"], \"qa-ship\": [\"shipping_update\"], \"qa-delay\": [\"delay_notice\"], \"qa-inv\": [\"invoice_email\"], \"qa-bis\": [\"back_in_stock\"], \"qa-mkt\": [\"marketing\"], \"qa-all\": [\"order_confirmation\", \"shipping_update\", \"delay_notice\", \"invoice_email\", \"back_in_stock\", \"marketing\"] }; // QA S20 test copy only");
fs.writeFileSync(f,s)' "$DST/shared/src/email.ts"
grep -n "EMAIL_PROVIDERS: EmailProviders" "$DST/shared/src/email.ts"
# the top level only (the flag build and wrangler dev read it); preview and production stay UNDECIDED
node -e '
const fs=require("fs");const f=process.argv[1];let s=fs.readFileSync(f,"utf8");
const a="\"EMAIL_PROVIDER\": \"UNDECIDED\",";const i=s.indexOf(a);if(i<0){console.error("anchor missing");process.exit(3)}
s=s.slice(0,i)+"\"EMAIL_PROVIDER\": \"qa-oc\","+s.slice(i+a.length);fs.writeFileSync(f,s)' "$DST/api/wrangler.jsonc"
grep -n '"EMAIL_PROVIDER"' "$DST/api/wrangler.jsonc"
