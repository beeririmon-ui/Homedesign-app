#!/usr/bin/env python3
"""AliExpress Dropshipping API CLI for the sourcing pipeline (registry + budget + cache, like cj_source.py).

Methods (official catalog, category "AE-Dropshipper", https://openservice.aliexpress.com/doc/api.htm#/api?cid=21038):
  search       aliexpress.ds.text.search          keyWord, local, countryCode, currency, sortBy, pageSize, pageIndex, categoryId
  product      aliexpress.ds.product.get          ship_to_country, product_id, target_currency, target_language
  freight      aliexpress.ds.freight.query        queryDeliveryReq{quantity, shipToCountry, productId, selectedSkuId, language, locale, currency}
  image-search aliexpress.ds.image.searchV2       param0{search_type, image_base64, currency, lang, sort_type, sort_order, ship_to}
  specialinfo  aliexpress.ds.product.specialinfo.get  itemId, countryCodes[], appKey   (certificates)
  category     aliexpress.ds.category.get         categoryId, language
  card         product + freight (+ specialinfo with --certs) -> product card in data/product-card.schema.json,
               registered in data/sources/seen.json as aliexpress:<id> (status card)
  check / mark registry only, no call

Usage:
  python3 scripts/ae/ds.py search "ceramic vase" [--ship-to IL] [--currency USD] [--page 1] [--size 20] [--sort orders,desc] [--category ID]
  python3 scripts/ae/ds.py product <item_id> [<item_id> ...] [--ship-to IL] [--slot living-room/vase] [--full]
  python3 scripts/ae/ds.py freight <item_id> --sku <sku_id> [--country IL] [--qty 1]
  python3 scripts/ae/ds.py image-search <path-or-https-url> [--type similar|same] [--ship-to IL]
  python3 scripts/ae/ds.py specialinfo <item_id> [--country IL]
  python3 scripts/ae/ds.py category [--id <category_id>]
  python3 scripts/ae/ds.py card <item_id> --slot <room>/<slot> [--out data/products/<slot>/<id>.json] [--sku <sku_id>] [--certs]
  python3 scripts/ae/ds.py check <item_id> [...]
  python3 scripts/ae/ds.py mark <item_id> --status rejected|seen|card --reason "..." [--slot room/slot] [--card-id ID]
Global flags (before the command): --dry-run --force --by NAME --run-id ID --max-calls N --no-cache --hide-seen --raw
Exit codes: 1 API/business error (full AliExpress message printed, never a secret), 2 not configured, 3 budget stop.

Raw commands print JSON to stdout; `card` prints Hebrew summary lines. Item ids are the aliexpress.com ids
(1005...); a .us id (3256...) is accepted by the API and the returned main/sub ids are registered as aliases.
"""
import argparse
import base64
import datetime as dt
import json
import os
import re
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO, "scripts", "sourcing"))
import client  # noqa: E402
import budget, cache, registry  # noqa: E402

SRC = "aliexpress"
SUPPLIER_NAME = "AliExpress"
ITEM_URL = "https://www.aliexpress.com/item/%s.html"
M_SEARCH, M_PRODUCT, M_FREIGHT = "aliexpress.ds.text.search", "aliexpress.ds.product.get", "aliexpress.ds.freight.query"
M_IMAGE, M_SPECIAL, M_CATEGORY = "aliexpress.ds.image.searchV2", "aliexpress.ds.product.specialinfo.get", "aliexpress.ds.category.get"
SORTS = ("min_price,asc", "min_price,desc", "orders,asc", "orders,desc", "comments,asc", "comments,desc")
MAX_IMAGE_BYTES = 5 * 1024 * 1024


def out(o):
    json.dump(o, sys.stdout, ensure_ascii=False, indent=1)
    print()


def key_of(item_id):
    return "%s:%s" % (SRC, str(item_id).strip())


def spend(a, endpoint):
    """Budget check (dry run) or charge, exactly like cj_source.spend. Raises BudgetExceeded on a stop."""
    if a.dry_run:
        ok, cost, problems, used = budget.can(SRC, endpoint, a.run_id, None, a.max_calls)
        return {"would_cost": cost, "used_today": used, "ok": ok, "problems": problems}
    cost, used = budget.charge(SRC, endpoint, a.run_id, None, a.max_calls)
    print("[budget] %s %s: -%d calls, %d used today" % (SRC, endpoint, cost, used), file=sys.stderr)
    return {"cost": cost, "used_today": used}


