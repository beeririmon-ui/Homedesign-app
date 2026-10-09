#!/usr/bin/env python3
"""(Re)build data/sources/seen.json from what is already in the repo. Safe to re-run: it merges into the
existing registry, never downgrades a status, and keeps entries that agents added by hand.

Sources, strongest first:
  1. data/products/**/*.json            -> status card   (pid from supplier.product_url, vids from notes, sku)
  2. data/leads/**/*.md|txt, sections whose heading says "Rejected" / "do not re-check"
                                         -> status rejected, reason = the line
     sections "Opened but not carded"   -> status seen, opened=true (do not re-open)
  3. any other CJ pid (19 digits) or AliExpress id mentioned in data/leads/** (md, txt, json)
                                         -> status seen, opened=false (known; read the note before opening)

Usage: python3 scripts/sourcing/build_seen.py [--dry-run]
"""
import glob, json, os, re, subprocess, sys

sys.path.insert(0, os.path.dirname(__file__))
import registry  # noqa: E402

REPO = registry.REPO
BY_FOLDER_ROOM = {"bath": "bath", "corridor": "corridor", "dining": "dining-room", "entrance": "hall",
                  "kids": "kids", "master": "master", "work": "work", "pool": None}
CJ_URL = re.compile(r"cjdropshipping\.com/product/[^\s\"')]*?-p-([0-9A-Za-z-]+)\.html", re.I)
AE_URL = re.compile(r"aliexpress\.[a-z.]+/(?:item|i)/(\d{12,17})\.html", re.I)
URL = re.compile(r"https?://\S+")
VID = re.compile(r"\bvids?\b[^0-9\n]{0,25}(\d{19})", re.I)
CJ_ID = re.compile(r"(?<![\d.])(\d{19})(?!\d)|\b([0-9A-F]{8}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{12})\b")
AE_ID = re.compile(r"(?<!\d)((?:1005|3256)\d{12})(?!\d)")
DATE_IN_NAME = re.compile(r"(\d{4}-\d{2}-\d{2})")
REJECT_HEAD = re.compile(r"reject|do not re-?check|not carded", re.I)
SKIP_HEAD = re.compile(r"re-?check of existing", re.I)
CATEGORY_LINE = re.compile(r"categor|getCategory|useful ids|\bid is\b", re.I)
OPENED_LINE = re.compile(r"✗|\bopened\b|product call", re.I)
NOT_OPENED = re.compile(r"not opened|unopened", re.I)


def category_ids():
    p = os.path.join(REPO, "docs", "suppliers", "cj-categories.md")
    txt = open(p, encoding="utf-8").read() if os.path.exists(p) else ""
    return {m.group(1) or m.group(2) for m in CJ_ID.finditer(txt)}


def ae_norm(i):
    # aliexpress.us item ids (3256...) are the same item as aliexpress.com (1005...).
    return "1005" + i[4:] if i.startswith("3256") and len(i) == 16 else i


def rel(p):
    return os.path.relpath(p, REPO)


def card_dates():
    """first commit date for each card file (git), else None."""
    out = {}
    try:
        log = subprocess.run(["git", "-C", REPO, "log", "--diff-filter=A", "--name-only", "--format=@%ad",
                              "--date=short", "--", "data/products"], capture_output=True, text=True).stdout
    except OSError:
        return out
    d = None
    for line in log.splitlines():
        if line.startswith("@"):
            d = line[1:]
        elif line.strip():
            out[line.strip()] = d  # log is newest first, so the last write is the oldest add
    return out


def card_room_slot(path, card):
    parts = rel(path).split(os.sep)  # data/products/<a>/<b?>/<file>
    top = parts[2]
    if top in BY_FOLDER_ROOM:
        room = BY_FOLDER_ROOM[top]
        return ("%s/%s" % (room, card.get("slot"))) if room and card.get("slot") else None
    return "living-room/%s" % card.get("slot")


def clean(line, n=220):
    s = re.sub(r"[*`_|]+", "", line).strip(" -•\t")
    s = re.sub(r"\s+", " ", s)
    return s[:n]


def snippet_after(line, m, ids):
    """Text from this id to the next id in the same line (the per-item reason)."""
    start, nxt = m.end(), len(line)
    for m2 in ids:
        if m2.start() > m.start():
            nxt = min(nxt, m2.start())
    s = clean(line[start:nxt]).strip(" ,;:()–-")
    return s if len(s) >= 8 else clean(line)


