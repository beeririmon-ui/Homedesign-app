#!/usr/bin/env python3
"""Final round, wave 3 (art director, 2026-10-14): certification first, on AliExpress.

Owner rule S2B: a light or a toy without a declared standard is not sold; a standard declared by the seller (the
"Certification" attribute of aliexpress.ds.product.get) is enough to list it as a candidate.
  plan     the remaining slot x style gaps (coverage.json) for lighting and kids' toys -> pseudo-room "w3"
  cache    the cached items whose Certification declares CE / EN71 (ae-certified-cache-2026-10-14.json) matched to those
           slots by product type; room SKU, freight to IL (cache first)
  search   new searches with the standard in the words ("CE wall lamp E27 220V", "EN71 wooden toy car"), 1-2 per slot;
           the best 8 per slot by quality get product.get and are kept only if the Certification attribute declares it
  sheet / (visual review fin-rev-w3*.json) / write   as final_ae.py, with standard_declared on the card (safety.certificates)
Output: data/leads/final-2026-10-13/results/wave3-aliexpress.json + .md
"""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import final_ae as F  # noqa: E402
import scale, ds  # noqa: E402
from scale import client, cache, registry, guard, Stop, fnum, pick_room_sku, sku_text, best_freight  # noqa: E402
from scale_config import SLOTS  # noqa: E402

ROOM = "w3"
CERTS = os.path.join(F.PACKS, "ae-certified-cache-2026-10-14.json")
CERT_RX = re.compile(r"\b(CE|EN\s?71|ASTM|UKCA|LVD|EMC)\b", re.I)
QUERIES = {"lighting": ["CE %s E27 220V", "CE certified %s"], "toys": ["EN71 %s", "CE %s toy"]}


def is_toy_key(key, g0):
    return key.startswith("kids/") and g0.get("category") == "art-decor-toys" and not re.search(r"print|art|blind", key)


def plan():
    cov = json.load(open(os.path.join(F.PACKS, "coverage.json")))["remaining"]
    G = F.gaps()
    keys = {}
    for st, lst in cov.items():
        for e in lst:
            key = e["slot"]
            if key not in G or key not in SLOTS:
                continue
            g0 = next(iter(G[key].values()))
            if e.get("category") == "lighting" or g0.get("electrical") or is_toy_key(key, g0):
                keys.setdefault(key, set()).add(st)
    out = {}
    for key, sts in sorted(keys.items()):
        gs = {s: G[key][s] for s in G[key]}
        g0 = next(iter(gs.values()))
        noun = F.NOUN.get(key) or " ".join(SLOTS[key]["q"].split()[-2:])
        kind = "toys" if is_toy_key(key, g0) else "lighting"
        out[key] = {"styles": sorted(sts, key=F.STYLES.index), "kind": kind,
                    "slot_price": {s: F.slot_price(gs[s], key) for s in gs}, "qty": F.qty_of(key, gs),
                    "envelope_cm": g0.get("envelope_cm"), "queries": [q % noun for q in QUERIES[kind]],
                    "existing": sorted({p.get("card_id") for g in gs.values() for p in g.get("existing_picks") or [] if p.get("card_id")})}
    os.makedirs(F.WORK, exist_ok=True)
    json.dump(out, open(os.path.join(F.WORK, "plan-%s.json" % ROOM), "w"), ensure_ascii=False, indent=1)
    print("w3 plan: %d slots (%d lighting, %d toys)" % (len(out), sum(1 for v in out.values() if v["kind"] == "lighting"),
                                                        sum(1 for v in out.values() if v["kind"] == "toys")))


def cert_of(res):
    pr = res.get("ae_item_properties")
    props = ds.as_list(pr.get("ae_item_property") if isinstance(pr, dict) else pr)
    cert, ip = None, None
    for p in props:
        if not isinstance(p, dict):
            continue
        n, v = str(p.get("attr_name") or ""), str(p.get("attr_value") or "")
        if n.lower().startswith("certification") and CERT_RX.search(v):
            cert = ", ".join(sorted({m.group(1).upper().replace(" ", "") for m in CERT_RX.finditer(v)}))
        if re.search(r"\bIP\s?([4-6]\d)\b", v, re.I) and re.search(r"ip|waterproof|protection", n, re.I):
            ip = "IP" + re.search(r"\bIP\s?([4-6]\d)\b", v, re.I).group(1)
    return cert, ip


