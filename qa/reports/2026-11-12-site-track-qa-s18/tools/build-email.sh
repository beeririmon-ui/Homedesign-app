#!/bin/bash
# QA S18, question 4b: the email-mode test build (setup-email-copy.sh): build-copy, check-config, the web build,
# check-promises (with a sending provider it checks only the build's choice), and the copy the web shipped.
set -o pipefail
source "$(dirname "$0")/noNet.sh"
QA=$(cd "$(dirname "$0")/.." && pwd)
cd "$QA/build-s18-email/site"
date -u +"=== build-copy %H:%M:%S"; npm run copy || { echo "build-copy FAILED"; exit 1; }
date -u +"=== check-config %H:%M:%S"; npm run check:config -w @hd/api; echo "check-config exit $?"
date -u +"=== web build %H:%M:%S"; npm run build -w @hd/web || { echo "web build FAILED"; exit 2; }
date -u +"=== check-promises %H:%M:%S"; npm run check:promises -- --json="$QA/data/check-promises-email.json"; echo "check-promises exit $?"
date -u +"=== copy in the bundle %H:%M:%S"
f=$(ls web/dist/assets/copy-*.js); echo "$f"; node -e 'const s=require("fs").readFileSync(process.argv[1],"utf8");for(const w of ["יישלחו לאימייל","עדכנו אותי כשחוזר","נעדכן אותך במייל","שלחנו לאימייל שלכם","חשבונית מס נשלחת במייל","דיוור שיווקי נשלח רק אם","הוא נפתח רק בדפדפן הזה","האתר לא שולח דיוור"])console.log((s.includes(w)?"in   ":"out  ")+w)' "$f"
date -u +"=== done %H:%M:%S"
