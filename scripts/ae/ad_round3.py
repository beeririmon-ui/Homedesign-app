#!/usr/bin/env python3
"""Round 3 of the art director (2026-10-12): data/leads/next-sourcing/round-3-2026-10-11.json, run through the official API.

  search   run search_plan tier1 -> tier2 -> tier3 (AliExpress entries), then spare only for slots that are not full;
           deferred never runs. A query serving several slots runs once. Per-slot query caps: high 6, medium 4, low 2.
           hide-seen: a product already in data/sources/seen.json is not opened again. For each new result that names the
           product and whose search price fits under the slot's breakeven: product.get, the SKU that fits the slot's
           envelope (scale_config size rules), freight to IL. A candidate "passes" when its landed cost is within
           landed_for_40_ils (and never above breakeven_landed_ils) and its SKU size was matched. A slot stops at 3 passing.
           Every query is appended to searched-index.json (aliexpress_queries_by_slot); opened products go to the registry
           (ds.fetch_product does it). State: data/leads/next-sourcing/round-3-results/_ae_state.json (resumable).
  freight  shipping to IL for data/leads/profit-fix-2026-10-11/ae-freight-requests.json items and queries
           -> data/leads/profit-fix-2026-10-11/ae-freight-results.json
  sheet    contact sheets of every candidate per room (review/sheets/ad3-<room>-<slot>.jpg + index) for the visual review
  write    merge review/ad3-<room>.json (fit for all six styles) -> round-3-results/<room>.json and .md; draft cards for
           Nordic fit >= 8 that pass the price ceiling (ids unique across data/products)

Stops on any AliExpress flow-control error (exit 4), like scale.py. Budget: scripts/sourcing/budget.py.
"""
import argparse, glob, json, os, re, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import scale  # noqa: E402
from scale import ds, client, cache, registry, budget, guard, Stop, fnum, pick_room_sku, sku_text, best_freight, economics  # noqa: E402
from scale_config import SLOTS, STYLES, GLOBAL_BAD  # noqa: E402

REPO = scale.REPO
NS = os.path.join(REPO, "data", "leads", "next-sourcing")
PLAN = os.path.join(NS, "round-3-2026-10-11.json")
INDEX = os.path.join(NS, "searched-index.json")
RES = os.path.join(NS, "round-3-results")
STATE = os.path.join(RES, "_ae_state.json")
SHEETS = os.path.join(REPO, "data", "leads", "aliexpress", "scale-2026-10", "review", "sheets")
REVIEW = os.path.join(REPO, "data", "leads", "aliexpress", "scale-2026-10", "review")
CAPS = {"high": 6, "medium": 4, "low": 2}
FX = scale.FX
STYLE_ORDER = scale.STYLE_ORDER


def load_json(p, default):
    return json.load(open(p)) if os.path.exists(p) else default


def save_json(p, d):
    tmp = p + ".tmp"
    with open(tmp, "w") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
        f.write("\n")
    os.replace(tmp, p)


def plan():
    d = json.load(open(PLAN))
    return d, {s["slot"]: s for s in d["slots"]}


def add_to_index(slot_keys, q):
    idx = load_json(INDEX, {})
    by = idx.setdefault("aliexpress_queries_by_slot", {})
    for k in slot_keys:
        lst = by.setdefault(k, [])
        if q not in lst:
            lst.append(q)
    idx["updated"] = time.strftime("%Y-%m-%d")
    save_json(INDEX, idx)


def names_product(key, title):
    cfg = SLOTS.get(key) or {}
    t = (title or "").lower()
    if cfg.get("must") and not re.search(cfg["must"], t, re.I):
        return False
    gbad = GLOBAL_BAD if not key.startswith("kids/") else GLOBAL_BAD.replace(r"cartoon|", "").replace(r"car\b|", "")
    if re.search(gbad, t, re.I) or (cfg.get("bad") and re.search(cfg["bad"], t, re.I)):
        return False
    return True


