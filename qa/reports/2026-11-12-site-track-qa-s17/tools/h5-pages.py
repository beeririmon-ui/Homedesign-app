"""
qa-agent, S17 (2026-11-12), QA note ה5: every product page of a build (web/dist/p/*/index.html, as prerendered): does it
have a picture (the gallery's <img>), its materials row, its notes, and any field that says its value is unknown
("לא צוין", "לא ידוע", "unknown"…), and any "בתמונה" note on a page without a picture.
    python3 -I h5-pages.py <dist> <label>
"""
import sys, os, re, json, html
dist, label = sys.argv[1], sys.argv[2]
UNKNOWN = re.compile(r'לא\s+(?:צוין|מצוין|צויין|ידוע|ידועה|ברור|מוגדר|הוגדר)|אינו\s+ידוע|\bunknown\b|\bN/?A\b|not stated|unspecified', re.I)
rows = []
for slug in sorted(os.listdir(os.path.join(dist, 'p'))):
    f = os.path.join(dist, 'p', slug, 'index.html')
    if not os.path.exists(f): continue
    s = open(f, encoding='utf8').read()
    main = re.search(r'<main.*?</main>', s, re.S)
    body = main.group(0) if main else s
    gallery = re.search(r'<section class="gallery".*?</section>', body, re.S)
    imgs = re.findall(r'<img [^>]*src="([^"]+)"', gallery.group(0)) if gallery else []
    specs = re.search(r'<dl class="specs-list">(.*?)</dl>', body, re.S)
    spec = dict(zip([html.unescape(re.sub('<[^>]+>', '', x)) for x in re.findall(r'<dt>(.*?)</dt>', specs.group(1))], [html.unescape(re.sub('<[^>]+>', '', x)) for x in re.findall(r'<dd>(.*?)</dd>', specs.group(1))])) if specs else {}
    notes = [html.unescape(re.sub('<[^>]+>', '', x)) for x in re.findall(r'<li>(.*?)</li>', re.search(r'<ul class="notes-list">(.*?)</ul>', body, re.S).group(1))] if re.search(r'<ul class="notes-list">', body) else []
    text = html.unescape(re.sub(r'<script.*?</script>|<style.*?</style>', '', body, flags=re.S))
    text = re.sub(r'<[^>]+>', ' ', text)
    unknown = sorted(set(m.group(0) for m in UNKNOWN.finditer(text)))
    rows.append({'page': slug, 'pictures': len(imgs), 'picture_kinds': sorted(set(re.findall(r'data-kind="([^"]+)"', gallery.group(0)))) if gallery else [], 'materials': spec.get('חומרים'), 'notes': notes, 'unknown_words': unknown, 'picture_note_without_picture': bool(not imgs and any(n.strip().startswith('בתמונה') for n in notes))})
no_pic = [r for r in rows if not r['pictures']]
bad = [r for r in rows if r['unknown_words'] or r['picture_note_without_picture']]
holders = [r for r in rows if 'magazine-holder' in r['page']]
out = {'label': label, 'pages': len(rows), 'without_a_picture': [r['page'] for r in no_pic], 'pages_with_an_issue': bad, 'magazine_holders': holders, 'picture_notes_shown': [(r['page'], r['picture_kinds'], [n for n in r['notes'] if n.startswith('בתמונה')]) for r in rows if any(n.startswith('בתמונה') for n in r['notes'])]}
json.dump(out, open(os.path.join(os.environ.get('QA_DATA', '.'), f'h5-pages-{label}.json'), 'w'), ensure_ascii=False, indent=1)
print(f"QA ה5 {label}: {len(rows)} product pages, {len(no_pic)} without a picture, {len(bad)} with an unknown value or a picture note without a picture")
for r in holders: print(f"  {r['page']}: pictures {r['pictures']} {r['picture_kinds']}, materials {r['materials']!r}, notes {r['notes']}")
for p, k, n in out['picture_notes_shown']: print(f"  'בתמונה' shown on {p} beside {k}: {n}")
