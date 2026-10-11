#!/usr/bin/env python3
"""AliExpress scale run (studio rules ז.00, user request 2026-10-11: "hundreds, not ten at a time").

Stages per room (outputs under data/leads/aliexpress/scale-2026-10/):
  screen   <room>   2 searches per slot x style ("<style word> <q>", page size 20 = the API max), a 2nd page for the first
                    query when page 1 is strong. Every row -> screen/<room>.jsonl. Transparent score (see score_row).
  detail   <room>   top N per slot x style (dedup across styles) -> ds.product.get + SKU that fits the room
                    (scale_config size regexes) + ds.freight.query for that SKU -> detail/<room>.json
  sheet    <room>   contact sheets of the top candidates (main image, index, price) -> review/<room>-<slot>.jpg, to look at
  finalize <room>   merge review/<room>.json (fit 1-10 + reason after looking at the images), economics, comparison with
                    the existing card, verdicts; writes <room>.json/.md, deep-2026-10/<room>.json, cards (ds.py card --sku --id)
                    for the best 3 per slot x style with fit >= 8 and margin >= the existing card's, registry seen/rejected.

Economics as site/shared/src/pricing.ts with the studio defaults (economics.ts, FR-C): fx 3.3, VAT 18%, card 2% + 1.20,
returns 8%, packaging 0. retail = the top of the market band (data/economics/market-prices.json). CAC (100 / 1.4 items)
is reported separately (margin_after_cac_ils), as in the studio.

Budget: every call goes through scripts/sourcing/budget.py (source "aliexpress"); --max-calls is this run's cap.
Stops immediately on any AliExpress flow-control / limit error (exit 4) and writes the observation to stop-<room>.txt.
"""
import argparse, glob, io, json, math, os, re, sys, time, types, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
import ds, client  # noqa: E402
from ds import budget, cache, registry  # noqa: E402
from scale_config import SLOTS, STYLES, GLOBAL_BAD, ROOMS, ROOM_DIRS  # noqa: E402

OUT = os.path.join(REPO, "data", "leads", "aliexpress", "scale-2026-10")
DEEP = os.path.join(REPO, "data", "leads", "aliexpress", "deep-2026-10")
FX, VAT, FEE, FEE_FIX, RET, CAC, ITEMS = 3.3, 0.18, 0.02, 1.2, 0.08, 100.0, 1.4
STYLE_ORDER = ["nordic", "warm-modern", "japandi", "mediterranean", "modern-country", "boho"]
STYLE_HE = {"nordic": "נורדי", "warm-modern": "מודרני חם", "japandi": "ג'פנדי", "mediterranean": "ים תיכוני",
            "modern-country": "כפרי מודרני", "boho": "בוהו"}
TODAY = "2026-10-11"


class Stop(Exception):
    pass


def ns(room, max_calls):
    return types.SimpleNamespace(dry_run=False, force=False, by="aliexpress-scale", run_id="scale-2026-10-%s" % room,
                                 max_calls=max_calls, no_cache=False, hide_seen=False, raw=True, ship_to="IL", currency="USD",
                                 lang="en", full=False, slot=None)


def guard(fn, *args):
    """Run an API helper; stop the whole run on flow control or a budget stop."""
    try:
        return fn(*args)
    except budget.BudgetExceeded as e:
        raise Stop("budget: %s" % e)
    except client.AeError as e:
        if client.is_flow_control(e) or "limit" in ("%s %s" % (e.code, e.message)).lower():
            raise Stop("flow control: %s | %s" % (e.code, e.message))
        raise


def slots_of(room):
    return [k for k in SLOTS if k.split("/")[0] == room]


def load_bands():
    d = json.load(open(os.path.join(REPO, "data", "economics", "market-prices.json")))
    return d["categories"]


BANDS = None


def band_of(cfg):
    global BANDS
    if BANDS is None:
        BANDS = load_bands()
    b = cfg["band"]
    if isinstance(b, list):
        return b, "estimated"
    return BANDS[b]["band"], b


def economics(retail, landed):
    net = retail / (1 + VAT)
    contribution = net - landed - (retail * FEE + FEE_FIX) - net * RET
    return round(contribution, 1), round(contribution / net, 3) if net else 0.0


def max_landed(retail, target=0.35):
    net = retail / (1 + VAT)
    return net * (1 - RET - target) - retail * FEE - FEE_FIX


