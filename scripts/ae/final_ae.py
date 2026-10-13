#!/usr/bin/env python3
"""The final sourcing round on AliExpress (art director, 2026-10-13): every room, all six styles.

Input: the gap packs data/leads/final-2026-10-13/<style>.json (709 slot x style gaps; slot spec, price ceiling, existing
picks, designer spec and queries, already_searched_aliexpress). One search per slot for all styles together:
  plan    per slot: the styles that need it, their slot prices, 2-4 new queries (designer queries first, round robin
          over the styles; never a query already in already_searched_aliexpress, searched-index.json or our screen files)
  search  text search pages 1-2 per query + image search from 2 close earlier candidates (reviewed fit >= 6), filtered by
          product type (scale_config must / STRICT, excluded words) and --hide-seen (registry)
  detail  the 12 best new items per slot by quality (names the product, orders, rating; price only as a loose cap)
          get product.get, the room SKU and freight to IL. Plus the pool: earlier-round items already reviewed at fit >= 7
          for a style that needs the slot (cache only)
  sheet   contact sheets per slot -> scale-2026-10/final/fin-<room>-<slot>.jpg + fin-<room>-index.json + brief
  (visual review: fin-rev-<room>.json, fit guess 1-10 for all six styles, type_ok, fits_envelope)
  write   a card (ds.py card) for an item with fit guess >= 7 for a style that needs the slot, no loss at that style's
          slot price and an envelope that fits (borderline allowed); up to 2 per needing style, 8 per slot, items that
          serve several styles first. No style_scores (the designers score in the finishing pass).
          -> data/leads/final-2026-10-13/results/aliexpress-<room>.json + .md; queries -> searched-index.json
Economics as the Studio: fx 3.3, VAT 18%, card fee 2% + 1.2, returns 8% of net; shipping for q units:
unit + (q-1) * max(0, unit - 3.72) USD.
"""
import datetime, glob, json, math, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import scale  # noqa: E402
import ds  # noqa: E402
from scale import client, cache, registry, guard, Stop, fnum, pick_room_sku, sku_text, best_freight  # noqa: E402
from scale_config import SLOTS, GLOBAL_BAD, ROUND3, STRICT  # noqa: E402

REPO = scale.REPO
STYLES = ["nordic", "warm-modern", "japandi", "mediterranean", "modern-country", "boho"]
PACKS = os.path.join(REPO, "data", "leads", "final-2026-10-13")
RES = os.path.join(PACKS, "results")
WORK = os.path.join(scale.OUT, "final")
INDEX = os.path.join(REPO, "data", "leads", "next-sourcing", "searched-index.json")
BY = "aliexpress-final"
TAG = "final-round 2026-10-13"


def gaps():
    out = {}
    for st in STYLES:
        for g in json.load(open(os.path.join(PACKS, st + ".json")))["gaps"]:
            out.setdefault(g["slot"], {})[st] = g
    return out


def slot_price(g, key=None):
    """The style's slot price from the pack; a gap without one gets the top of the slot's market band (scale_config)."""
    pc = g.get("price_ceiling") or {}
    if pc.get("slot_price_ils"):
        return pc["slot_price_ils"]
    if key:
        return scale.band_of(SLOTS[key])[0][1]
    return None


