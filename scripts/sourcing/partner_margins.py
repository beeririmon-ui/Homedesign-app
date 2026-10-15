"""Margins on partner (Israeli maker) products, by discount or commission level (2026-10-15).

We sell at the maker's own retail price (the Israeli value, rule ה.10). The maker gives us a discount,
or keeps the sale price minus our commission: both mean we pay retail × (1 − d).
The business deducts input VAT, so both sides are compared net of VAT.

  net = P / 1.18
  cost = P × (1 − d) / 1.18
  fees = 0.02 × P + 1.2           (card)
  returns = r × net               (r = 0.08 by default; 0 when the item is made to order and not returnable)
  margin = (net − cost − fees − returns) / net

  python3 scripts/sourcing/partner_margins.py                # writes the margin tables for the picks
"""
import json, os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
D = os.path.join(ROOT, "data/leads/final-2026-10-13")
LEVELS = [0.25, 0.30, 0.35, 0.40, 0.50]


def margin(price, d, r=0.08):
    net = price / 1.18
    cost = price * (1 - d) / 1.18
    fees = 0.02 * price + 1.2
    contrib = net - cost - fees - r * net
    return round(100 * contrib / net, 1), round(contrib)


def needed_discount(price, target=0.40, r=0.08):
    """The discount (or commission) that gives the target margin."""
    lo, hi = 0.0, 0.9
    for _ in range(40):
        mid = (lo + hi) / 2
        if margin(price, mid, r)[0] / 100 < target:
            lo = mid
        else:
            hi = mid
    return round(100 * hi)


def main():
    cat = json.load(open(f"{D}/partners-lighting-catalog-2026-10-15.json"))
    picks = json.load(open(f"{D}/partners-lighting-picks-2026-10-15.json"))
    prices = {}
    for st in cat["studios"]:
        for p in st["products"]:
            prices[p["slug"]] = p
    out = {"date": "2026-10-15", "levels": LEVELS, "studios": []}
    for st in picks["studios"]:
        rows = []
        seen = set()
        for pk in st.get("picks", []):
            prod = prices.get(pk["slug"])
            if not prod:
                continue
            size = pk.get("size") or ""
            price = None
            for s in prod.get("sizes") or []:
                if s.get("price_ils") and (not size or size.lower() in (s.get("label") or "").lower()):
                    price = s["price_ils"]
                    break
            if price is None:
                ps = [s.get("price_ils") for s in prod.get("sizes") or [] if s.get("price_ils")]
                price = min(ps) if ps else None
            key = (pk["slug"], size)
            if price is None or key in seen:
                continue
            seen.add(key)
            rows.append({
                "slug": pk["slug"], "name": prod.get("name"), "size": size, "price_ils": price,
                "shortlist": pk["slug"] in (st.get("shortlist") or []),
                "margins": {f"{int(l * 100)}": margin(price, l) for l in LEVELS},
                "margins_no_returns": {f"{int(l * 100)}": margin(price, l, 0)[0] for l in LEVELS},
                "discount_for_40": needed_discount(price),
                "discount_for_40_no_returns": needed_discount(price, r=0),
                "discount_for_30": needed_discount(price, 0.30),
            })
        out["studios"].append({"name": st["name"], "rows": rows})
    json.dump(out, open(f"{D}/partners-lighting-margins-2026-10-15.json", "w"), ensure_ascii=False, indent=1)
    for st in out["studios"]:
        print("##", st["name"])
        for r in st["rows"]:
            m = r["margins"]
            print(f"{'*' if r['shortlist'] else ' '} {r['name'][:28]:28} {r['size'][:10]:10} ₪{r['price_ils']:>5} | "
                  + " ".join(f"{k}%→{v[0]}% (₪{v[1]})" for k, v in m.items())
                  + f" | 40% needs {r['discount_for_40']}% ({r['discount_for_40_no_returns']}% if no returns)")


if __name__ == "__main__":
    main()