def detail_one(a, key, iid, det, source, quality=0, need_cert=True):
    k = "%s|%s" % (key, iid)
    if k in det and det[k].get("product_ok") is not None and "ship_usd" in det[k]:
        return det[k]
    a.slot = key
    hit = cache.get(ds.SRC, iid, "product", allow_stale=True)
    try:
        prod = hit["payload"] if hit else guard(ds.fetch_product, a, iid)[0]
    except client.AeError as e:
        det[k] = {"key": key, "item_id": iid, "product_ok": False, "error": "%s %s" % (e.code, e.message)}
        return det[k]
    res = prod.get("result") or {}
    cert, ip = cert_of(res)
    base = res.get("ae_item_base_info_dto") or {}
    imgs = [u for u in str((res.get("ae_multimedia_info_dto") or {}).get("image_urls") or "").split(";") if u]
    rec = {"key": key, "item_id": iid, "source": source, "quality": quality, "title": base.get("subject"), "image": imgs[0] if imgs else None,
           "cert": cert, "ip": ip, "product_ok": True}
    if need_cert and not cert:
        rec.update(product_ok=False, error="no declared standard")
        det[k] = rec
        return rec
    skus = ds.as_list(res.get("ae_item_sku_info_dtos"))
    sku, how = pick_room_sku(skus, key)
    rec.update(n_skus=len(skus), sku=str(sku.get("sku_id")) if sku else None, sku_label=sku_text(sku) if sku else None, sku_pick=how,
               sku_labels=[sku_text(s) for s in skus][:30],
               price_usd=(ds.num(sku.get("offer_sale_price")) or ds.num(sku.get("sku_price"))) if sku else None)
    if rec["sku"]:
        fh = cache.get(ds.SRC, iid, "freight:%s:IL:1" % rec["sku"], kind="freight", allow_stale=True)
        if fh:
            fr = fh["payload"]
        else:
            try:
                fr, _ = guard(ds.fetch_freight, a, iid, rec["sku"], "IL", 1)
            except client.AeError as e:
                fr = {"options": [], "msg": "%s %s" % (e.code, e.message)}
        b = best_freight(fr.get("options"))
        rec.update(ship_usd=b["fee"] if b else None, ship_days="%s-%s" % (b.get("days_min"), b.get("days_max")) if b else None,
                   ship_ok=bool(b))
    det[k] = rec
    return rec


def do_cache(a):
    P = F.load_plan(ROOM)
    items = json.load(open(CERTS))
    items = items.get("items") if isinstance(items, dict) else items
    path = F.det_path(ROOM)
    det = json.load(open(path)) if os.path.exists(path) else {}
    n = 0
    try:
        for it in items:
            for key, p in P.items():
                if (it.get("kind") == "toy") != (p["kind"] == "toys"):
                    continue
                if not F.type_ok(it.get("title"), key):
                    continue
                detail_one(a, key, str(it["item_id"]), det, "certified cache")
                n += 1
                if n % 20 == 0:
                    json.dump(det, open(path, "w"), ensure_ascii=False, indent=0)
    finally:
        json.dump(det, open(path, "w"), ensure_ascii=False, indent=0)
    print("w3 cache: %d slot matches, %d with a standard and freight" % (n, sum(1 for r in det.values() if r.get("cert") and r.get("ship_ok"))))