def passes(c, ceil):
    if c.get("landed_ils") is None:
        return False
    lim = ceil.get("landed_for_40_ils") or ceil.get("breakeven_landed_ils")
    be = ceil.get("breakeven_landed_ils")
    if lim is None:
        return False
    if be is not None and c["landed_ils"] > be:
        return False
    return c["landed_ils"] <= lim and c.get("size_ok")


def entries(d, st, slots):
    """Plan entries in order, with the tier name; spare entries only for slots not full."""
    for tier in ("tier1", "tier2", "tier3", "spare"):
        for e in d["search_plan"][tier]:
            if e.get("source") == "aliexpress":
                yield tier, e


def do_search(a, per_query=5):
    d, slots = plan()
    st = load_json(STATE, {"queries_done": [], "slots": {}})
    reg = registry.load()
    for tier, e in entries(d, st, slots):
        q = e["query"]
        if q in st["queries_done"]:
            continue
        keys = [k for k in e["slots"] if k in slots and slots[k]["status"] != "on-hold"]
        live = []
        for k in keys:
            s = st["slots"].setdefault(k, {"queries": [], "candidates": {}})
            npass = sum(1 for c in s["candidates"].values() if c.get("passes"))
            cap = CAPS.get(slots[k].get("priority"), 2)
            if npass >= 3:
                continue
            if tier != "spare" and len(s["queries"]) >= cap:
                continue
            live.append(k)
        if not live:
            continue
        try:
            res = guard(scale.search, a, q, 1)
        except client.AeError as ex:
            print("[ad3] skip query %r: %s %s" % (q, ex.code, ex.message), file=sys.stderr)
            st["queries_done"].append(q); save_json(STATE, st)
            continue
        for k in live:
            s = st["slots"][k]
            s["queries"].append(q)
            ceil = slots[k].get("price_ceiling") or {}
            be_usd = ceil.get("breakeven_landed_usd") or ((ceil.get("breakeven_landed_ils") or 1e9) / FX)
            rows = []
            for p in res.get("products") or []:
                iid = str(p.get("itemId"))
                if iid in s["candidates"]:
                    continue
                c = registry.check(ds.key_of(iid), reg)
                if c["action"] == "skip":  # hide-seen
                    continue
                price = fnum(p.get("targetSalePrice"))
                if price is None or price > be_usd or not names_product(k, p.get("title")):
                    continue
                rows.append((int(fnum(p.get("orders")) or 0), p))
            for _, p in sorted(rows, key=lambda x: -x[0])[:per_query]:
                iid = str(p.get("itemId"))
                a.slot = k
                try:
                    prod, _ = guard(ds.fetch_product, a, iid)
                except client.AeError as ex:
                    continue
                r = prod.get("result") or {}
                skus = ds.as_list(r.get("ae_item_sku_info_dtos"))
                sku, how = pick_room_sku(skus, k) if k in SLOTS else (ds.pick_sku(skus), "sku-default")
                if not sku:
                    continue
                price = ds.num(sku.get("offer_sale_price")) or ds.num(sku.get("sku_price"))
                try:
                    fr, _ = guard(ds.fetch_freight, a, iid, str(sku["sku_id"]), "IL", 1)
                except client.AeError as ex:
                    fr = {"options": [], "msg": "%s %s" % (ex.code, ex.message)}
                b = best_freight(fr.get("options"))
                base = r.get("ae_item_base_info_dto") or {}
                size_ok = how == "size-match" or len(skus) <= 1 or not (SLOTS.get(k) or {}).get("size")
                c = {"item_id": iid, "title": base.get("subject") or p.get("title"), "image": p.get("itemMainPic"),
                     "url": ds.ITEM_URL % iid, "query": q, "tier": tier, "sku": str(sku.get("sku_id")), "sku_label": sku_text(sku),
                     "sku_pick": how, "n_skus": len(skus), "price_usd": price, "ship_usd": b["fee"] if b else None,
                     "ship_days": "%s-%s" % (b.get("days_min"), b.get("days_max")) if b else None,
                     "ship_company": (b.get("company") or b.get("code")) if b else None,
                     "landed_ils": round((price + b["fee"]) * FX, 1) if (b and price is not None) else None,
                     "orders": int(fnum(p.get("orders")) or 0), "rating": ds.num(base.get("avg_evaluation_rating")),
                     "reviews": base.get("evaluation_count"), "size_ok": size_ok,
                     "no_ship": None if b else (fr.get("msg") or fr.get("code"))}
                if c["landed_ils"] is not None and ceil.get("slot_price_ils"):
                    c["margin_ils"], c["margin_pct"] = economics(ceil["slot_price_ils"], c["landed_ils"])
                c["passes"] = passes(c, ceil)
                s["candidates"][iid] = c
                if sum(1 for x in s["candidates"].values() if x.get("passes")) >= 3:
                    break
        add_to_index(e["slots"], q)
        st["queries_done"].append(q)
        save_json(STATE, st)
        print("[ad3] %s %r -> %s" % (tier, q, ", ".join("%s:%d/%d" % (k, sum(1 for c in st["slots"][k]["candidates"].values() if c.get("passes")),
                                                                     len(st["slots"][k]["candidates"])) for k in live)), file=sys.stderr)
    full = sum(1 for k, s in st["slots"].items() if sum(1 for c in s["candidates"].values() if c.get("passes")) >= 3)
    print("ad3 search: %d queries done, %d slots touched, %d full" % (len(st["queries_done"]), len(st["slots"]), full))