def lang_full(code):
    """text.search / freight want a full locale (en_US); product.get accepts 'en' or 'en_US'."""
    return code if "_" in code else {"en": "en_US", "he": "he_IL", "iw": "he_IL"}.get(code, code + "_US" if len(code) == 2 else code)


# ----------------------------------------------------------------------------- search

def do_search(a):
    params = {"keyWord": a.q, "local": lang_full(a.lang), "countryCode": a.ship_to, "currency": a.currency,
              "pageSize": a.size, "pageIndex": a.page}
    if a.sort:
        params["sortBy"] = a.sort
    if a.category:
        params["categoryId"] = a.category
    cache_key = dict(params)
    hit = None if a.no_cache else cache.get_query(SRC, "search", cache_key)
    if hit:
        res = dict(hit["payload"], cached_at=hit["fetched_at"])
    elif a.dry_run:
        return out({"dry_run": True, "would_call": M_SEARCH, "params": params, "budget": spend(a, "search")})
    else:
        spend(a, "search")
        d = client.call_ok(M_SEARCH, params)
        data = d.get("data") if isinstance(d, dict) else None
        if isinstance(data, dict):
            prods = data.get("products")
            if isinstance(prods, dict):  # TOP sometimes nests lists as {"product": [...]}
                prods = next(iter(prods.values()), [])
            for p in prods or []:
                u = p.get("itemUrl")
                if u and u.startswith("//"):
                    p["itemUrl"] = "https:" + u
            data["products"] = prods or []
        res = {"query": a.q, "params": params, "total": (data or {}).get("totalCount"), "page": (data or {}).get("pageIndex"),
               "products": (data or {}).get("products", []), "code": d.get("code"), "msg": d.get("msg")}
        cache.put_query(SRC, "search", cache_key, res, endpoint=M_SEARCH)
    if a.raw:
        return out(res)
    reg = registry.load()
    prods, skipped = [], 0
    for p in res.get("products") or []:
        pid = p.get("itemId") or p.get("item_id")
        c = registry.check(key_of(pid), reg) if pid else {"action": "open", "why": ""}
        if a.hide_seen and c["action"] == "skip":
            skipped += 1
            continue
        prods.append(dict(p, registry=c["action"], registry_why=c["why"]))
    out(dict(res, products=prods, skipped_by_registry=skipped))


# ----------------------------------------------------------------------------- product

def trim_product(d, full=False):
    """Drop the two HTML blobs (detail, mobile_detail) unless --full; they are huge and useless in the cache."""
    if full or not isinstance(d, dict):
        return d
    r = d.get("result")
    base = (r or {}).get("ae_item_base_info_dto") if isinstance(r, dict) else None
    if isinstance(base, dict):
        for k in ("detail", "mobile_detail"):
            if k in base:
                base[k] = "<removed; use --full>"
    return d


def fetch_product(a, item_id, use_cache=True):
    """-> (payload, source) where source is CACHE or CALLED. Caches and registers as seen/opened."""
    hit = None if (a.no_cache or not use_cache) else cache.get(SRC, item_id, "product")
    if hit:
        return hit["payload"], "CACHE"
    spend(a, "product")
    params = {"ship_to_country": a.ship_to, "product_id": item_id, "target_currency": a.currency, "target_language": a.lang}
    d = trim_product(client.call_ok(M_PRODUCT, params), getattr(a, "full", False))
    cache.put(SRC, item_id, "product", d, endpoint=M_PRODUCT, params=params)
    r = d.get("result") or {}
    base, skus = r.get("ae_item_base_info_dto") or {}, r.get("ae_item_sku_info_dtos") or []
    if isinstance(skus, dict):
        skus = next(iter(skus.values()), [])
    conv = r.get("product_id_converter_result") or {}
    aliases = [str(x) for x in (conv.get("main_product_id"), conv.get("sub_product_id")) if x and str(x) != str(item_id)]
    registry.add(key_of(item_id), "seen", "opened via scripts/ae/ds.py: %s" % (base.get("subject") or "")[:120], by=a.by,
                 slot=getattr(a, "slot", None), opened=True, vids=aliases,
                 skus=[str(s.get("sku_id")) for s in skus if s.get("sku_id")], url=ITEM_URL % item_id)
    return d, "CALLED"