NOUN = {"living-room/accent-sconces": "wall sconce", "living-room/floor-lamp": "floor lamp", "living-room/vase": "vase",
        "dining-room/bench-pad": "bench cushion", "dining-room/centerpiece-vase": "vase", "dining-room/canisters": "canister jar set",
        "dining-room/condiment-set": "salt pepper grinder", "dining-room/curtains": "curtain", "dining-room/framed-art": "kitchen wall art",
        "dining-room/herb-pots": "herb pot", "dining-room/open-shelf-ceramics": "pitcher jug", "dining-room/sink-set": "soap dispenser tray set",
        "dining-room/utensil-crock": "utensil holder", "dining-room/mug-set": "mug", "hall/bench-cushion": "bench cushion",
        "hall/ceiling-light": "flush ceiling light", "hall/console-vessel": "tall vase", "hall/key-tray": "key tray",
        "hall/planter": "tall planter", "hall/runner-rug": "runner rug", "hall/umbrella-stand": "umbrella stand", "hall/wall-hooks": "wall hooks",
        "corridor/gallery-art": "framed art print set", "corridor/gallery-stool": "wooden stool", "corridor/picture-lights": "picture light",
        "corridor/runner-rug": "hallway runner rug", "master/basket": "laundry basket", "master/bedding": "duvet cover set",
        "master/bedside-carafe": "water carafe", "master/candle-holders": "candle holder", "master/curtains": "curtains",
        "master/cushions": "lumbar pillow cover", "master/floor-lamp": "floor lamp", "master/nightstand-vase": "small vase",
        "master/pendant": "pendant lamp", "master/pillowcases": "pillowcase", "master/planter": "floor plant pot", "master/rug": "area rug",
        "master/sill-vase": "bud vase", "master/throw": "throw blanket", "master/trinket-dish": "trinket dish", "kids/bedding": "kids duvet cover",
        "kids/bookshelf": "kids bookshelf", "kids/desk-chair": "kids chair", "kids/desk-organizer": "pen holder", "kids/doll": "waldorf doll",
        "kids/doll-pram": "doll pram", "kids/rug": "kids rug", "kids/skateboard": "kids skateboard", "kids/toy-basket": "toy storage basket",
        "kids/toy-cars": "wooden toy car", "kids/wall-sconce": "wall lamp", "work/desk-tray": "desk tray", "work/framed-art": "wall art print",
        "work/magazine-holder": "magazine file holder", "work/shelf-boxes": "storage box with lid", "work/wall-sconce": "reading wall lamp",
        "work/waste-basket": "waste basket", "work/rug": "area rug", "bath/bin": "pedal bin", "bath/candle": "scented candle",
        "bath/hand-towel": "hand towel", "bath/reed-diffuser": "reed diffuser", "bath/shower-stool": "shower stool",
        "bath/storage-basket": "storage basket", "bath/toilet-brush": "toilet brush", "bath/toilet-paper-stand": "toilet paper stand",
        "bath/towel-ladder": "towel ladder", "bath/towel-ring": "towel ring", "bath/vanity-sconces": "vanity wall light"}

# new queries when the designer and base queries were all run already: the slot's noun with materials of its category
MATS = {"textile": ["cotton linen", "waffle", "jute", "boucle", "chunky knit", "striped cotton"],
        "lighting": ["rattan", "linen shade", "black metal", "ceramic", "paper", "brass"],
        "ceramics-tableware": ["matte ceramic", "stoneware", "terracotta", "reactive glaze", "speckled", "glass"],
        "storage-function": ["oak wood", "bamboo", "black metal", "seagrass", "teak", "stone resin"],
        "art-decor-toys": ["wooden", "handmade", "felt", "natural", "vintage", "cotton"]}

def qty_of(key, gs):
    q = SLOTS[key].get("qty")
    for g in gs.values():
        if g.get("set_of"):
            q = q or g["set_of"]
    return int(q or 1)


def econ(rec, price, q):
    if rec.get("price_usd") is None or rec.get("ship_usd") is None or not price:
        return None
    u = rec["ship_usd"]
    ship = u + (q - 1) * max(0.0, u - 3.72)
    landed = round((rec["price_usd"] * q + ship) * scale.FX, 1)
    contrib, margin = scale.economics(price, landed)
    return {"landed_ils": landed, "contribution_ils": contrib, "margin_pct": round(margin * 100, 1)}


def norm(q):
    return re.sub(r"\s+", " ", (q or "").lower().strip())


def used_queries(key, gs, room):
    used = set()
    for g in gs.values():
        used |= {norm(q) for q in g.get("already_searched_aliexpress") or []}
    try:
        used |= {norm(q) for q in json.load(open(INDEX))["aliexpress_queries_by_slot"].get(key, [])}
    except (OSError, ValueError, KeyError):
        pass
    slot = key.split("/")[1]
    p = os.path.join(scale.OUT, "screen", room + ".jsonl")
    if os.path.exists(p):
        for l in open(p):
            r = json.loads(l)
            if r.get("slot") == slot:
                used.add(norm(re.sub(r"^(r6:|r7:|img7:)?", "", re.sub(r":p\d+$", "", r.get("query") or ""))))
    return used


