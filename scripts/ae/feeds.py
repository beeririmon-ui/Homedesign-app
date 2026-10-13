#!/usr/bin/env python3
"""Catalog harvest from the official AliExpress DS product feeds (2026-10-13).

Why: the search method misses good products. aliexpress.ds.text.search has weak relevance and its index is a subset of
the app catalog (the user's towel ladders were not returned even by their exact titles; README "סבב 6"). The DS API also
exposes curated product feeds (aliexpress.ds.feedname.get: 123 feeds, e.g. AEB_US_Home&Garden_TopSellers with 94,652
items) readable page by page with aliexpress.ds.recommend.feed.get (country IL, 50 per page, optional category_id).
Here we read the home-related feeds whole, keep a local catalog, and match every slot by product type.

  harvest <feed_name> [--category ID] [--max-pages N]   pages -> ~/.cache/ae-feeds/<feed>[__cat].jsonl (resumable)
  match                                                  every catalog row x every slot (scale_config must/STRICT, bad
                                                         words), ranked by sales volume and rating
                                                         -> data/leads/aliexpress/catalog-2026-10/matches.json (+ .md)
Budget: one call per page, through scripts/sourcing/budget.py. Stops on flow control (exit 4) and resumes from the
last page next time.
"""
import argparse, glob, json, math, os, re, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import scale  # noqa: E402
from scale import ds, client, guard, Stop, fnum  # noqa: E402
from scale_config import SLOTS, GLOBAL_BAD, STRICT  # noqa: E402

CACHE = os.path.expanduser("~/.cache/ae-feeds")
OUTDIR = os.path.join(scale.REPO, "data", "leads", "aliexpress", "catalog-2026-10")
M_FEED = "aliexpress.ds.recommend.feed.get"


def fname(feed, cat):
    return os.path.join(CACHE, re.sub(r"[^A-Za-z0-9_.-]+", "_", feed) + ("__%s" % cat if cat else "") + ".jsonl")


def harvest(feed, cat, max_pages, a):
    os.makedirs(CACHE, exist_ok=True)
    path = fname(feed, cat)
    state_p = path + ".state"
    st = json.load(open(state_p)) if os.path.exists(state_p) else {"page": 0, "total": None, "done": False}
    if st["done"]:
        print("harvest %s: already done (%s rows)" % (feed, st.get("rows")))
        return
    rows = st.get("rows", 0)
    with open(path, "a") as f:
        while st["page"] < max_pages:
            page = st["page"] + 1
            p = {"feed_name": feed, "country": "IL", "target_currency": "USD", "target_language": "EN", "page_no": page, "page_size": 50}
            if cat:
                p["category_id"] = cat
            guard(ds.spend, a, "search")
            try:
                d = guard(client.call_ok, M_FEED, p)
            except client.AeError as e:
                # "405 The result is empty" also comes mid-feed (lighting stopped at page 25 of 338): wait, retry, then skip
                print("[feeds] %s p%d: %s %s" % (feed, page, e.code, e.message), file=sys.stderr)
                st["empty"] = st.get("empty", 0) + 1
                if st["empty"] >= 6:
                    st["empty"] = 0
                    json.dump(st, open(state_p, "w"))
                    break
                time.sleep(10)
                if st["empty"] % 2 == 0:
                    st["page"] = page  # two misses on this page: skip it
                continue
            st["empty"] = 0
            r = d.get("result") or {}
            prods = r.get("products") or []
            if isinstance(prods, dict):
                prods = next(iter(prods.values()), [])
            st["total"] = r.get("total_record_count")
            for x in prods:
                f.write(json.dumps({"item_id": str(x.get("product_id")), "title": x.get("product_title"),
                                    "price_usd": fnum(x.get("target_sale_price")), "volume": int(fnum(re.sub(r"[^0-9.]", "", str(x.get("lastest_volume") or "0")) or 0) or 0),
                                    "rating": fnum(x.get("evaluate_rate")), "image": x.get("product_main_image_url"),
                                    "images": (x.get("product_small_image_urls") or [])[:4], "cat1": x.get("first_level_category_name"),
                                    "cat2": x.get("second_level_category_name"), "cat2_id": x.get("second_level_category_id"),
                                    "feed": feed}, ensure_ascii=False) + "\n")
            rows += len(prods)
            st["page"], st["rows"] = page, rows
            if r.get("is_finished") or not prods:
                st["done"] = True
            json.dump(st, open(state_p, "w"))
            if st["done"]:
                break
            if page % 20 == 0:
                print("[feeds] %s: page %d, %d rows of %s" % (feed, page, rows, st["total"]), file=sys.stderr)
    print("harvest %s%s: %d rows, page %d, total %s, done %s" % (feed, " cat %s" % cat if cat else "", rows, st["page"], st["total"], st["done"]))


