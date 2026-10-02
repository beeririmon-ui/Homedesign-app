#!/usr/bin/env python3
"""Small CJ Dropshipping API client for the sourcing agents.

Auth: an access token is read from ~/.cache/cj/token.json. If it is missing, the
script exchanges the API key in the CJ_API_KEY environment variable for one.
Never commit keys or tokens to the repo.

Usage:
  python3 scripts/cj.py search "chunky knit throw blanket" [--size 20] [--page 1]
  python3 scripts/cj.py list ["name words"] [--category <categoryId>] [--size 50] [--page 1]
      # /product/list: browse a whole category page by page (see docs/suppliers/cj-categories.md)
  python3 scripts/cj.py product <pid>
  python3 scripts/cj.py freight <vid> [--to IL] [--qty 1]
Output is JSON on stdout.
"""
import json, os, sys, argparse, urllib.request, urllib.parse

BASE = "https://developers.cjdropshipping.com/api2.0/v1"
CACHE = os.path.expanduser("~/.cache/cj/token.json")


def _req(method, path, params=None, body=None, token=None):
    url = BASE + path + ("?" + urllib.parse.urlencode(params) if params else "")
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(url, data=data, method=method)
    r.add_header("Content-Type", "application/json")
    if token:
        r.add_header("CJ-Access-Token", token)
    with urllib.request.urlopen(r, timeout=60) as resp:
        return json.load(resp)


def token():
    if os.path.exists(CACHE):
        return json.load(open(CACHE))["data"]["accessToken"]
    key = os.environ.get("CJ_API_KEY")
    if not key:
        sys.exit("No CJ token cache and no CJ_API_KEY in the environment.")
    d = _req("POST", "/authentication/getAccessToken", body={"apiKey": key})
    if not d.get("result"):
        sys.exit("CJ auth failed: %s" % d.get("message"))
    os.makedirs(os.path.dirname(CACHE), mode=0o700, exist_ok=True)
    with open(CACHE, "w") as f:
        json.dump(d, f)
    os.chmod(CACHE, 0o600)
    return d["data"]["accessToken"]


def search(q, page, size):
    d = _req("GET", "/product/listV2", {"keyWord": q, "page": page, "size": size}, token=token())
    out = []
    for block in (d.get("data") or {}).get("content") or []:
        for p in block.get("productList") or []:
            out.append({k: p.get(k) for k in ("id", "nameEn", "sku", "sellPrice", "listedNum",
                                                "warehouseInventoryNum", "bigImage", "isVideo")})
    return {"query": q, "total": (d.get("data") or {}).get("totalRecords"), "products": out}


def listing(q, page, size, category=None):
    params = {"pageNum": page, "pageSize": size}
    if q: params["productNameEn"] = q
    if category: params["categoryId"] = category
    d = _req("GET", "/product/list", params, token=token())
    data = d.get("data") or {}
    out = [{"id": p.get("pid"), "nameEn": p.get("productNameEn"), "sku": p.get("productSku"),
            "sellPrice": p.get("sellPrice"), "listedNum": p.get("listedNum"), "bigImage": p.get("productImage"),
            "category": p.get("categoryName")} for p in data.get("list") or []]
    return {"query": q, "total": data.get("total"), "products": out, "message": d.get("message")}


def product(pid):
    p = _req("GET", "/product/query", {"pid": pid}, token=token()).get("data") or {}
    keep = ("pid", "productNameEn", "productSku", "productImageSet", "productWeight", "materialNameEn",
            "packingNameEn", "sellPrice", "suggestSellPrice", "listedNum", "categoryName", "description",
            "productVideo", "supplierName")
    out = {k: p.get(k) for k in keep}
    out["url"] = "https://cjdropshipping.com/product/-p-%s.html" % pid
    out["variants"] = [{k: v.get(k) for k in ("vid", "variantNameEn", "variantSku", "variantImage",
                                              "variantKey", "variantSellPrice", "variantWeight",
                                              "variantLength", "variantWidth", "variantHeight", "inventoryNum")}
                       for v in p.get("variants") or []]
    return out


def freight(vid, to, qty):
    d = _req("POST", "/logistic/freightCalculate", token=token(),
             body={"startCountryCode": "CN", "endCountryCode": to, "products": [{"quantity": qty, "vid": vid}]})
    return {"vid": vid, "to": to, "options": [{"name": r.get("logisticName"), "days": r.get("logisticAging"),
                                               "usd": r.get("logisticPrice")} for r in d.get("data") or []],
            "message": d.get("message")}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search"); s.add_argument("q"); s.add_argument("--page", type=int, default=1); s.add_argument("--size", type=int, default=20)
    l = sub.add_parser("list"); l.add_argument("q", nargs="?", default=""); l.add_argument("--category"); l.add_argument("--page", type=int, default=1); l.add_argument("--size", type=int, default=50)
    p = sub.add_parser("product"); p.add_argument("pid")
    f = sub.add_parser("freight"); f.add_argument("vid"); f.add_argument("--to", default="IL"); f.add_argument("--qty", type=int, default=1)
    a = ap.parse_args()
    if a.cmd == "search": res = search(a.q, a.page, a.size)
    elif a.cmd == "list": res = listing(a.q, a.page, a.size, a.category)
    elif a.cmd == "product": res = product(a.pid)
    else: res = freight(a.vid, a.to, a.qty)
    json.dump(res, sys.stdout, ensure_ascii=False, indent=1)
    print()