def do_search(a):
    P = F.load_plan(ROOM)
    path = F.det_path(ROOM)
    det = json.load(open(path)) if os.path.exists(path) else {}
    reg = registry.load()
    try:
        for key, p in P.items():
            used = F.used_queries(key, F.gaps()[key], key.split("/")[0])
            rows = {}
            for q in p["queries"]:
                if F.norm(q) in used:
                    continue
                a.slot = key
                try:
                    res = guard(scale.search, a, q, 1)
                except client.AeError as e:
                    print("[w3] skip %r: %s" % (q, e), file=sys.stderr)
                    continue
                for z in res.get("products") or []:
                    r = {"item_id": str(z.get("itemId")), "title": z.get("title"), "price_usd": fnum(z.get("targetSalePrice")),
                         "orders": int(fnum(z.get("orders")) or 0), "rating": fnum(z.get("evaluateRate"))}
                    if registry.check(ds.key_of(r["item_id"]), reg)["action"] == "skip":
                        continue
                    qq = F.quality(r, key, max([v for v in p["slot_price"].values() if v] or [0]))
                    if qq is not None:
                        rows[r["item_id"]] = max(qq, rows.get(r["item_id"], 0))
            for iid, qq in sorted(rows.items(), key=lambda x: -x[1])[:8]:
                detail_one(a, key, iid, det, "search", qq)
            json.dump(det, open(path, "w"), ensure_ascii=False, indent=0)
            print("[w3] %s searched" % key, file=sys.stderr)
    finally:
        json.dump(det, open(path, "w"), ensure_ascii=False, indent=0)
    print("w3 search: %d records with a standard and freight" % sum(1 for r in det.values() if r.get("cert") and r.get("ship_ok")))


GROUPS = [("picture", r"picture light|painting light|art light|mirror light|mirror front"), ("floor", r"floor lamp|standing lamp"),
          ("table", r"table lamp|desk lamp|bedside lamp|night light|reading lamp"),
          ("sconce", r"wall lamp|wall light|sconce|wall mounted"), ("ceiling", r"ceiling|flush mount|semi flush"),
          ("pendant", r"pendant|chandelier|hanging lamp|hanging light|suspension")]
GROUP_SLOTS = {"picture": r"picture-lights", "floor": r"floor-lamp", "table": r"table-lamp|desk-lamp",
               "sconce": r"sconce", "ceiling": r"ceiling-light", "pendant": r"pendant"}


def group_of(rec):
    slot = rec["key"].split("/")[1]
    if slot in ("toy-cars", "doll", "soft-toy", "doll-pram"):
        return "toy-" + slot
    t = (rec.get("title") or "").lower()
    return next((n for n, rx in GROUPS if re.search(rx, t)), None)


def group_keys(g, P):
    if g.startswith("toy-"):
        return ["kids/" + g[4:]] if "kids/" + g[4:] in P else []
    return [k for k in P if re.search(GROUP_SLOTS[g], k.split("/")[1])]