def load_catalog():
    seen = {}
    for p in glob.glob(os.path.join(CACHE, "*.jsonl")):
        for l in open(p):
            try:
                r = json.loads(l)
            except ValueError:
                continue
            if r["item_id"] not in seen or (r.get("volume") or 0) > (seen[r["item_id"]].get("volume") or 0):
                seen[r["item_id"]] = r
    return list(seen.values())


def match():
    cat = load_catalog()
    out, md = {}, ["# קטלוג AliExpress מהפידים הרשמיים: התאמה לעמדות (2026-10-13)", "",
                   "%d מוצרים ייחודיים מפידי הבית (top sellers). התאמה לפי סוג מוצר (STRICT / must), בלי מילים פסולות, מדורג לפי נפח מכירות ודירוג." % len(cat), "",
                   "| עמדה | מוצרים מתאימים | 3 המובילים (מכירות) |", "| --- | --- | --- |"]
    for key, cfg in SLOTS.items():
        strict = STRICT.get(key)
        gbad = GLOBAL_BAD if not key.startswith("kids/") else GLOBAL_BAD.replace(r"cartoon|", "").replace(r"car\b|", "")
        hits = []
        for r in cat:
            t = r.get("title") or ""
            if not (re.search(strict, t, re.I) if strict else re.search(cfg["must"], t, re.I)):
                continue
            if re.search(gbad, t, re.I) or (cfg.get("bad") and re.search(cfg["bad"], t, re.I)):
                continue
            q = 8 * math.log10((r.get("volume") or 0) + 1) + (5 if (r.get("rating") or 0) >= 95 else 0)
            hits.append(dict(r, q=round(q, 1)))
        hits.sort(key=lambda r: -r["q"])
        out[key] = hits[:60]
        md.append("| %s | %d | %s |" % (key, len(hits), " · ".join("[%s](https://www.aliexpress.com/item/%s.html) (%s)" % ((h["title"] or "")[:35].replace("|", "/"), h["item_id"], h.get("volume")) for h in hits[:3])))
    os.makedirs(OUTDIR, exist_ok=True)
    json.dump(out, open(os.path.join(OUTDIR, "matches.json"), "w"), ensure_ascii=False, indent=0)
    open(os.path.join(OUTDIR, "matches.md"), "w").write("\n".join(md) + "\n")
    print("match: %d catalog rows, %d slots with matches" % (len(cat), sum(1 for v in out.values() if v)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["harvest", "match"])
    ap.add_argument("feed", nargs="?")
    ap.add_argument("--category")
    ap.add_argument("--max-pages", type=int, default=2000)
    a0 = ap.parse_args()
    a = scale.ns("feeds", 12000)
    try:
        if a0.stage == "harvest":
            harvest(a0.feed, a0.category, a0.max_pages, a)
        else:
            match()
    except Stop as e:
        print("feeds STOP: %s" % e, file=sys.stderr)
        return 4
    return 0


if __name__ == "__main__":
    sys.exit(main())
