#!/usr/bin/env python3
"""List the SKUs of cached AliExpress products (no API call): python3 scripts/ae/scale_skus.py <item_id> ..."""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import ds
for iid in sys.argv[1:]:
    hit = ds.cache.get(ds.SRC, iid, "product", allow_stale=True)
    if not hit:
        print(iid, "not cached"); continue
    r = hit["payload"].get("result") or {}
    print("==", iid, ((r.get("ae_item_base_info_dto") or {}).get("subject") or "")[:90])
    for s in ds.as_list(r.get("ae_item_sku_info_dtos")):
        print("  ", s.get("sku_id"), ds.num(s.get("offer_sale_price")) or ds.num(s.get("sku_price")), "stock", s.get("sku_available_stock"), "|", __import__("scale").sku_text(s)[:90])
