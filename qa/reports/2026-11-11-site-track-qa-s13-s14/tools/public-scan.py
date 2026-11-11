"""qa-agent, 2026-11-11 (S13–S14 at a8104956): my own scan of the HD_PUBLIC=1 build (web/dist of the second copy).

  1. admin code: routes, headers, the screen's words, the admin's actions (S13: none of it may be in the public build)
  2. suppliers: names, CJ SKUs, listing numbers (11+ digits), internal fields (S7, ת12)
  3. what must not be built: house pages, media/house, story, test
  4. ת33: Latin in the visible text of every public page (units after a number and a standard's mark allowed), the
     Morandi triptych's page, and every card's `notes` (≥ 12 characters) searched for in the build

usage: python3 -I public-scan.py <dist> <repo> <out.json>
"""
import json
import os
import re
import sys
from html.parser import HTMLParser

dist, repo, out = sys.argv[1], sys.argv[2], sys.argv[3]
TEXT = re.compile(r"\.(html|js|css|json|txt|xml|svg|webmanifest)$|^_headers$|^_redirects$")
files = []
for root, _, names in os.walk(dist):
    for n in names:
        p = os.path.join(root, n)
        files.append(os.path.relpath(p, dist))

ADMIN = re.compile(
    r"/api/admin|/admin/|x-hd-dev-admin|ADMIN_DEV|cf-access|Cf-Access|requireAdmin|audit_log|invoice-check|mock-supplier|"
    r"cancel_requested|claim_lost|refund\.requested|ניהול הזמנות|נבדק על ידי אדם|ספק מדומה|דורש טיפול|בקשת ביטול נשלחה לספק|"
    r"supplier_shipments|credit_note|processCreditNote|NOTIFY_PROVIDER"
)
SUPPLIER = re.compile(r"\b(?:cj ?dropshipping|cjdropshipping|aliexpress|ali ?express|zendrop|alibaba|cainiao|1688|temu|dsers|eprolo|hypersku|yakkyofy)\b", re.I)
CJ_SKU = re.compile(r"\bCJ[A-Z]{2,6}\d{5,}[A-Z0-9-]*\b")
LISTING = re.compile(r"(?<![\d.])\d{11,}(?![\d.])")
FIELDS = re.compile(r'"(?:set_skus|supplier_sku|card_id|supplier_url|supplier_name|source_path|notes)"\s*:')

res = {"dist": dist, "files": len(files), "text_files": 0, "admin": [], "supplier": [], "cj_sku": [], "listing": [], "fields": [], "not_built": {}, "latin": [], "notes_found": [], "morandi": None}
for rel in files:
    base = os.path.basename(rel)
    if not TEXT.search(base):
        continue
    res["text_files"] += 1
    try:
        t = open(os.path.join(dist, rel), encoding="utf-8").read()
    except UnicodeDecodeError:
        continue
    for key, rx in (("admin", ADMIN), ("supplier", SUPPLIER), ("cj_sku", CJ_SKU), ("listing", LISTING), ("fields", FIELDS)):
        for m in rx.finditer(t):
            res[key].append(f"{rel}: {m.group(0)!r} …{t[max(0, m.start() - 40):m.end() + 40]!r}"[:240])
    if re.search(r"(^|/)admin(/|$)", rel):
        res["admin"].append(f"path {rel}")
for d in ("house", "media/house", "story", "media/story", "test", "media/test"):
    res["not_built"][d] = os.path.exists(os.path.join(dist, d))


class Visible(HTMLParser):
    def __init__(self):
        super().__init__()
        self.skip = 0
        self.out = []
        self.attrs_text = []

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript", "template"):
            self.skip += 1
        a = dict(attrs)
        for k, v in attrs:
            if k in ("alt", "title", "aria-label", "placeholder") and v:
                self.attrs_text.append(v)
        # the meta text a customer or a search engine reads (not viewport, robots, locale)
        if tag == "meta" and (a.get("name") in ("description",) or (a.get("property") or "").startswith("og:")) and a.get("property") != "og:locale" and a.get("property") != "og:url" and a.get("property") != "og:image" and a.get("content"):
            self.attrs_text.append(a["content"])

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript", "template") and self.skip:
            self.skip -= 1

    def handle_data(self, data):
        if not self.skip and data.strip():
            self.out.append(data.strip())


# allowed Latin: a unit right after a number (3000K, 90-260V, 5W, 220mm, 50x70cm), a standard's mark, the brand's own
# symbols; the rest is a finding
ALLOW = re.compile(r"^(?:CE|UL|IP\d{2}|EN\d*|LED|USB|E27|E14|GU10|RoHS|FSC|OEKO|TEX|WCAG|AA|RTL|SVG|AVIF|WebP|JPEG|PNG)$", re.I)
UNIT_AFTER_NUMBER = re.compile(r"\d[\d.,×x\-–]*\s?(?:[a-zA-Z]{1,3})\b")
for rel in files:
    if not rel.endswith(".html"):
        continue
    v = Visible()
    v.feed(open(os.path.join(dist, rel), encoding="utf-8").read())
    text = " ".join(v.out + v.attrs_text)
    stripped = UNIT_AFTER_NUMBER.sub(" ", text)
    stripped = re.sub(r"https?://\S+|\S+@\S+|\b[\w.-]+\.(?:co\.il|com|org)\b", " ", stripped)
    words = [w for w in re.findall(r"[A-Za-z][A-Za-z'’-]+", stripped) if not ALLOW.match(w)]
    if words:
        res["latin"].append({"page": rel, "words": sorted(set(words))[:30]})
    if "morandi" in rel.lower() or "מורנדי" in text:
        if res["morandi"] is None and "/p/" in "/" + rel:
            res["morandi"] = {"page": rel, "text": text[:600]}

# every card's notes (12+ characters) searched for in the build
notes = []
for root, _, names in os.walk(os.path.join(repo, "data/products")):
    for n in names:
        if n.endswith(".json"):
            try:
                c = json.load(open(os.path.join(root, n), encoding="utf-8"))
            except Exception:
                continue
            for k in ("notes", "note", "sourcing_notes"):
                v = c.get(k) if isinstance(c, dict) else None
                if isinstance(v, str) and len(v) >= 12:
                    notes.append((n, v))
                elif isinstance(v, list):
                    notes += [(n, x) for x in v if isinstance(x, str) and len(x) >= 12]
blob = ""
for rel in files:
    if TEXT.search(os.path.basename(rel)):
        try:
            blob += open(os.path.join(dist, rel), encoding="utf-8").read()
        except UnicodeDecodeError:
            pass
for n, v in notes:
    probe = v.strip()[:40]
    if probe and probe in blob:
        res["notes_found"].append(f"{n}: {probe!r}")
res["notes_checked"] = len(notes)
for k in ("admin", "supplier", "cj_sku", "listing", "fields"):
    res[k + "_count"] = len(res[k])
    res[k] = res[k][:40]
json.dump(res, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps({k: res[k] for k in res if k.endswith("_count") or k in ("files", "text_files", "not_built", "notes_checked")}, ensure_ascii=False))
print("latin pages:", len(res["latin"]), json.dumps(res["latin"][:12], ensure_ascii=False))
print("notes found:", res["notes_found"][:5])
print("morandi:", json.dumps(res["morandi"], ensure_ascii=False)[:700])
