"""Stage 3 prep (offline): room SKU, economics, shortlist per slot x style. No network.

python3 -I prep.py <room>  -> scratch/work/prep-<room>.json
"""
import importlib.util, json, math, os, re, sys

REPO = "/home/user/homedesign-app"
WORK = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(REPO, "scripts", "ae"))
sys.path.insert(0, os.path.join(REPO, "scripts", "sourcing"))
import ds, cache  # noqa
import scale  # noqa  (economics twin of econCalc, bands, existing cards)
from scale_config import SLOTS, STYLES, GLOBAL_BAD  # noqa

spec = importlib.util.spec_from_file_location("studio_build", os.path.join(REPO, "studio", "build.py"))
B = importlib.util.module_from_spec(spec)
spec.loader.exec_module(B)

FX, VAT, FEE, FEE_FIX, RET, CAC, IPO = 3.3, 0.18, 0.02, 1.2, 0.08, 100.0, 1.4
PARCEL_FIXED_USD = 3.72
STYLE_ORDER = scale.STYLE_ORDER


def p9(x):
    return max(9, math.floor((x + 1) / 10) * 10 - 1)


def ship_for_qty(unit, q):
    return unit + (q - 1) * max(0.0, unit - PARCEL_FIXED_USD)


def econ(cost_usd, qty, ship_total_usd, retail):
    """econCalc (studio/src/index.html) with the studio defaults (FR-C), packaging 0."""
    landed = (cost_usd * qty + ship_total_usd) * FX
    net = retail / (1 + VAT)
    contribution = net - landed - (retail * FEE + FEE_FIX) - net * RET
    return round(landed, 1), round(contribution, 1), round(contribution / net, 3), round(contribution - CAC / IPO, 1)


def band_at(band, qty):
    return p9(band[1] * qty) if qty > 1 else band[1]


# ----------------------------------------------------------------------------- sizes
NUM = r"(\d+(?:\.\d+)?)"
UNIT = r"\s*(cm|mm|m|inch|in|\")?"
PAIR = re.compile(r"(?:\b([WHLD])\s*[:=]?\s*)?" + NUM + UNIT + r"\s*(?:[x×*X]|by)\s*(?:([WHLD])\s*[:=]?\s*)?" + NUM + UNIT, re.I)
TRIPLE = re.compile(NUM + UNIT + r"\s*[x×*X]\s*" + NUM + UNIT + r"\s*[x×*X]\s*" + NUM + UNIT, re.I)
SINGLE = re.compile(r"(?:(diameter|dia\.?|height|width|length|depth|h|w|d|l)\s*[:=]?\s*)?" + NUM + r"\s*(cm|mm|m)\b", re.I)
WM = re.compile(r"width\s*" + NUM + r"\s*m\b.*?height\s*" + NUM + r"\s*m\b", re.I)


def to_cm(v, u):
    v = float(v)
    u = (u or "").lower()
    if u == "mm":
        return v / 10
    if u == "m":
        return v * 100
    if u in ("inch", "in", '"'):
        return v * 2.54
    return v


def dims_of(label):
    """-> (pairs [(w, h, wtag, htag)], singles [(tag, cm)]) from a SKU label, in cm. Kelvin/ml/W values ignored."""
    lab = re.sub(r"\b\d{3,4}\s*k\b", " ", label or "", flags=re.I)
    lab = re.sub(r"size\s*\(inch\)", "size", lab, flags=re.I)  # AliExpress header; the values are cm
    pairs, singles = [], []
    m = WM.search(lab)
    if m:
        pairs.append((float(m.group(1)) * 100, float(m.group(2)) * 100, "w", "h"))
    t = TRIPLE.search(lab)
    if t:
        u = t.group(6) or t.group(4) or t.group(2)
        vals = [to_cm(t.group(i), u) for i in (1, 3, 5)]
        pairs.append((vals[0], vals[1], None, None))
        singles.append(("h", vals[2]))
    for m in PAIR.finditer(lab):
        if t and m.start() >= t.start() and m.end() <= t.end():
            continue
        u2 = m.group(6)
        u1 = m.group(3) or u2
        a, b = to_cm(m.group(2), u1), to_cm(m.group(5), u2)
        pairs.append((a, b, (m.group(1) or "").lower() or None, (m.group(4) or "").lower() or None))
    rest = PAIR.sub(" ", lab)
    for m in SINGLE.finditer(rest):
        singles.append(((m.group(1) or "").lower()[:1] or None, to_cm(m.group(2), m.group(3))))
    return pairs, singles


