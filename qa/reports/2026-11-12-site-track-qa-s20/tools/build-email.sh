#!/bin/bash
# QA S20, ת62: the order_confirmation-only build (setup-email-copy.sh): build-copy, check-config, the web build, the API
# build, check-promises; then which copy lines the web shipped.
set -o pipefail
source "$(dirname "$0")/noNet.sh"
QA=$(cd "$(dirname "$0")/.." && pwd)
cd "$QA/build-s20-email/site"
date -u +"=== build-copy %H:%M:%S"; npm run copy || { echo "build-copy FAILED"; exit 1; }
node -e 'const c=require("./.generated/copy.he.json");console.log("capabilities",JSON.stringify(c.capabilities),"sends",c.sends);for(const [k,v] of Object.entries(c.strings))console.log("  "+k.padEnd(30)+JSON.stringify(v))'
date -u +"=== check-config %H:%M:%S"; npm run check:config -w @hd/api; echo "check-config exit $?"
date -u +"=== web build %H:%M:%S"; npm run build -w @hd/web > "$QA/data/build-email-web.log" 2>&1 || { echo "web build FAILED"; tail -20 "$QA/data/build-email-web.log"; exit 2; }
date -u +"=== api build %H:%M:%S"; npm run build -w @hd/api > "$QA/data/build-email-api.log" 2>&1 || { echo "api build FAILED"; tail -20 "$QA/data/build-email-api.log"; exit 3; }
date -u +"=== check-promises %H:%M:%S"; npm run check:promises -- --json="$QA/data/check-promises-email-oc.json"; echo "check-promises exit $?"
date -u +"=== the email lines in the bundle %H:%M:%S"
node -e '
const fs=require("fs");const src=JSON.parse(fs.readFileSync("copy/promises.he.json","utf8")).strings;
const js=fs.readdirSync("web/dist/assets").filter(f=>f.endsWith(".js")).map(f=>fs.readFileSync("web/dist/assets/"+f,"utf8")).join("\n");
const html=[];(function w(d){for(const e of fs.readdirSync(d,{withFileTypes:true})){const p=d+"/"+e.name;if(e.isDirectory())w(p);else if(p.endsWith(".html"))html.push(fs.readFileSync(p,"utf8"))}})("web/dist");
const all=js+html.join("\n");
for(const [k,e] of Object.entries(src)) if("email" in e && e.email) console.log((all.includes(e.email)?"IN   ":"out  ")+k.padEnd(30)+" needs "+JSON.stringify(e.needs))'
date -u +"=== done %H:%M:%S"