def plan(room):
    G = gaps()
    out = {}
    for key, gs in sorted(G.items()):
        if key.split("/")[0] != room:
            continue
        used = used_queries(key, gs, room)
        pools = []
        for st in STYLES:
            if st in gs:
                pools.append([q for q in gs[st].get("designer_queries") or []])
        pools.append([SLOTS[key]["q"]] + ROUND3.get(key, []))
        noun = NOUN.get(key) or " ".join(SLOTS[key]["q"].split()[-2:])
        cat = next(iter(gs.values())).get("category")
        pools.append(["%s %s" % (m, noun) for m in MATS.get(cat, MATS["storage-function"]) if not set(m.split()) & set(noun.split())])
        picked, i = [], 0
        while len(picked) < 4 and any(pools):
            pool = pools[i % len(pools)]
            while pool:
                q = pool.pop(0)
                if norm(q) not in used and norm(q) not in {norm(x) for x in picked}:
                    picked.append(q)
                    break
            i += 1
            if i > 200:
                break
        out[key] = {"styles": sorted(gs, key=STYLES.index), "need": {s: gs[s].get("need") for s in gs},
                    "priority": {s: gs[s].get("priority") for s in gs},
                    "slot_price": {s: slot_price(gs[s], key) for s in gs}, "qty": qty_of(key, gs),
                    "envelope_cm": next(iter(gs.values())).get("envelope_cm"), "queries": picked,
                    "existing": sorted({p.get("card_id") for g in gs.values() for p in g.get("existing_picks") or [] if p.get("card_id")})}
    os.makedirs(WORK, exist_ok=True)
    json.dump(out, open(os.path.join(WORK, "plan-%s.json" % room), "w"), ensure_ascii=False, indent=1)
    print("final plan %s: %d slots, %d queries" % (room, len(out), sum(len(v["queries"]) for v in out.values())))
    return out


def load_plan(room):
    return json.load(open(os.path.join(WORK, "plan-%s.json" % room)))


def type_ok(title, key):
    t = title or ""
    cfg = SLOTS[key]
    strict = STRICT.get(key)
    if not (re.search(cfg["must"], t, re.I) or (strict and re.search(strict, t, re.I))):
        return False
    gbad = GLOBAL_BAD if not key.startswith("kids/") else GLOBAL_BAD.replace(r"cartoon|", "").replace(r"car\b|", "")
    return not (re.search(gbad, t, re.I) or (cfg.get("bad") and re.search(cfg["bad"], t, re.I)))


def quality(r, key, maxprice):
    if not type_ok(r.get("title"), key):
        return None
    if r.get("price_usd") is not None and maxprice and r["price_usd"] * scale.FX > 3 * maxprice:
        return None
    s = 30 + (15 if STRICT.get(key) and re.search(STRICT[key], r.get("title") or "", re.I) else 0)
    s += min(25, 8 * math.log10((r.get("orders") or 0) + 1))
    rt = r.get("rating")
    if rt is not None:
        s += 5 if rt >= 95 else 2 if rt >= 90 else -5 if rt < 80 else 0
    s += 20 * (r.get("sim") or 0)
    return round(s, 1)


def close_seeds(room, key, n=2):
    slot = key.split("/")[1]
    try:
        rv = json.load(open(os.path.join(scale.OUT, "review", room + ".json")))
        det = json.load(open(os.path.join(scale.OUT, "detail", room + ".json")))
    except (OSError, ValueError):
        return []
    out = []
    for rec in det.values():
        if rec.get("slot") != slot or not rec.get("image"):
            continue
        fits = [v.get("fit") or 0 for v in (rv.get(rec["item_id"]) or {}).values() if isinstance(v, dict) and v.get("verdict") != "reject"]
        if fits and max(fits) >= 6:
            out.append((max(fits), rec["item_id"], rec["image"]))
    out.sort(key=lambda x: -x[0])
    return out[:n]


def screen_path(room):
    return os.path.join(WORK, "screen-%s.jsonl" % room)