def do_product(a):
    reg = registry.load()
    results = []
    for item_id in a.ids:
        c = registry.check(key_of(item_id), reg, a.force)
        native = c["key"].split(":", 1)[1]
        if c["action"] == "skip":
            stale = cache.get(SRC, native, "product", allow_stale=True)
            results.append({"id": native, "action": "SKIP", "why": c["why"], "cached": bool(stale), "cached_at": stale and stale["fetched_at"]})
            continue
        hit = None if a.no_cache else cache.get(SRC, native, "product")
        if hit:
            results.append({"id": native, "action": "CACHE", "why": c["why"], "cached_at": hit["fetched_at"], "payload": None if a.dry_run else hit["payload"]})
            continue
        if a.dry_run:
            results.append({"id": native, "action": "WOULD_CALL", "why": c["why"], "budget": spend(a, "product")})
            continue
        payload, _ = fetch_product(a, native, use_cache=False)
        results.append({"id": native, "action": "CALLED", "why": c["why"], "payload": payload})
    if a.dry_run:
        out({"dry_run": True, "results": results, "summary": {k: sum(r["action"] == k for r in results) for k in ("SKIP", "CACHE", "WOULD_CALL")}})
    else:
        out(results if len(results) > 1 else results[0])


# ----------------------------------------------------------------------------- freight

def normalize_freight(d):
    r = (d or {}).get("result") or {}
    opts = r.get("delivery_options") or []
    if isinstance(opts, dict):
        opts = next(iter(opts.values()), [])
    res = []
    for o in opts:
        cent = o.get("shipping_fee_cent")
        try:
            fee = round(int(cent) / 100.0, 2) if cent not in (None, "") else None
        except ValueError:
            fee = None
        if fee is None:
            m = re.search(r"([\d.]+)", str(o.get("shipping_fee_format") or ""))
            fee = float(m.group(1)) if m else None
        res.append({"code": o.get("code"), "company": o.get("company"), "fee": 0.0 if o.get("free_shipping") else fee,
                    "currency": o.get("shipping_fee_currency"), "days_min": o.get("min_delivery_days"),
                    "days_max": o.get("max_delivery_days"), "estimated": o.get("estimated_delivery_time") or o.get("delivery_date_desc"),
                    "tracking": o.get("tracking"), "free_shipping": o.get("free_shipping"), "ship_from": o.get("ship_from_country"),
                    "stock": o.get("available_stock"), "guaranteed_days": o.get("guaranteed_delivery_days")})
    return {"options": res, "success": r.get("success"), "code": r.get("code"), "msg": r.get("msg")}


def fetch_freight(a, item_id, sku_id, country, qty):
    section = "freight:%s:%s:%d" % (sku_id, country, qty)
    hit = None if a.no_cache else cache.get(SRC, item_id, section, kind="freight")
    if hit:
        return dict(hit["payload"], cached_at=hit["fetched_at"]), "CACHE"
    spend(a, "freight")
    req = {"quantity": qty, "shipToCountry": country, "productId": str(item_id), "selectedSkuId": str(sku_id),
           "language": lang_full(a.lang), "locale": lang_full(a.lang), "currency": a.currency}
    try:
        d = client.call_ok(M_FREIGHT, {"queryDeliveryReq": req})
        res = dict(normalize_freight(d), item_id=str(item_id), sku_id=str(sku_id), country=country, qty=qty, raw=d if a.raw else None)
    except client.AeError as e:
        if "DELIVERY" not in str(e.code or "").upper() and "DELIVERY" not in str(e.message or "").upper():
            raise
        res = {"options": [], "success": False, "code": e.code, "msg": e.message, "item_id": str(item_id), "sku_id": str(sku_id), "country": country, "qty": qty}
    cache.put(SRC, item_id, section, res, endpoint=M_FREIGHT, params=req)
    return res, "CALLED"