def main():
    dry = "--dry-run" in sys.argv
    with registry.locked():
        reg = registry.load()
        today = registry.today()
        dates = card_dates()
        known_vids = set()
        cats = category_ids()
        reg.setdefault("cards", {})
        n_cards = 0
        # 1. cards
        for f in sorted(glob.glob(os.path.join(REPO, "data/products/**/*.json"), recursive=True)):
            card = json.load(open(f))
            sup = card.get("supplier") or {}
            url = sup.get("product_url") or ""
            m = CJ_URL.search(url)
            if not m:
                ma = AE_URL.search(url)
                if not ma:
                    print("WARN no supplier id in", rel(f), url, file=sys.stderr)
                    continue
                key = "aliexpress:" + ae_norm(ma.group(1))
            else:
                key = "cj:" + m.group(1)
            notes = card.get("notes") or ""
            vids = VID.findall(notes)
            known_vids.update(vids)
            reason = "card %s (%s)" % (card.get("id"), card.get("status"))
            registry.add(key, "card", reason, by="sourcing-agent", slot=card_room_slot(f, card),
                         card_id=card.get("id"), opened=True, source=rel(f), vids=vids,
                         skus=[sup.get("sku")] if sup.get("sku") else [], url=url,
                         date=dates.get(rel(f)) or today, reg=reg)
            reg["cards"][card.get("id")] = {"key": key, "vids": vids, "sku": sup.get("sku"), "url": url,
                                            "path": rel(f), "slot": card_room_slot(f, card),
                                            "status": card.get("status")}
            n_cards += 1
        # 2 + 3. lead files
        mentioned = []
        files = sorted(glob.glob(os.path.join(REPO, "data/leads/**/*.md"), recursive=True) +
                       glob.glob(os.path.join(REPO, "data/leads/**/*.txt"), recursive=True))
        for f in files:
            fdate = (DATE_IN_NAME.search(os.path.basename(f)) or [None, today])[1]
            section, sub = None, None
            for line in open(f, encoding="utf-8"):
                if line.startswith("#"):
                    h = line.strip("# \n")
                    section = None
                    if REJECT_HEAD.search(h) and not SKIP_HEAD.search(h):
                        section = "seen" if re.search(r"not carded", h, re.I) else "rejected"
                    sub = None
                    continue
                msub = re.match(r"^([a-z][a-z-]+):\s*$", line.strip())
                if msub:
                    sub = msub.group(1)
                    continue
                for v in VID.findall(line):
                    known_vids.add(v)
                for u in URL.findall(line):
                    ma = AE_URL.search(u)
                    if ma:
                        mentioned.append(("aliexpress:" + ae_norm(ma.group(1)), clean(line), f, fdate, False))
                    mc = CJ_URL.search(u)
                    if mc:
                        mentioned.append(("cj:" + mc.group(1), clean(line), f, fdate, False))
                text = URL.sub(" ", line)
                ids = list(CJ_ID.finditer(text))
                vid_spans = [m.span(1) for m in VID.finditer(text)]
                for m in ids:
                    pid = m.group(1) or m.group(2)
                    if m.group(1) and any(a <= m.start(1) < b for a, b in vid_spans):
                        continue
                    if pid in cats or (not section and CATEGORY_LINE.search(text)):
                        continue  # a CJ category id, not a product
                    key = "cj:" + pid
                    why = snippet_after(text, m, ids)
                    src = "%s" % rel(f)
                    if section:
                        slot = ("living-room/%s" % sub) if sub else None
                        registry.add(key, section, why, by="sourcing-agent (%s)" % os.path.basename(f),
                                     slot=slot, opened=True, source=src, date=fdate, reg=reg)
                    else:
                        opened = bool(OPENED_LINE.search(text)) and not NOT_OPENED.search(text)
                        mentioned.append((key, why, f, fdate, opened))
                for m in AE_ID.finditer(text):
                    mentioned.append(("aliexpress:" + ae_norm(m.group(1)), clean(line), f, fdate, False))
        # JSON lead files (mostly AliExpress web leads)
        for f in sorted(glob.glob(os.path.join(REPO, "data/leads/**/*.json"), recursive=True)):
            fdate = (DATE_IN_NAME.search(os.path.basename(f)) or [None, None])[1]
            d = json.load(open(f))
            fdate = fdate or d.get("searched_at") or d.get("collected") or today

            def walk(o):
                if isinstance(o, dict):
                    urls = [v for v in o.values() if isinstance(v, str) and ("aliexpress" in v or "cjdropshipping" in v)]
                    for u in urls:
                        ma, mc = AE_URL.search(u), CJ_URL.search(u)
                        k = ("aliexpress:" + ae_norm(ma.group(1))) if ma else ("cj:" + mc.group(1)) if mc else None
                        if k:
                            name = o.get("title") or o.get("name") or ""
                            extra = o.get("concerns") or o.get("verdict") or ""
                            mentioned.append((k, clean("web lead: %s. %s" % (name, extra)), f, fdate, False))
                    for v in o.values():
                        walk(v)
                elif isinstance(o, list):
                    for v in o:
                        walk(v)
            walk(d)
        n_m = 0
        for key, why, f, fdate, opened in mentioned:
            if key.startswith("cj:") and key[3:] in known_vids:
                continue  # a variant id, not a product id
            if registry.resolve(reg, key)[1] is None:
                n_m += 1
            registry.add(key, "seen", "mentioned in %s: %s" % (os.path.basename(f), why), by="lead-file",
                         opened=opened, source=rel(f), date=fdate, reg=reg)
        # Variant or category ids that an older build recorded as products are removed.
        for v in list(known_vids) + list(cats):
            e = reg["items"].get("cj:" + v)
            if e and e["status"] == "seen" and e.get("by") == "lead-file":
                del reg["items"]["cj:" + v]
        if not dry:
            registry.save(reg)
    from collections import Counter
    c = Counter((k.split(":")[0], v["status"], bool(v.get("opened"))) for k, v in reg["items"].items())
    print("cards read: %d; new mentions: %d" % (n_cards, n_m))
    for k, n in sorted(c.items()):
        print("  %-11s %-9s opened=%-5s %d" % (k + (n,)))
    print("aliases:", len(reg["aliases"]), "->", "dry run, not written" if dry else rel(registry.SEEN))


if __name__ == "__main__":
    main()