def wh(p):
    """(width, height) of a pair, honouring W/H/L tags (L = drop for textiles)."""
    a, b, ta, tb = p
    if ta in ("h", "l") and tb == "w":
        return b, a
    return a, b


def short_long(p):
    return min(p[0], p[1]), max(p[0], p[1])


def inr(x, lo, hi):
    return lo <= x <= hi


def pair_rule(fit, near=None):
    """fit/near: (short_lo, short_hi, long_lo, long_hi) on sorted sides."""
    def f(pairs, singles, lab):
        if not pairs:
            return None
        res = "no"
        for p in pairs:
            s, l = short_long(p)
            if inr(s, *fit[:2]) and inr(l, *fit[2:]):
                return "fit"
            if near and inr(s, *near[:2]) and inr(l, *near[2:]):
                res = "near"
        return res
    return f


def curtain_rule(pairs, singles, lab):
    if not pairs:
        hs = [v for t, v in singles if t in ("h", "l")]
        if hs:
            return "fit" if any(inr(h, 270, 290) for h in hs) else ("near" if any(inr(h, 265, 300) for h in hs) else "no")
        return None
    res = "no"
    for p in pairs:
        w, h = wh(p)
        if inr(w, 125, 160) and inr(h, 270, 290):
            return "fit"
        if inr(w, 100, 220) and inr(h, 265, 300):
            res = "near"
    return res


def single_rule(lo, hi, nlo, nhi, use_pairs=True):
    def f(pairs, singles, lab):
        vals = [v for _, v in singles]
        if use_pairs:
            for p in pairs:
                vals += [p[0], p[1]]
        if not vals:
            return None
        if any(inr(v, lo, hi) for v in vals):
            return "fit"
        if any(inr(v, nlo, nhi) for v in vals):
            return "near"
        return "no"
    return f


def box_rule(lo, hi, nlo, nhi):
    """3D items (baskets, poufs): the two largest dimensions of the SKU (or its single values) inside the range."""
    def f(pairs, singles, lab):
        vals = sorted([v for _, v in singles] + [x for p in pairs for x in p[:2]], reverse=True)
        if not vals:
            return None
        top = vals[:2] if len(vals) >= 2 else vals
        if all(inr(v, lo, hi) for v in top):
            return "fit"
        if all(inr(v, nlo, nhi) for v in top):
            return "near"
        return "no"
    return f


def words_rule(fit_rx, no_rx):
    def f(pairs, singles, lab):
        if re.search(fit_rx, lab, re.I):
            return "fit"
        if re.search(no_rx, lab, re.I):
            return "no"
        return None
    return f


def framed(rule, triptych=False):
    """framed art: 'Unframed / No Frame' SKUs never fit (the Bible needs a frame)."""
    def f(pairs, singles, lab):
        if re.search(r"un-?framed|no\s*frame|frameless|without\s*frame|canvas\s*only|only\s*canvas|not\s*framed", lab, re.I):
            return "no"
        return rule(pairs, singles, lab)
    return f


def living_art(pairs, singles, lab):
    """total 145-165 x 70-100: one 100x150, a pair 70x100, or a triptych 50x70."""
    res = None
    for p in pairs:
        s, l = short_long(p)
        if inr(s, 95, 105) and inr(l, 140, 155):
            return "fit"
        if inr(s, 65, 75) and inr(l, 95, 105):
            return "fit"  # a pair
        if inr(s, 48, 55) and inr(l, 68, 75):
            return "fit"  # a triptych
        if inr(s, 55, 80) and inr(l, 80, 120):
            res = "near"
        elif res is None:
            res = "no"
    return res