def do_freight(a):
    src = os.path.join(REPO, "data", "leads", "profit-fix-2026-10-11", "ae-freight-requests.json")
    dst = os.path.join(REPO, "data", "leads", "profit-fix-2026-10-11", "ae-freight-results.json")
    req = json.load(open(src))
    out = load_json(dst, {"version": 1, "source": "scripts/ae/ad_round3.py freight", "items": {}})
    for it in req.get("items") or []:
        iid = str(it["item_id"])
        if iid in out["items"]:
            continue
        a.slot = it.get("slot")
        try:
            prod, _ = guard(ds.fetch_product, a, iid)
        except client.AeError as ex:
            out["items"][iid] = {"error": "%s %s" % (ex.code, ex.message), "slot": it.get("slot")}
            continue
        r = prod.get("result") or {}
        skus = ds.as_list(r.get("ae_item_sku_info_dtos"))
        key = it.get("slot")
        if it.get("sku"):
            sku = next((s for s in skus if str(s.get("sku_id")) == str(it["sku"])), None)
            how = "given"
        else:
            sku, how = pick_room_sku(skus, key) if key in SLOTS else (ds.pick_sku(skus), "sku-default")
        if not sku:
            out["items"][iid] = {"error": "no sku", "slot": key}
            continue
        fr, _ = guard(ds.fetch_freight, a, iid, str(sku["sku_id"]), "IL", 1)
        opts = [o for o in fr.get("options") or [] if o.get("fee") is not None]
        cheap = min(opts, key=lambda o: (o["fee"], o.get("days_max") or 99)) if opts else None
        u20 = [o for o in opts if (o.get("days_max") or 99) <= 20]
        fast = min(u20, key=lambda o: o["fee"]) if u20 else None
        pk = r.get("package_info_dto") or {}
        out["items"][iid] = {"slot": key, "sku": str(sku["sku_id"]), "sku_label": sku_text(sku), "sku_pick": how,
                             "price_usd": ds.num(sku.get("offer_sale_price")) or ds.num(sku.get("sku_price")),
                             "stock": sku.get("sku_available_stock"),
                             "ship_cheapest": {"usd": cheap["fee"], "days": "%s-%s" % (cheap.get("days_min"), cheap.get("days_max")), "company": cheap.get("company")} if cheap else None,
                             "ship_under20": {"usd": fast["fee"], "days": "%s-%s" % (fast.get("days_min"), fast.get("days_max")), "company": fast.get("company")} if fast else None,
                             "no_ship": None if opts else (fr.get("msg") or fr.get("code")),
                             "package_cm": [pk.get("package_length"), pk.get("package_width"), pk.get("package_height")],
                             "checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        save_json(dst, out)
    save_json(dst, out)
    print("ad3 freight: %d items -> %s" % (len(out["items"]), os.path.relpath(dst, REPO)))


def room_of(k):
    return k.split("/")[0]


def do_sheet(room):
    from PIL import Image, ImageDraw
    import urllib.request
    st = load_json(STATE, {"slots": {}})
    os.makedirs(SHEETS, exist_ok=True)
    imgdir = os.path.expanduser("~/.cache/ae-scale-img")
    os.makedirs(imgdir, exist_ok=True)
    index, n = {}, 0
    for k, s in sorted(st["slots"].items()):
        if room_of(k) != room or not s["candidates"]:
            continue
        cells = sorted([c for c in s["candidates"].values() if c.get("landed_ils") is not None],
                       key=lambda c: (not c.get("passes"), c["landed_ils"]))
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
                            data = r.read()
                        open(fp, "wb").write(data)
                        break
                    except Exception:
                        pass
            try:
                im = Image.open(fp).convert("RGB"); im.thumbnail((W - 10, H - 60)); sheet.paste(im, (x + 5, y + 5))
            except Exception:
                d.text((x + 10, y + 100), "no image", fill="red")
            n += 1
            index[str(n)] = {"slot": k.split("/")[1], "item_id": c["item_id"], "style": "nordic"}
            d.rectangle([x, y + H - 55, x + W, y + H], fill="white")
            d.text((x + 5, y + H - 52), "#%d %s %s" % (n, "PASS" if c.get("passes") else "----", c["item_id"][-6:]), fill="black")
            d.text((x + 5, y + H - 38), "%.0f ILS %s" % (c["landed_ils"], (c.get("sku_label") or "")[:26]), fill="black")
            d.text((x + 5, y + H - 24), (c.get("title") or "")[:40], fill="gray")
        sheet.save(os.path.join(SHEETS, "ad3-%s-%s.jpg" % (room, k.split("/")[1])), quality=80)
    save_json(os.path.join(SHEETS, "ad3-%s-index.json" % room), index)
    print("ad3 sheets %s: %d candidates" % (room, n))


def card_id_unique(base):
    ids = set()
    for p in glob.glob(os.path.join(REPO, "data", "products", "**", "*.json"), recursive=True):
        ids.add(os.path.splitext(os.path.basename(p))[0])
    cid, i = base, 2
    while cid in ids:
        cid = "%s-%d" % (base, i); i += 1
    return cid


def do_write(room, a, write_cards=True):
    d, slots = plan()
    st = load_json(STATE, {"slots": {}})
    rv = load_json(os.path.join(REVIEW, "ad3-%s.json" % room), {})
    os.makedirs(RES, exist_ok=True)
    out = {"room": room, "date": time.strftime("%Y-%m-%d"), "source": "AliExpress DS API, art director round 3 (scripts/ae/ad_round3.py)", "slots": {}}
    md = ["# סבב 3 של המנהל: %s (AliExpress)" % room, "",
          "עובר = נחיתה עד landed_for_40_ils (ולא מעל breakeven), מידת SKU שאומתה מול המעטפת. fit לכל ששת הסגנונות אחרי מבט בתמונה. כרטיס טיוטה רק ל-fit נורדי 8+ שעובר את התקרה.", ""]
    cards = []
    for k, s in sorted(st["slots"].items()):
        if room_of(k) != room:
            continue
        ceil = (slots.get(k) or {}).get("price_ceiling") or {}
        cands = []
        for c in s["candidates"].values():
            fits = {stl: v for stl, v in (rv.get(c["item_id"]) or {}).items() if isinstance(v, dict) and "fit" in v}
            c2 = dict(c, fit={stl: v["fit"] for stl, v in fits.items()}, reason={stl: v.get("reason") for stl, v in fits.items()},
                      reviewed=bool(fits), reject=any(v.get("verdict") == "reject" for v in fits.values()))
            cands.append(c2)
        cands.sort(key=lambda c: (not c["passes"], -(c["fit"].get("nordic") or 0), c["landed_ils"] or 1e9))
        out["slots"][k] = {"price_ceiling": ceil, "queries": s["queries"], "passed": sum(1 for c in cands if c["passes"]), "candidates": cands}
        md += ["## %s" % k.split("/")[1], "", "תקרה: נחיתה עד ₪%s (40%%), איזון ₪%s, מחיר העמדה ₪%s. שאילתות: %d." % (
            ceil.get("landed_for_40_ils"), ceil.get("breakeven_landed_ils"), ceil.get("slot_price_ils"), len(s["queries"])), "",
               "| | מוצר | SKU | $ מוצר+משלוח | נחיתה ₪ | רווח | fit (נ/מח/ג'/ים/כ/ב) |", "| --- | --- | --- | --- | --- | --- | --- |"]
        for c in cands[:12]:
            f = c["fit"]
            md.append("| %s | [%s](%s) | %s | %s+%s | %s | %s | %s |" % (
                "✓" if c["passes"] else "", (c["title"] or "")[:55].replace("|", "/"), c["url"], (c.get("sku_label") or "")[:35].replace("|", "/"),
                c["price_usd"], c["ship_usd"], c["landed_ils"], "%d%%" % round(c["margin_pct"] * 100) if c.get("margin_pct") is not None else "",
                "/".join(str(f.get(x, "–")) for x in STYLE_ORDER)))
        md.append("")
        if write_cards:
            for c in cands:
                if c["passes"] and (c["fit"].get("nordic") or 0) >= 8 and not c["reject"]:
                    existing = None
                    for p in glob.glob(os.path.join(REPO, "data", "products", "**", "*.json"), recursive=True):
                        try:
                            if (json.load(open(p)).get("supplier") or {}).get("product_url") == c["url"]:
                                existing = p; break
                        except ValueError:
                            pass
                    if existing:
                        c["card_id"] = os.path.splitext(os.path.basename(existing))[0]
                        continue
                    slot = k.split("/")[1]
                    cid = card_id_unique("%s-aliexpress-%s-%s" % (slot, ds.slugify(c["title"] or c["item_id"], words=4, maxlen=36), c["item_id"][-6:]))
                    path = scale.card_path(room, slot, cid)
                    rc = ds.main(["--by", "aliexpress-scale", "--run-id", a.run_id, "--max-calls", str(a.max_calls), "card", c["item_id"],
                                  "--slot", k, "--sku", c["sku"], "--id", cid, "--out", path])
                    if rc in (0, None):
                        cc = json.load(open(path))
                        cc["notes"] = (cc.get("notes") or "") + " Art director round 3 (2026-10-12): fit %s; landed %s ILS vs ceiling %s (40%%), margin %s at %s ILS. Reviewer: %s" % (
                            json.dumps(c["fit"]), c["landed_ils"], ceil.get("landed_for_40_ils"),
                            "%d%%" % round(c["margin_pct"] * 100) if c.get("margin_pct") is not None else "?", ceil.get("slot_price_ils"), c["reason"].get("nordic"))
                        save_json(path, cc)
                        c["card_id"] = cid
                        cards.append(cid)
    save_json(os.path.join(RES, room + ".json"), out)
    with open(os.path.join(RES, room + ".md"), "w") as f:
        f.write("\n".join(md) + "\n")
    print("ad3 write %s: %d slots, %d passing, %d new cards" % (room, len(out["slots"]), sum(v["passed"] for v in out["slots"].values()), len(cards)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["search", "freight", "sheet", "write"])
    ap.add_argument("room", nargs="?")
    ap.add_argument("--max-calls", type=int, default=6000)
    ap.add_argument("--no-cards", action="store_true")
    a0 = ap.parse_args()
    a = scale.ns("ad3", a0.max_calls)
    try:
        if a0.stage == "search":
            do_search(a)
        elif a0.stage == "freight":
            do_freight(a)
        elif a0.stage == "sheet":
            do_sheet(a0.room)
        elif a0.stage == "write":
            do_write(a0.room, a, not a0.no_cards)
    except Stop as e:
        msg = "ad3 STOP %s at %s: %s" % (a0.stage, time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()), e)
        with open(os.path.join(scale.OUT, "stop-ad3.txt"), "a") as f:
            f.write(msg + "\n")
        print(msg, file=sys.stderr)
        return 4
    return 0


if __name__ == "__main__":
    sys.exit(main())
