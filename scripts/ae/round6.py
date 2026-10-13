#!/usr/bin/env python3
"""Round 6 (2026-10-13): fix of the screening method for the slots still empty.

Diagnosis (data/leads/aliexpress/scale-2026-10/README.md, "סבב 6"): the screen score of scale.py ranked rows by price
against the market band (IKEA-level), so right-type products were dropped before anyone looked at them (utensil crock:
36 of 36 right-type results dropped for price; toilet brush 53 of 57; umbrella stand 32 of 49) and the visual review saw
the cheapest junk. Here:
  search  for every slot still empty (scale.missing_slots): the slot's base query and its round-3 queries, no style word,
          default relevance, pages 1-3 (text search relevance is weak, the right products are spread over pages)
  rank    by QUALITY only: names the product (scale_config must / STRICT), no excluded words, orders, rating; price only as
          a loose cap (search price x 3.3 <= 3 x the slot price); the 15 best per slot (all rounds' rows) get product.get,
          the room SKU and freight to IL (scale.do_detail machinery) -> detail/<room>.json
  sheet   per slot, those 15 ranked by quality -> review/sheets/r6-<room>-<slot>.jpg + index (visual review for all styles)
Price is judged only after the review (scale.py finalize + the price proposal rule: 40% at the band, else a proposed
price when it stays within the Israeli market's p90).
"""
import json, math, os, re, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import scale  # noqa: E402
from scale import ds, client, cache, registry, guard, Stop, fnum, pick_room_sku, sku_text, best_freight  # noqa: E402
from scale_config import SLOTS, GLOBAL_BAD, ROUND3, STRICT  # noqa: E402

OUT = scale.OUT
PLAN = os.path.join(scale.REPO, "data", "leads", "next-sourcing", "round-3-2026-10-11.json")


def slot_price(key):
    try:
        for s in json.load(open(PLAN))["slots"]:
            if s["slot"] == key and (s.get("price_ceiling") or {}).get("slot_price_ils"):
                return s["price_ceiling"]["slot_price_ils"]
    except (OSError, ValueError):
        pass
    band, _ = scale.band_of(SLOTS[key])
    return band[1]


def quality(row, key):
    """Quality score, no price preference. None = not this product / excluded."""
    t = row.get("title") or ""
    cfg = SLOTS[key]
    strict = STRICT.get(key)
    if not (re.search(cfg["must"], t, re.I) or (strict and re.search(strict, t, re.I))):
        return None
    gbad = GLOBAL_BAD if not key.startswith("kids/") else GLOBAL_BAD.replace(r"cartoon|", "").replace(r"car\b|", "")
    if re.search(gbad, t, re.I) or (cfg.get("bad") and re.search(cfg["bad"], t, re.I)):
        return None
    if row.get("price_usd") is not None and row["price_usd"] * scale.FX > 3 * slot_price(key):
        return None
    s = 30 + (15 if strict and re.search(strict, t, re.I) else 0)
    s += min(25, 8 * math.log10((row.get("orders") or 0) + 1))
    r = row.get("rating")
    if r is not None:
        s += 5 if r >= 95 else 2 if r >= 90 else -5 if r < 80 else 0
    return round(s, 1)


