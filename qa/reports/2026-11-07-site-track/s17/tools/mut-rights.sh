#!/bin/bash
# S17, QA ת45: QA's mutations of a public build (qa/reports/2026-11-11-site-track-qa-s15-s16/tools/mut-rights.sh), each
# against the content-based gate (`check:rights` with HD_PUBLIC=1, on a copy of the public dist: --dist=), and QA's own scan.
#   R0  the clean public build
#   R1  the picture at its own path                    R2  the same bytes as media/og/look-1.webp + og:image
#   R3  og:image hotlinked to the supplier's CDN       R4  the picture inlined as a data: URI
#   R6  the story's own copies (media/story/products, as a flag build ships them): the public build's story ledger is
#       empty (the rule withheld them), so only the pixels can find them
# Run from site/, right after `HD_PUBLIC=1 npm run build`, with STORY_COPIES=<a saved copy of a flag build's
# web/public/media/story/products>. Writes data/mut-rights.log and data/rights-r*.json beside this folder.
set -u
cd "$(dirname "$0")/../../../../../site"
S17=$(cd ../qa/reports/2026-11-07-site-track/s17 && pwd)
T=${SCRATCH:-$(mktemp -d)}
export HD_PUBLIC=1
rm -rf "$T/dist-clean" && cp -a web/dist "$T/dist-clean"
check() { # $1 name, $2 dist
  npx --no-install tsx tools/check-image-rights.ts --dist="$2" --json="$S17/data/rights-$1.json" > "$T/rights.log" 2>&1
  local e=$?
  grep -E "by content|by bytes|by pixels|by host|by data-uri|a file of|names products" "$T/rights.log" | head -4 | cut -c1-260 | sed 's/^/    /'
  echo "    check:rights exit $e"
}
scan() { NODE_PATH=$PWD/node_modules node ../qa/reports/2026-11-11-site-track-qa-s15-s16/tools/rights-scan.mjs "$1" web/public/media/products .cache/supplier-images ../data/products "$S17/data/qa-scan-$2.json" | head -1 | sed 's/^/    QA scan: /'; }
fresh() { rm -rf "$T/d" && cp -a "$T/dist-clean" "$T/d"; }
ID=$(node -e "const l=require('./.generated/rights/shop.json');const e=l.entries.find(x=>x.source==='shop'&&x.rights!=='confirmed'&&/\/opt-/.test(x.file));console.log(e.file)")
PAGE=$(ls -d "$T"/dist-clean/p/*/ | head -1 | sed "s#$T/dist-clean/##")index.html
CARDURL=$(grep -rhoE 'https://ae01\.alicdn\.com/kf/[A-Za-z0-9_./-]+\.jpg' ../data/products | head -1)
echo "the picture: $ID ($(stat -c %s "$ID") B); the page: $PAGE; the hotlink: ${CARDURL:0:60}…"
echo "=== R0 the clean public build"; check r0 "$T/dist-clean"; scan "$T/dist-clean" r0
echo "=== R1 at its own path"; fresh; P=$(echo "$ID" | sed 's#web/public/##'); mkdir -p "$T/d/$(dirname "$P")" && cp "$ID" "$T/d/$P"; check r1 "$T/d"
echo "=== R2 under another name, as og:image"; fresh; mkdir -p "$T/d/media/og" && cp "$ID" "$T/d/media/og/look-1.webp"
sed -i 's#</head>#<meta property="og:image" content="https://example.co.il/media/og/look-1.webp"></head>#' "$T/d/$PAGE"; check r2 "$T/d"; scan "$T/d" r2
echo "=== R3 a hotlink to the supplier CDN as og:image"; fresh; sed -i "s#</head>#<meta property=\"og:image\" content=\"$CARDURL\"></head>#" "$T/d/$PAGE"; check r3 "$T/d"; scan "$T/d" r3
echo "=== R4 inlined as a data: URI"; fresh
node -e "const fs=require('fs');const b=fs.readFileSync(process.argv[1]).toString('base64');const p=process.argv[2];fs.writeFileSync(p,fs.readFileSync(p,'utf8').replace('</body>','<img alt=\"\" src=\"data:image/webp;base64,'+b+'\"></body>'))" "$ID" "$T/d/$PAGE"
check r4 "$T/d"; scan "$T/d" r4
echo "=== R6 the story's own copies ($(find "$STORY_COPIES" -type f | wc -l) files), the story ledger of this public build: $(node -e "console.log(require('./.generated/rights/story.json').entries.length)") entries"
fresh; mkdir -p "$T/d/media/story" && cp -a "$STORY_COPIES" "$T/d/media/story/products"; check r6 "$T/d"; scan "$T/d" r6
node -e "const r=require('$S17/data/rights-r6.json');const f=r.findings;console.log('    R6 found: '+new Set(f.map(x=>x.where)).size+' files, by '+JSON.stringify(r.by_content.found))"
rm -rf "$T/d"
