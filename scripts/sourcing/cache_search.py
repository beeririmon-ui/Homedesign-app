"""Search the local supplier cache (no API calls): every AliExpress and CJ product we already fetched,
plus every listing that came back in a cached AliExpress search (2026-10-17, massive round).

Index (rebuilt when missing or older than the cache): ~/.cache/sourcing/cache-index.json
  opened products   data/sources/aliexpress/<id>.json, data/sources/cj/<pid>.json  -> title, price, image, weight,
                    package, cheapest cached freight to IL (fee + days), store, registry status
  search listings   data/sources/aliexpress/queries/search-*.json -> title, price, image, orders (no freight: "listed")

  python3 -I scripts/sourcing/cache_search.py "seagrass" "basket"          # all words must appear in the title
  python3 -I scripts/sourcing/cache_search.py --any "bamboo,teak" "stool"  # plus at least one of the --any words
  python3 -I scripts/sourcing/cache_search.py --not "plastic,resin" --max-usd 40 --opened "ceramic" "vase"
  python3 -I scripts/sourcing/cache_search.py --id aliexpress:1005002719451626     # one record, all SKUs
  python3 -I scripts/sourcing/cache_search.py --rebuild
Output: JSON lines, best first (opened with freight, then opened, then listed; then orders).
"""
import argparse, glob, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
IDX = os.path.expanduser("~/.cache/sourcing/cache-index.json")
AE = os.path.join(ROOT, "data/sources/aliexpress")
CJ = os.path.join(ROOT, "data/sources/cj")
SEEN = os.path.join(ROOT, "data/sources/seen.json")


def _f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _ae_product(path, reg):
    d = json.load(open(path))
    secs = d.get("sections") or {}
    p = ((secs.get("product") or {}).get("payload") or {}).get("result") or {}
    base = p.get("ae_item_base_info_dto") or {}
    skus = p.get("ae_item_sku_info_dtos") or []
    if isinstance(skus, dict):
        skus = skus.get("ae_item_sku_info_d_t_o") or (list(skus.values())[0] if skus else [])
    prices = [x for x in (_f(s.get("offer_sale_price") or s.get("sku_price")) for s in skus if isinstance(s, dict)) if x]
    pics = ((p.get("ae_multimedia_info_dto") or {}).get("image_urls") or "").split(";")
    pkg = p.get("package_info_dto") or {}
    fr = []
    for k, v in secs.items():
        if k.startswith("freight"):
            for o in ((v.get("payload") or {}).get("options") or []):
                fee = _f(o.get("fee"))
                if fee is not None:
                    fr.append((fee, o.get("days_min"), o.get("days_max"), k.split(":")[1]))
    fr.sort()
    key = f"aliexpress:{d.get('id')}"
    r = reg.get(key) or {}
    return {"key": key, "src": "aliexpress", "kind": "opened", "title": base.get("subject") or "",
            "usd_min": min(prices) if prices else None, "usd_max": max(prices) if prices else None, "skus": len(skus),
            "image": pics[0] if pics and pics[0] else None, "url": f"https://www.aliexpress.com/item/{d.get('id')}.html",
            "kg": _f(pkg.get("gross_weight")), "pkg_cm": [pkg.get("package_length"), pkg.get("package_width"), pkg.get("package_height")],
            "freight_usd": fr[0][0] if fr else None, "freight_days": f"{fr[0][1]}-{fr[0][2]}" if fr else None,
            "freight_sku": fr[0][3] if fr else None, "orders": base.get("sales_count"), "rating": base.get("avg_evaluation_rating"),
            "store": (p.get("ae_store_info") or {}).get("store_name"), "category_id": base.get("category_id"),
            "registry": r.get("status") or ("seen" if r else None), "registry_reason": (r.get("reason") or "")[:120],
            "card_ids": r.get("card_ids") or []}


def _cj_product(path, reg):
    d = json.load(open(path))
    secs = d.get("sections") or {}
    p = (secs.get("product") or {}).get("payload") or {}
    p = p.get("data") if isinstance(p.get("data"), dict) else p
    imgs = p.get("productImageSet") or []
    if isinstance(imgs, str):
        imgs = [i for i in re.split(r"[;,]", imgs.strip("[]").replace('"', "")) if i]
    fr = []
    for k, v in secs.items():
        if k.startswith("freight"):
            pl = v.get("payload") or {}
            for o in (pl.get("data") if isinstance(pl.get("data"), list) else pl.get("options") or []):
                fee = _f(o.get("logisticPrice") or o.get("fee"))
                if fee is not None:
                    fr.append((fee, o.get("logisticAging") or o.get("days")))
    fr.sort(key=lambda x: x[0])
    key = f"cj:{d.get('id')}"
    r = reg.get(key) or {}
    sp = str(p.get("sellPrice") or "")
    nums = [x for x in (_f(v) for v in re.split(r"[-~ ]+", sp)) if x]
    return {"key": key, "src": "cj", "kind": "opened", "title": p.get("productNameEn") or "",
            "usd_min": min(nums) if nums else None, "usd_max": max(nums) if nums else None,
            "skus": len(p.get("variants") or []), "image": imgs[0] if imgs else None,
            "url": f"https://cjdropshipping.com/product/-p-{d.get('id')}.html",
            "kg": (_f(str(p.get("productWeight") or "").split("-")[-1]) or 0) / 1000 or None, "pkg_cm": None,
            "material": p.get("materialNameEn"), "category": p.get("categoryName"),
            "freight_usd": fr[0][0] if fr else None, "freight_days": fr[0][1] if fr else None,
            "orders": p.get("listedNum"), "registry": r.get("status") or ("seen" if r else None),
            "registry_reason": (r.get("reason") or "")[:120], "card_ids": r.get("card_ids") or []}