def do_freight(a):
    if a.dry_run:
        return out({"dry_run": True, "would_call": M_FREIGHT, "item_id": a.item_id, "sku": a.sku, "country": a.country, "qty": a.qty,
                    "budget": spend(a, "freight")})
    res, how = fetch_freight(a, a.item_id, a.sku, a.country, a.qty)
    out(dict(res, source=how))


# ----------------------------------------------------------------------------- image search

def load_image_b64(src):
    if re.match(r"^https://", src):
        req = urllib.request.Request(src, headers={"User-Agent": client.USER_AGENT})
        with urllib.request.urlopen(req, timeout=60) as r:
            data = r.read(MAX_IMAGE_BYTES + 1)
    elif re.match(r"^[a-z]+://", src):
        sys.exit("image-search: only https URLs or local files are accepted.")
    else:
        with open(src, "rb") as f:
            data = f.read(MAX_IMAGE_BYTES + 1)
    if len(data) > MAX_IMAGE_BYTES:
        sys.exit("image-search: image larger than %d MB; resize it first." % (MAX_IMAGE_BYTES // (1024 * 1024)))
    return base64.b64encode(data).decode("ascii")


def do_image(a):
    if a.dry_run:
        return out({"dry_run": True, "would_call": M_IMAGE, "image": a.image, "type": a.type, "budget": spend(a, "image")})
    b64 = load_image_b64(a.image)
    spend(a, "image")
    param0 = {"search_type": a.type, "image_base64": b64, "currency": a.currency, "lang": a.lang,
              "sort_type": a.sort, "sort_order": a.order, "ship_to": a.ship_to}
    d = client.call_ok(M_IMAGE, {"param0": param0})
    r = d.get("result") or {}
    items = r.get("data") or []
    if isinstance(items, dict):
        items = next(iter(items.values()), [])
    reg = registry.load()
    res = []
    for p in items:
        pid = p.get("product_id")
        c = registry.check(key_of(pid), reg) if pid else {"action": "open", "why": ""}
        if a.hide_seen and c["action"] == "skip":
            continue
        res.append(dict(p, registry=c["action"], registry_why=c["why"]))
    out({"image": a.image, "type": a.type, "count": len(res), "products": res, "code": r.get("code"), "messages": r.get("messages")})


# ----------------------------------------------------------------------------- specialinfo / category

def fetch_specialinfo(a, item_id, country):
    section = "specialinfo:%s" % country
    hit = None if a.no_cache else cache.get(SRC, item_id, section, kind="product")
    if hit:
        return hit["payload"], "CACHE"
    spend(a, "specialinfo")
    d = client.call_ok(M_SPECIAL, {"itemId": item_id, "countryCodes": [country], "appKey": client.app_key()})
    data = (d.get("result") or {}).get("data") or {}
    certs = data.get("item_qualification_list") or []
    if isinstance(certs, dict):
        certs = next(iter(certs.values()), [])
    res = {"item_id": str(item_id), "country": country, "certificates": certs}
    cache.put(SRC, item_id, section, res, endpoint=M_SPECIAL, params={"country": country})
    return res, "CALLED"


def do_specialinfo(a):
    if a.dry_run:
        return out({"dry_run": True, "would_call": M_SPECIAL, "item_id": a.item_id, "budget": spend(a, "specialinfo")})
    res, how = fetch_specialinfo(a, a.item_id, a.country)
    out(dict(res, source=how))


def do_category(a):
    params = {"language": a.lang}
    if a.id:
        params["categoryId"] = a.id
    hit = None if a.no_cache else cache.get_query(SRC, "category", params)
    if hit:
        return out(dict(hit["payload"], cached_at=hit["fetched_at"]))
    if a.dry_run:
        return out({"dry_run": True, "would_call": M_CATEGORY, "params": params, "budget": spend(a, "category")})
    spend(a, "category")
    d = client.call_ok(M_CATEGORY, params)
    r = d.get("result") or {}
    cats = r.get("categories") or []
    if isinstance(cats, dict):
        cats = next(iter(cats.values()), [])
    res = {"params": params, "total": r.get("total_result_count"), "categories": cats}
    cache.put_query(SRC, "category", params, res, endpoint=M_CATEGORY)
    out(res)


# ----------------------------------------------------------------------------- card

def slugify(s, words=4, maxlen=40):
    toks = re.findall(r"[a-z0-9]+", (s or "").lower())
    stop = {"the", "a", "an", "for", "and", "with", "of", "in", "on", "to", "home", "decor", "decoration", "new", "hot", "sale"}
    toks = [t for t in toks if t not in stop] or toks
    return "-".join(toks[:words])[:maxlen].strip("-") or "item"


def as_list(v):
    if isinstance(v, dict):
        return next(iter(v.values()), []) if v else []
    return v or []


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def pick_sku(skus, wanted=None):
    if wanted:
        for s in skus:
            if wanted in (str(s.get("sku_id")), str(s.get("id")), str(s.get("sku_attr"))):
                return s
        sys.exit("card: SKU %s not found on this product; SKUs: %s" % (wanted, ", ".join(str(s.get("sku_id")) for s in skus)))
    in_stock = [s for s in skus if (num(s.get("sku_available_stock")) or 0) > 0] or skus
    return min(in_stock, key=lambda s: num(s.get("offer_sale_price")) or num(s.get("sku_price")) or 1e9) if in_stock else None


def slot_spec(room, slot):
    try:
        with open(os.path.join(REPO, "data", "slots", room + ".json")) as f:
            for s in json.load(f).get("slots", []):
                if s.get("id") == slot:
                    return s
    except (OSError, ValueError):
        pass
    return {}


def build_card(item_id, product, sku, freight, certs, room, slot, card_id, by):
    r = product.get("result") or {}
    base = r.get("ae_item_base_info_dto") or {}
    store = r.get("ae_store_info") or {}
    pack = r.get("package_info_dto") or {}
    media = r.get("ae_multimedia_info_dto") or {}
    props = as_list(r.get("ae_item_properties"))
    spec = slot_spec(room, slot)
    sku = sku or {}
    imgs = [u for u in (media.get("image_urls") or "").split(";") if u]
    for s in as_list(r.get("ae_item_sku_info_dtos")):
        for p in as_list(s.get("ae_sku_property_dtos")):
            u = p.get("sku_image")
            if u and u not in imgs:
                imgs.append(u)
    materials = [p.get("attr_value") for p in props if "material" in str(p.get("attr_name") or "").lower() and p.get("attr_value")]
    voltage = next((p.get("attr_value") for p in props if "voltage" in str(p.get("attr_name") or "").lower()), None)
    plug = next((p.get("attr_value") for p in props if "plug" in str(p.get("attr_name") or "").lower()), None)
    opts = sorted([o for o in (freight or {}).get("options") or [] if o.get("fee") is not None], key=lambda o: (o["fee"], o.get("days_max") or 999))
    cheapest = opts[0] if opts else None
    fastest = min(opts, key=lambda o: (o.get("days_max") or 999, o["fee"])) if opts else None
    sku_label = ", ".join("%s: %s" % (p.get("sku_property_name"), p.get("property_value_definition_name") or p.get("sku_property_value"))
                          for p in as_list(sku.get("ae_sku_property_dtos")))
    price = num(sku.get("offer_sale_price")) or num(sku.get("sku_price"))
    notes = []
    notes.append("DRAFT from AliExpress DS API (%s, %s): colors (HEX), visual_weight, product dimensions and texture are NOT filled; "
                 "fill them from the photos before QA (sourcing-agent)." % (dt.date.today().isoformat(), by))
    if sku_label:
        notes.append("SKU %s (%s), stock %s, list price %s %s." % (sku.get("sku_id"), sku_label, sku.get("sku_available_stock"), sku.get("sku_price"), sku.get("currency_code")))
    if pack:
        notes.append("Package (not product): %s x %s x %s cm, gross %s kg." % (pack.get("package_length"), pack.get("package_width"), pack.get("package_height"), pack.get("gross_weight")))
    if opts:
        notes.append("Shipping to %s: cheapest %s %s %s, %s-%s days (%s)%s." % (
            (freight or {}).get("country"), cheapest["fee"], cheapest.get("currency"), cheapest.get("company") or cheapest.get("code"),
            cheapest.get("days_min"), cheapest.get("days_max"), cheapest.get("code"),
            "; fastest %s %s %s, %s-%s days" % (fastest["fee"], fastest.get("currency"), fastest.get("company") or fastest.get("code"), fastest.get("days_min"), fastest.get("days_max")) if fastest is not cheapest else ""))
    elif freight is not None:
        notes.append("NO shipping option to %s returned (%s)." % (freight.get("country"), freight.get("msg") or freight.get("code")))
    notes.append("Store: %s (id %s, %s); ratings described %s / communication %s / shipping %s; product %s stars, %s reviews, %s sold; AE category %s." % (
        store.get("store_name"), store.get("store_id"), store.get("store_country_code"), store.get("item_as_described_rating"),
        store.get("communication_rating"), store.get("shipping_speed_rating"), base.get("avg_evaluation_rating"), base.get("evaluation_count"),
        base.get("sales_count"), base.get("category_id")))
    dims = [p for p in props if any(w in str(p.get("attr_name") or "").lower() for w in ("size", "dimension", "height", "diameter", "length", "width"))]
    if dims:
        notes.append("Listed attributes: " + "; ".join("%s = %s" % (p.get("attr_name"), p.get("attr_value")) for p in dims[:8]) + ".")
    card = {
        "id": card_id,
        "slot": slot,
        "name": base.get("subject"),
        "category": slot,
        "rooms": [room],
        "placement": spec.get("placement"),
        "supplier": {"name": SUPPLIER_NAME, "product_url": ITEM_URL % item_id, "sku": str(sku.get("sku_id")) if sku.get("sku_id") else None,
                     "rating": num(base.get("avg_evaluation_rating"))},
        "price": {"cost": price, "currency": sku.get("currency_code") or base.get("currency_code") or "USD", "suggested_retail": None},
        "shipping": {"days_min": cheapest.get("days_min") if cheapest else None, "days_max": cheapest.get("days_max") if cheapest else None,
                     "ships_to": [(freight or {}).get("country")] if cheapest else []},
        "dimensions_cm": {"width": None, "depth": None, "height": None},
        "colors": {"dominant_hex": None, "secondary_hex": [], "temperature": None},
        "materials": materials,
        "texture": None,
        "finish": None,
        "visual_weight": None,
        "lighting": None,
        "images": {"urls": imgs, "quality": "medium", "usage_rights": "unclear"},
        "style_scores": {},
        "status": "candidate",
        "notes": " ".join(notes),
    }
    if certs is not None or voltage or plug:
        safety = {"ce": None, "ip_rating": None, "toy_standard": [], "power": None, "plug_type": plug, "voltage": voltage,
                  "certificates": [], "source": "aliexpress.ds.product.get attributes"}
        for c in (certs or {}).get("certificates") or []:
            name, url = str(c.get("name") or c.get("key") or ""), str(c.get("value") or "")
            if url.startswith("https://"):
                safety["certificates"].append({"name": name, "url": url, "verified": False})
            if "ce" == name.strip().lower() or name.lower().startswith("ce "):
                safety["ce"] = True
        if certs is not None:
            safety["source"] += " + aliexpress.ds.product.specialinfo.get"
        card["safety"] = safety
    return card, cheapest, fastest


def do_card(a):
    if "/" not in a.slot:
        sys.exit("card: --slot must be <room>/<slot>, e.g. living-room/vase")
    room, slot = a.slot.split("/", 1)
    item_id = str(a.item_id).strip()
    if a.dry_run:
        return out({"dry_run": True, "would_call": [M_PRODUCT, M_FREIGHT] + ([M_SPECIAL] if a.certs else []), "item_id": item_id,
                    "cached_product": bool(cache.get(SRC, item_id, "product")), "budget": spend(a, "product")})
    product, how_p = fetch_product(a, item_id)
    r = product.get("result") or {}
    skus = as_list(r.get("ae_item_sku_info_dtos"))
    sku = pick_sku(skus, a.sku)
    freight = None
    if not a.no_freight and sku and sku.get("sku_id"):
        freight, _ = fetch_freight(a, item_id, str(sku["sku_id"]), a.ship_to, a.qty)
    certs = None
    if a.certs:
        certs, _ = fetch_specialinfo(a, item_id, a.ship_to)
    base = r.get("ae_item_base_info_dto") or {}
    card_id = a.id or "%s-aliexpress-%s" % (slot, slugify(base.get("subject")))
    path = a.out or os.path.join(REPO, "data", "products", slot, card_id + ".json")
    card, cheapest, fastest = build_card(item_id, product, sku, freight, certs, room, slot, card_id, a.by)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w") as f:
        json.dump(card, f, ensure_ascii=False, indent=2)
        f.write("\n")
    registry.add(key_of(item_id), "card", "card %s via scripts/ae/ds.py" % card_id, by=a.by, slot=a.slot, card_id=card_id, opened=True,
                 skus=[str(s.get("sku_id")) for s in skus if s.get("sku_id")], url=ITEM_URL % item_id)
    rel = os.path.relpath(path, REPO) if os.path.abspath(path).startswith(REPO) else path
    print("כרטיס נכתב: %s" % rel)
    print("מוצר: %s (AliExpress %s, %s)" % (card["name"], item_id, "מהמטמון" if how_p == "CACHE" else "נקרא מה-API"))
    print("מחיר: %s %s | SKU %s | מלאי %s" % (card["price"]["cost"], card["price"]["currency"], card["supplier"]["sku"], (sku or {}).get("sku_available_stock")))
    if cheapest:
        line = "משלוח ל-%s: הזול %s %s, %s–%s ימים (%s)" % (a.ship_to, cheapest["fee"], cheapest.get("currency"), cheapest.get("days_min"), cheapest.get("days_max"), cheapest.get("company") or cheapest.get("code"))
        if fastest is not cheapest:
            line += " | המהיר %s %s, %s–%s ימים (%s)" % (fastest["fee"], fastest.get("currency"), fastest.get("days_min"), fastest.get("days_max"), fastest.get("company") or fastest.get("code"))
        print(line)
    elif freight is not None:
        print("משלוח ל-%s: אין אפשרות משלוח (%s)" % (a.ship_to, freight.get("msg") or freight.get("code")))
    else:
        print("משלוח: לא נבדק (--no-freight או בלי SKU)")
    pack = r.get("package_info_dto") or {}
    if pack:
        print('אריזה: %s×%s×%s ס"מ, %s ק"ג (אריזה, לא המוצר)' % (pack.get("package_length"), pack.get("package_width"), pack.get("package_height"), pack.get("gross_weight")))
    print("תמונות: %d | דירוג %s (%s ביקורות) | חנות: %s" % (len(card["images"]["urls"]), base.get("avg_evaluation_rating"), base.get("evaluation_count"), (r.get("ae_store_info") or {}).get("store_name")))
    if card.get("safety", {}).get("certificates"):
        print("תעודות: %s" % ", ".join(c["name"] for c in card["safety"]["certificates"]))
    print("להשלים ידנית לפני QA: צבעים (HEX), משקל ויזואלי, מידות המוצר, טקסטורה%s" % ("" if card["materials"] else ", חומרים"))
    print("נרשם ב-seen.json: %s status=card card_id=%s" % (key_of(item_id), card_id))


# ----------------------------------------------------------------------------- main

def main(argv=None):
    ap = argparse.ArgumentParser(description="AliExpress DS importer (registry + budget + cache)")
    ap.add_argument("--dry-run", action="store_true"); ap.add_argument("--force", action="store_true")
    ap.add_argument("--by", default="sourcing-agent"); ap.add_argument("--run-id")
    ap.add_argument("--max-calls", type=int); ap.add_argument("--no-cache", action="store_true")
    ap.add_argument("--hide-seen", action="store_true"); ap.add_argument("--raw", action="store_true")
    # The same global flags are also accepted after the subcommand (SUPPRESS keeps the main parser's values).
    g = argparse.ArgumentParser(add_help=False); S = argparse.SUPPRESS
    for flag in ("--dry-run", "--force", "--no-cache", "--hide-seen", "--raw"):
        g.add_argument(flag, action="store_true", default=S)
    g.add_argument("--by", default=S); g.add_argument("--run-id", default=S); g.add_argument("--max-calls", type=int, default=S)
    sub = ap.add_subparsers(dest="cmd", required=True)
    _add = sub.add_parser
    sub.add_parser = lambda name, **kw: _add(name, parents=[g], **kw)
    s = sub.add_parser("search"); s.add_argument("q"); s.add_argument("--ship-to", default="IL"); s.add_argument("--currency", default="USD")
    s.add_argument("--page", type=int, default=1); s.add_argument("--size", type=int, default=20); s.add_argument("--sort", choices=SORTS)
    s.add_argument("--category"); s.add_argument("--lang", default="en_US")
    p = sub.add_parser("product"); p.add_argument("ids", nargs="+"); p.add_argument("--ship-to", default="IL"); p.add_argument("--currency", default="USD")
    p.add_argument("--lang", default="en"); p.add_argument("--slot"); p.add_argument("--full", action="store_true")
    f = sub.add_parser("freight"); f.add_argument("item_id"); f.add_argument("--sku", required=True); f.add_argument("--country", default="IL")
    f.add_argument("--qty", type=int, default=1); f.add_argument("--currency", default="USD"); f.add_argument("--lang", default="en_US")
    i = sub.add_parser("image-search"); i.add_argument("image"); i.add_argument("--type", choices=("similar", "same"), default="similar")
    i.add_argument("--ship-to", default="IL"); i.add_argument("--currency", default="USD"); i.add_argument("--lang", default="en")
    i.add_argument("--sort", choices=("price", "orders"), default="orders"); i.add_argument("--order", choices=("asc", "desc"), default="desc")
    sp = sub.add_parser("specialinfo"); sp.add_argument("item_id"); sp.add_argument("--country", default="IL")
    cg = sub.add_parser("category"); cg.add_argument("--id"); cg.add_argument("--lang", default="en")
    c = sub.add_parser("card"); c.add_argument("item_id"); c.add_argument("--slot", required=True); c.add_argument("--out"); c.add_argument("--id")
    c.add_argument("--sku"); c.add_argument("--ship-to", default="IL"); c.add_argument("--qty", type=int, default=1); c.add_argument("--currency", default="USD")
    c.add_argument("--lang", default="en"); c.add_argument("--certs", action="store_true"); c.add_argument("--no-freight", action="store_true")
    ck = sub.add_parser("check"); ck.add_argument("ids", nargs="+")
    m = sub.add_parser("mark"); m.add_argument("item_id"); m.add_argument("--status", required=True, choices=registry.STATUSES)
    m.add_argument("--reason", required=True); m.add_argument("--slot"); m.add_argument("--card-id")
    a = ap.parse_args(argv)
    try:
        if a.cmd == "check":
            reg = registry.load()
            return out([{k: v for k, v in registry.check(key_of(x), reg, a.force).items() if k != "entry"} for x in a.ids])
        if a.cmd == "mark":
            if a.dry_run:
                return out({"dry_run": True, "would_mark": key_of(a.item_id), "status": a.status})
            return out(registry.add(key_of(a.item_id), a.status, a.reason, by=a.by, slot=a.slot, card_id=a.card_id, opened=True))
        if not a.dry_run and not client.configured():
            print("aliexpress: not configured. חסרים משתני הסביבה AE_DS_APP_KEY / AE_DS_APP_SECRET (מגדירים בהגדרות הסביבה של Claude, לא בצ'אט). "
                  "ראו scripts/ae/README.md. Nothing was called.", file=sys.stderr)
            return 2
        {"search": do_search, "product": do_product, "freight": do_freight, "image-search": do_image,
         "specialinfo": do_specialinfo, "category": do_category, "card": do_card}[a.cmd](a)
        return 0
    except budget.BudgetExceeded as e:
        print("BUDGET STOP: %s" % e, file=sys.stderr)
        return 3
    except client.AeConfigError as e:
        print("לא מוגדר: %s" % e.message, file=sys.stderr)
        return 2
    except client.AeAuthRequired as e:
        print(e.message, file=sys.stderr)
        return 1
    except client.AeError as e:
        print(str(e), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
