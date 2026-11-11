#!/bin/bash
# The public build served by its own Worker (QA_PORT 8796): the old card-id addresses (ת41), the house address, the
# sitemap and robots, status_he and the old words, the supplier pictures' paths.
B=http://127.0.0.1:${QA_PORT:-8796}
D=$(dirname "$0")/../build-s1516-pub/site/web/dist
FULL=$(dirname "$0")/../build-s1516/site/.generated/catalog.full.json
echo "--- _redirects: $(wc -c < $D/_redirects) bytes, $(grep -c . $D/_redirects) lines"
python3 -I -c "
import json;c=json.load(open('$FULL'))
ids=[p['card_id'] for p in c['products'] if p.get('card_id') and p['card_id']!=p['id']]
print(len(ids));print('\n'.join(ids))" > $(dirname "$0")/../s1516-tmp/ids.txt 2>/dev/null || true
N=$(head -1 $(dirname "$0")/../s1516-tmp/ids.txt); echo "--- old card-id addresses: $N"
codes=$(tail -n +2 $(dirname "$0")/../s1516-tmp/ids.txt | while read id; do curl -s -o /dev/null -w "%{http_code}\n" "$B/p/$id/"; done | sort | uniq -c | tr '\n' ' '); echo "    status codes: $codes"
rm -f $(dirname "$0")/../s1516-tmp/ids.txt
for u in "/rooms/living-room/" "/rooms/living-room/?style=warm-modern" "/rooms/living-room/?style=japandi"; do
  h=$(curl -s "$B$u"); echo "--- $u: $(curl -s -o /dev/null -w '%{http_code}' "$B$u"); canonical $(echo "$h" | grep -oE '<link rel="canonical" href="[^"]+"' | sed 's/.*href=//'); title $(echo "$h" | grep -oE '<title>[^<]+' | sed 's/<title>//'); data-house $(echo "$h" | grep -oE 'data-house="[^"]+"' | head -1)"
done
echo "--- sitemap: $(curl -s $B/sitemap.xml | grep -c '<loc>') urls; with ?style: $(curl -s $B/sitemap.xml | grep -c 'style=')"
for w in "עוד לא באתר הציבורי" "וריאציות" "(סט)" "media/products/" "warm-modern" "מודרני חם"; do echo "--- '$w' in public dist (html/js/css/json): $(grep -rlF --include=*.html --include=*.js --include=*.css --include=*.json --include=*.txt --include=*.xml -- "$w" $D | wc -l) files"; done
echo "--- media/products in public dist: $(ls $D/media/products 2>/dev/null | wc -l) entries"