# ----------------------------------------------------------------------------- screen

def search(a, q, page):
    params = {"keyWord": q, "local": "en_US", "countryCode": "IL", "currency": "USD", "pageSize": 20, "pageIndex": page}
    hit = cache.get_query(ds.SRC, "search", params)
    if hit:
        return hit["payload"]
    ds.spend(a, "search")
    d = client.call_ok(ds.M_SEARCH, params)
    data = d.get("data") if isinstance(d, dict) else None
    prods = []
    if isinstance(data, dict):
        prods = data.get("products") or []
        if isinstance(prods, dict):
            prods = next(iter(prods.values()), [])
    res = {"query": q, "params": params, "total": (data or {}).get("totalCount"), "page": page, "products": prods}
    cache.put_query(ds.SRC, "search", params, res, endpoint=ds.M_SEARCH)
    return res


def fnum(v):
    try:
        return float(str(v).replace("%", "").replace(",", ""))
    except (TypeError, ValueError):
        return None


def score_row(row, key, style):
    """Transparent heuristic, 0-100. Returns (score, notes)."""
    cfg, st = SLOTS[key], STYLES[style]
    t = (row.get("title") or "").lower()
    s, why = 0, []
    if re.search(cfg["must"], t, re.I):
        s += 30
    else:
        s -= 40; why.append("no-noun")
    gbad = GLOBAL_BAD if not key.startswith("kids/") else GLOBAL_BAD.replace(r"cartoon|", "").replace(r"car\b|", "")
    bad = re.findall(gbad, t, re.I) + re.findall(st["bad"], t, re.I) + (re.findall(cfg["bad"], t, re.I) if cfg.get("bad") else [])
    if bad:
        s -= 25 * len(bad); why.append("bad:" + ",".join(sorted(set(b if isinstance(b, str) else b[0] for b in bad))))
    bonus = set(m if isinstance(m, str) else m[0] for m in re.findall(st["bonus"], t, re.I))
    s += min(20, 5 * len(bonus))
    band, _ = band_of(cfg)
    ml = max_landed(band[1])
    est = ((row.get("price_usd") or 0) + cfg.get("ship", 5)) * FX
    if row.get("price_usd") is None:
        s -= 10
    elif est <= ml:
        s += 20 if est >= 0.15 * ml else 12
    elif est <= 1.3 * ml:
        s += 5; why.append("price-tight")
    else:
        s -= 20; why.append("price-high")
    o = row.get("orders") or 0
    s += min(15, 5 * math.log10(o + 1))
    r = row.get("rating")
    if r is not None:
        s += 5 if r >= 95 else 2 if r >= 90 else -5 if r < 80 else 0
    return round(s, 1), why