RULES = {
    "living-room/curtains": curtain_rule,
    "living-room/rug": pair_rule((195, 245, 285, 345), (175, 250, 245, 350)),
    "living-room/framed-art": framed(living_art),
    "living-room/wall-decor": single_rule(33, 47, 28, 55),
    "living-room/accent-sconces": single_rule(10, 20, 8, 25),
    "living-room/vase": single_rule(25, 35, 22, 40),
    "living-room/floor-lamp": single_rule(145, 165, 135, 175),
    "living-room/planter": single_rule(30, 45, 26, 50),
    "living-room/sofa-cover": words_rule(r"3\s*-?\s*seat|three\s*seat|190\s*-\s*2[3-4]0|large\b|\bL\b", r"\b[1-2]\s*-?\s*seat|single\s*seat|4\s*-?\s*seat|chair|armchair|l-?shape"),
    "living-room/cushions": pair_rule((43, 52, 43, 52), (28, 60, 40, 65)),
    "living-room/basket": box_rule(33, 45, 28, 50),
    "living-room/table-runner": pair_rule((28, 40, 95, 130), (28, 42, 130, 140)),
    "living-room/bowl": single_rule(16, 24, 14, 27),
    "living-room/candle-holders": single_rule(1, 12, 1, 15),
    "living-room/pouf": single_rule(40, 55, 33, 60),
    "living-room/pendant": single_rule(40, 50, 35, 55),
    "dining-room/dining-pendant": single_rule(45, 55, 40, 60),
    "dining-room/table-runner": pair_rule((30, 40, 130, 150), (28, 42, 120, 160)),
    "dining-room/centerpiece-vase": single_rule(20, 28, 18, 30),
    "dining-room/candle-holders": single_rule(1, 12, 1, 15),
    "dining-room/curtains": curtain_rule,
    "dining-room/floor-vase": single_rule(50, 65, 45, 70),
    "dining-room/bench-pad": pair_rule((28, 40, 130, 145), (28, 45, 115, 150)),
    "dining-room/dining-rug": pair_rule((195, 245, 195, 245), (180, 250, 195, 300)),
    "dining-room/framed-art": framed(pair_rule((28, 36, 38, 46), (25, 42, 35, 52))),
    "dining-room/open-shelf-ceramics": single_rule(18, 26, 10, 28),
    "dining-room/utensil-crock": single_rule(16, 20, 14, 22),
    "dining-room/cutting-boards": pair_rule((18, 28, 34, 50), (15, 32, 30, 55)),
    "dining-room/condiment-set": single_rule(15, 20, 12, 24),
    "dining-room/bowl": single_rule(20, 26, 18, 28),
    "dining-room/paper-towel-holder": single_rule(30, 34, 27, 37),
    "dining-room/herb-pots": single_rule(10, 12, 9, 14),
    "dining-room/kitchen-runner": pair_rule((44, 62, 235, 285), (40, 70, 180, 300)),
    "dining-room/step-stool": single_rule(40, 48, 35, 52),
    "master/curtains": curtain_rule,
    "master/framed-art": framed(pair_rule((50, 70, 100, 125), (45, 75, 90, 130))),
    "master/bedside-sconces": single_rule(12, 22, 10, 26),
    "master/sill-vase": single_rule(22, 30, 20, 33),
    "master/planter": single_rule(36, 45, 30, 50),
    "master/floor-lamp": single_rule(148, 165, 135, 175),
    "master/nightstand-tray": pair_rule((18, 30, 26, 36), (15, 32, 22, 40)),
    "master/nightstand-vase": single_rule(22, 28, 20, 30),
    "master/trinket-dish": single_rule(8, 13, 6, 15),
    "master/pillowcases": pair_rule((45, 52, 63, 76), (40, 55, 60, 80)),
    "master/bedding": pair_rule((195, 230, 200, 260), (180, 240, 200, 270)),
    "master/cushions": pair_rule((30, 42, 50, 66), (28, 50, 45, 70)),
    "master/throw": pair_rule((120, 160, 170, 210), (100, 180, 150, 230)),
    "master/rug": pair_rule((195, 225, 275, 305), (180, 240, 250, 320)),
    "master/basket": box_rule(30, 40, 26, 45),
    "master/pendant": single_rule(40, 50, 35, 55),
}
PLUG_IN = {"living-room/floor-lamp", "living-room/wall-sconce", "master/floor-lamp", "dining-room/kitchen-sconce"}
LAMPS = PLUG_IN | {"living-room/accent-sconces", "living-room/pendant", "dining-room/dining-pendant", "master/bedside-sconces", "master/pendant"}

