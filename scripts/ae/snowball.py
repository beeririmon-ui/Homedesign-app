#!/usr/bin/env python3
"""Round 7 (2026-10-13): image-search snowball from reviewed products.

The user's screenshots showed it: image search from a photo of the right product finds the exact listing and its twins,
where text search does not (README "סבב 6"). Here the seeds are the products the visual review liked (round 6 sheets,
fit >= 7 in some style, right type) for every slot still empty; each seed's main image goes to ds.image.searchV2
(results sorted by orders). Results that name the product (must / STRICT) and look alike (similarity >= 0.55) are
added to the screen file (round 7), the 10 best per slot by orders and similarity get product.get + freight
(round6 detail machinery) and a sheet review/sheets/r7-<room>-<slot>.jpg for the visual review.

  python3 scripts/ae/snowball.py search <room>
  python3 scripts/ae/snowball.py detail <room>
  python3 scripts/ae/snowball.py sheet <room>
"""
import json, math, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import scale  # noqa: E402
import round6  # noqa: E402
from scale import client, guard, Stop, fnum  # noqa: E402
from scale_config import SLOTS, GLOBAL_BAD, STRICT  # noqa: E402

OUT = scale.OUT
MIN_SIM = 0.55


def seeds(room, key, n=3):
    slot = key.split("/")[1]
    rv = json.load(open(os.path.join(OUT, "review", room + ".json")))
    det = json.load(open(os.path.join(OUT, "detail", room + ".json")))
    out = []
    for rec in det.values():
        if rec.get("slot") != slot or not rec.get("image"):
            continue
        r = rv.get(rec["item_id"]) or {}
        fits = [v.get("fit") or 0 for v in r.values() if isinstance(v, dict) and v.get("verdict") != "reject"]
        if fits and max(fits) >= 7:
            out.append((max(fits), rec["item_id"], rec["image"]))
    out.sort(key=lambda x: -x[0])
    return out[:n]


def match(row, key):
    t = row.get("title") or ""
    cfg = SLOTS[key]
    strict = STRICT.get(key)
    if not (re.search(cfg["must"], t, re.I) or (strict and re.search(strict, t, re.I))):
        return False
    gbad = GLOBAL_BAD if not key.startswith("kids/") else GLOBAL_BAD.replace(r"cartoon|", "").replace(r"car\b|", "")
    return not (re.search(gbad, t, re.I) or (cfg.get("bad") and re.search(cfg["bad"], t, re.I)))


def do_search(room, a):
    path = os.path.join(OUT, "screen", room + ".jsonl")
    rows = [json.loads(l) for l in open(path)]
    done = {r["query"] for r in rows if r.get("round") == 7}
    added = 0
    for key in scale.missing_slots(room):
        for fit, sid, url in seeds(room, key):
            q = "img7:" + sid
            if q in done:
                continue
            try:
                res = guard(scale.image_search, a, "ae:" + sid, url)
            except (client.AeError, OSError, SystemExit) as e:
                print("[r7] skip %s %s: %s" % (key, sid, e), file=sys.stderr)
                continue
            for p in res.get("products") or []:
                price = fnum(p.get("target_sale_price"))
                r = {"item_id": str(p.get("product_id")), "title": p.get("product_title"),
                     "price_usd": round(price / 100.0, 2) if price is not None else None,
                     "orders": int(re.sub(r"[^0-9]", "", str(p.get("latest_volume") or "0")) or 0),
                     "rating": (fnum(p.get("evaluate_rate")) or 0) * 20 or None, "image": p.get("product_main_image_url"),
                     "sim": fnum(p.get("similarity_score")), "seed": sid, "query": q, "page": 1, "slot": key.split("/")[1],
                     "cate": p.get("second_level_category_id"), "round": 7, "style": "nordic", "score": 0, "why": []}
                if r["item_id"] != sid and match(r, key) and (r["sim"] or 0) >= MIN_SIM:
                    rows.append(r)
                    added += 1
            done.add(q)
        print("[r7] %s searched" % key, file=sys.stderr)
    with open(path, "w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print("r7 search %s: %d new rows" % (room, added))


def shortlist(room, top=10):
    rows = [json.loads(l) for l in open(os.path.join(OUT, "screen", room + ".jsonl"))]
    out = {}
    for key in scale.missing_slots(room):
        slot = key.split("/")[1]
        best = {}
        for r in rows:
            if r.get("round") != 7 or r["slot"] != slot:
                continue
            q = round(40 * (r.get("sim") or 0) + min(25, 8 * math.log10((r.get("orders") or 0) + 1)), 1)
            if r["item_id"] not in best or best[r["item_id"]][0] < q:
                best[r["item_id"]] = (q, r)
        out[key] = sorted(best.values(), key=lambda x: -x[0])[:top]
    return out


def main():
    stage, room = sys.argv[1], sys.argv[2]
    a = scale.ns(room, 6000)
    # detail and sheet reuse round 6 with this shortlist; sheets are named r7-*
    round6.shortlist = lambda room, top=10: shortlist(room, top)
    try:
        if stage == "search":
            do_search(room, a)
        elif stage == "detail":
            round6.do_detail(room, a)
        elif stage == "sheet":
            round6.do_sheet(room, prefix="r7")
    except Stop as e:
        print("r7 STOP %s %s: %s" % (stage, room, e), file=sys.stderr)
        return 4
    return 0


if __name__ == "__main__":
    sys.exit(main())