def do_search(room, a):
    P = load_plan(room)
    path = screen_path(room)
    rows = [json.loads(l) for l in open(path)] if os.path.exists(path) else []
    done = {r["query"] for r in rows}
    reg = registry.load()
    added = 0
    for key, p in P.items():
        a.slot = key
        tasks = [("t", q, pg) for q in p["queries"] for pg in (1, 2)] + [("i", s, u) for _, s, u in close_seeds(room, key)]
        for kind, q, x in tasks:
            tag = "fin:%s:p%s" % (q, x) if kind == "t" else "fin-img:%s" % q
            if tag in done:
                continue
            try:
                if kind == "t":
                    res = guard(scale.search, a, q, x)
                    prods = [{"item_id": str(z.get("itemId")), "title": z.get("title"), "price_usd": fnum(z.get("targetSalePrice")),
                              "orders": int(fnum(z.get("orders")) or 0), "rating": fnum(z.get("evaluateRate")), "image": z.get("itemMainPic"),
                              "cate": z.get("cateId")} for z in res.get("products") or []]
                else:
                    res = guard(scale.image_search, a, "ae:" + q, x)
                    prods = []
                    for z in res.get("products") or []:
                        pr = fnum(z.get("target_sale_price"))
                        prods.append({"item_id": str(z.get("product_id")), "title": z.get("product_title"),
                                      "price_usd": round(pr / 100.0, 2) if pr is not None else None,
                                      "orders": int(re.sub(r"[^0-9]", "", str(z.get("latest_volume") or "0")) or 0),
                                      "rating": (fnum(z.get("evaluate_rate")) or 0) * 20 or None, "image": z.get("product_main_image_url"),
                                      "sim": fnum(z.get("similarity_score")), "cate": z.get("second_level_category_id")})
            except (client.AeError, OSError, SystemExit) as e:
                print("[final] skip %s %r: %s" % (key, q, e), file=sys.stderr)
                done.add(tag)
                continue
            for r in prods:
                if kind == "i" and ((r.get("sim") or 0) < 0.55 or r["item_id"] == q):
                    continue
                if registry.check(ds.key_of(r["item_id"]), reg)["action"] == "skip":
                    continue  # --hide-seen
                r.update(key=key, query=tag)
                rows.append(r)
                added += 1
            done.add(tag)
        print("[final] %s searched" % key, file=sys.stderr)
        with open(path, "w") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print("final search %s: %d new rows" % (room, added))


def shortlist(room, top=12):
    P = load_plan(room)
    path = screen_path(room)
    rows = [json.loads(l) for l in open(path)] if os.path.exists(path) else []
    out = {}
    for key, p in P.items():
        maxp = max([v for v in p["slot_price"].values() if v] or [0])
        best = {}
        for r in rows:
            if r.get("key") != key:
                continue
            q = quality(r, key, maxp)
            if q is None:
                continue
            if r["item_id"] not in best or best[r["item_id"]][0] < q:
                best[r["item_id"]] = (q, r)
        out[key] = sorted(best.values(), key=lambda x: -x[0])[:top]
    return out


def det_path(room):
    return os.path.join(WORK, "detail-%s.json" % room)