def do_gsheet():
    """One sheet per product group (wall sconces, pendants...): a light is reviewed once and matched to every slot it fits."""
    from PIL import Image, ImageDraw
    import urllib.request
    P = F.load_plan(ROOM)
    G = F.gaps()
    det = json.load(open(F.det_path(ROOM)))
    by_group = {}
    for r in det.values():
        if not (r.get("cert") and r.get("ship_ok") and r.get("price_usd") is not None):
            continue
        g = group_of(r)
        if g and group_keys(g, P):
            by_group.setdefault(g, {}).setdefault(r["item_id"], r)
    index, brief, n = {}, {}, 0
    imgdir = os.path.expanduser("~/.cache/ae-scale-img")
    for g, recs in sorted(by_group.items()):
        cells = sorted(recs.values(), key=lambda r: -(r.get("quality") or 0))
        brief[g] = {k: {"styles_needing": P[k]["styles"], "envelope_cm": P[k]["envelope_cm"], "qty": P[k]["qty"],
                        "name_he": next(iter(G[k].values())).get("name_he"),
                        "designer_spec_he": {s: (G[k][s].get("designer_spec_he") or "")[:350] for s in P[k]["styles"] if G[k].get(s, {}).get("designer_spec_he")}}
                    for k in group_keys(g, P)}
        W, H, cols = 260, 300, 6
        sheet = Image.new("RGB", (W * cols, H * ((len(cells) + cols - 1) // cols)), "white")
        d = ImageDraw.Draw(sheet)
        for i, c in enumerate(cells):
            x, y = (i % cols) * W, (i // cols) * H
            fp = os.path.join(imgdir, c["item_id"] + ".jpg")
            if not os.path.exists(fp) and c.get("image"):
                for url in (c["image"] + "_220x220.jpg", c["image"]):
                    try:
                        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=20) as rr:
                            open(fp, "wb").write(rr.read())
                        break
                    except Exception:
                        pass
            try:
                im = Image.open(fp).convert("RGB"); im.thumbnail((W - 10, H - 60)); sheet.paste(im, (x + 5, y + 5))
            except Exception:
                d.text((x + 10, y + 100), "no image", fill="red")
            n += 1
            index[str(n)] = {"group": g, "item_id": c["item_id"], "key": c["key"]}
            landed = round((c["price_usd"] + (c.get("ship_usd") or 0)) * scale.FX)
            d.rectangle([x, y + H - 55, x + W, y + H], fill="white")
            d.text((x + 5, y + H - 52), "#%d %s %s" % (n, c.get("cert") or "", c["item_id"][-6:]), fill="black")
            d.text((x + 5, y + H - 38), "%d ILS %s" % (landed, (c.get("sku_label") or "")[:26]), fill="black")
            d.text((x + 5, y + H - 24), (c.get("title") or "")[:40], fill="gray")
        sheet.save(os.path.join(F.WORK, "w3-%s.jpg" % g), quality=80)
    json.dump(index, open(os.path.join(F.WORK, "w3g-index.json"), "w"), indent=0)
    json.dump(brief, open(os.path.join(F.WORK, "w3g-brief.json"), "w"), ensure_ascii=False, indent=1)
    print("w3 group sheets: %d items in %s" % (n, {g: len(v) for g, v in by_group.items()}))


def do_expand():
    """Group review (w3g-rev-*.json, with slots_ok) -> the per-slot index and review that final_ae.do_write reads."""
    import glob
    P = F.load_plan(ROOM)
    gidx = json.load(open(os.path.join(F.WORK, "w3g-index.json")))
    rev = {}
    for rp in sorted(glob.glob(os.path.join(F.WORK, "w3g-rev-*.json"))):
        rev.update(json.load(open(rp)))
    det = json.load(open(F.det_path(ROOM)))
    by_item = {}
    for r in det.values():
        by_item.setdefault(r["item_id"], r)
    idx, frev, n = {}, {}, 0
    for num, e in gidx.items():
        v = rev.get(num)
        if not v:
            continue
        keys = [k for k in (v.get("slots_ok") or []) if k in group_keys(e["group"], P)] or ([e["key"]] if not v.get("type_ok", True) else [])
        for k in keys:
            n += 1
            idx[str(n)] = {"key": k, "item_id": e["item_id"], "source": det.get("%s|%s" % (e["key"], e["item_id"]), {}).get("source", "search")}
            frev[str(n)] = dict(v, fits_envelope=v.get("fits_envelope") if k == e["key"] and v.get("fits_envelope") else "yes" if k in (v.get("slots_ok") or []) else "no")
            kk = "%s|%s" % (k, e["item_id"])
            if kk not in det:
                det[kk] = dict(by_item[e["item_id"]], key=k)
    json.dump(idx, open(os.path.join(F.WORK, "fin-%s-index.json" % ROOM), "w"), indent=0)
    json.dump(frev, open(os.path.join(F.WORK, "fin-rev-%s.json" % ROOM), "w"), ensure_ascii=False, indent=0)
    json.dump(det, open(F.det_path(ROOM), "w"), ensure_ascii=False, indent=0)
    print("w3 expand: %d slot candidates from %d reviewed items" % (n, len(rev)))


BAD_SKU = re.compile(r"cold|6000|6500|daylight|white light|neutral|4000|4500|tri[- ]?colou?r|three colou?r|dimmable 3|\b(us|au|uk)\b ?plug|plug type (us|au|uk)", re.I)


def sku_score(label):
    t = label or ""
    s = 0
    s += 3 if re.search(r"warm|3000|2700", t, re.I) else 0
    s -= 5 if re.search(r"cold|6000|6500|daylight|white light", t, re.I) else 0
    s -= 2 if re.search(r"neutral|4000|4500|tri[- ]?colou?r|three colou?r", t, re.I) else 0
    s -= 5 if re.search(r"\b(us|au|uk)\b ?plug|plug type ?:? ?(us|au|uk)\b", t, re.I) else 0
    s += 1 if re.search(r"\beu\b", t, re.I) else 0
    return s


def do_fixsku(a):
    """Lights: the chosen SKU is often cold/neutral light or a US/AU/UK plug; take the warm-light EU SKU of the same listing."""
    path = F.det_path(ROOM)
    det = json.load(open(path))
    n = 0
    for k, r in det.items():
        if not (r.get("cert") and r.get("sku") and not k.split("|")[0].split("/")[1] in ("toy-cars", "doll", "soft-toy", "doll-pram")):
            continue
        if not BAD_SKU.search(r.get("sku_label") or ""):
            continue
        hit = cache.get(ds.SRC, r["item_id"], "product", allow_stale=True)
        if not hit:
            continue
        skus = ds.as_list((hit["payload"].get("result") or {}).get("ae_item_sku_info_dtos"))
        cur = sku_score(r.get("sku_label"))
        light_rx = r"warm|cold|neutral|light|white|daylight|tri|colou?r(ed)?|temperature|emitting|\d{4} ?k|plug|type|us|eu|uk|au|remote|dimming|dimmable"

        def keep(x):  # the same size / body colour as the chosen SKU: only the light colour or the plug changes
            a_ = {w for w in re.findall(r"[a-z0-9]+", (r.get("sku_label") or "").lower()) if not re.fullmatch(light_rx, w)}
            b_ = {w for w in re.findall(r"[a-z0-9]+", sku_text(x).lower()) if not re.fullmatch(light_rx, w)}
            return len(a_ & b_) - len(a_ ^ b_)
        best = max(skus, key=lambda x: (keep(x), sku_score(sku_text(x)), -(ds.num(x.get("offer_sale_price")) or 999)), default=None)
        if best is not None and keep(best) < max(keep(x) for x in skus):
            best = None
        if not best or sku_score(sku_text(best)) <= cur:
            continue
        r.update(sku=str(best.get("sku_id")), sku_label=sku_text(best), sku_pick="warm-eu",
                 price_usd=ds.num(best.get("offer_sale_price")) or ds.num(best.get("sku_price")))
        a.slot = r["key"]
        try:
            fr, _ = guard(ds.fetch_freight, a, r["item_id"], r["sku"], "IL", 1)
        except client.AeError as e:
            fr = {"options": [], "msg": "%s %s" % (e.code, e.message)}
        b = best_freight(fr.get("options"))
        r.update(ship_usd=b["fee"] if b else None, ship_days="%s-%s" % (b.get("days_min"), b.get("days_max")) if b else None, ship_ok=bool(b))
        n += 1
    json.dump(det, open(path, "w"), ensure_ascii=False, indent=0)
    print("w3 fixsku: %d light SKUs switched to warm light / EU plug" % n)


def main():
    stage = sys.argv[1]
    a = scale.ns(ROOM, 3000)
    a.run_id, a.by = "final-wave3-2026-10-14", F.BY
    F.TAG = "final-round wave-3 2026-10-14"
    F.RESNAME = "wave3-aliexpress"
    try:
        if stage == "plan":
            plan()
        elif stage == "cache":
            do_cache(a)
        elif stage == "search":
            do_search(a)
        elif stage == "sheet":
            # only records with a declared standard reach the sheet
            path = F.det_path(ROOM)
            det = json.load(open(path))
            for r in det.values():
                if not r.get("cert"):
                    r["ship_ok"] = False
            json.dump(det, open(path, "w"), ensure_ascii=False, indent=0)
            F.do_sheet(ROOM)
        elif stage == "gsheet":
            do_gsheet()
        elif stage == "fixsku":
            do_fixsku(a)
        elif stage == "expand":
            do_expand()
        elif stage == "write":
            F.do_write(ROOM, a)
    except Stop as e:
        print("w3 STOP %s: %s" % (stage, e), file=sys.stderr)
        return 4
    return 0


if __name__ == "__main__":
    sys.exit(main())