# room quantity of listing units (a pair of identical pieces) and whether the market band is for the whole pair
SETQ = {"living-room/curtains": (2, "pair"), "living-room/accent-sconces": (2, "unit"), "living-room/candle-holders": (2, "unit"),
        "dining-room/candle-holders": (2, "unit"), "dining-room/cutting-boards": (2, "unit"), "dining-room/mug-set": (3, "unit"),
        "dining-room/herb-pots": (2, "unit"), "dining-room/canisters": (3, "unit"),
        "master/curtains": (2, "pair"), "master/bedside-sconces": (2, "unit"), "master/candle-holders": (2, "unit"),
        "master/pillowcases": (2, "pair"), "dining-room/curtains": (1, "pair")}
PCS = [(re.compile(r"\b(?:set\s*of\s*|)(\d)\s*(?:pcs|pc|pieces|piece|panels?|pack|pairs?|sets?)\b(?!\s*(?:/|per)\s*(?:color|colour))", re.I), None),
       (re.compile(r"\bpair\b|\b2\s*x\b|\btwo\b|\bdouble\b|\bset\s*of\s*2\b", re.I), 2),
       (re.compile(r"\bset\s*of\s*3\b|\bthree\b|\b3\s*x\b", re.I), 3)]


def pieces(text):
    for rx, n in PCS:
        m = rx.search(text or "")
        if m:
            k = n if n else int(m.group(1))
            if "pair" in m.group(0).lower() and not n:
                k *= 2
            return max(1, k)
    return None


def sku_rows(product):
    r = (product or {}).get("result") or {}
    rows = []
    for s in ds.as_list(r.get("ae_item_sku_info_dtos")):
        lab = scale.sku_text(s)
        rows.append({"id": str(s.get("sku_id")), "label": lab, "price": ds.num(s.get("offer_sale_price")) or ds.num(s.get("sku_price")),
                     "stock": ds.num(s.get("sku_available_stock")) or 0})
    return rows


FRAMED = re.compile(r"framed|with\s*frame|\bframe\b", re.I)
UNFRAMED = re.compile(r"un-?framed|no\s*frame|frameless|without\s*frame|not\s*framed", re.I)
BAD_PLUG = re.compile(r"\b(us|uk|au|jp|br|cn)\s*-?\s*plug|110\s*v|\b(us|uk|au)\b\s*(?:standard|version)", re.I)
EU_PLUG = re.compile(r"\beu\b|europe|220\s*v|230\s*v|240\s*v|\bil\b|israel", re.I)
COLD = re.compile(r"cold|cool\s*white|6000|6500|white\s*light\b", re.I)
WARM = re.compile(r"warm|2700|3000", re.I)
NOBULB = re.compile(r"no\s*bulb|without\s*(?:light\s*)?(?:bulb|source)|bulb\s*not\s*included|excluding", re.I)
REMOTE = re.compile(r"remote|dimm|rgb|app\b|tuya|smart|three\s*colou?r|tricolor|3\s*colou?r", re.I)