def do_detail(room, a):
    path = det_path(room)
    det = json.load(open(path)) if os.path.exists(path) else {}
    n = 0
    try:
        for key, picks in shortlist(room).items():
            for q, r in picks:
                k = "%s|%s" % (key, r["item_id"])
                rec = det.get(k) or {"key": key, "item_id": r["item_id"], "source": "search"}
                rec.update(quality=q, query=r["query"], title=rec.get("title") or r["title"], image=rec.get("image") or r["image"],
                           orders=r.get("orders"), rating=r.get("rating"))
                if not rec.get("product_ok") and "error" not in rec:
                    a.slot = key
                    try:
                        prod, _ = guard(ds.fetch_product, a, r["item_id"])
                    except client.AeError as e:
                        rec.update(product_ok=False, error="%s %s" % (e.code, e.message)); det[k] = rec; continue
                    res = prod.get("result") or {}
                    skus = ds.as_list(res.get("ae_item_sku_info_dtos"))
                    sku, how = pick_room_sku(skus, key)
                    base = res.get("ae_item_base_info_dto") or {}
                    rec.update(product_ok=True, title=base.get("subject") or rec["title"], n_skus=len(skus),
                               ae_rating=ds.num(base.get("avg_evaluation_rating")), reviews=base.get("evaluation_count"),
                               sku=str(sku.get("sku_id")) if sku else None, sku_label=sku_text(sku) if sku else None, sku_pick=how,
                               sku_labels=[sku_text(s) for s in skus][:30],
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
    print("final detail %s: %d records" % (room, n))


def pool(room, P):
    """Earlier-round items reviewed at fit >= 7 for a style that needs the slot, not carded, shipping known (cache only)."""
    try:
        rv = json.load(open(os.path.join(scale.OUT, "review", room + ".json")))
        det = json.load(open(os.path.join(scale.OUT, "detail", room + ".json")))
    except (OSError, ValueError):
        return {}
    reg = registry.load()
    out = {}
    for rec in det.values():
        key = "%s/%s" % (room, rec.get("slot"))
        if key not in P or not rec.get("ship_ok") or scale.landed(rec) is None:
            continue
        r = rv.get(rec["item_id"]) or {}
        fits = {s: (v.get("fit") or 0) for s, v in r.items() if isinstance(v, dict) and v.get("verdict") != "reject" and s in P[key]["styles"]}
        if not fits or max(fits.values()) < 7:
            continue
        if (registry.check(ds.key_of(rec["item_id"]), reg).get("entry") or {}).get("status") == "card":
            continue
        out.setdefault(key, []).append(dict(rec, key=key, source="earlier round, reviewed", earlier_fit=fits))
    for key in out:
        out[key] = sorted(out[key], key=lambda r: -max(r["earlier_fit"].values()))[:6]
    return out


def do_sheet(room):
    from PIL import Image, ImageDraw
    import urllib.request
    P = load_plan(room)
    det = json.load(open(det_path(room))) if os.path.exists(det_path(room)) else {}
    pl = pool(room, P)
    imgdir = os.path.expanduser("~/.cache/ae-scale-img")
    os.makedirs(imgdir, exist_ok=True)
    index, brief, n = {}, {}, 0
    for key in P:
        cells = [r for r in det.values() if r.get("key") == key and r.get("ship_ok") and scale.landed(r) is not None]
        cells.sort(key=lambda r: -(r.get("quality") or 0))
        cells += [r for r in pl.get(key, []) if r["item_id"] not in {c["item_id"] for c in cells}]
        if not cells:
            continue
        slot = key.split("/")[1]
        G = gaps()[key]
        brief[key] = {"styles_needing": P[key]["styles"], "envelope_cm": P[key]["envelope_cm"], "qty": P[key]["qty"],
                      "name_he": next(iter(G.values())).get("name_he"),
                      "designer_spec_he": {s: G[s].get("designer_spec_he") for s in G if G[s].get("designer_spec_he")}}
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
            index[str(n)] = {"key": key, "item_id": c["item_id"], "source": c.get("source", "search")}
            d.rectangle([x, y + H - 55, x + W, y + H], fill="white")
            d.text((x + 5, y + H - 52), "#%d %s %s" % (n, "P" if c.get("source") != "search" else "", c["item_id"][-6:]), fill="black")
            d.text((x + 5, y + H - 38), "%.0f ILS %s" % (scale.landed(c), (c.get("sku_label") or "")[:26]), fill="black")
            d.text((x + 5, y + H - 24), (c.get("title") or "")[:40], fill="gray")
        sheet.save(os.path.join(WORK, "fin-%s-%s.jpg" % (room, slot)), quality=80)
    json.dump(index, open(os.path.join(WORK, "fin-%s-index.json" % room), "w"), indent=0)
    json.dump(brief, open(os.path.join(WORK, "fin-%s-brief.json" % room), "w"), ensure_ascii=False, indent=1)
    print("final sheets %s: %d candidates in %d slots" % (room, n, len(brief)))


def card_path(room, slot, cid):
    return scale.card_path(room, slot, cid)


def existing_card_for(room, slot, iid):
    d = os.path.dirname(card_path(room, slot, "x"))
    for p in glob.glob(os.path.join(d, "*.json")):
        try:
            c = json.load(open(p))
        except ValueError:
            continue
        if (c.get("supplier") or {}).get("product_url") == ds.ITEM_URL % iid:
            return c.get("id"), p
    return None, None


def do_write(room, a, write_cards=True):
    P = load_plan(room)
    idx = json.load(open(os.path.join(WORK, "fin-%s-index.json" % room)))
    rev = {}
    for rp in sorted(glob.glob(os.path.join(WORK, "fin-rev-%s.json" % room)) + glob.glob(os.path.join(WORK, "fin-rev-%s-*.json" % room))):
        rev.update(json.load(open(rp)))  # the review may come in parts (fin-rev-<room>-a.json, -b.json)
    det = json.load(open(det_path(room))) if os.path.exists(det_path(room)) else {}
    old = json.load(open(os.path.join(scale.OUT, "detail", room + ".json")))
    G = gaps()
    result = {"room": room, "source": "AliExpress (official DS API)", "date": "2026-10-13", "method": __doc__.split("\n\n")[1].strip(),
              "api_calls": None, "slots": {}}
    cands = {}
    for num, e in idx.items():
        v = rev.get(num)
        if not v:
            continue
        key = e["key"]
        rec = det.get("%s|%s" % (key, e["item_id"])) or old.get("%s|%s" % (key.split("/")[1], e["item_id"])) or {}
        p = P[key]
        styles = {s: float((v.get("styles") or {}).get(s, 0) or 0) for s in STYLES}
        c = {"source": "AliExpress", "id": e["item_id"], "url": ds.ITEM_URL % e["item_id"], "title": rec.get("title"),
             "image": rec.get("image"), "sku_or_vid": rec.get("sku"), "sku_label": rec.get("sku_label"), "cost_usd": rec.get("price_usd"),
             "ship_usd": rec.get("ship_usd"), "ship_days": rec.get("ship_days"), "qty": p["qty"],
             "dims_cm": v.get("dims_cm"), "fits_envelope": v.get("fits_envelope", "borderline"), "type_ok": bool(v.get("type_ok", True)),
             "style_fit_guess": styles, "found_by": e.get("source"), "card_id": None, "why_he": v.get("reason"), "econ": {}}
        for s in p["styles"]:
            c["econ"][s] = econ(rec, p["slot_price"].get(s), p["qty"])
        c["eligible"] = [s for s in p["styles"] if c["type_ok"] and c["fits_envelope"] in ("yes", "borderline")
                         and styles[s] >= 7 and c["econ"].get(s) and c["econ"][s]["contribution_ils"] >= 0]
        first = next((x for x in c["econ"].values() if x), None)
        c.update(landed_ils=first and first["landed_ils"], slot_price_ils=p["slot_price"], margin_pct={s: x and x["margin_pct"] for s, x in c["econ"].items()})
        cands.setdefault(key, []).append(c)
    carded = []
    for key, p in P.items():
        cs = cands.get(key, [])
        existing = set(p["existing"])
        picks, per_style = [], {s: 0 for s in p["styles"]}
        for c in sorted(cs, key=lambda c: (-len(c["eligible"]), -sum(c["style_fit_guess"][s] for s in c["eligible"]),
                                           -max([x["margin_pct"] for x in c["econ"].values() if x] or [0]))):
            if not c["eligible"] or len(picks) >= 8:
                continue
            if not any(per_style[s] < 2 for s in c["eligible"]):
                continue
            picks.append(c)
            for s in c["eligible"]:
                per_style[s] += 1
        slot = key.split("/")[1]
        for c in picks:
            iid = c["id"]
            cid, path = existing_card_for(room, slot, iid)
            if cid in existing or (cid and path):
                c["card_id"] = cid
                c["card_note"] = "existing card"
                continue
            if not write_cards:
                continue
            cid = "%s-aliexpress-%s-%s" % (slot, ds.slugify(c["title"] or iid, words=4, maxlen=36), iid[-6:])
            path = card_path(room, slot, cid)
            argv = ["--by", BY, "--run-id", a.run_id, "--max-calls", str(a.max_calls), "card", iid, "--slot", key, "--id", cid, "--out", path]
            if c["sku_or_vid"]:
                argv += ["--sku", c["sku_or_vid"]]
            rc = ds.main(argv)
            if rc not in (0, None) or not os.path.exists(path):
                print("card failed %s %s rc=%s" % (key, iid, rc), file=sys.stderr)
                continue
            card = json.load(open(path))
            card.setdefault("room", room)
            ec = "; ".join("%s: price ₪%s, landed ₪%s, margin %s%%" % (s, p["slot_price"].get(s), x["landed_ils"], x["margin_pct"])
                           for s, x in c["econ"].items() if x and s in c["eligible"])
            fits = ", ".join("%s %g" % (s, c["style_fit_guess"][s]) for s in STYLES)
            card["notes"] = ("%s: AliExpress, qty %d, SKU %s. Economics at the slot price: %s. Style fit guess (not a score): %s. "
                             "Envelope: %s%s. %s " % (TAG, c["qty"], c["sku_label"], ec, fits, c["fits_envelope"],
                                                      " (%s)" % c["dims_cm"] if c.get("dims_cm") else "", c["why_he"] or "")) + (card.get("notes") or "")
            card["style_scores"] = {}
            json.dump(card, open(path, "w"), ensure_ascii=False, indent=2)
            open(path, "a").write("\n")
            c["card_id"] = cid
            carded.append(cid)
        # registry: what was looked at and not carded
        for c in cs:
            if c["card_id"]:
                continue
            st = "rejected" if (not c["type_ok"] or max(c["style_fit_guess"].values()) < 6) else "seen"
            why = "%s: %s" % (TAG, c["why_he"] or "") if st == "rejected" else "%s: reviewed, not chosen (fit %s)" % (TAG, max(c["style_fit_guess"].values()))
            try:
                registry.add(ds.key_of(c["id"]), st, why, by=BY, slot=key, opened=True, url=c["url"])
            except Exception as e:
                print("registry %s: %s" % (c["id"], e), file=sys.stderr)
        need = {s: G[key][s].get("need") for s in p["styles"]}
        filled = {s: sum(1 for c in picks if s in c["eligible"]) for s in p["styles"]}
        if picks:
            verdict = "נמצאו %d מוצרים: %s" % (len(picks), ", ".join("%s %d/%s" % (s, filled[s], need[s]) for s in p["styles"] if filled[s]))
        elif cs:
            best = max(cs, key=lambda c: max(c["style_fit_guess"].values()))
            verdict = "לא נמצא מוצר עובר. הקרוב: %s (fit %g, %s)" % (best["id"], max(best["style_fit_guess"].values()), best["why_he"] or "")
        else:
            verdict = "לא נמצאו מועמדים מהסוג הנכון"
        result["slots"][key] = {"styles_needing": p["styles"], "queries_aliexpress": p["queries"],
                                "candidates": [{k: v for k, v in c.items() if k != "eligible"} | {"eligible_styles": c["eligible"]} for c in cs],
                                "verdict_he": verdict}
    os.makedirs(RES, exist_ok=True)
    json.dump(result, open(os.path.join(RES, "aliexpress-%s.json" % room), "w"), ensure_ascii=False, indent=1)
    write_md(room, result, P)
    add_index(room, P)
    print("final write %s: %d cards" % (room, len(carded)))


def write_md(room, result, P):
    L = ["# סבב הליקוט האחרון, AliExpress: %s (2026-10-13)" % room, "",
         "חיפוש אחד לכל עמדה לכל הסגנונות, 2–4 שאילתות חדשות לכל עמדה, וחיפוש לפי תמונה ממועמדים קרובים מסבבים קודמים. "
         "אחר כך בדיקה מלאה, משלוח לישראל וניחוש התאמה (1–10) לכל סגנון. כרטיס נכתב רק ל-fit 7 ומעלה בסגנון שצריך את העמדה, "
         "בלי הפסד במחיר העמדה ובמעטפת שמתאימה. אין style_scores בכרטיסים: הניקוד האמיתי יינתן בפינישים.", "",
         "| עמדה | סגנונות שצריכים | כרטיסים | מסקנה |", "| --- | --- | --- | --- |"]
    tot = 0
    for key, s in result["slots"].items():
        cards = [c["card_id"] for c in s["candidates"] if c.get("card_id")]
        tot += len(cards)
        L.append("| %s | %s | %s | %s |" % (key, ", ".join(s["styles_needing"]), "<br>".join(cards) or "—", s["verdict_he"].replace("|", "/")))
    L += ["", "סה\"כ כרטיסים (כולל קיימים שנבחרו שוב): %d." % tot]
    open(os.path.join(RES, "aliexpress-%s.md" % room), "w").write("\n".join(L) + "\n")


def add_index(room, P):
    d = json.load(open(INDEX))
    q = d.setdefault("aliexpress_queries_by_slot", {})
    for key, p in P.items():
        lst = q.setdefault(key, [])
        for x in p["queries"]:
            if x not in lst:
                lst.append(x)
    d["updated"] = "2026-10-13"
    json.dump(d, open(INDEX, "w"), ensure_ascii=False, indent=1)


def main():
    stage, room = sys.argv[1], sys.argv[2]
    a = scale.ns(room, 4000)
    a.run_id, a.by = "final-2026-10-13-%s" % room, BY
    a.hide_seen = True
    try:
        if stage == "plan":
            plan(room)
        elif stage == "search":
            do_search(room, a)
        elif stage == "detail":
            do_detail(room, a)
        elif stage == "sheet":
            do_sheet(room)
        elif stage == "write":
            do_write(room, a, write_cards="--no-cards" not in sys.argv)
    except Stop as e:
        print("final STOP %s %s: %s" % (stage, room, e), file=sys.stderr)
        return 4
    return 0


if __name__ == "__main__":
    sys.exit(main())