def build():
    reg = (json.load(open(SEEN)).get("items") or {}) if os.path.exists(SEEN) else {}
    recs = {}
    for f in glob.glob(os.path.join(AE, "*.json")):
        try:
            r = _ae_product(f, reg)
            recs[r["key"]] = r
        except Exception:
            pass
    for f in glob.glob(os.path.join(CJ, "*.json")):
        try:
            r = _cj_product(f, reg)
            recs[r["key"]] = r
        except Exception:
            pass
    for f in glob.glob(os.path.join(AE, "queries", "search-*.json")):
        try:
            d = json.load(open(f))
        except Exception:
            continue
        q = (d.get("params") or {}).get("keyWord")
        for p in (d.get("payload") or {}).get("products") or []:
            key = f"aliexpress:{p.get('itemId')}"
            if key in recs:
                recs[key].setdefault("found_by", [])
                if q and q not in recs[key]["found_by"] and len(recs[key]["found_by"]) < 5:
                    recs[key]["found_by"].append(q)
                continue
            r = reg.get(key) or {}
            recs[key] = {"key": key, "src": "aliexpress", "kind": "listed", "title": p.get("title") or "",
                         "usd_min": _f(p.get("targetSalePrice") or p.get("salePrice")), "usd_max": None,
                         "image": p.get("itemMainPic"), "url": f"https://www.aliexpress.com/item/{p.get('itemId')}.html",
                         "orders": p.get("orders"), "freight_usd": None, "found_by": [q] if q else [],
                         "registry": r.get("status") or ("seen" if r else None),
                         "registry_reason": (r.get("reason") or "")[:120], "card_ids": r.get("card_ids") or []}
    os.makedirs(os.path.dirname(IDX), exist_ok=True)
    json.dump({"built_from": ROOT, "records": list(recs.values())}, open(IDX, "w"))
    return list(recs.values())


def load(rebuild=False):
    if rebuild or not os.path.exists(IDX):
        return build()
    return json.load(open(IDX))["records"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("words", nargs="*")
    ap.add_argument("--any", default="")
    ap.add_argument("--not", dest="nots", default="")
    ap.add_argument("--max-usd", type=float)
    ap.add_argument("--opened", action="store_true", help="only products with cached details")
    ap.add_argument("--src", choices=["aliexpress", "cj"])
    ap.add_argument("--limit", type=int, default=40)
    ap.add_argument("--id")
    ap.add_argument("--rebuild", action="store_true")
    a = ap.parse_args()
    recs = load(a.rebuild)
    if a.rebuild and not a.words and not a.id:
        print(f"index: {len(recs)} records ({sum(r['kind'] == 'opened' for r in recs)} opened)")
        return
    if a.id:
        for r in recs:
            if r["key"] == a.id:
                print(json.dumps(r, ensure_ascii=False, indent=1))
        return
    words = [w.lower() for w in a.words]
    anys = [w.strip().lower() for w in a.any.split(",") if w.strip()]
    nots = [w.strip().lower() for w in a.nots.split(",") if w.strip()]
    hits = []
    for r in recs:
        t = r["title"].lower()
        if any(w not in t for w in words) or (anys and not any(w in t for w in anys)) or any(w in t for w in nots):
            continue
        if a.opened and r["kind"] != "opened":
            continue
        if a.src and r["src"] != a.src:
            continue
        if a.max_usd and (r.get("usd_min") or 0) > a.max_usd:
            continue
        hits.append(r)
    hits.sort(key=lambda r: (r["kind"] != "opened", r.get("freight_usd") is None, -int(_f(r.get("orders")) or 0)))
    for r in hits[:a.limit]:
        print(json.dumps({k: v for k, v in r.items() if v not in (None, [], "")}, ensure_ascii=False))
    print(f"# {len(hits)} hits", file=sys.stderr)


if __name__ == "__main__":
    main()