def pick_room(rows, key, title, detail_sku):
    """The SKU shown in the room: in stock, not a bogus 'contact us' row, the size that fits the envelope (cheapest
    among them); lamps: an EU / 220-240V SKU, warm light. -> (row, size_status, how)."""
    rule = RULES.get(key)
    ok = [r for r in rows if r["stock"] > 0 and r["price"] and not ds.sku_options.BOGUS.search(r["label"] or "")]
    if not ok:
        ok = [r for r in rows if r["price"]]
    if key in LAMPS:
        noplug = [r for r in ok if not BAD_PLUG.search(r["label"] or "")]
        ok = noplug or ok
        if key in PLUG_IN:
            eu = [r for r in ok if EU_PLUG.search(r["label"] or "")]
            ok = eu or ok
        warm = [r for r in ok if not COLD.search(r["label"] or "") and not REMOTE.search(r["label"] or "")]
        ok = warm or ok
    if not ok:
        return None, None, "no-sku"
    status = {}
    if rule:
        for r in ok:
            p, s = dims_of(r["label"])
            status[r["id"]] = rule(p, s, r["label"] or "")
        fits = [r for r in ok if status[r["id"]] == "fit"]
        if fits:
            return min(fits, key=lambda r: r["price"]), "fit", "size-fit"
        nears = [r for r in ok if status[r["id"]] == "near"]
        if nears:
            return min(nears, key=lambda r: r["price"]), "near", "size-near"
        if any(v == "no" for v in status.values()):
            # every SKU with a size is outside the envelope; try the title (one-size listings)
            p, s = dims_of(title)
            t = rule(p, s, title or "") if (p or s) else None
            if all(v == "no" for v in status.values()):
                d = next((r for r in ok if r["id"] == detail_sku), None) or min(ok, key=lambda r: r["price"])
                return d, "no", "no-size-fits"
        # sizes unknown in the SKUs: the title decides
        p, s = dims_of(title)
        t = rule(p, s, title or "") if (p or s) else None
        d = next((r for r in ok if r["id"] == detail_sku), None) or min(ok, key=lambda r: r["price"])
        return d, t or "unknown", "title-" + (t or "unknown")
    d = next((r for r in ok if r["id"] == detail_sku), None) or min(ok, key=lambda r: r["price"])
    return d, "n/a", "no-size-rule"


def bad_words(title, key, style):
    cfg, st = SLOTS[key], STYLES[style]
    t = (title or "").lower()
    bad = re.findall(GLOBAL_BAD, t, re.I) + re.findall(st["bad"], t, re.I) + (re.findall(cfg["bad"], t, re.I) if cfg.get("bad") else [])
    extra = re.findall(r"\b(glossy|mirror|led strip|neon|cartoon|plastic|pvc|acrylic|artificial|fake flowers?|metallic gold|rhinestone|crystal|velvet)\b", t, re.I)
    if style in ("boho", "mediterranean") and "velvet" in [x.lower() for x in extra]:
        extra = [x for x in extra if x.lower() != "velvet"]
    return sorted(set(b if isinstance(b, str) else b[0] for b in bad + extra if (b if isinstance(b, str) else b[0])))


