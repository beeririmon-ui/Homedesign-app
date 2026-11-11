#!/bin/bash
# S15, the image-rights gate (`check:rights`, HD_PUBLIC=1) against my mutations of the public build, each followed by my own
# byte-level scan (rights-scan.mjs). The supplier picture used is a real one with usage_rights unclear: an option picture
# of the first withheld product (from the flag build's media/products).
#   R1  the picture back at its own path (dist/media/products/<id>/<opt>.640.webp)
#   R2  the same bytes under another name (dist/media/og/<slug>.webp), named by a product page's og:image
#   R3  a hotlink to the supplier's own CDN (the card's picture URL) as a product page's og:image
#   R4  the picture inlined as a data: URI in a product page
#   R5  the source: the public build reads the full supplier manifest (the vite alias removed), rebuilt
# The dist is restored from a copy after R1–R4, and rebuilt clean after R5.
cd "$(dirname "$0")/../build-s1516-pub/site"
export PATH=/opt/node22/bin:$PATH HD_PUBLIC=1 NODE_PATH=$PWD/node_modules
QA=$(cd ../.. && pwd)
T=$QA/s1516-tmp; D=$QA/s1516-data
FLAG=$QA/build-s1516/site/web/dist/media/products
rm -rf $T/dist-clean && cp -a web/dist $T/dist-clean
check() { npx tsx tools/check-image-rights.ts > $T/rights.log 2>&1; local e=$?; head -c 600 $T/rights.log | sed 's/^/    /'; echo "    check:rights exit $e"; }
scan() { node $QA/s1516-tools/rights-scan.mjs web/dist $FLAG .cache/supplier-images ../data/products $D/rights-scan-$1.json | head -2 | sed 's/^/    /'; }
ID=$(ls $FLAG | head -1); OPT=$(ls $FLAG/$ID | grep -E '^opt-.*\.640\.webp$' | head -1); [ -z "$OPT" ] && OPT=$(ls $FLAG/$ID | head -1)
PAGE=$(ls -d web/dist/p/*/ | head -1)index.html
CARDURL=$(grep -rhoE 'https://ae01\.alicdn\.com/kf/[A-Za-z0-9_./-]+\.jpg' ../data/products | head -1)
echo "the picture: $ID/$OPT ($(stat -c %s $FLAG/$ID/$OPT) B); the page: ${PAGE#web/dist/}; the hotlink: ${CARDURL:0:60}…"
echo "=== R0 the clean public build"; check; scan r0
echo "=== R1 at its own path"; mkdir -p web/dist/media/products/$ID && cp $FLAG/$ID/$OPT web/dist/media/products/$ID/; check; scan r1
rm -rf web/dist && cp -a $T/dist-clean web/dist
echo "=== R2 under another name, as og:image"; mkdir -p web/dist/media/og && cp $FLAG/$ID/$OPT web/dist/media/og/look-1.webp
sed -i 's#</head>#<meta property="og:image" content="https://example.co.il/media/og/look-1.webp"></head>#' $PAGE; check; scan r2
rm -rf web/dist && cp -a $T/dist-clean web/dist
echo "=== R3 a hotlink to the supplier CDN as og:image"; sed -i "s#</head>#<meta property=\"og:image\" content=\"$CARDURL\"></head>#" $PAGE; check; scan r3
rm -rf web/dist && cp -a $T/dist-clean web/dist
echo "=== R4 inlined as a data: URI"; python3 -I - "$FLAG/$ID/$OPT" "$PAGE" <<'PY'
import sys,base64
b=base64.b64encode(open(sys.argv[1],'rb').read()).decode()
p=sys.argv[2]; s=open(p,encoding='utf8').read()
s=s.replace('</body>','<img alt="" src="data:image/webp;base64,'+b+'"></body>',1)
open(p,'w',encoding='utf8').write(s)
PY
check; scan r4
rm -rf web/dist && cp -a $T/dist-clean web/dist
echo "=== R5 the source: the public build reads the full manifest (the alias removed), rebuilt"
cp web/vite.config.ts $T/vite.config.ts.bak
sed -i 's#...(PUBLIC ? \[{ find: /^@generated\\/supplier-images\\.json\$/, replacement: PUBLIC_SUPPLIER }\] : \[\]),#// QA R5: alias removed#' web/vite.config.ts
grep -n "QA R5" web/vite.config.ts
npm run build -w @hd/web > $T/r5-web.log 2>&1; echo "    web build exit $?"
check; scan r5
cp $T/vite.config.ts.bak web/vite.config.ts
echo "=== restored: rebuilt clean"; npm run build -w @hd/web > $T/r6-web.log 2>&1; echo "    web build exit $?"; check; scan r6
diff -q web/vite.config.ts $QA/build-s1516/site/web/vite.config.ts && echo "vite.config.ts identical to the clean copy"