def do_search(room, a):
    path = os.path.join(OUT, "screen", room + ".jsonl")
    rows = [json.loads(l) for l in open(path)]
    done = {r["query"] for r in rows if r.get("round") == 6}
    added = 0
    for key in scale.missing_slots(room):
        qs = [SLOTS[key]["q"]] + [q for q in ROUND3.get(key, []) if q != SLOTS[key]["q"]]
        for q in qs[:3]:
            for page in (1, 2, 3):
                tag = "r6:%s:p%d" % (q, page)
                if tag in done:
                    continue
                try:
                    res = guard(scale.search, a, q, page)
                except client.AeError as e:
                    print("[r6] skip %r p%d: %s %s" % (q, page, e.code, e.message), file=sys.stderr)
                    continue
                for p in res.get("products") or []:
                    rows.append({"item_id": str(p.get("itemId")), "title": p.get("title"), "price_usd": fnum(p.get("targetSalePrice")),
                                 "orders": int(fnum(p.get("orders")) or 0), "rating": fnum(p.get("evaluateRate")),
                                 "image": p.get("itemMainPic"), "query": tag, "page": page, "slot": key.split("/")[1],
                                 "cate": p.get("cateId"), "round": 6, "style": "nordic", "score": 0, "why": []})
                    added += 1
                done.add(tag)
        print("[r6] %s searched" % key, file=sys.stderr)
    with open(path, "w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print("r6 search %s: %d new rows" % (room, added))


def shortlist(room, top=15):
    rows = [json.loads(l) for l in open(os.path.join(OUT, "screen", room + ".jsonl"))]
    reg = registry.load()
    out = {}
    for key in scale.missing_slots(room):
        slot = key.split("/")[1]
        best = {}
        for r in rows:
            if r["slot"] != slot:
                continue
            q = quality(r, key)
            if q is None:
                continue
            if r["item_id"] not in best or best[r["item_id"]][0] < q:
                best[r["item_id"]] = (q, r)
        picks = []
        for q, r in sorted(best.values(), key=lambda x: -x[0]):
            c = registry.check(ds.key_of(r["item_id"]), reg)
            if c["action"] == "skip" and (c.get("entry") or {}).get("status") == "rejected" and "fit" in str((c.get("entry") or {}).get("reason")):
                continue  # rejected on looks earlier; price rejections get another chance
            picks.append((q, r))
            if len(picks) >= top:
                break
        out[key] = picks
    return out


def do_detail(room, a):
    path = os.path.join(OUT, "detail", room + ".json")
    det = json.load(open(path))
    n = 0
    try:
        for key, picks in shortlist(room).items():
            slot = key.split("/")[1]
            for q, r in picks:
                k = "%s|%s" % (slot, r["item_id"])
                rec = det.get(k) or {"slot": slot, "item_id": r["item_id"], "styles": ["nordic"], "screen": {}}
                rec.setdefault("screen", {}).setdefault("nordic", {"score": q, "why": [], "query": r["query"]})
                rec["r6_quality"] = q
                rec.update(title=rec.get("title") or r["title"], image=rec.get("image") or r["image"], orders=r["orders"], rating=r["rating"])
                if not rec.get("product_ok"):
                    try:
                        a.slot = "%s/%s" % (room, slot)
                        prod, _ = guard(ds.fetch_product, a, r["item_id"])
                    except client.AeError as e:
                        rec.update(product_ok=False, error="%s %s" % (e.code, e.message)); det[k] = rec; continue
                    res = prod.get("result") or {}
                    skus = ds.as_list(res.get("ae_item_sku_info_dtos"))
                    sku, how = pick_room_sku(skus, "%s/%s" % (room, slot))
                    base = res.get("ae_item_base_info_dto") or {}
                    rec.update(product_ok=True, title=base.get("subject") or rec["title"], n_skus=len(skus),
                               ae_rating=ds.num(base.get("avg_evaluation_rating")), reviews=base.get("evaluation_count"),
                               sku=str(sku.get("sku_id")) if sku else None, sku_label=sku_text(sku) if sku else None, sku_pick=how,
                               price_usd=(ds.num(sku.get("offer_sale_price")) or ds.num(sku.get("sku_price"))) if sku else None)
                if rec.get("product_ok") and rec.get("sku") and "ship_usd" not in rec:
                    try:
                        fr, _ = guard(ds.fetch_freight, a, r["item_id"], rec["sku"], "IL", 1)
                    except client.AeError as e:
                        fr = {"options": [], "msg": "%s %s" % (e.code, e.message)}
                    b = best_freight(fr.get("options"))
                    rec.update(ship_usd=b["fee"] if b else None, ship_days="%s-%s" % (b.get("days_min"), b.get("days_max")) if b else None,
                               ship_company=(b.get("company") or b.get("code")) if b else None, ship_ok=bool(b),
                               ship_msg=None if b else (fr.get("msg") or fr.get("code")))
                det[k] = rec
                n += 1
                if n % 20 == 0:
                    json.dump(det, open(path, "w"), ensure_ascii=False, indent=0)
    finally:
        json.dump(det, open(path, "w"), ensure_ascii=False, indent=0)
    print("r6 detail %s: %d records" % (room, n))


def do_sheet(room, prefix="r6"):
    from PIL import Image, ImageDraw
    import urllib.request
    det = json.load(open(os.path.join(OUT, "detail", room + ".json")))
    sl = shortlist(room)
    odir = os.path.join(OUT, "review", "sheets")
    imgdir = os.path.expanduser("~/.cache/ae-scale-img")
    os.makedirs(imgdir, exist_ok=True)
    index, n = {}, 0
    for key, picks in sl.items():
        slot = key.split("/")[1]
        cells = [det.get("%s|%s" % (slot, r["item_id"])) for _, r in picks]
        cells = [c for c in cells if c and c.get("ship_ok") and scale.landed(c) is not None]
        if not cells:
            continue
        W, H, cols = 260, 300, 6
        sheet = Image.new("RGB", (W * cols, H * ((len(cells) + cols - 1) // cols)), "white")
        d = ImageDraw.Draw(sheet)
        for i, c in enumerate(cells):
            x, y = (i % cols) * W, (i // cols) * H
            fp = os.path.join(imgdir, c["item_id"] + ".jpg")
            if not os.path.exists(fp) and c.get("image"):
                for url in (c["image"] + "_220x220.jpg", c["image"]):
                    try:
                        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=20) as r:
                            open(fp, "wb").write(r.read())
                        break
                    except Exception:
                        pass
            try:
                im = Image.open(fp).convert("RGB"); im.thumbnail((W - 10, H - 60)); sheet.paste(im, (x + 5, y + 5))
            except Exception:
                d.text((x + 10, y + 100), "no image", fill="red")
            n += 1
            index[str(n)] = {"slot": slot, "item_id": c["item_id"], "style": "nordic"}
            d.rectangle([x, y + H - 55, x + W, y + H], fill="white")
            d.text((x + 5, y + H - 52), "#%d q%s %s" % (n, c.get("r6_quality"), c["item_id"][-6:]), fill="black")
            d.text((x + 5, y + H - 38), "%.0f ILS %s" % (scale.landed(c), (c.get("sku_label") or "")[:26]), fill="black")
            d.text((x + 5, y + H - 24), (c.get("title") or "")[:40], fill="gray")
        sheet.save(os.path.join(odir, "%s-%s-%s.jpg" % (prefix, room, slot)), quality=80)
    json.dump(index, open(os.path.join(odir, "%s-%s-index.json" % (prefix, room)), "w"), indent=0)
    print("%s sheets %s: %d candidates in %d slots" % (prefix, room, n, len(sl)))


STYLES6 = ["nordic", "warm-modern", "japandi", "mediterranean", "modern-country", "boho"]


def do_merge(room, prefix="r6"):
    """Visual review of the r6 sheets (review/r6rev-<room>.json, by sheet number) -> review/<room>.json (by item id)."""
    src = os.path.join(OUT, "review", "%srev-%s.json" % (prefix, room))
    idx = json.load(open(os.path.join(OUT, "review", "sheets", "%s-%s-index.json" % (prefix, room))))
    rv_path = os.path.join(OUT, "review", room + ".json")
    rv = json.load(open(rv_path)) if os.path.exists(rv_path) else {}
    n = 0
    for num, v in json.load(open(src)).items():
        ent = idx.get(str(num))
        if not ent:
            continue
        rec = rv.setdefault(ent["item_id"], {})
        for st in STYLES6:
            fit = (v.get("styles") or {}).get(st)
            if fit is None:
                continue
            e = {"fit": fit, "reason": v.get("reason"), "review": prefix}
            if not v.get("type_ok", True):
                e["verdict"] = "reject"
            rec[st] = e
        n += 1
    json.dump(rv, open(rv_path, "w"), ensure_ascii=False, indent=0)
    # finalize walks rec["styles"]: the r6 records were searched without a style, so all six styles are judged
    det_path = os.path.join(OUT, "detail", room + ".json")
    det = json.load(open(det_path))
    for ent in idx.values():
        rec = det.get("%s|%s" % (ent["slot"], ent["item_id"]))
        if rec:
            rec["styles"] = sorted(set(rec.get("styles") or []) | set(STYLES6))
    json.dump(det, open(det_path, "w"), ensure_ascii=False, indent=0)
    print("r6 merge %s: %d items" % (room, n))


def main():
    stage, room = sys.argv[1], sys.argv[2]
    if stage in ("merge", "merge7"):
        do_merge(room, "r7" if stage == "merge7" else "r6")
        return 0
    a = scale.ns(room, 6000)
    try:
        if stage == "search":
            do_search(room, a)
        elif stage == "detail":
            do_detail(room, a)
        elif stage == "sheet":
            do_sheet(room)
    except Stop as e:
        print("r6 STOP %s %s: %s" % (stage, room, e), file=sys.stderr)
        return 4
    return 0


if __name__ == "__main__":
    sys.exit(main())