def run(room):
    det = json.load(open(os.path.join(REPO, "data/leads/aliexpress/scale-2026-10/detail/%s.json" % room)))
    out = []
    for k, rec in det.items():
        key = "%s/%s" % (room, rec["slot"])
        cfg = SLOTS[key]
        band0, band_src = scale.band_of(cfg)
        r = {"key": k, "room": room, "slot": rec["slot"], "item_id": rec["item_id"], "title": rec.get("title"), "image": rec.get("image"),
             "styles": rec.get("styles") or [], "screen": rec.get("screen") or {}, "orders": rec.get("orders"), "rating": rec.get("rating"),
             "ae_rating": rec.get("ae_rating"), "reviews": rec.get("reviews"), "sales": rec.get("sales"), "materials": rec.get("materials") or [],
             "band_src": band_src, "drop": None}
        if not rec.get("product_ok"):
            r["drop"] = "no product data (%s)" % (rec.get("error") or "")[:80]
            out.append(r); continue
        if not rec.get("ship_ok") or rec.get("ship_usd") is None:
            r["drop"] = "no shipping to IL (%s)" % (rec.get("ship_msg") or "")
            out.append(r); continue
        if rec.get("price_usd") is None:
            r["drop"] = "no price"
            out.append(r); continue
        hit = cache.get("aliexpress", rec["item_id"], "product", allow_stale=True)
        rows = sku_rows(hit["payload"]) if hit else []
        if rec["slot"] == "framed-art" and rows:
            # the Bible needs a frame: framed SKUs only; a listing whose attributes say "Unframed" and has no framed SKU is out
            fr_rows = [x for x in rows if FRAMED.search(x["label"] or "") and not UNFRAMED.search(x["label"] or "")]
            props = {str(p.get("attr_name")).lower(): str(p.get("attr_value")) for p in ds.as_list(((hit["payload"].get("result") or {}).get("ae_item_properties")))}
            fm = props.get("frame mode") or props.get("frame") or ""
            if fr_rows:
                rows = fr_rows
            elif re.search(r"unframed|^no$|scroll", fm, re.I) or not fm:
                r["drop"] = "unframed canvas (Frame mode = %s), no framed SKU" % (fm or "not stated")
                out.append(r); continue
        fr = ds.cached_freights(rec["item_id"])
        q_sku, q_price = rec["sku"], rec["price_usd"]
        room_row, size, how = pick_room(rows, key, rec.get("title"), q_sku) if rows else (None, None, "no-cache")
        if room_row is None:
            room_row = {"id": q_sku, "label": rec.get("sku_label"), "price": q_price, "stock": rec.get("stock")}
            size = size or "unknown"
        # shipping: quoted for the room SKU (cache), else the detail quote scaled by the SKU price ratio (studio parcel model)
        if room_row["id"] in fr and isinstance(fr[room_row["id"]].get("amount"), (int, float)):
            ship = fr[room_row["id"]]["amount"]
            basis = "quoted" if room_row["id"] == q_sku else "quoted (cache)"
        elif room_row["id"] == q_sku:
            ship, basis = rec["ship_usd"], "quoted"
        else:
            ratio = max(1.0, (room_row["price"] or q_price) / q_price) if q_price else 1.0
            if "selection standard" in str(rec.get("ship_company") or "").lower():
                # AliExpress Choice: a flat fee per item, whatever the SKU (1.99 USD in all 843 Selection Standard quotes of this run)
                ship = rec["ship_usd"]
                how_est = "Choice flat fee"
            elif ratio >= 1.5:  # a much bigger SKU (rug, curtain, set): shipping in proportion to the price (weight proxy), conservative
                ship = round(rec["ship_usd"] * ratio, 2)
                how_est = "x price ratio"
            else:  # a close SKU: the studio's parcel model (shipForQty: about 3.72 USD of a parcel is fixed)
                ship = round(rec["ship_usd"] + (ratio - 1) * max(0.0, rec["ship_usd"] - PARCEL_FIXED_USD), 2)
                how_est = "parcel model"
            basis = "estimated from SKU %s (quoted %.2f USD for a %.2f USD SKU; price ratio %.2f, %s)" % (q_sku, rec["ship_usd"], q_price, ratio, how_est)
        # pieces and quantity for the room
        need, band_kind = SETQ.get(key, (1, "unit"))
        pcs = pieces(room_row.get("label") or "") or (pieces(rec.get("title")) if need > 1 else None) or 1
        qty = max(1, math.ceil(need / pcs)) if need > 1 else 1
        if band_kind == "pair":
            band_unit = [round(band0[0] / 2 * min(pcs, 2), 1), round(band0[1] / 2 * min(pcs, 2), 1)] if need >= 1 else band0
        else:
            band_unit = [band0[0] * min(pcs, need), band0[1] * min(pcs, need)] if need > 1 else band0
        retail = band_at(band_unit, qty)
        L, m_ils, m_pct, m_cac = econ(room_row["price"], qty, ship_for_qty(ship, qty), retail)
        r.update(sku=room_row["id"], sku_label=room_row.get("label"), sku_how=how, size=size, price_usd=room_row["price"],
                 stock=room_row.get("stock"), n_skus=len(rows), detail_sku=q_sku, detail_price=q_price, ship_usd=ship, ship_basis=basis,
                 ship_days=rec.get("ship_days"), ship_company=rec.get("ship_company"), pcs=pcs, qty=qty, need=need,
                 band=band0, band_unit=band_unit, retail=retail, landed_ils=L, margin_ils=m_ils, margin_pct=m_pct, margin_after_cac=m_cac)
        if size == "no":
            r["drop"] = "no SKU fits the room envelope"
        out.append(r)
    json.dump(out, open(os.path.join(WORK, "prep-%s.json" % room), "w"), ensure_ascii=False, indent=0)
    return out


if __name__ == "__main__":
    for room in sys.argv[1:]:
        o = run(room)
        import collections
        c = collections.Counter((x["drop"] or "ok").split(" (")[0] for x in o)
        s = collections.Counter(x.get("size") for x in o if not x["drop"])
        b = collections.Counter(x.get("ship_basis", "")[:9] for x in o if not x["drop"])
        print(room, len(o), dict(c), dict(s), dict(b))
