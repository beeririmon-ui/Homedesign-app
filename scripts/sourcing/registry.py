#!/usr/bin/env python3
"""The "seen" registry: every supplier item that any agent has already examined.

File: data/sources/seen.json (in the repo; it is the shared memory between rounds).

    {"version": 1, "updated": "<iso>",
     "items":   {"cj:<pid>": {key, status, reason, card_id?, card_ids?, slot?, vids?, skus?,
                              url?, opened, recheck_after?, source?, first_seen, last_seen, by}},
     "aliases": {"cj:vid:<vid>": "cj:<pid>", "cj:sku:<sku>": "cj:<pid>", ...}}

status:
  card      a product card exists (data/products/**); never re-open, read the card.
  rejected  opened and rejected; never re-open. Exception: a price/shipping reason may be
            re-checked after 90 days (recheck_after).
  seen      known item. opened=true: already opened, read the cache / the source file, do not
            re-open (unless --force). opened=false: only mentioned in a list or a lead file;
            opening it is allowed, but read the note first.

CLI:
  python3 scripts/sourcing/registry.py check cj:2608020808091620300 [more keys or bare ids]
  python3 scripts/sourcing/registry.py add cj:<pid> --status rejected --reason "..." --by sourcing-agent [--slot master/pendant]
  python3 scripts/sourcing/registry.py stats
"""
import argparse, contextlib, datetime as dt, fcntl, json, os, re, sys, tempfile

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SEEN = os.path.join(REPO, "data", "sources", "seen.json")
LOCK = os.path.expanduser("~/.cache/sourcing/seen.lock")
STATUSES = ("card", "rejected", "seen")
RANK = {"seen": 0, "rejected": 1, "card": 2}  # a stronger status is never downgraded by add()
PRICE_WORDS = re.compile(r"\bprice\b|\$\d|\bshipping\b|\bfreight\b|\bDHL\b|no IL route|out of stock", re.I)
# A design/fit reason is final even when the line also mentions a price.
DESIGN_WORDS = re.compile(r"replica|copy|look-alike|brass|gold|chrome|glass|plastic|acrylic|resin|print|canvas|"
                          r"rattan|straw|pattern|floral|tassel|too (big|small|wide|tall|short|low|narrow)|"
                          r"\d+\s*(cm|×|x)|\b(base|size|wide|high|tall|deep|width|height)\b|plug|110V|≤36V|US\b|colou?rs? only|figurative|glossy", re.I)
RECHECK_DAYS = 90


def today():
    return dt.datetime.now(dt.timezone.utc).date().isoformat()


def now():
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def norm_key(k, source="cj"):
    """'2608...' -> 'cj:2608...'; 'cj:2608...' stays; an alias (vid/sku) resolves later."""
    k = k.strip()
    return k if ":" in k else "%s:%s" % (source, k)


@contextlib.contextmanager
def locked():
    os.makedirs(os.path.dirname(LOCK), exist_ok=True)
    with open(LOCK, "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def load(path=SEEN):
    if not os.path.exists(path):
        return {"version": 1, "updated": None, "items": {}, "aliases": {}}
    with open(path) as f:
        d = json.load(f)
    d.setdefault("items", {}); d.setdefault("aliases", {})
    return d


def save(reg, path=SEEN):
    reg["updated"] = now()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), prefix=".seen-", suffix=".json")
    with os.fdopen(fd, "w") as f:
        json.dump(reg, f, ensure_ascii=False, indent=1, sort_keys=True)
        f.write("\n")
    os.replace(tmp, path)


def resolve(reg, key):
    """Return (canonical key, entry or None). Accepts pid keys and vid/sku aliases."""
    key = norm_key(key)
    if key in reg["items"]:
        return key, reg["items"][key]
    src, _, native = key.partition(":")
    for alias in (key, "%s:vid:%s" % (src, native), "%s:sku:%s" % (src, native)):
        if alias in reg["aliases"]:
            k = reg["aliases"][alias]
            return k, reg["items"].get(k)
    return key, None


def decide(entry, force=False):
    """-> (action, why). action: 'open' (allowed), 'skip' (do not call the supplier), 'warn' (allowed, read the note)."""
    if entry is None:
        return "open", "not in the registry"
    st = entry.get("status")
    why = "%s: %s" % (st, entry.get("reason") or "")
    if entry.get("card_ids") and len(entry["card_ids"]) > 1:
        why += " [cards: %s]" % ", ".join(entry["card_ids"])
    if force:
        return "open", "forced; " + why
    if st == "card":
        return "skip", why
    if st == "rejected":
        ra = entry.get("recheck_after")
        if ra and ra <= today():
            return "open", "recheck window reached (%s); %s" % (ra, why)
        return "skip", why
    if st == "seen" and entry.get("opened"):
        ra = entry.get("recheck_after")
        if ra and ra <= today():
            return "open", "recheck window reached (%s); %s" % (ra, why)
        return "skip", why
    return "warn", why


