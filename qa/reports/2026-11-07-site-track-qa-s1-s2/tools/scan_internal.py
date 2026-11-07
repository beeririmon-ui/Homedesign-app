"""qa-agent, 2026-11-07 (interface track S1/S2): no internal information on the public story pages.

    python3 qa/reports/2026-11-07-site-track-qa-s1-s2/tools/scan_internal.py [out.json]

Scans every built file a story page can load (site/web/dist/story/**, the story JS/CSS chunks it references, and the
media folder's text files) for: cost, margin, landed / no-loss / economics fields, supplier names as fields, supplier
hosts or listing URLs, supplier SKU codes (CJ…, AliExpress item ids), USD amounts. Product slugs (our own ids, e.g.
vase-aliexpress-…-589009) are reported apart: they name the source and carry part of the listing id.
"""
import json, re, sys, os, glob
SITE = '/home/user/homedesign-app/site'
DIST = f'{SITE}/web/dist'
out_path = sys.argv[1] if len(sys.argv) > 1 else '/dev/stdout'
pages = sorted(glob.glob(f'{DIST}/story/**/index.html', recursive=True))
chunks = set()
for p in pages:
    for m in re.findall(r'(?:src|href)="(/assets/[^"]+\.(?:js|css))"', open(p, encoding='utf8').read()):
        chunks.add(m)
# the chunks a story entry imports (one level of static/dynamic imports)
for c in list(chunks):
    if c.endswith('.js'):
        for m in re.findall(r'["\'](\./[^"\']+\.js|/assets/[^"\']+\.js)["\']', open(DIST + c, encoding='utf8').read()):
            chunks.add('/assets/' + m[2:] if m.startswith('./') else m)
media_text = [f for f in glob.glob(f'{DIST}/media/story/**/*', recursive=True) if f.endswith(('.json', '.txt', '.html'))]
files = pages + [DIST + c for c in sorted(chunks)] + media_text
PATTERNS = {
    'cost/margin words (field names)': r'"(cost[_a-z]*|margin[_a-z]*|landed[_a-z]*|no_loss[_a-z]*|economics|unit_economics|highest_comparable[_a-z]*|price_source|fx_usd_ils|shipping_usd[_a-z]*|cost_usd[_a-z]*)"\s*:',
    'supplier field': r'"(supplier|supplier_image|supplier_url|name_supplier|source_path|fulfillment_source|shipping_line)"\s*:',
    'supplier hosts / listing URLs': r'(cjdropshipping|aliexpress\.(com|us|ru)|alicdn|ae01\.|zendrop\.com|1688\.com|alibaba\.com|cf\.cjdropshipping)',
    'any external https URL': r'https?://(?!127\.0\.0\.1|localhost|example\.co\.il|www\.w3\.org)[a-z0-9.-]+\.[a-z]{2,}[^\s"\'<>]*',
    'supplier SKU codes': r'\bCJ[A-Z]{2,4}\d{6,}[A-Z]{0,3}\b|\b1005\d{9,}\b',
    'USD amounts': r'\$\s?\d|\bUSD\b',
}
hits = {k: [] for k in PATTERNS}
for f in files:
    t = open(f, encoding='utf8', errors='replace').read()
    for k, rx in PATTERNS.items():
        for m in re.finditer(rx, t, re.I if k != 'supplier SKU codes' else 0):
            hits[k].append({'file': f.replace(SITE + '/', ''), 'match': m.group(0)[:80], 'context': t[max(0, m.start() - 60):m.end() + 40].replace('\n', ' ')})
# product slugs with a source in them, in the public URLs
slugs = sorted({os.path.basename(os.path.dirname(p)) for p in pages if '/p/' in p})
src_slugs = [s for s in slugs if re.search(r'-(aliexpress|cj|zendrop)-', s)]
id_slugs = [s for s in src_slugs if re.search(r'-\d{6}$', s)]
res = {'files_scanned': len(files), 'pages': len(pages), 'chunks': sorted(chunks), 'hits': {k: v[:20] for k, v in hits.items()}, 'counts': {k: len(v) for k, v in hits.items()},
       'detail_slugs': len(slugs), 'slugs_naming_the_source': src_slugs, 'slugs_ending_in_a_listing_number': id_slugs}
json.dump(res, open(out_path, 'w'), ensure_ascii=False, indent=1)
print(json.dumps({'files': len(files), 'counts': res['counts'], 'slugs_naming_source': len(src_slugs), 'slugs_with_number': id_slugs}, ensure_ascii=False))