def do_screen(room, a):
    os.makedirs(os.path.join(OUT, "screen"), exist_ok=True)
    path = os.path.join(OUT, "screen", room + ".jsonl")
    rows, calls0 = [], None
    for key in slots_of(room):
        cfg = SLOTS[key]
        for style in STYLE_ORDER:
            for qi, w in enumerate(STYLES[style]["words"]):
                q = "%s %s" % (w, cfg["q"])
                pages = [1]
                got = []
                for page in pages:
                    res = guard(search, a, q, page)
                    for p in res.get("products") or []:
                        r = {"item_id": str(p.get("itemId")), "title": p.get("title"), "price_usd": fnum(p.get("targetSalePrice")),
                             "orders": int(fnum(p.get("orders")) or 0), "rating": fnum(p.get("evaluateRate")),
                             "image": p.get("itemMainPic"), "query": q, "page": page, "slot": key.split("/")[1], "style": style,
                             "cate": p.get("cateId")}
                        r["score"], r["why"] = score_row(r, key, style)
                        got.append(r)
                    # a second page for the first query when page 1 is strong (>= 12 rows that name the product)
                    if qi == 0 and page == 1 and sum(1 for r in got if "no-noun" not in r["why"] and r["score"] >= 40) >= 12:
                        pages.append(2)
                rows += got
        print("[screen] %s: %d rows so far" % (key, len(rows)), file=sys.stderr)
    with open(path, "w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print("screen %s: %d rows, %d unique items -> %s" % (room, len(rows), len({r["item_id"] for r in rows}), os.path.relpath(path, REPO)))


# ----------------------------------------------------------------------------- detail

def sku_text(s):
    return " ".join("%s %s" % (p.get("sku_property_name"), p.get("property_value_definition_name") or p.get("sku_property_value"))
                    for p in ds.as_list(s.get("ae_sku_property_dtos")))


def pick_room_sku(skus, key):
    """The SKU that fits the room: the first size regex that matches an in-stock SKU (cheapest among matches);
    else the cheapest in stock (flag sku-default)."""
    stock = [s for s in skus if (ds.num(s.get("sku_available_stock")) or 0) > 0] or skus
    price = lambda s: ds.num(s.get("offer_sale_price")) or ds.num(s.get("sku_price")) or 1e9
    for rx in SLOTS[key].get("size") or []:
        m = [s for s in stock if re.search(rx, sku_text(s), re.I) and not ds.sku_options.BOGUS.search(sku_text(s))]
        if m:
            return min(m, key=price), "size-match"
    ok = [s for s in stock if not ds.sku_options.BOGUS.search(sku_text(s))] or stock
    return (min(ok, key=price), "sku-default") if ok else (None, "no-sku")


def best_freight(opts):
    """Cheapest option with days_max <= 45; else the cheapest at all."""
    o = [x for x in opts or [] if x.get("fee") is not None]
    if not o:
        return None
    fast = [x for x in o if (x.get("days_max") or 99) <= 45]
    return min(fast or o, key=lambda x: (x["fee"], x.get("days_max") or 99))


def shortlist(room, top):
    rows = [json.loads(l) for l in open(os.path.join(OUT, "screen", room + ".jsonl"))]
    for r in rows:  # rescore with the current config (fixes to scale_config apply without new searches)
        r["score"], r["why"] = score_row(r, "%s/%s" % (room, r["slot"]), r["style"])
    reg = registry.load()
    picks = {}  # (slot, style) -> [rows]
    for key in slots_of(room):
        slot = key.split("/")[1]
        for style in STYLE_ORDER:
            cand = {}
            for r in rows:
                if r["slot"] == slot and r["style"] == style and r["score"] >= 35:
                    if r["item_id"] not in cand or cand[r["item_id"]]["score"] < r["score"]:
                        cand[r["item_id"]] = r
            ranked = []
            for r in sorted(cand.values(), key=lambda r: -r["score"]):
                c = registry.check(ds.key_of(r["item_id"]), reg)
                if c["action"] == "skip" and (c.get("entry") or {}).get("status") == "rejected":
                    continue
                ranked.append(r)
                if len(ranked) >= top:
                    break
            picks[(slot, style)] = ranked
    return picks


def do_detail(room, a, top):
    picks = shortlist(room, top)
    path = os.path.join(OUT, "detail", room + ".json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    done = json.load(open(path)) if os.path.exists(path) else {}
    items = {}
    for (slot, style), rs in picks.items():
        for r in rs:
            items.setdefault((slot, r["item_id"]), []).append((style, r))
    print("detail %s: %d slot x item pairs, %d unique items" % (room, len(items), len({i for _, i in items})), file=sys.stderr)
    n = 0
    try:
        for (slot, iid), styles in items.items():
            k = "%s|%s" % (slot, iid)
            if k in done and done[k].get("styles") and set(s for s, _ in styles) <= set(done[k]["styles"]):
                continue
            key = "%s/%s" % (room, slot)
            rec = done.get(k) or {"slot": slot, "item_id": iid}
            rec["styles"] = sorted(set(rec.get("styles", [])) | set(s for s, _ in styles), key=STYLE_ORDER.index)
            rec["screen"] = {s: {"score": r["score"], "why": r["why"], "query": r["query"]} for s, r in styles}
            r0 = styles[0][1]
            rec.update(title=r0["title"], image=r0["image"], orders=r0["orders"], rating=r0["rating"], search_price_usd=r0["price_usd"])
            if "product_ok" not in rec:
                try:
                    a.slot = key
                    prod, _ = guard(ds.fetch_product, a, iid)
                except client.AeError as e:
                    rec.update(product_ok=False, error="%s %s" % (e.code, e.message))
                    done[k] = rec
                    continue
                r = prod.get("result") or {}
                base = r.get("ae_item_base_info_dto") or {}
                skus = ds.as_list(r.get("ae_item_sku_info_dtos"))
                props = ds.as_list(r.get("ae_item_properties"))
                sku, how = pick_room_sku(skus, key)
                rec.update(product_ok=True, title=base.get("subject") or rec["title"], n_skus=len(skus),
                           ae_rating=ds.num(base.get("avg_evaluation_rating")), reviews=base.get("evaluation_count"),
                           sales=base.get("sales_count"),
                           materials=[p.get("attr_value") for p in props if "material" in str(p.get("attr_name") or "").lower()][:4],
                           sku=str(sku.get("sku_id")) if sku else None, sku_label=sku_text(sku) if sku else None, sku_pick=how,
                           price_usd=(ds.num(sku.get("offer_sale_price")) or ds.num(sku.get("sku_price"))) if sku else None,
                           stock=ds.num(sku.get("sku_available_stock")) if sku else None)
            if rec.get("product_ok") and rec.get("sku") and "ship_usd" not in rec:
                fr, _ = guard(ds.fetch_freight, a, iid, rec["sku"], "IL", 1)
                b = best_freight(fr.get("options"))
                rec.update(ship_usd=b["fee"] if b else None, ship_days="%s-%s" % (b.get("days_min"), b.get("days_max")) if b else None,
                           ship_company=(b.get("company") or b.get("code")) if b else None, ship_ok=bool(b),
                           ship_msg=None if b else (fr.get("msg") or fr.get("code")))
            done[k] = rec
            n += 1
            if n % 25 == 0:
                json.dump(done, open(path, "w"), ensure_ascii=False, indent=0)
                print("[detail] %s: %d done" % (room, n), file=sys.stderr)
    finally:
        json.dump(done, open(path, "w"), ensure_ascii=False, indent=0)
    print("detail %s: %d records -> %s" % (room, len(done), os.path.relpath(path, REPO)))


# ----------------------------------------------------------------------------- economics + ranking

def landed(rec):
    if rec.get("price_usd") is None or rec.get("ship_usd") is None:
        return None
    return round((rec["price_usd"] + rec["ship_usd"]) * FX, 1)


def prelim_fit(rec, style):
    """Heuristic fit 1-10 before anyone looked at the image; capped at 7 (8+ needs a look at the photo)."""
    sc = (rec.get("screen") or {}).get(style, {}).get("score", 0)
    f = 3 + sc / 15.0
    if rec.get("ae_rating") and rec["ae_rating"] >= 4.7:
        f += 0.5
    if any(re.search(r"plastic|pvc|acrylic|resin", str(m), re.I) for m in rec.get("materials") or []):
        f -= 2
    return round(max(1, min(7, f)), 1)


def ranked_for_review(room):
    det = json.load(open(os.path.join(OUT, "detail", room + ".json")))
    out = {}
    for k, rec in det.items():
        L = landed(rec)
        if not rec.get("ship_ok") or L is None:
            continue
        key = "%s/%s" % (room, rec["slot"])
        band, _ = band_of(SLOTS[key])
        m_ils, m_pct = economics(band[1], L)
        for style in rec["styles"]:
            out.setdefault((rec["slot"], style), []).append((prelim_fit(rec, style) + max(-2, min(2, m_pct * 4)), rec, m_pct))
    for v in out.values():
        v.sort(key=lambda x: -x[0])
    return out


def do_sheet(room, per_style):
    from PIL import Image, ImageDraw
    rk = ranked_for_review(room)
    odir = os.path.join(OUT, "review", "sheets")
    os.makedirs(odir, exist_ok=True)
    imgdir = os.path.join(os.path.expanduser("~/.cache/ae-scale-img"))
    os.makedirs(imgdir, exist_ok=True)
    index = {}
    for key in slots_of(room):
        slot = key.split("/")[1]
        cells = []
        seen = set()
        for style in STYLE_ORDER:
            for _, rec, m in rk.get((slot, style), [])[:per_style]:
                if rec["item_id"] in seen:
                    continue
                seen.add(rec["item_id"])
                cells.append((style, rec, m))
        if not cells:
            continue
        W, H, cols = 260, 300, 6
        rows = (len(cells) + cols - 1) // cols
        sheet = Image.new("RGB", (W * cols, H * rows), "white")
        d = ImageDraw.Draw(sheet)
        for i, (style, rec, m) in enumerate(cells):
            x, y = (i % cols) * W, (i // cols) * H
            fp = os.path.join(imgdir, rec["item_id"] + ".jpg")
            if not os.path.exists(fp) and rec.get("image"):
                for url in (rec["image"] + "_220x220.jpg", rec["image"]):
                    try:
                        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                        with urllib.request.urlopen(req, timeout=20) as r:
                            data = r.read()
                        with open(fp, "wb") as f:
                            f.write(data)
                        break
                    except Exception:
                        pass
            try:
                im = Image.open(fp).convert("RGB")
                im.thumbnail((W - 10, H - 60))
                sheet.paste(im, (x + 5, y + 5))
            except Exception:
                d.text((x + 10, y + 100), "no image", fill="red")
            n = len(index) + 1
            index[str(n)] = {"slot": slot, "item_id": rec["item_id"], "style": style}
            d.rectangle([x, y + H - 55, x + W, y + H], fill="white")
            d.text((x + 5, y + H - 52), "#%d %s %s" % (n, style[:6], rec["item_id"][-6:]), fill="black")
            d.text((x + 5, y + H - 38), "$%.2f+%.2f m%d%% %s" % (rec.get("price_usd") or 0, rec.get("ship_usd") or 0, round(m * 100), (rec.get("sku_label") or "")[:16]), fill="black")
            d.text((x + 5, y + H - 24), (rec.get("title") or "")[:40], fill="gray")
        sheet.save(os.path.join(odir, "%s-%s.jpg" % (room, slot)), quality=80)
    json.dump(index, open(os.path.join(odir, room + "-index.json"), "w"), indent=0)
    print("sheets %s: %d candidates -> %s" % (room, len(index), os.path.relpath(odir, REPO)))


# ----------------------------------------------------------------------------- existing cards

def existing_cards(room):
    """{slot: [{card_id, landed_ils, supplier, fit_by_style}]} for the room's current cards (all suppliers)."""
    fx_cj = json.load(open(os.path.join(REPO, "data", "economics", "freight-cj.json")))["products"]
    base = os.path.join(REPO, "data", "products")
    out = {}
    if ROOM_DIRS[room] is None:
        paths = [p for p in glob.glob(os.path.join(base, "*", "*.json"))]
        known = {k.split("/")[1] for k in slots_of(room)}
        paths = [p for p in paths if os.path.basename(os.path.dirname(p)) in known]
    else:
        paths = glob.glob(os.path.join(base, ROOM_DIRS[room], "*", "*.json"))
    for p in paths:
        try:
            c = json.load(open(p))
        except ValueError:
            continue
        slot = os.path.basename(os.path.dirname(p))
        cost = (c.get("price") or {}).get("cost")
        if not isinstance(cost, (int, float)):
            continue
        ship, src = None, None
        q = (fx_cj.get(c.get("id")) or {}).get("options") or []
        if q:
            ship, src = min(o["usd"] for o in q if isinstance(o.get("usd"), (int, float))), "cj-freight"
        if ship is None:
            o = (c.get("options") or {})
            for s in o.get("skus") or []:
                if s.get("id") == o.get("default_sku") and isinstance((s.get("shipping_il") or {}).get("amount"), (int, float)):
                    ship, src = s["shipping_il"]["amount"], "options"
        if ship is None:
            m = re.search(r"shipping to IL\s*:[^$\d]*(?:\$\s*(\d+(?:\.\d+)?)|(\d+(?:\.\d+)?)\s*USD)", c.get("notes") or "", re.I)
            if m:
                ship, src = float(m.group(1) or m.group(2)), "notes"
        cur = (c.get("price") or {}).get("currency") or "USD"
        if cur == "ILS":
            L = round(cost + (ship or 0), 1)
        else:
            L = round((cost + (ship if ship is not None else 5.0)) * FX, 1)
        sup = (c.get("supplier") or {}).get("name") or "?"
        fits = {k: (v or {}).get("score") for k, v in (c.get("style_scores") or {}).items() if isinstance(v, dict)}
        out.setdefault(slot, []).append({"card_id": c.get("id"), "landed_ils": L, "ship_src": src or "estimated-5usd", "supplier": sup,
                                         "fits": fits, "status": c.get("status")})
    return out


def compare_card(cards, style):
    """The existing card to beat for a style: the best-fitting card for that style (else the cheapest landed)."""
    if not cards:
        return None
    scored = [c for c in cards if isinstance(c["fits"].get(style), (int, float))]
    if scored:
        return max(scored, key=lambda c: (c["fits"][style], -c["landed_ils"]))
    return min(cards, key=lambda c: c["landed_ils"])


# ----------------------------------------------------------------------------- finalize

def card_path(room, slot, card_id):
    d = os.path.join(REPO, "data", "products", slot) if ROOM_DIRS[room] is None else os.path.join(REPO, "data", "products", ROOM_DIRS[room], slot)
    return os.path.join(d, card_id + ".json")


def do_finalize(room, a, write_cards=True):
    det = json.load(open(os.path.join(OUT, "detail", room + ".json")))
    rv_path = os.path.join(OUT, "review", room + ".json")
    review = json.load(open(rv_path)) if os.path.exists(rv_path) else {}
    cards = existing_cards(room)
    recs = []
    for k, rec in det.items():
        key = "%s/%s" % (room, rec["slot"])
        cfg = SLOTS[key]
        band, band_src = band_of(cfg)
        L = landed(rec)
        for style in rec.get("styles", []):
            rvw = (review.get(rec["item_id"]) or {})
            rv = rvw.get(style) or rvw.get("*") or {}
            fit = rv.get("fit", prelim_fit(rec, style))
            reason = rv.get("reason") or ("screening only (not looked at): " + ", ".join(
                [x for x in (rec.get("screen", {}).get(style, {}).get("why") or [])] or ["keyword fit"]))
            cmp_ = compare_card(cards.get(rec["slot"]), style)
            r = {"room": room, "slot": rec["slot"], "style": style, "item_id": rec["item_id"], "title": rec.get("title"),
                 "url": ds.ITEM_URL % rec["item_id"], "image": rec.get("image"), "sku": rec.get("sku"), "sku_label": rec.get("sku_label"),
                 "sku_pick": rec.get("sku_pick"), "price_usd": rec.get("price_usd"), "ship_usd": rec.get("ship_usd"),
                 "ship_days": rec.get("ship_days"), "ship_company": rec.get("ship_company"), "landed_ils": L,
                 "retail_band_ils": band, "band_source": band_src, "orders": rec.get("orders"), "reviews": rec.get("reviews"),
                 "rating": rec.get("ae_rating"), "materials": rec.get("materials"), "fit": fit, "reviewed": bool(rv),
                 "reason": reason, "compared_to": {"card_id": cmp_["card_id"], "landed_ils": cmp_["landed_ils"], "supplier": cmp_["supplier"]} if cmp_ else None}
            if L is None:
                r.update(margin_ils=None, margin_pct=None, margin_after_cac_ils=None, verdict="reject",
                         reject_why="no product data" if not rec.get("product_ok") else "no shipping to IL (%s)" % rec.get("ship_msg"))
            else:
                m_ils, m_pct = economics(band[1], L)
                r.update(margin_ils=m_ils, margin_pct=m_pct, margin_after_cac_ils=round(m_ils - CAC / ITEMS, 1))
                if rv.get("verdict") == "reject" or fit < 6:
                    r.update(verdict="reject", reject_why=rv.get("reason") or "fit %.1f" % fit)
                elif m_pct < 0:
                    r.update(verdict="reject", reject_why="loses money at the top of the market band (margin %d%%)" % round(m_pct * 100))
                else:
                    r["verdict"] = "candidate"
            recs.append(r)
    # rank per slot x style: fit first, then margin
    by = {}
    for r in recs:
        by.setdefault((r["slot"], r["style"]), []).append(r)
    to_card = {}
    for (slot, style), rs in by.items():
        live = sorted([r for r in rs if r["verdict"] == "candidate"], key=lambda r: (-r["fit"], -(r["margin_ils"] or -999)))
        for i, r in enumerate(live):
            r["verdict"] = "best" if i == 0 and r["fit"] >= 8 else "alternative"
            c = r["compared_to"]
            # same retail band for both, so "margin at least as good" == landed cost not higher
            beats = c is None or r["landed_ils"] <= c["landed_ils"]
            r["beats_existing"] = beats
            r["low_margin"] = r["margin_pct"] < 0.35
            if i < 3 and r["fit"] >= 8 and beats:
                to_card.setdefault((slot, r["item_id"]), []).append(r)
    # cards
    carded = []
    if write_cards:
        for (slot, iid), rs in to_card.items():
            r0 = max(rs, key=lambda r: r["fit"])
            cid = "%s-aliexpress-%s-%s" % (slot, ds.slugify(r0["title"] or iid, words=4, maxlen=36), iid[-6:])
            path = card_path(room, slot, cid)
            if not os.path.exists(path):
                argv = ["--by", "aliexpress-scale", "--run-id", a.run_id, "--max-calls", str(a.max_calls), "card", iid,
                        "--slot", "%s/%s" % (room, slot), "--sku", r0["sku"], "--id", cid, "--out", path]
                rc = ds.main(argv)
                if rc not in (0, None):
                    print("card failed %s %s rc=%s" % (slot, iid, rc), file=sys.stderr)
                    continue
                add_scale_note(path, rs)
            carded.append(cid)
            for r in rs:
                r["card_id"] = cid
    # registry: rejected with reason (only items not carded and not already rejected)
    reg = registry.load()
    for r in recs:
        if r["verdict"] == "reject" and not r.get("card_id"):
            c = registry.check(ds.key_of(r["item_id"]), reg)
            st = (c.get("entry") or {}).get("status")
            if st not in ("card", "rejected") and all(x["verdict"] == "reject" for x in recs if x["item_id"] == r["item_id"]):
                registry.add(ds.key_of(r["item_id"]), "rejected", "scale run 2026-10-11 %s/%s: %s" % (room, r["slot"], r.get("reject_why")),
                             by="aliexpress-scale", slot="%s/%s" % (room, r["slot"]), opened=True)
    write_outputs(room, recs, carded)
    return recs, carded


def add_scale_note(path, rs):
    c = json.load(open(path))
    txt = open(path).read()
    note = " Scale run 2026-10-11 (screening fit, not the designer's score): " + "; ".join(
        "%s %s/10 (%s), landed %.0f ILS, margin %d%% at %s ILS" % (r["style"], r["fit"], r["reason"], r["landed_ils"], round(r["margin_pct"] * 100), r["retail_band_ils"][1]) for r in rs)
    c["notes"] = (c.get("notes") or "") + note
    with open(path, "w") as f:
        json.dump(c, f, ensure_ascii=False, indent=2)
        f.write("\n")


def write_outputs(room, recs, carded):
    os.makedirs(DEEP, exist_ok=True)
    order = {s: i for i, s in enumerate(STYLE_ORDER)}
    vo = {"best": 0, "alternative": 1, "reject": 2}
    recs.sort(key=lambda r: (r["slot"], order[r["style"]], vo[r["verdict"]], -(r["fit"] or 0), -(r["margin_ils"] or -999)))
    screen = sum(1 for _ in open(os.path.join(OUT, "screen", room + ".jsonl")))
    meta = {"room": room, "updated": TODAY, "run": "aliexpress-scale 2026-10-11", "method": "scripts/ae/scale.py (see its docstring)",
            "economics": {"fx_usd_ils": FX, "vat": VAT, "card_fee": [FEE, FEE_FIX], "returns": RET, "cac_ils": CAC, "items_per_order": ITEMS,
                          "retail": "top of the market band (data/economics/market-prices.json); band_source 'estimated' = no market data"},
            "totals": {"screened_rows": screen, "detailed": len({r["item_id"] for r in recs}), "records": len(recs),
                       "best": sum(r["verdict"] == "best" for r in recs), "alternative": sum(r["verdict"] == "alternative" for r in recs),
                       "reject": sum(r["verdict"] == "reject" for r in recs), "carded": len(set(carded))},
            "records": recs}
    for d in (OUT, DEEP):
        with open(os.path.join(d, room + ".json"), "w") as f:
            json.dump(meta, f, ensure_ascii=False, indent=1)
            f.write("\n")
    write_md(room, meta)


def write_md(room, meta):
    recs = meta["records"]
    t = meta["totals"]
    L = ["# AliExpress בקנה מידה: %s (2026-10-11)" % room, "",
         "סוננו %d שורות חיפוש, נבדקו לעומק %d מוצרים (%d רשומות מוצר×סגנון). best %d · alternative %d · reject %d · כרטיסים חדשים %d." % (
             t["screened_rows"], t["detailed"], t["records"], t["best"], t["alternative"], t["reject"], t["carded"]), "",
         "עלות נחיתה = (מחיר SKU + משלוח זול עד 45 יום) × 3.3. רווח = לפי pricing.ts במחיר העליון של רצועת השוק (מע\"מ 18%, עמלה 2%+1.2, החזרות 8%), לפני CAC. "
         "fit ≥ 8 רק אחרי מבט בתמונה; fit בלי מבט (screening) מוגבל ל-7. "
         "ההשוואה: הכרטיס הקיים בעמדה עם הציון הגבוה לסגנון (אחרת הזול).", ""]
    slots = sorted({r["slot"] for r in recs}, key=lambda s: [k.split("/")[1] for k in slots_of(room)].index(s))
    for slot in slots:
        rs = [r for r in recs if r["slot"] == slot]
        L += ["## %s" % slot, "", "| סגנון | הבחירה | SKU | $ מוצר+משלוח | נחיתה ₪ | רצועה ₪ | רווח | fit | מול הכרטיס הקיים |", "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
        for st in STYLE_ORDER:
            live = [r for r in rs if r["style"] == st and r["verdict"] in ("best", "alternative")]
            if not live:
                L.append("| %s | — אין מועמד שעבר | | | | | | | |" % STYLE_HE[st])
                continue
            r = live[0]
            c = r["compared_to"]
            cmp_ = "%s ₪%.0f (%s)" % (c["card_id"], c["landed_ils"], c["supplier"]) if c else "אין כרטיס"
            L.append("| %s | [%s](%s)%s%s | %s | %.2f+%.2f, %s ימים | %.0f | %d–%d | ₪%.0f · %d%% | %s%s | %s %s |" % (
                STYLE_HE[st], (r["title"] or "")[:60].replace("|", "/"), r["url"], " · **%s**" % r["verdict"],
                " · כרטיס" if r.get("card_id") else "", (r.get("sku_label") or "—")[:40].replace("|", "/"),
                r["price_usd"], r["ship_usd"], r["ship_days"], r["landed_ils"], r["retail_band_ils"][0], r["retail_band_ils"][1],
                r["margin_ils"], round(r["margin_pct"] * 100), r["fit"], "" if r["reviewed"] else " (סינון)", cmp_,
                "✓ זול/רווחי יותר" if r.get("beats_existing") else "✗"))
        alts = [r for r in rs if r["verdict"] == "alternative"]
        if alts:
            L.append("")
            L.append("חלופות: " + " · ".join("%s [%s](%s) ₪%.0f/%d%%" % (STYLE_HE[r["style"]], r["item_id"], r["url"], r["landed_ils"], round(r["margin_pct"] * 100)) for r in alts[:12]))
        L.append("")
    with open(os.path.join(OUT, room + ".md"), "w") as f:
        f.write("\n".join(L) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["screen", "detail", "sheet", "finalize", "all"])
    ap.add_argument("room", choices=ROOMS)
    ap.add_argument("--max-calls", type=int, default=3000)
    ap.add_argument("--top", type=int, default=8)
    ap.add_argument("--per-style", type=int, default=3)
    ap.add_argument("--no-cards", action="store_true")
    a0 = ap.parse_args()
    a = ns(a0.room, a0.max_calls)
    t0 = time.time()
    try:
        if a0.stage in ("screen", "all"):
            do_screen(a0.room, a)
        if a0.stage in ("detail", "all"):
            do_detail(a0.room, a, a0.top)
        if a0.stage in ("sheet", "all"):
            do_sheet(a0.room, a0.per_style)
        if a0.stage == "finalize":
            recs, carded = do_finalize(a0.room, a, not a0.no_cards)
            print("finalize %s: %d records, %d cards" % (a0.room, len(recs), len(set(carded))))
    except Stop as e:
        msg = "%s STOP %s at %s: %s" % (a0.room, a0.stage, time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()), e)
        os.makedirs(OUT, exist_ok=True)
        with open(os.path.join(OUT, "stop-%s.txt" % a0.room), "a") as f:
            f.write(msg + "\n")
        print(msg, file=sys.stderr)
        return 4
    finally:
        print("[%s %s] %.0fs, budget today: %s" % (a0.stage, a0.room, time.time() - t0, budget.status()["sources"]["aliexpress"]["used"]), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