def check(key, reg=None, force=False):
    reg = reg or load()
    k, e = resolve(reg, key)
    action, why = decide(e, force)
    return {"key": k, "action": action, "why": why, "entry": e}


def _note(e, text, keep=6):
    notes = e.setdefault("notes", [])
    if text not in notes and len(notes) < keep:
        notes.append(text)


def add(key, status, reason=None, by="unknown", slot=None, card_id=None, opened=True, source=None,
        vids=(), skus=(), url=None, date=None, reg=None, write=True):
    """Insert or update an entry. Status only goes up (seen < rejected < card); last_seen always moves."""
    if status not in STATUSES:
        raise ValueError("status must be one of %s" % (STATUSES,))
    date = date or today()
    own = reg is None
    ctx = locked() if (own and write) else contextlib.nullcontext()
    with ctx:
        if own:
            reg = load()
        key, e = resolve(reg, key)
        if e is None:
            e = {"key": key, "status": status, "reason": reason, "first_seen": date, "last_seen": date,
                 "by": by, "opened": bool(opened)}
            reg["items"][key] = e
        else:
            old_rank, new_rank = RANK.get(e.get("status"), 0), RANK[status]
            upgrade = new_rank > old_rank or (new_rank == old_rank and (
                not e.get("reason") or (opened and not e.get("opened")) or (opened and by == e.get("by"))))
            if upgrade:
                if e.get("reason") and reason and e["reason"] != reason:
                    _note(e, e["reason"])
                e["status"] = status
                e["reason"] = reason or e.get("reason")
                e["by"] = by
            elif reason and reason != e.get("reason"):
                _note(e, reason)
            e["first_seen"] = min(e.get("first_seen") or date, date)
            e["last_seen"] = max(e.get("last_seen") or date, date)
            e["opened"] = bool(e.get("opened")) or bool(opened)
        if slot and not e.get("slot"):
            e["slot"] = slot
        if card_id:
            reg.setdefault("cards", {}).setdefault(card_id, {"key": key})
            ids = e.setdefault("card_ids", [])
            if card_id not in ids:
                ids.append(card_id); ids.sort()
            e["card_id"] = e.get("card_id") or card_id
        if url and not e.get("url"):
            e["url"] = url
        if source:
            srcs = e.setdefault("sources", [])
            if source not in srcs:
                srcs.append(source)
        src = key.split(":", 1)[0]
        for v in vids:
            if v:
                lst = e.setdefault("vids", [])
                if v not in lst: lst.append(v)
                reg["aliases"]["%s:vid:%s" % (src, v)] = key
        for s in skus:
            if s:
                lst = e.setdefault("skus", [])
                if s not in lst: lst.append(s)
                reg["aliases"]["%s:sku:%s" % (src, s)] = key
        if (e["status"] in ("rejected", "seen") and e.get("opened") and e.get("by") != "lead-file" and e.get("reason") and PRICE_WORDS.search(e["reason"])
                and not DESIGN_WORDS.search(e["reason"])):
            d0 = dt.date.fromisoformat(e["last_seen"])
            e["recheck_after"] = (d0 + dt.timedelta(days=RECHECK_DAYS)).isoformat()
        else:
            e.pop("recheck_after", None)
        if own and write:
            save(reg)
    return e


def main(argv=None):
    ap = argparse.ArgumentParser(description="seen.json registry")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check"); c.add_argument("keys", nargs="+"); c.add_argument("--force", action="store_true")
    a = sub.add_parser("add")
    a.add_argument("key"); a.add_argument("--status", required=True, choices=STATUSES)
    a.add_argument("--reason"); a.add_argument("--by", required=True); a.add_argument("--slot")
    a.add_argument("--card-id"); a.add_argument("--not-opened", action="store_true")
    a.add_argument("--vid", action="append", default=[]); a.add_argument("--sku", action="append", default=[])
    sub.add_parser("stats")
    a_ = ap.parse_args(argv)
    if a_.cmd == "check":
        reg = load()
        out = [check(k, reg, a_.force) for k in a_.keys]
        json.dump(out, sys.stdout, ensure_ascii=False, indent=1); print()
        return 1 if any(o["action"] == "skip" for o in out) else 0
    if a_.cmd == "add":
        e = add(a_.key, a_.status, a_.reason, a_.by, a_.slot, a_.card_id, not a_.not_opened,
                vids=a_.vid, skus=a_.sku)
        json.dump(e, sys.stdout, ensure_ascii=False, indent=1); print()
        return 0
    reg = load()
    from collections import Counter
    c = Counter((k.split(":")[0], v["status"]) for k, v in reg["items"].items())
    print("updated:", reg.get("updated"))
    for (src, st), n in sorted(c.items()):
        print("  %-14s %-9s %d" % (src, st, n))
    print("  aliases:", len(reg["aliases"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
