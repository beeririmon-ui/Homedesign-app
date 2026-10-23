#!/usr/bin/env python3
"""No product loses money, in any scenario (owner, 2026-10-20; docs/studio-rules.md ה.13, amended 2026-10-20).

"בא נוודא שאין דבר כזה מוצר מפסיד בשום צורה! יכול להיות יקר ללקוח אבל אין מפסיד!"

For every product the Studio or the site can sell, this computes the worst-case contribution (before CAC, in the
Studio formula) over its scenarios, the break-even price, and the no-loss price: the lowest price on the Studio's
usual endings (a whole shekel that ends in 9: 19, 29 ... 149, 159 ...) whose contribution is zero or more in every
scenario. Proposed price = max(current price, no-loss price). A price is never lowered, and a price the owner set in
the Studio is never changed (it is reported instead; today: the wabi-sabi cushion at ₪69, decision NL1).

The corrected scenario rules (BRIEF-no-loss-2026-10-20.md, "Correction", after the first pass raised 162 prices):
  1. Shipping method: only the method we ship with by default, the cheapest method to Israel, tracked where the
     supplier offers tracking (usually CJ Eub, or the AliExpress method on the card). Never CJ To Door, DHL or any
     express line when a cheaper method exists. A product whose only method is express is listed as "express only".
  2. Quantity: the Studio's combined parcel, freight for q = unit + (q − 1) · max(0, unit − 3.72). Not a parcel per unit.
  3. kitchen-sconce-aliexpress-rustic-wooden-wall-sconce-632957 is one unit (the Studio inferred 4 from the record).
  4. Variants, colours and sizes stay in the worst case; an estimated freight is taken at its worst case.
  5. Proposed price = max(current, no-loss), rounded up to an ending in 9. Never lower.

The Studio formula (studio/src/index.html econCalc; site/shared/src/pricing.ts unitEconomics is the same formula):
    net = P / (1 + vat)            fees = P * card_pct + card_fixed       reserve = net * returns_pct
    landed = (unit cost * q + freight for q) * usd_ils
    contribution = net - landed - fees - reserve - packaging            margin = contribution / net
The customer's delivery fee (₪29 under ₪299) is not revenue in the Studio formula, so it is not counted here either.

What the Studio sells is read the way the Studio reads it: studio/build.py is imported and its own loaders run
(load_products, sell_qty_default, lead_records, load_economics), so the unit count, the cost of the sale, the freight
source and the starting price are exactly the Studio's.

Scenarios of one product (every one must give a contribution >= 0), all by the default shipping method:
  * the sale (the units the Studio sells, sell_qty), freight by the combined-parcel formula (a real quote for exactly
    those units, when one exists, is taken as it is);
  * one piece of a set (ה.6, P1: a set is also sold singly), at unit_retail_ils or the site's estimate
    (site/shared/src/packs.ts unitPriceEstimateIls), with the freight of one piece;
  * every other supplier option in stock (card `options.skus`, USD), at the price the site gives it
    (site/shared/src/options.ts skuRetail: the room SKU's price moved by the difference of the 40% recommendations,
    or the Studio's sku_retail_ils), with its own cost and freight, and its single piece;
  * more than one sale in a cart is never worse per sale (the combined parcel is at most the sum of the parts).
Freight: every quote of the default method found for the room SKU (the Studio's freight file or card SKU, the pricing
team's manual figure, the cached supplier answers in data/sources, the final-round record) and the highest of them.
A product with no quote at all takes the worst of the estimates written for it (card notes, the pricing file, the
final round) and is flagged.

  python3 -I scripts/economics/no_loss.py                     # audit, summary on stdout
  python3 -I scripts/economics/no_loss.py --json FILE         # the full audit as JSON
  python3 -I scripts/economics/no_loss.py --report            # report mode: writes data/economics/no-loss-report-<date>.json
                                                              # and .md, touches no data
  python3 -I scripts/economics/no_loss.py --check             # invariants of the computation; exit 1 when a product (not
                                                              # owner-set, not express-only) loses at its current price,
                                                              # exit 2 when an invariant fails
  python3 -I scripts/economics/no_loss.py --apply             # the apply brief (manager's policy, 2026-10-20): raise the headline
                                                              # prices in their source of truth and write
                                                              # data/economics/no-loss-changes-<date>.json
  python3 -I scripts/economics/no_loss.py --audit [--tests F] # after the apply: data/economics/no-loss-audit-<date>.json and .md
                                                              # (F: a JSON of test results to include)
  --db DIR      a Studio db export (DIR/product_edits/<id>.json): prices the owner set there are never changed
  --date YYYY-MM-DD   the date written on the reports (default: today)

Importable: audit(), product_scenarios(), worst_case(), no_loss_price(), break_even_price(), contribution(),
rejected_loss_only(). Only the standard library. Reads cached data only; no supplier is contacted.
"""
from __future__ import annotations

import contextlib
import datetime as dt
import glob
import importlib.util
import io
import json
import math
import os
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
ECO = ROOT / "data" / "economics"
SOURCES = ROOT / "data" / "sources"
FINAL = ROOT / "data" / "leads" / "final-2026-10-13"
BUILD_PY = ROOT / "studio" / "build.py"
COVERAGE_PY = ROOT / "scripts" / "sourcing" / "final_round_coverage.py"
PRICING_FILES = ("living-room-2026-10-11.json", "other-rooms-2026-10-11.json")

# The Studio's defaults (studio/src/index.html ECON_META); data/economics/settings.json `economics` overrides them.
STUDIO_DEFAULTS = {"usd_ils": 3.3, "vat_pct": 18, "card_pct": 2, "card_fixed_ils": 1.2, "returns_pct": 8, "cac_ils": 100,
                   "packaging_ils": 0, "target_margin_pct": 40, "items_per_order": 1.4}
PARCEL_FIXED_USD = 3.72  # the Studio's per-parcel fixed part (CJ basket test, freight-bundles.json)
UNIT_PREMIUM = 1.15      # site/shared/src/packs.ts: one piece of a set costs 15% more per piece
VAT_THRESHOLD_ILS = 247  # $75 x 3.3: the personal-import VAT exemption (docs/tax/README.md); counted before and after
EPS = 1e-9

# Units of the sale fixed by the manager (2026-10-20, correction rule 3), where the Studio's own reading is wrong.
UNIT_OVERRIDES = {
    "kitchen-sconce-aliexpress-rustic-wooden-wall-sconce-632957":
        (1, "המנהל (2026-10-20): מנורת מטבח אחת, לא 4. הסטודיו הסיק 4 יח' מעלות הנחיתה ברשומה (₪100.6 = יחידה אחת + משלוח)"),
}


# --------------------------------------------------------------------------- formula

def isnum(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def load_settings(eco_dir: Path = ECO) -> dict:
    s = dict(STUDIO_DEFAULTS)
    try:
        f = json.loads((eco_dir / "settings.json").read_text(encoding="utf-8"))
        for k, v in ((f or {}).get("economics") or {}).items():
            if k in s and isnum(v):
                s[k] = v
    except FileNotFoundError:
        pass
    return s


def contribution(price_ils: float, landed_ils: float, s: dict) -> float:
    """The Studio formula, per sale, before CAC."""
    net = price_ils / (1 + s["vat_pct"] / 100)
    fees = price_ils * s["card_pct"] / 100 + s["card_fixed_ils"]
    return net - landed_ils - fees - net * s["returns_pct"] / 100 - s["packaging_ils"]


def margin(price_ils: float, landed_ils: float, s: dict) -> float | None:
    net = price_ils / (1 + s["vat_pct"] / 100)
    return contribution(price_ils, landed_ils, s) / net if net > 0 else None


def break_even_for(landed_ils: float, s: dict) -> float:
    """The price (continuous) whose contribution is exactly zero for this landed cost."""
    k = (1 - s["returns_pct"] / 100) / (1 + s["vat_pct"] / 100) - s["card_pct"] / 100
    return (landed_ils + s["card_fixed_ils"] + s["packaging_ils"]) / k


def charm_up(x: float) -> int:
    """The lowest whole price that ends in 9 and is >= x (site/shared/src/pricing.ts charmRoundUpIls)."""
    up = math.ceil(x - 1e-9)
    r = up % 10
    return up if r == 9 else up + (9 - r + 10) % 10


def charm_down(x: float) -> int:
    n = math.floor(x + 1e-9)
    return n - ((n - 9) % 10 + 10) % 10


def unit_price_estimate(set_ils: float, n: int) -> int:
    """site/shared/src/packs.ts unitPriceEstimateIls: one piece of a set of n sold at set_ils."""
    per_piece = math.ceil(set_ils / n - 1e-9)
    est = charm_down(math.ceil(set_ils / n * UNIT_PREMIUM - 1e-9))
    return est if est >= per_piece else charm_up(per_piece)


def recommended(landed_ils: float, s: dict) -> int | None:
    """site/shared/src/pricing.ts recommendedRetailIls: the lowest ...9 price at the target margin."""
    den = (1 - s["returns_pct"] / 100 - s["target_margin_pct"] / 100) / (1 + s["vat_pct"] / 100) - s["card_pct"] / 100
    return charm_up((landed_ils + s["card_fixed_ils"] + s["packaging_ils"]) / den) if den > 0 else None


def ship_for_qty(unit_usd: float, q: int) -> float:
    """The Studio's combined parcel (shipForQty): unit + (q - 1) * max(0, unit - 3.72)."""
    return unit_usd + (q - 1) * max(0.0, unit_usd - PARCEL_FIXED_USD)


def inv_ship_for_qty(q_usd: float, n: int) -> float:
    """One piece's freight from a quote for n pieces, by the Studio's combined-parcel formula (shipForQty inverted)."""
    if n <= 1:
        return q_usd
    u = (q_usd + (n - 1) * PARCEL_FIXED_USD) / n
    return u if u >= PARCEL_FIXED_USD else q_usd


# --------------------------------------------------------------------------- the Studio's view

class Ctx:
    """The Studio's own reading of the repo: cards, sell quantities, economics entries (studio/build.py loaders)."""

    def __init__(self, eco_dir: Path = ECO, db: Path | None = None):
        self.eco_dir = eco_dir
        self.db = db
        self.s = load_settings(eco_dir)
        spec = importlib.util.spec_from_file_location("studio_build_for_no_loss", BUILD_PY)
        B = importlib.util.module_from_spec(spec)
        log = io.StringIO()
        with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
            spec.loader.exec_module(B)
            plan = B.read_json(B.ROOT / "docs" / "house-plan.json")
            order, rooms = B.load_rooms(plan)
            slots = B.load_slots(order, rooms)
            products = B.load_products(set(order))
            B.mark_duplicates(products)
            B.attach_candidates(slots, products)
            self.slot_by_key = {x["key"]: x for rows in slots.values() for x in rows}
            recs = B.lead_records()
            for p in products:
                p["_lead_rec"] = recs.get(p["id"])
                p["_sell_qty"] = B.sell_qty_default(p, self.slot_by_key)
            self.eco = B.load_economics(eco_dir, products)
        self.build_log = log.getvalue()
        self.B = B
        self.products = products
        self.by_id = {}
        for p in products:
            self.by_id.setdefault(p["id"], p)  # the first card wins a duplicate id, as in the Studio
        self.E = self.eco["products"]
        self.rows = self._read_json(eco_dir / "products.json").get("products") or {}
        self.pricing = {}
        for f in PRICING_FILES:
            d = self._read_json(eco_dir / "pricing" / f)
            for k, v in (d.get("products") or {}).items():
                if isinstance(v, dict):
                    self.pricing[k] = v
        self.freight_files = {}
        for f, src in (("freight-cj.json", "cj"), ("freight-zendrop.json", "zendrop"), ("freight-aliexpress.json", "aliexpress")):
            self.freight_files[src] = self._read_json(eco_dir / f).get("products") or {}
        self.owner_edits = self._owner_edits(db)

    @staticmethod
    def _read_json(p: Path) -> dict:
        try:
            d = json.loads(Path(p).read_text(encoding="utf-8"))
            return d if isinstance(d, dict) else {}
        except FileNotFoundError:
            return {}

    def _owner_edits(self, db: Path | None) -> dict:
        """id -> the retail price the owner set in the Studio (db product_edits, or retail_src "studio" in products.json)."""
        out = {}
        for k, v in self.rows.items():
            if isinstance(v, dict) and v.get("retail_src") == "studio" and isnum(v.get("retail_ils")):
                out[k] = {"retail_ils": v["retail_ils"], "where": "data/economics/products.json (retail_src studio)"}
        if db and Path(db).is_dir():
            for f in sorted(Path(db, "product_edits").glob("*.json")):
                try:
                    d = json.loads(f.read_text(encoding="utf-8"))
                except Exception:
                    continue
                r = (((d or {}).get("fields") or {}).get("economics") or {}).get("retail_ils")
                if isnum(r):
                    out[f.stem] = {"retail_ils": r, "where": f"Studio db product_edits/{f.name}"
                                   + (f" (synced {d.get('synced_at')})" if d.get("synced") else " (not synced)"),
                                   "history": d.get("history") or []}
        return out


# --------------------------------------------------------------------------- freight evidence

def _ae_item(url: str) -> str | None:
    m = re.search(r"aliexpress\.[a-z.]+/item/(\d+)\.html", url or "", re.I)
    return m.group(1) if m else None


def _cj_pid(url: str) -> str | None:
    m = re.search(r"-p-([^./?#]+)\.html", url or "")
    return m.group(1) if m else None


_SRC_CACHE: dict = {}


def source_quotes(kind: str, pid: str | None) -> dict:
    """{(sku or vid, qty): [{usd, days, name, tracking}]} from the cached supplier answers (data/sources/<kind>/<id>.json)."""
    if not pid:
        return {}
    key = (kind, pid)
    if key in _SRC_CACHE:
        return _SRC_CACHE[key]
    out = {}
    f = SOURCES / kind / f"{pid}.json"
    if f.exists():
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            d = {}
        for k, sec in ((d or {}).get("sections") or {}).items():
            m = re.match(r"freight:([^:]+):IL:(\d+)$", k)
            if not m or not isinstance(sec, dict):
                continue
            pl = sec.get("payload") or {}
            opts = []
            for o in pl.get("options") or []:
                if not isinstance(o, dict):
                    continue
                if kind == "aliexpress":
                    if str(o.get("currency") or "USD").upper() != "USD" or not isnum(o.get("fee")):
                        continue
                    dmax = o.get("days_max")
                    opts.append({"usd": float(o["fee"]), "days": f"{o.get('days_min')}-{dmax}" if dmax else None,
                                 "name": o.get("company") or o.get("code"), "tracking": o.get("tracking")})
                elif isnum(o.get("usd")):
                    opts.append({"usd": float(o["usd"]), "days": o.get("days"), "name": o.get("name")})
            if opts:
                out[(m.group(1), int(m.group(2)))] = opts
    _SRC_CACHE[key] = out
    return out


def cj_vid(cpid: str, variant_sku: str) -> str | None:
    """The CJ vid of a variant SKU, from the cached product answer (data/sources/cj/<pid>.json)."""
    f = SOURCES / "cj" / f"{cpid}.json"
    if not (variant_sku and f.exists()):
        return None
    try:
        pl = ((json.loads(f.read_text(encoding="utf-8")).get("sections") or {}).get("product") or {}).get("payload") or {}
    except Exception:
        return None
    for v in pl.get("variants") or []:
        if isinstance(v, dict) and str(v.get("variantSku") or "") == variant_sku and v.get("vid"):
            return str(v["vid"])
    return None


def _est_from_text(text: str) -> float | None:
    """'Shipping to IL: ... 1.99 USD' / '$23.39' in a card's notes (studio/build.py card_ship), USD."""
    m = re.search(r"shipping to IL\s*:", text or "", re.I)
    if not m:
        return None
    seg = text[m.end():m.end() + 160]
    a = re.search(r"\$\s*(\d+(?:\.\d+)?)|(\d+(?:\.\d+)?)\s*USD", seg)
    return float(a.group(1) or a.group(2)) if a else None


# an express line: DHL, UPS, FedEx, TNT, EMS, Aramex, "Premium", CJ To Door, "...Express" (not AliExpress itself)
EXPRESS_RX = re.compile(r"\bDHL\b|fedex|\bUPS\b|\bTNT\b|\bEMS\b|aramex|premium|to\s*door|(?<!ali)express", re.I)


def is_express(name) -> bool:
    return bool(EXPRESS_RX.search(str(name or "")))


def default_quote(options: list[dict]) -> dict | None:
    """The method we ship with by default (correction rule 1): the cheapest method to Israel, tracked where the supplier
    offers tracking; an express line only when it is the only method. {usd, label, express, free} or None."""
    ok = [o for o in options if isinstance(o, dict) and isnum(o.get("usd"))]
    if not ok:
        return None
    tracked = [o for o in ok if o.get("tracking") is True]
    pool = tracked if tracked and any(o.get("tracking") is False for o in ok) else ok
    std = [o for o in pool if not is_express(o.get("name"))]
    pick = min(std or pool, key=lambda o: o["usd"])
    return {"usd": float(pick["usd"]), "label": f"{pick.get('name') or ''} {pick.get('days') or ''}".strip(),
            "express": not std, "free": float(pick["usd"]) == 0.0}


def freight(p: dict, e: dict, ctx: Ctx, n: int) -> dict:
    """The room SKU's freight by the default method: one piece, the sale of n pieces (the combined parcel unless a real
    quote for n pieces exists), and one piece of the set; where each number comes from and whether it is an estimate.
    Every quote of that method found (the Studio's freight file or card SKU, the manual figure, the cached supplier
    answers) is read and the highest one is taken (an estimate at its worst case)."""
    pid, flags, notes = p["id"], [], []
    fr = e.get("freight") or {}
    manual = (e.get("manual") or {}).get("shipping_cost_usd")
    unit, sale = [], []   # [(usd, source, express, free)] for ONE piece / for exactly n pieces (n > 1)
    if fr.get("status") == "no_route":
        return {"no_route": True, "flags": ["no-route"], "notes": [f"{fr.get('src')}: אין משלוח לישראל"]}
    qq = int(fr.get("quoted_qty") or 1)
    raw = (ctx.freight_files.get(fr.get("src")) or {}).get(pid) if fr.get("src") in ("cj", "zendrop", "aliexpress") else None
    opts = [o for o in (raw or {}).get("options") or [] if isinstance(o, dict)]
    if not opts:
        opts = [o for o in (fr.get("cheapest"), fr.get("under20")) if isinstance(o, dict)]
    dq = default_quote(opts)
    if dq:
        src = f"הסטודיו ({fr.get('src')}): {dq['label']}"
        if qq > 1 and qq == n:
            sale.append((dq["usd"], src + f" (ל-{qq} יח')", dq["express"], dq["free"]))
        elif qq > 1:
            # quoted for another count of pieces (a set of 4 pegs sold as one unit): the Studio takes it as the unit's
            # freight (effProduct: quotedForSale only when quoted_qty == the units sold), and so does this
            unit.append((dq["usd"], src + f" (הוצע ל-{qq} יח'; נלקח ליחידת מכירה, כמו בסטודיו)", dq["express"], dq["free"]))
            flags.append("freight-quote-other-qty")
        else:
            unit.append((dq["usd"], src, dq["express"], dq["free"]))
    if isnum(manual):
        unit.append((float(manual), "ידני (data/economics/products.json shipping_cost_usd)", False, float(manual) == 0.0))
    from_cache = not unit and not sale
    sup = p.get("supplier") or {}
    url = sup.get("product_url") or ""
    o = p.get("options") if isinstance(p.get("options"), dict) else {}
    room_sku = str(o.get("default_sku") or sup.get("sku") or "")
    cache = []
    ae = _ae_item(url)
    if ae:
        cache += [(f"מטמון AliExpress {ae} sku {sku}", qty, os_) for (sku, qty), os_ in source_quotes("aliexpress", ae).items()
                  if sku == room_sku]
    cj_entry = ctx.freight_files.get("cj", {}).get(pid) or {}
    cpid, vid = cj_entry.get("pid") or _cj_pid(url), cj_entry.get("vid")
    if cpid and not vid:
        vid = cj_vid(cpid, room_sku)
    if cpid and vid:
        cache += [(f"מטמון CJ vid {v}", qty, os_) for (v, qty), os_ in source_quotes("cj", cpid).items() if v == str(vid)]
    n_cache = 0
    for lab, qty, os_ in cache:
        d = default_quote(os_)
        if not d:
            continue
        if qty == 1:
            unit.append((d["usd"], f"{lab} ×1: {d['label']}", d["express"], d["free"]))
        elif qty == n:
            sale.append((d["usd"], f"{lab} ×{qty}: {d['label']}", d["express"], d["free"]))
        else:
            continue
        n_cache += 1
    if from_cache and n_cache:
        flags.append("freight-from-cache-only")
        notes.append("לסטודיו אין משלוח למוצר; נלקח ממטמון הספק")
    m_other = re.search(r"estimated from SKU (\d+)", p.get("notes") or "")
    if m_other and m_other.group(1) != room_sku and not any("מטמון" in x[1] for x in unit):
        flags.append("freight-from-other-sku")
        notes.append(f"המשלוח נמדד על מק\"ט אחר ({m_other.group(1)}), לא על המק\"ט שבחדר: הערכה")
    estimated = False
    if not unit and not sale:
        # no quote at all: the worst of the estimates written for this product
        ests = []
        tx = _est_from_text(p.get("notes") or "")
        if tx is not None:
            ests.append((tx, "הערות הכרטיס (הערכה)", False, tx == 0.0))
        pr = ctx.pricing.get(pid) or {}
        if isnum(pr.get("ship_usd_per_unit_used")):
            ests.append((float(pr["ship_usd_per_unit_used"]), f"קובץ התמחור: {str(pr.get('ship_src_used') or '')[:80]} (הערכה)", False, False))
        rec = (p.get("_lead_rec") or {}).get("rec") or {}
        if isnum(rec.get("ship_usd")) and rec["ship_usd"] >= 0:
            rq = next((int(rec[k]) for k in ("qty_in_sale", "qty") if isnum(rec.get(k)) and rec[k] >= 1), 1)
            src = f"הליקוט האחרון {p['_lead_rec'].get('file')} (ל-{rq} יח', הערכה)"
            exp = is_express(f"{rec.get('why_he') or ''} {rec.get('price_basis_he') or ''}") and "To Door" in f"{rec.get('why_he')}{rec.get('price_basis_he')}"
            if rq == 1:
                ests.append((float(rec["ship_usd"]), src, exp, False))
            elif rq == n:
                sale.append((float(rec["ship_usd"]), src, exp, False))
        if ests:
            unit.append(max(ests, key=lambda x: x[0]))
            notes.append("משלוח מוערך: " + "; ".join(f"${x[0]:g} {x[1]}" for x in ests))
        if ests or sale:
            estimated = True
            flags.append("freight-estimated")
    out = {"no_route": False, "flags": flags, "notes": notes, "estimated": estimated,
           "all_quotes": [{"usd": round(x[0], 4), "src": x[1], "express": x[2], "for_units": 1} for x in unit]
                         + [{"usd": round(x[0], 4), "src": x[1], "express": x[2], "for_units": n} for x in sale]}
    # an express quote counts only when no standard quote exists (the express line is then the only method)
    std_u, std_s = [x for x in unit if not x[2]], [x for x in sale if not x[2]]
    express_only = not std_u and not std_s and bool(unit or sale)
    if not express_only:
        unit, sale = std_u, std_s
    u = max(unit, key=lambda x: x[0]) if unit else None
    sq = max(sale, key=lambda x: x[0]) if sale else None
    if u is None and sq is None:
        out["missing"] = True
        out["flags"].append("freight-missing")
        return out
    if n == 1:
        sale_usd, sale_src, sale_est = u[0], u[1], False
    elif sq is not None:
        sale_usd, sale_src, sale_est = max(sq[0], u[0] if u else 0.0), sq[1], False
    else:  # the Studio's combined parcel for n pieces (correction rule 2)
        sale_usd, sale_src, sale_est = ship_for_qty(u[0], n), f"{u[1]}, ל-{n} יח' בחבילה משולבת (יחידה + (n−1) × max(0, יחידה − $3.72))", True
    if u is not None:
        single_usd, single_src, single_est = u[0], u[1], False
    else:  # only a quote for the whole set: one piece by the same formula, inverted
        single_usd, single_src, single_est = inv_ship_for_qty(sq[0], n), sq[1] + " (ליחידה לפי נוסחת החבילה)", True
    bound = u or sq
    out["method"] = {"label": bound[1], "express": bound[2], "free": bound[3],
                     "unit_usd": round(u[0], 4) if u else None, "unit_src": u[1] if u else None,
                     "sale_usd": round(sale_usd, 4), "sale_src": sale_src, "sale_estimated": sale_est,
                     "single_usd": round(single_usd, 4), "single_src": single_src, "single_estimated": single_est}
    out["express_only"] = express_only
    if express_only:
        out["flags"].append("express-only")
        notes.append("לספק אין במוצר הזה שיטה רגילה: המשלוח היחיד הוא אקספרס (" + bound[1] + (", חינם" if bound[3] else "") + ")")
    if n > 1 and sale_est:
        out["flags"].append("qty-freight-estimated")
    return out


# --------------------------------------------------------------------------- scenarios

def price_source(p: dict, e: dict, ctx: Ctx) -> dict:
    """Where the product's retail price lives (the real source of truth for it)."""
    pid = p["id"]
    if pid in ctx.owner_edits:
        o = ctx.owner_edits[pid]
        return {"kind": "owner", "where": o["where"], "retail_ils": o["retail_ils"]}
    if pid in ctx.rows and isnum((ctx.rows[pid] or {}).get("retail_ils")):
        return {"kind": "products.json", "where": "data/economics/products.json", "field": f"products.{pid}.retail_ils",
                "retail_ils": ctx.rows[pid]["retail_ils"]}
    src = str(e.get("retail_src") or "")
    if src == "initial-card":
        pr = p.get("price") or {}
        fld = "retail_ils" if isnum(pr.get("retail_ils")) and pr["retail_ils"] > 0 else "suggested_retail"
        return {"kind": "card", "where": p["_path"], "field": f"price.{fld}", "retail_ils": e.get("retail_ils")}
    if src.startswith("initial-leads"):
        lr = p.get("_lead_rec") or {}
        return {"kind": "leads", "where": f"data/leads/final-2026-10-13/results/{lr.get('file')}", "field": "price_ils",
                "retail_ils": e.get("retail_ils"), "card": p["_path"]}
    return {"kind": "none", "where": None, "retail_ils": None}


SET_RX = re.compile(r"זוג|סט|לשניים|לשלושה|ל-\d|\d\s*יח|[×x]\s*\d|\d\s*[×x]\b|\bpair\b|\bset\b|\d-piece|\bpcs\b", re.I)


def highest_comp(p: dict, e: dict, ctx: Ctx, n: int) -> tuple[float | None, str | None]:
    """The highest Israeli comparable for the whole sale: the pricing team's il_value.high (already for the sale), else
    the highest comparable, where a comparable for one piece counts n times in a sale of n (a final-round comparable is
    per piece unless its title says pair / set / x2)."""
    iv = (ctx.rows.get(p["id"]) or {}).get("il_value") or e.get("il_value") or {}
    if isnum(iv.get("high")) and iv["high"] > 0:
        return float(iv["high"]), "il_value.high"
    comps = [(c.get("price"), str(c.get("title") or "")) for c in iv.get("comps") or [] if isinstance(c, dict)]
    rec = (p.get("_lead_rec") or {}).get("rec") or {}
    for c in rec.get("comps") or []:
        if isinstance(c, dict):
            price = next((c[k] for k in ("price_ils", "price") if isnum(c.get(k))), None)
            comps.append((price, str(c.get("title") or c.get("name") or c.get("shop_title") or "")))
    comps = [(x, tt) for x, tt in comps if isnum(x) and x > 0]
    if not comps:
        return None, None
    if n > 1 and p["id"] not in ctx.rows:
        best = max(x if SET_RX.search(tt) else x * n for x, tt in comps)
        return float(best), f"ההשוואה הגבוהה למכירה ({n} יח'; השוואה ליחידה × {n})"
    return float(max(x for x, _ in comps)), "ההשוואה הגבוהה"


def _sku_cost(card_unit: float, default_sku: float, sku: float) -> float:
    """site/shared/src/options.ts skuCostCents, in USD."""
    if not default_sku > 0:
        return sku
    if abs(card_unit - default_sku) <= max(0.01, card_unit * 0.005):
        return sku
    ratio = card_unit / default_sku
    k = round(ratio)
    if k >= 2 and abs(ratio - k) <= 0.02 * k:
        return sku * k
    return max(0.0, card_unit + (sku - default_sku))


ROOM_SKU_HE = "המק\"ט שבחדר"


def product_scenarios(p: dict, e: dict, ctx: Ctx, n_override: int | None = None) -> dict:
    """Inputs and scenarios of one product. Each scenario: {id, kind, quantity, variant, variant_sku, method, label_he,
    landed_ils, freight_usd, freight_src, estimated, price(P) -> the price it is sold at when the product is priced P}."""
    s = ctx.s
    fx = s["usd_ils"]
    pid = p["id"]
    sq = e.get("sell_qty")
    n = int(sq) if isnum(sq) and sq >= 1 else int((p.get("_sell_qty") or {}).get("qty") or 1)
    pr = p.get("price") or {}
    flags, notes = [], []
    if not (isnum(sq) and sq >= 1) and n > 1 and "לפי עלות הנחיתה" in str((p.get("_sell_qty") or {}).get("reason") or ""):
        # the Studio read the units of the sale off the record's landed cost (studio/build.py lead_qty), not off a qty field
        flags.append("qty-inferred-from-landed")
    studio_n = n
    if pid in UNIT_OVERRIDES and n_override is None:
        n, why = UNIT_OVERRIDES[pid]
        flags.append("unit-override")
        notes.append(f"כמות המכירה נקבעה ל-{n} (הסטודיו: {studio_n}): {why}")
    if n_override:
        n = n_override
    cur = str(pr.get("currency") or "USD").upper()
    sale_cost = e.get("sale_cost_usd") if isnum(e.get("sale_cost_usd")) and e["sale_cost_usd"] > 0 else None
    if cur != "USD" and sale_cost is None:
        return {"n": n, "studio_n": studio_n, "missing": f"עלות במטבע {cur}, לא בדולר", "flags": ["cost-not-usd"], "scenarios": []}
    unit_cost = sale_cost / n if sale_cost is not None else pr.get("cost")
    if not isnum(unit_cost):
        return {"n": n, "studio_n": studio_n, "missing": "אין עלות", "flags": ["cost-missing"], "scenarios": []}
    unit_cost = float(unit_cost)
    cost_src = ("עלות המכירה מקובץ התמחור" if e.get("sale_cost_src") == "pricing" else
                "עלות המכירה מהליקוט" if e.get("sale_cost_src") == "leads" else "עלות הכרטיס")
    if e.get("sale_cost_src") == "leads":
        flags.append("sale-cost-from-leads")
    row = ctx.rows.get(pid) or {}
    if isnum(row.get("price_for_qty")) and int(row["price_for_qty"]) != n:
        flags.append("price-qty-mismatch")
        notes.append(f"המחיר בקובץ התמחור הוא ל-{int(row['price_for_qty'])} יח', והמכירה כאן היא {n} יח'")
    fr = freight(p, e, ctx, n)
    flags += fr["flags"]
    notes += fr["notes"]
    if fr.get("no_route"):
        return {"n": n, "studio_n": studio_n, "missing": "הספק לא שולח לישראל", "flags": flags, "notes": notes, "scenarios": []}
    if fr.get("missing"):
        return {"n": n, "studio_n": studio_n, "missing": "אין משלוח ואין הערכה", "flags": flags, "notes": notes, "scenarios": []}
    fm = fr["method"]
    unit_retail = row.get("unit_retail_ils")
    unit_retail = unit_retail if isnum(unit_retail) and unit_retail > 0 else None
    scen = [{"id": "sale", "kind": "sale", "quantity": n, "variant": ROOM_SKU_HE, "variant_sku": None, "method": fm["label"],
             "label_he": f"המכירה ({n} יח'), {ROOM_SKU_HE}", "landed_ils": (unit_cost * n + fm["sale_usd"]) * fx,
             "freight_usd": fm["sale_usd"], "freight_src": fm["sale_src"], "estimated": fm["sale_estimated"], "price": lambda P: P}]
    if n > 1:
        up = (lambda P, n=n: unit_retail) if unit_retail else (lambda P, n=n: unit_price_estimate(P, n))
        scen.append({"id": "single", "kind": "single", "quantity": 1, "variant": ROOM_SKU_HE, "variant_sku": None, "method": fm["label"],
                     "label_he": "יחידה אחת מהסט" + ("" if unit_retail else " (מחיר היחידה: ההערכה של האתר)"),
                     "landed_ils": (unit_cost + fm["single_usd"]) * fx, "freight_usd": fm["single_usd"],
                     "freight_src": fm["single_src"], "estimated": fm["single_estimated"], "price": up})
    # the other supplier options, at the price the site gives them (skuRetail with the Studio's price)
    o = p.get("options") if isinstance(p.get("options"), dict) else None
    n_var = 0
    if o and sale_cost is not None and n > 1:
        # a mixed set (the sale's cost is not n x the room SKU's: plates, side plates and bowls, two of each): the card's
        # options are the set's parts, not variants of the sale, so they are not priced as the sale
        flags.append("options-are-set-parts")
        o = None
    elif o and sale_cost is not None:
        # the sale's cost is not the room SKU's (a shade with its suspension set, a pitcher with its jar): the site prices
        # each option on that sale cost moved by the SKU difference (skuCostCents), and so does this; check that the
        # options are variants of the sale and not its parts
        flags.append("options-with-sale-cost")
        notes.append("עלות המכירה אינה עלות המק\"ט שבחדר: מחיר האפשרויות חושב על עלות המכירה כמו באתר; לבדוק שהאפשרויות הן וריאנטים ולא חלקי הסט")
    if o and cur == "USD":
        skus = [x for x in o.get("skus") or [] if isinstance(x, dict)]
        dflt = next((x for x in skus if x.get("id") == o.get("default_sku")), None)
        dprice = ((dflt or {}).get("price") or {})
        if dflt and str(dprice.get("currency") or "").upper() == "USD" and isnum(dprice.get("amount")):
            dq = (dflt.get("shipping_il") or {})
            eco_unit = fm["single_usd"]
            rec_d = recommended((unit_cost + eco_unit) * n * fx, s)
            ae = _ae_item((p.get("supplier") or {}).get("product_url") or "")
            cache = source_quotes("aliexpress", ae) if ae else {}
            for x in skus:
                if x is dflt:
                    continue
                xp = x.get("price") or {}
                if str(xp.get("currency") or "").upper() != "USD" or not isnum(xp.get("amount")):
                    continue
                if x.get("stock") == 0:
                    continue  # out of stock: the site does not sell it
                xc = _sku_cost(unit_cost, float(dprice["amount"]), float(xp["amount"]))
                xq = x.get("shipping_il") or {}
                delta = 0.0
                if isnum(xq.get("amount")) and isnum(dq.get("amount")) and str(xq.get("currency")).upper() == str(dq.get("currency")).upper() == "USD":
                    delta = float(xq["amount"]) - float(dq["amount"])
                site_unit = max(0.0, eco_unit + delta)
                rec_x = recommended((xc + site_unit) * n * fx, s)
                ov = (row.get("sku_retail_ils") or {}).get(str(x.get("id")))
                if isnum(ov) and ov > 0:
                    xprice = (lambda P, v=ov: v)
                elif rec_x is None or rec_d is None:
                    continue
                else:
                    xprice = (lambda P, rx=rec_x, rd=rec_d: (P + (rx - rd)) if P + (rx - rd) > 0 else rx)
                n_var += 1
                # the SKU's own quote in the cache, by the default method (its worst case against the room SKU's moved quote)
                own = None
                for (sku, qty), opts in cache.items():
                    if sku == str(x.get("id")) and qty == 1:
                        own = default_quote(opts)
                lab = ", ".join(f"{k}={v}" for k, v in (x.get("values") or {}).items())[:80]
                u = max(0.0, fm["single_usd"] + delta)
                sale_usd = max(0.0, fm["sale_usd"] + n * delta)
                if own and not own["express"]:
                    u = max(u, own["usd"])
                    sale_usd = max(sale_usd, ship_for_qty(own["usd"], n))
                scen.append({"id": f"variant/{x.get('id')}", "kind": "variant", "quantity": n, "variant": lab, "variant_sku": x.get("id"),
                             "method": fm["label"], "label_he": f"אפשרות {lab} ({n} יח'; מחיר האפשרות לפי האתר)",
                             "landed_ils": (xc * n + sale_usd) * fx, "freight_usd": sale_usd,
                             "freight_src": "ההפרש של המק\"ט + " + str(fm["single_src"]), "estimated": n > 1 or not own,
                             "price": xprice})
                if n > 1:
                    scen.append({"id": f"variant-single/{x.get('id')}", "kind": "variant-single", "quantity": 1, "variant": lab,
                                 "variant_sku": x.get("id"), "method": fm["label"], "label_he": f"יחידה אחת, אפשרות {lab}",
                                 "landed_ils": (xc + u) * fx, "freight_usd": u, "freight_src": "ההפרש של המק\"ט", "estimated": True,
                                 "price": (lambda P, f=xprice, n=n: unit_price_estimate(f(P), n))})
    studio = studio_shown(p, e, ctx, studio_n, unit_cost if sale_cost is None else sale_cost / studio_n)
    return {"n": n, "studio_n": studio_n, "unit_cost_usd": unit_cost, "cost_src": cost_src, "freight": fr, "scenarios": scen,
            "flags": sorted(set(flags)), "notes": notes, "variants": n_var, "studio": studio, "unit_retail_ils": unit_retail}


def studio_shown(p: dict, e: dict, ctx: Ctx, n: int, unit_cost: float) -> dict | None:
    """The Studio's own default reading (shipping method 'cheapest'): econCalc + shipForQty, as on its product card."""
    fr = e.get("freight") or {}
    man = (e.get("manual") or {}).get("shipping_cost_usd")
    o = None if fr.get("status") == "no_route" else (fr.get("cheapest") or fr.get("under20"))
    if isnum(man):
        usd, src, qfs = float(man), "manual", False
    elif isinstance(o, dict) and isnum(o.get("usd")):
        usd, src = float(o["usd"]), fr.get("src")
        qfs = int(fr.get("quoted_qty") or 0) == n
    else:
        return None
    tot = usd if qfs else (ship_for_qty(usd, n) if n > 1 else usd)
    return {"units": n, "freight_usd": round(tot, 4), "src": src, "landed_ils": (unit_cost * n + tot) * ctx.s["usd_ils"]}


def worst_case(P: float, scen: list[dict], s: dict) -> tuple[float, dict | None, float | None]:
    """(lowest contribution over the scenarios at price P, that scenario, the price it is sold at)."""
    best = (math.inf, None, None)
    for x in scen:
        R = x["price"](P)
        c = contribution(R, x["landed_ils"], s)
        if c < best[0]:
            best = (c, x, R)
    return best


def _pick(scen, kinds=None):
    return [x for x in scen if kinds is None or x["kind"] in kinds]


def no_loss_price(P0: float | None, scen: list[dict], s: dict, kinds: set | None = None) -> int | None:
    """The lowest price >= P0 (never lower) on the ...9 endings with a contribution >= 0 in every scenario."""
    sc = _pick(scen, kinds)
    if not sc:
        return None
    if P0 and worst_case(P0, sc, s)[0] >= -EPS:
        return P0
    P = charm_up((P0 or 9) + (1 if P0 else 0))
    while P < 1_000_000:
        if worst_case(P, sc, s)[0] >= -EPS:
            return P
        P += 10
    return None


def break_even_price(scen: list[dict], s: dict, kinds: set | None = None) -> float | None:
    """The (continuous) product price at which the worst scenario breaks even."""
    sc = _pick(scen, kinds)
    if not sc:
        return None
    lo, hi = 0.0, 1.0
    while worst_case(hi, sc, s)[0] < 0 and hi < 1e7:
        hi *= 2
    for _ in range(60):
        mid = (lo + hi) / 2
        if worst_case(mid, sc, s)[0] >= 0:
            hi = mid
        else:
            lo = mid
    return round(hi, 2)


# --------------------------------------------------------------------------- scope

def _coverage_module():
    spec = importlib.util.spec_from_file_location("final_round_coverage_for_no_loss", COVERAGE_PY)
    m = importlib.util.module_from_spec(spec)
    cwd = os.getcwd()
    try:
        spec.loader.exec_module(m)  # it moves to the repo root; restored below
    finally:
        os.chdir(cwd)
    return m


def coverage_counted() -> dict:
    """card id -> [(slot, style)] the coverage script counts (final_round_coverage.py results() + the packs' picks)."""
    cwd = os.getcwd()
    out: dict = {}
    try:
        m = _coverage_module()
        os.chdir(ROOT)
        with contextlib.redirect_stderr(io.StringIO()):
            cards, _il, _q = m.results()
        for st, by_slot in cards.items():
            for slot, ids in by_slot.items():
                for cid in ids:
                    out.setdefault(cid, []).append((slot, st))
        for st in m.STYLES:
            pack = json.load(open(os.path.join(m.D, f"{st}.json")))
            for g in pack.get("gaps") or []:
                for pk in g.get("existing_picks") or []:
                    if pk.get("card_id"):
                        out.setdefault(pk["card_id"], []).append((g["slot"], st + " (pick)"))
    finally:
        os.chdir(cwd)
    return out


# --------------------------------------------------------------------------- audit

# The apply policy (manager, 2026-10-20, BRIEF "Apply"): the headline price is set by the room SKU, in its sale units, by
# the default shipping method. Variant prices the site derives (skuRetail) and the single-unit estimate are reported for
# SITE1 (the site floors a derived price at that variant's own no-loss price), not a reason to raise the headline.
HEADLINE_KINDS = {"sale"}


def _scen_out(x: dict, R: float, c: float, s: dict) -> dict:
    return {"scenario": x["id"], "kind": x["kind"], "label_he": x["label_he"], "method": x["method"], "quantity": x["quantity"],
            "variant": x["variant"], "variant_sku": x.get("variant_sku"), "sold_at_ils": R, "landed_ils": round(x["landed_ils"], 2),
            "freight_usd": round(x["freight_usd"], 4), "freight_src": x["freight_src"], "freight_estimated": x["estimated"],
            "contribution_ils": round(c, 2), "margin_pct": round(100 * (margin(R, x["landed_ils"], s) or 0), 1)}


def losing_derived(P: float, scen: list[dict], s: dict) -> list[dict]:
    """The site-derived scenarios (variants, single units) that lose at headline price P, each with its own no-loss price:
    the SITE1 floor (a derived price never below that variant's break-even, rounded to ...9)."""
    out = []
    for x in scen:
        if x["kind"] in HEADLINE_KINDS:
            continue
        R = x["price"](P)
        c = contribution(R, x["landed_ils"], s)
        if c < -EPS:
            be = break_even_for(x["landed_ils"], s)
            out.append(dict(_scen_out(x, R, c, s), own_no_loss_ils=charm_up(be), own_break_even_ils=round(be, 2)))
    return out


def audit(eco_dir: Path = ECO, db: Path | None = None, ctx: Ctx | None = None) -> dict:
    ctx = ctx or Ctx(eco_dir, db)
    s = ctx.s
    counted = coverage_counted()
    ids = []
    seen = set()
    for pid in list(ctx.rows.keys()) + sorted(counted) + sorted(p["id"] for p in ctx.products if "retail_ils" in ctx.E.get(p["id"], {})):
        if pid not in seen:
            seen.add(pid)
            ids.append(pid)
    rows = []
    for pid in ids:
        p = ctx.by_id.get(pid)
        scope = [k for k, ok in (("products.json", pid in ctx.rows), ("coverage", pid in counted),
                                 ("studio-price", p is not None and "retail_ils" in ctx.E.get(pid, {}))) if ok]
        if p is None:
            rows.append({"id": pid, "scope": scope, "status": "no-card", "flag": "cannot-compute", "missing": "אין כרטיס במוצרים",
                         "current_price_ils": (ctx.rows.get(pid) or {}).get("retail_ils")})
            continue
        e = ctx.E.get(pid, {})
        src = price_source(p, e, ctx)
        P0 = src.get("retail_ils")
        P0 = P0 if isnum(P0) and P0 > 0 else None
        sc = product_scenarios(p, e, ctx)
        r = {"id": pid, "card": p["_path"], "slot": p.get("_slot_key"), "scope": scope,
             "counted_in": sorted({f"{a}:{b}" for a, b in counted.get(pid, [])}),
             "price_source": {k: v for k, v in src.items() if k != "retail_ils"}, "current_price_ils": P0,
             "sale_units": sc["n"], "studio_units": sc.get("studio_n"), "flags": sc.get("flags", []), "notes": sc.get("notes", [])}
        if not sc["scenarios"]:
            r.update(status="cannot-compute", flag="cannot-compute", missing=sc.get("missing"))
            rows.append(r)
            continue
        scen = sc["scenarios"]
        n = sc["n"]
        fr = sc["freight"]
        express_only = bool(fr.get("express_only"))
        row = ctx.rows.get(pid) or {}
        # policy 3: a products.json price for one unit where the Studio sells more units: the sale price is price x units
        mismatch = (P0 is not None and "price-qty-mismatch" in sc["flags"] and isnum(row.get("price_for_qty"))
                    and int(row["price_for_qty"]) == 1 and n > 1)
        P_sale0 = P0 * n if mismatch else P0
        sale_sc = [x for x in scen if x["kind"] in HEADLINE_KINDS]
        w_room = worst_case(P_sale0, sale_sc, s) if P_sale0 else (None, None, None)
        room_loses = P_sale0 is not None and w_room[0] < -EPS
        P_room_floor = no_loss_price(None, scen, s, HEADLINE_KINDS)      # the lowest headline price that does not lose
        P_room = no_loss_price(P_sale0, scen, s, HEADLINE_KINDS)         # = the current sale price when it does not lose
        P_all = no_loss_price(P0, scen, s)                               # every scenario (information, SITE1)
        P_floor = no_loss_price(None, scen, s)
        w0 = worst_case(P0, scen, s) if P0 else (None, None, None)
        be_room = break_even_price(scen, s, HEADLINE_KINDS)
        be_all = break_even_price(scen, s)
        hc, hc_src = highest_comp(p, e, ctx, n)
        owner = src["kind"] == "owner"
        if express_only:
            proposed, status = P0, "express-only"   # listed separately (rule 1), not for sale pending NL2
        elif P0 is None:
            proposed, status = P_room_floor, "no-price"
        elif owner:
            proposed, status = P0, ("owner-set-loses" if room_loses else "ok")
        elif mismatch:
            proposed, status = charm_up(max(P_sale0, P_room)), "raise"   # the row is rewritten for the sale units
        elif room_loses:
            proposed, status = P_room, "raise"
        else:
            proposed, status = P0, "ok"
        r.update({
            "unit_cost_usd": round(sc["unit_cost_usd"], 4), "cost_src": sc["cost_src"], "variants_checked": sc["variants"],
            "scenarios": len(scen),
            "freight": {"method": fr["method"]["label"], "express_only": express_only, "free": fr["method"]["free"],
                        "unit_usd": fr["method"]["unit_usd"], "unit_src": fr["method"]["unit_src"],
                        "sale_usd": fr["method"]["sale_usd"], "sale_src": fr["method"]["sale_src"], "sale_estimated": fr["method"]["sale_estimated"],
                        "single_usd": fr["method"]["single_usd"], "all_quotes": fr["all_quotes"]},
            "current_sale_price_ils": P_sale0,
            "sale_price_basis": "price × units (price_for_qty 1, the Studio sells more)" if mismatch else "the row's price for the sale",
            "headline_at_current": None if w_room[1] is None else _scen_out(w_room[1], w_room[2], w_room[0], s),
            "worst_at_current": None if w0[1] is None else _scen_out(w0[1], w0[2], w0[0], s),
            "break_even_ils": be_room, "break_even_all_scenarios_ils": be_all,
            "no_loss_room_sku_ils": P_room, "no_loss_room_sku_floor_ils": P_room_floor,
            "no_loss_ils": P_all, "no_loss_floor_ils": P_floor,
            "proposed_price_ils": proposed, "raised": bool(P_sale0 and proposed and proposed > P_sale0 + 1e-9),
            "raise_ratio": round(proposed / P_sale0, 3) if (P_sale0 and proposed) else None,
            "highest_comp_ils": round(hc, 2) if hc else None, "highest_comp_src": hc_src,
            "status": status,
        })
        if proposed:
            wp = worst_case(proposed, scen, s)
            hp = worst_case(proposed, sale_sc, s)
            r["at_proposed"] = {"sale_contribution_ils": round(hp[0], 2), "sale_margin_pct": round(100 * (margin(hp[2], hp[1]["landed_ils"], s) or 0), 1),
                                "headline": _scen_out(hp[1], hp[2], hp[0], s), "worst": _scen_out(wp[1], wp[2], wp[0], s)}
            r["ratio_to_highest_comp"] = round(proposed / hc, 2) if hc else None
            r["derived_losing_at_proposed"] = losing_derived(proposed, scen, s)
        # the flag of the policy: ok (40%+) / below-floor (0-40%) / above-market (above the highest comp, with the ratio)
        if status in ("ok", "raise", "owner-set-loses"):
            m_sale = r["at_proposed"]["sale_margin_pct"]
            if hc and proposed > hc + 1e-9:
                r["flag"] = "above-market"
            else:
                r["flag"] = "ok" if m_sale >= s["target_margin_pct"] - 1e-6 else "below-floor"
            r["flag_detail"] = {"sale_margin_pct": m_sale, "worst_margin_pct": r["at_proposed"]["worst"]["margin_pct"],
                                "highest_comp_ils": r["highest_comp_ils"], "ratio_to_highest_comp": r.get("ratio_to_highest_comp"),
                                "forced_by_no_loss": bool(hc and P_room_floor and P_room_floor > hc), "raised": r["raised"]}
        elif status == "express-only":
            r["flag"] = "express-only"
            r["express"] = {"method": fr["method"]["label"], "freight_usd": fr["method"]["sale_usd"], "free": fr["method"]["free"],
                            "loses_at_current": room_loses, "no_loss_at_express_ils": P_room,
                            "ratio_to_highest_comp": round(P_room / hc, 2) if (P_room and hc) else None,
                            "note_he": "אין לספק שיטה רגילה למוצר הזה; לא למכירה עד החלטה NL2 (העלאה, או \"המלאי אינו זמין כעת\" לפי PRE1)"}
        elif status == "no-price":
            r["flag"] = "no-price"
        if owner:
            r["owner_set"] = {"where": src["where"], "price_ils": P0, "room_sku_loses": room_loses, "no_loss_room_sku_ils": P_room,
                              "no_loss_all_scenarios_ils": P_all, "break_even_room_ils": be_room,
                              "derived_losing": r.get("derived_losing_at_proposed"),
                              "note_he": "מחיר שהמשתמש קבע בסטודיו: לא משתנה (NL1)"}
        st = sc.get("studio")
        r["studio_shown"] = None
        if st and P0:
            r["studio_shown"] = {"units": st["units"], "contribution_ils": round(contribution(P0, st["landed_ils"], s), 2),
                                 "margin_pct": round(100 * margin(P0, st["landed_ils"], s), 1), "freight_usd": st["freight_usd"],
                                 "src": st["src"], "landed_ils": round(st["landed_ils"], 2)}
            if r["studio_shown"]["contribution_ils"] < -0.005 and status == "ok":
                r["flags"] = sorted(set(r["flags"]) | {"studio-shows-loss"})
                r["notes"].append(f"הסטודיו עצמו מציג הפסד במחיר הנוכחי (₪{r['studio_shown']['contribution_ils']:g}, משלוח ${st['freight_usd']:g} "
                                  f"מ-{st['src']}), אבל בשיטת ברירת המחדל של הדוח אין הפסד")
            rm = row.get("margin_pct")
            if isnum(rm) and abs(rm - r["studio_shown"]["margin_pct"]) > 1.0:
                r["flags"] = sorted(set(r["flags"]) | {"row-margin-differs"})
                r["notes"].append(f"margin_pct בקובץ התמחור ({rm:g}%) שונה מקריאת הסטודיו במחיר הנוכחי ({r['studio_shown']['margin_pct']:g}%): "
                                  "חושב על מחיר, מק\"ט או כמות אחרים")
        if "qty-inferred-from-landed" in r["flags"] and n > 1:
            one = product_scenarios(p, e, ctx, n_override=1)
            r["if_one_unit"] = {"no_loss_ils": no_loss_price(None, one["scenarios"], s, HEADLINE_KINDS) if one["scenarios"] else None,
                                "note_he": f"הסטודיו מניח {n} יח' לפי עלות הנחיתה ברשומה; אם המכירה היא יחידה אחת, זה המחיר שלא מפסיד"}
        rows.append(r)
    return {"settings": s, "rows": rows, "ctx": ctx, "db": str(db) if db else None}


# --------------------------------------------------------------------------- rejected candidates (report only)

# The review of every round-5 and round-6 candidate without a card, fit 7+, that the record says loses money
# (economics agent, 2026-10-20, from each record's why_he / price_basis_he): "in" = rejected ONLY for the loss
# (a borderline envelope that the record leaves to "check in the frame" is not a rejection); otherwise the other reason.
# high = the highest Israeli price the record names for the whole sale, when its comps do not hold it.
# styles = only these styles count (the record says the item fits the slot only there).
REVIEW = {
    ("round5-aliexpress", "bath/ledge-planter", "1005005532674549"): ("in", 90, None, "מעטפת גבולית (גובה 10, לבדוק בפריים)"),
    ("round5-aliexpress", "bath/shower-curtain", "1005009330407914"): ("out", None, None, "פאנל 140 צר מהמעטפת, לא עמיד למים"),
    ("round5-aliexpress", "bath/toilet-brush", "1005009105041173"): ("in", 120, None, "מעטפת גבולית (11×40)"),
    ("round5-aliexpress", "bath/toilet-brush", "1005009768828838"): ("in", 120, None, "מעטפת גבולית; משלוח 22–29 יום"),
    ("round5-aliexpress", "bath/toothbrush-cup", "1005012763561649"): ("in", 59.9, None, None),
    ("round5-aliexpress", "corridor/gallery-stool", "1005009998944410"): ("in", 150, None, "משלוח מוערך (~$85 ל-4 ק\"ג), אין הצעה במטמון"),
    ("round5-aliexpress", "corridor/gallery-stool", "1005008788426888"): ("out", None, None, "רחב מהמעטפת"),
    ("round5-aliexpress", "corridor/gallery-stool", "1005013193019065"): ("in", 450, None, "מעטפת גבולית (32, לבדוק בפריים)"),
    ("round5-aliexpress", "dining-room/herb-pots", "1005009049409120"): ("in", 79.6, None, "4 עציצים; ההשוואה 4 × ₪19.90"),
    ("round5-aliexpress", "hall/planter", "1005008561559475"): ("in", None, None, "מעטפת גבולית; לא נבדקו השוואות (משלוח $281)"),
    ("round5-aliexpress", "hall/storage-boxes", "1005007386854858"): ("out", None, None, "גובה כ-17 מתחת ל-20, מלאי 7"),
    ("round5-aliexpress", "hall/storage-boxes", "1005012923580024"): ("in", 200, None, "מעטפת גבולית (L, לבדוק בפריים); זוג"),
    ("round5-art-toys", "living-room/framed-art", "1643938313063108608"): ("in", 979, None, "שלישייה; To Door ‏$121 ליחידה"),
    ("round5-ceramics", "dining-room/tableware-set", "1005013098570619"): ("out", None, None, "אין קערה 14–16"),
    ("round5-ceramics", "dining-room/tableware-set", "1005012142300525"): ("out", None, None, "לא מפסיד ב-₪399 (4.5%); החלטת מעצב על הקערה"),
    ("round5-designer-cards", "kids/bookshelf", "1005007471139220"): ("in", 278, None, "זוג מדפים 50"),
    ("round5-designer-cards", "dining-room/bowl", "1392716043398549504"): ("in", 184, None, None),
    ("round5-designer-cards", "dining-room/canisters", "1475674474018902016"): ("in", 210, None, "סט של 3"),
    ("round5-designer-cards", "dining-room/tableware-set", "2624310"): ("in", 485, None, "סט 6; בתמונה סימן מים של מותג אחר"),
    ("round5-lighting", "living-room/floor-lamp", "1005009386433696"): ("in", None, None, "משלוח $718; אין השוואה ברשומה (מחיר השווי ₪949)"),
    ("round5-lighting", "living-room/floor-lamp", "1005009795773948"): ("out", None, None, "לא נדחה על הפסד: בתור לבדיקת משלוח (20% בשווי)"),
    ("round5-lighting", "living-room/floor-lamp", "1005008633875443"): ("out", None, None, "לא מפסיד (8%); משקל ומידות לא ידועות"),
    ("round5-lighting", "master/floor-lamp", "1005012507637187"): ("in", None, None, "מעטפת גבולית; 12 ק\"ג"),
    ("round5-lighting", "master/floor-lamp", "1005009551034916"): ("in", None, None, "מעטפת גבולית"),
    ("round5-lighting", "master/floor-lamp", "1005009386433696"): ("in", None, None, "משלוח $718"),
    ("round5-lighting", "master/floor-lamp", "1005009795773948"): ("out", None, None, "בתור לבדיקת משלוח; העמדה מלאה"),
    ("round5-lighting", "master/floor-lamp", "1005008633875443"): ("out", None, None, "לא מפסיד; העמדה מלאה"),
    ("round5-lighting", "master/bedside-sconces", "1575023214701588480"): ("out", None, None, "CE לא מוצהר"),
    ("round5-lighting", "master/bedside-sconces", "2412081303011612400"): ("out", None, None, "CE לא מוצהר, נורה חשופה"),
    ("round5-lighting", "dining-room/dining-pendant", "1005010594359379"): ("in", 490, None, None),
    ("round5-lighting", "dining-room/dining-pendant", "1005007823892653"): ("out", None, None, "תחתית פתוחה בלי בטנה, 83 יום"),
    ("round5-lighting", "dining-room/dining-pendant", "2412060717211601300"): ("out", None, None, "CE לא מוצהר"),
    ("round5-lighting", "dining-room/dining-pendant", "1005008672138088"): ("in", 490, None, "משלוח $111"),
    ("round5-lighting", "dining-room/dining-pendant", "1005010452173413"): ("out", None, None, "קליעה פתוחה, 3000K"),
    ("round5-lighting", "living-room/pendant", "2617436"): ("out", None, None, "CE, גובה מחוץ למעטפת"),
    ("round5-lighting", "living-room/pendant", "1005008672138088"): ("in", None, None, "משלוח $111"),
    ("round5-lighting", "living-room/pendant", "1005010452173413"): ("out", None, None, "אותה מנורה נדחתה בעמדות אחרות על קליעה פתוחה"),
    ("round5-lighting", "master/pendant", "2507150418081621400"): ("out", None, None, "CE לא מוצהר"),
    ("round5-lighting", "master/pendant", "1005006435771102"): ("in", None, None, "משלוח $180, 10 ק\"ג"),
    ("round5-lighting", "master/pendant", "1005008672138088"): ("in", None, None, "משלוח $111"),
    ("round5-lighting", "master/pendant", "1005010452173413"): ("out", None, None, "קליעה פתוחה"),
    ("round5-lighting", "living-room/wall-sconce", "2503210146241626900"): ("out", None, None, "CE לא מוצהר"),
    ("round5-lighting", "hall/table-lamp", "2917655"): ("out", None, None, "CE, בלי מידות"),
    ("round5-lighting", "hall/table-lamp", "2601290355081633900"): ("out", None, None, "CE לא מוצהר"),
    ("round5-lighting", "corridor/picture-lights", "1005008195905528"): ("in", 599.7, None, "שלישייה; מעטפת גבולית"),
    ("round5-lighting", "corridor/picture-lights", "1005012786446230"): ("out", None, None, "38 מול 25–32"),
    ("round5-lighting", "bath/ceiling-light", "1005009044003157"): ("out", None, None, "אין IP44 מוצהר: חסום למקלחת (ד.5)"),
    ("round5-lighting", "bath/ceiling-light", "1005008258911244"): ("out", None, None, "אין IP44 מוצהר: חסום למקלחת (ד.5)"),
    ("round5-lighting", "bath/ceiling-light", "1005011887658332"): ("out", None, None, "אין IP44 מוצהר: חסום למקלחת (ד.5)"),
    ("round5-lighting", "bath/ceiling-light", "1005008519856029"): ("out", None, None, "אין IP44 מוצהר: חסום למקלחת (ד.5)"),
    ("round5-lighting", "bath/ceiling-light", "1005007452122011"): ("out", None, None, "אין IP44 מוצהר: חסום למקלחת (ד.5)"),
    ("round5-lighting", "bath/ceiling-light", "1005008503056368"): ("out", None, None, "אין IP44 מוצהר: חסום למקלחת (ד.5)"),
    ("round5-lighting", "bath/ceiling-light", "1005006794324716"): ("out", None, None, "אין IP44 מוצהר: חסום למקלחת (ד.5)"),
    ("round5-lighting", "bath/ceiling-light", "1005009229528573"): ("out", None, None, "אין IP44 מוצהר: חסום למקלחת (ד.5)"),
    ("round5-lighting", "bath/ceiling-light", "1005010309140025"): ("out", None, None, "אין IP44 מוצהר: חסום למקלחת (ד.5)"),
    ("round5-lighting", "bath/ceiling-light", "1005010228428551"): ("out", None, None, "אין IP44 מוצהר: חסום למקלחת (ד.5)"),
    ("round5-storage-rooms", "dining-room/canisters", "630486F8-02A0-4D93-85DA-D3D4DEAF41C9"): ("out", None, None, "גבהים 8–18 נמוכים מהמדרגה"),
    ("round5-storage-rooms", "dining-room/sink-set", "1005012088062199"): ("out", None, None, "סט אמבטיה, לא מוצר העמדה"),
    ("round5-lighting", "corridor/ceiling-lights", "1005010338870714"): ("in", None, None, "משלוח $266, 15 ק\"ג"),
    ("round5-lighting", "corridor/ceiling-lights", "1005008258911244"): ("in", 864, None, "זוג; 2 × ₪432"),
    ("round5-storage-bath-hall", "bath/bin", "2603030314101627400"): ("out", None, None, "מחוץ למעטפת"),
    ("round5-storage-bath-hall", "corridor/gallery-stool", "1005012957725537"): ("in", 530, None, "מעטפת גבולית"),
    ("round5-storage-bath-hall", "corridor/gallery-stool", "1005010196581566"): ("in", 530, None, "מעטפת גבולית; גזע עץ כבד"),
    ("round5-storage-rooms", "living-room/magazine-holder", "2608300209161600400"): ("in", 229, None, "מעטפת גבולית"),
    ("round5-storage-rooms", "work/magazine-holder", "2608300209161600400"): ("in", 229, None, "מעטפת גבולית"),
    ("round5-storage-rooms", "master/nightstand-tray", "1393439287588032512"): ("in", 139, None, None),
    ("round5-textile", "living-room/sofa-cover", "1005012935062690"): ("in", 150, None, None),
    ("round5b-furniture-boxes", "living-room/pouf", "2512291109531602600"): ("out", None, None, "קוטר 50 מול 42–45"),
    ("round5b-furniture-boxes", "living-room/pouf", "4000528998843"): ("out", None, None, "פוף ממולא, בניגוד להנחיית המעצב"),
    ("round5b-furniture-boxes", "work/shelf-boxes", "2883881"): ("out", None, None, "אותה קופסה כבר כרטיס מ-AliExpress"),
    ("round5b-furniture-boxes", "work/shelf-boxes", "1005011528913221"): ("out", None, None, "מלאי 2; צנרת PU"),
    ("round5b-furniture-boxes", "hall/storage-boxes", "1705144683208388608"): ("in", 398, None, "זוג; מעטפת גבולית"),
    ("round5c-aliexpress", "bath/toilet-brush", "1005012951198712"): ("in", 90, None, "מעטפת גבולית"),
    ("round5c-aliexpress", "corridor/gallery-stool", "1005009978712423"): ("out", None, None, "רוחב +17%"),
    ("round5c-aliexpress", "dining-room/dining-pendant", "1005004131706427"): ("in", 640, None, None),
    ("round5c-aliexpress", "dining-room/dining-pendant", "1005008591633464"): ("out", None, None, "ה-50 אזל; הכרטיס הלך לרישום המקביל"),
    ("round5c-aliexpress", "dining-room/dining-pendant", "1005009697479922"): ("out", None, None, "אותו מוצר כמו 1005004131706427, יקר יותר"),
    ("round5c-aliexpress", "hall/storage-boxes", "1005008457400321"): ("out", None, None, "נמוך מהמעטפת"),
    ("round5c-aliexpress", "kids/bookshelf", "1005007471139220"): ("out", None, None, "כפול: אותו מוצר ואותה עמדה כמו ברשומה של round5-designer-cards"),
    ("round5c-aliexpress", "kids/roman-blind", "1005011673106863"): ("out", None, None, "סתירה Cordless/Pulling Cord (בטיחות), בלי פשתן מוצהר"),
    ("round5c-aliexpress", "living-room/wall-decor", "1005012947811160"): ("in", 99, None, "בלי חישוק פליז"),
    ("round5c-aliexpress", "master/nightstand-tray", "1005007695543234"): ("in", 89, None, "מעטפת גבולית (20)"),
    ("round5c-aliexpress", "work/shelf-boxes", "1005006768278100"): ("in", 198, None, "זוג; מעטפת גבולית"),
    ("round5e-aliexpress", "corridor/ceiling-lights", "1005012943662628"): ("in", 1164, None, "זוג; 2 × ₪582"),
    ("round5e-aliexpress", "corridor/ceiling-lights", "1005009553503527"): ("in", 1164, None, "זוג; 2 × ₪582; מעטפת גבולית"),
    ("round5e-aliexpress", "corridor/gallery-stool", "1005007997798374"): ("in", 990, None, "מעטפת גבולית (32)"),
    ("round5e-aliexpress", "dining-room/bowl", "1005010778409131"): ("in", 60, None, None),
    ("round5e-aliexpress", "dining-room/bowl", "1005006118879427"): ("in", 60, None, None),
    ("round5e-aliexpress", "dining-room/mug-set", "1005010196442767"): ("in", None, None, "3 ספלים; משלוח $18.73 ליחידה; אין השוואה ברשומה"),
    ("round5e-aliexpress", "dining-room/tableware-set", "1005009383541847"): ("out", None, None, "צלחות סגלגלות, אין קערה"),
    ("round5e-aliexpress", "hall/storage-boxes", "4000162528005"): ("out", None, None, "נמוך מהמעטפת, מלאי 3"),
    ("round5e-aliexpress", "kids/roman-blind", "1005009611594530"): ("out", None, None, "פוליאסטר, 74 יום"),
    ("round5e-aliexpress", "living-room/floor-lamp", "1005009785153450"): ("in", 1000, None, "מעטפת גבולית; משלוח $266"),
    ("round5e-aliexpress", "master/nightstand-tray", "1005005170440217"): ("out", None, None, "פינות חדות"),
    ("round5e-aliexpress", "master/pendant", "1005008743252990"): ("in", 652, None, "מעטפת גבולית"),
    ("round5e-aliexpress", "work/desk-tray", "1005009871058468"): ("out", None, None, "לא סגנון חסר בעמדה; עץ כהה אסור בנורדי"),
    ("round5e-aliexpress", "work/shelf-boxes", "1005009831522799"): ("in", 180, None, "זוג; מעטפת גבולית"),
    ("round5e-aliexpress", "work/shelf-boxes", "1005004334268523"): ("out", None, None, "מגש פתוח, לא קופסה"),
    ("round5e-aliexpress", "work/shelf-boxes", "1005006975059141"): ("out", None, None, "נמוך מהמעטפת"),
    ("round5f-aliexpress", "bath/bath-towels", "1005012773111382"): ("in", 279.8, None, "זוג; נדחה כי המחיר שלא מפסיד מעל ההשוואה (בדיוק מה שהכלל החדש מתיר)"),
    ("round5f-aliexpress", "dining-room/dining-pendant", "1005007506247443"): ("out", None, None, "קליעה פתוחה בלי בטנה"),
    ("round5f-aliexpress", "living-room/pendant", "1005013224966509"): ("in", None, ["mediterranean"], "לבוהו המידה לא מתאימה; ים-תיכוני בלבד"),
    ("round5f-aliexpress", "living-room/pendant", "1005007360409254"): ("out", None, None, "מחוץ למעטפת, פרנזים"),
    ("round6-methods", "hall/storage-boxes", "1005008480586450"): ("in", 196, None, "זוג; בתור חיפוש-תמונה למוכר זול"),
    ("round6-methods", "work/shelf-boxes", "2110994015976243202"): ("in", 360, None, "זוג; 2 × ₪180"),
}
LOSS_RX = re.compile(r"מפסיד|הפסד|\bloss|loses|losing", re.I)


def coverage_counts(extra: dict | None = None) -> dict:
    """{style: {eligible, ready, one_ready}} by the coverage script's own rule (its functions, nothing written), with
    `extra` {style: {slot: {listing key: variants}}} counted as if those candidates had cards."""
    import collections
    m = _coverage_module()
    cwd = os.getcwd()
    try:
        os.chdir(ROOT)
        elig, hold = m.eligible(), m.on_hold()
        with contextlib.redirect_stderr(io.StringIO()):
            cards, _il, _q = m.results()
        var, lst = m.card_variants(), m.card_listing()
        for st, by_slot in (extra or {}).items():
            for slot, d in by_slot.items():
                for key, n in d.items():
                    cards[st][slot][key] = n
                    lst[key] = key

        def options(g, st, s):
            have_ids = [p.get("card_id") for p in g.get("existing_picks") or [] if p.get("card_id")]
            groups, picks_in = collections.defaultdict(int), collections.Counter()
            for c in have_ids:
                L = lst.get(c, f"card:{c}")
                picks_in[L] += 1
                groups[L] = max(groups[L], var.get(c, 1))
            for c, n in cards[st].get(s, {}).items():
                if c not in have_ids:
                    L = lst.get(c, f"card:{c}")
                    groups[L] = max(groups[L], min(3, n) if n else var.get(c, 1))
            return sum(min(3, max(v, picks_in[L])) for L, v in groups.items()) + (g["have"] - len(have_ids))

        out = {}
        for st in m.STYLES:
            pack = json.load(open(f"{m.D}/{st}.json"))
            gaps = {g["slot"]: g for g in pack["gaps"]}
            slots = sorted(x for x in elig if not (st == "nordic" and x in hold))
            ready = one = 0
            for x in slots:
                g = gaps.get(x)
                if not g:
                    ready += 1
                    one += 1
                    continue
                n = options(g, st, x)
                ready += n >= 3
                one += n >= 1
            out[st] = {"eligible": len(slots), "ready": ready, "one_ready": one,
                       "pct_ready": round(100 * ready / len(slots), 1), "pct_one_ready": round(100 * one / len(slots), 1)}
        return out
    finally:
        os.chdir(cwd)


def candidate_freight(c: dict, q: int) -> dict:
    """A candidate's freight for the sale by the corrected rules, from the cached supplier answers (the record's SKU, else
    the worst over the SKUs in the cache), else the record's own ship_usd (for the sale it priced). {sale_usd, src,
    express, estimated}."""
    src = str(c.get("source") or "").lower()
    cid = str(c.get("id") or "")
    sv = str(c.get("sku_or_vid") or "")
    quotes = source_quotes("aliexpress", cid) if src.startswith("ali") else source_quotes("cj", cid) if src == "cj" else {}
    per_sku: dict = {}
    for (sku, qty), opts in quotes.items():
        d = default_quote(opts)
        if d:
            per_sku.setdefault(sku, {})[qty] = d
    text = f"{c.get('why_he') or ''} {c.get('price_basis_he') or ''}"
    rec_ship = float(c["ship_usd"]) if isnum(c.get("ship_usd")) and c["ship_usd"] >= 0 else None
    rec_express = bool(re.search(r"to\s*door|\bDHL\b|fedex|\bUPS\b|aramex", text, re.I))
    if per_sku:
        if sv in per_sku:
            cands = [(sv, per_sku[sv])]
        else:
            cands = sorted(per_sku.items())
        best = None
        for sku, byq in cands:
            d1 = byq.get(1) or min(byq.values(), key=lambda d: d["usd"])
            unit = d1["usd"] if 1 in byq else inv_ship_for_qty(d1["usd"], min(byq))
            sale = byq[q]["usd"] if q in byq else ship_for_qty(unit, q)
            cand = {"sale_usd": round(sale, 4), "unit_usd": round(unit, 4), "sku": sku, "sku_match": sku == sv or not sv,
                    "method": d1["label"], "express": d1["express"],
                    "estimated": q not in byq and q > 1, "src": f"מטמון {('AliExpress' if src.startswith('ali') else 'CJ')} {cid} {sku}: {d1['label']}"
                    + (f" (ל-{q} יח' בחבילה משולבת)" if q not in byq and q > 1 else "")}
            if best is None or cand["sale_usd"] > best["sale_usd"] or (cand["express"] is False and best["express"]):
                best = cand if (best is None or not (best["express"] is False and cand["express"])) else best
        if best and not (best["express"] and rec_ship is not None and not rec_express and rec_ship < best["sale_usd"]):
            if rec_ship is not None and not rec_express and rec_ship > best["sale_usd"] and not best["express"]:
                best = dict(best, sale_usd=round(rec_ship, 4), src=f"הרשומה (${rec_ship:g} למכירה, גבוה מהמטמון {best['src']})")
            best["record_ship_usd"] = rec_ship
            best["record_express"] = rec_express
            return best
    if rec_ship is None:
        return {"sale_usd": None, "src": "אין משלוח ברשומה ולא במטמון", "express": False, "estimated": True, "record_ship_usd": None}
    return {"sale_usd": round(rec_ship, 4), "src": "הרשומה (ship_usd למכירה)" + (" — קו אקספרס לפי הנימוק" if rec_express else ""),
            "express": rec_express, "estimated": True, "record_ship_usd": rec_ship, "record_express": rec_express}


def rejected_loss_only(s: dict) -> dict:
    """Round-5 and round-6 candidates without a card, fit 7+, rejected only because they lost money: their no-loss price
    (the default method, the combined parcel), the ratio to the highest Israeli price, and the coverage gain per style if
    they were counted. Report only: no result file and no coverage file is written."""
    reviewed, keep, unknown = [], [], []
    for f in sorted(glob.glob(str(FINAL / "results" / "round*-*.json"))):
        d = json.load(open(f))
        stem = os.path.basename(f)[:-5]
        for key, sl in (d.get("slots") or {}).items():
            for c in (sl.get("candidates") or []) if isinstance(sl, dict) else []:
                if not isinstance(c, dict) or c.get("card_id"):
                    continue
                fit = {k: float(v) for k, v in (c.get("style_fit_guess") or {}).items() if isnum(v)}
                if not fit or max(fit.values()) < 7:
                    continue
                m = c.get("margin_pct")
                text = f"{c.get('why_he') or ''} {c.get('price_basis_he') or ''}"
                if not ((isnum(m) and m < 0) or LOSS_RX.search(text)):
                    continue
                rv = REVIEW.get((stem, key, str(c.get("id"))))
                if rv is None:
                    unknown.append({"file": stem, "slot": key, "id": c.get("id")})
                    continue
                verdict, high, only, note = rv
                row = {"file": f"{stem}.json", "slot": key, "id": str(c.get("id")), "source": c.get("source"),
                       "url": c.get("url"), "title": c.get("title"), "verdict": verdict, "note_he": note,
                       "fit_7_plus": {k: v for k, v in fit.items() if v >= 7 and (not only or k in only)},
                       "fits_envelope": c.get("fits_envelope"), "why_he": c.get("why_he")}
                reviewed.append(row)
                if verdict != "in":
                    continue
                q = next((int(c[k]) for k in ("qty_in_sale", "qty") if isnum(c.get(k)) and c[k] >= 1), 1)
                cost = float(c["cost_usd"]) if isnum(c.get("cost_usd")) and c["cost_usd"] > 0 else None
                fr = candidate_freight(c, q)
                rec_landed = float(c["landed_ils"]) if isnum(c.get("landed_ils")) and c["landed_ils"] > 0 else None
                rec_ship = fr.get("record_ship_usd")
                # the record's landed cost is the sourcing team's figure for the whole sale (its cost_usd is sometimes per
                # unit, sometimes per sale): keep it and replace only the freight by the corrected rules
                if fr.get("sale_usd") is not None and rec_landed is not None and rec_ship is not None:
                    landed = rec_landed + (fr["sale_usd"] - rec_ship) * s["usd_ils"]
                    fr["landed_basis"] = "הנחיתה שברשומה, עם המשלוח המתוקן במקום משלוח הרשומה"
                elif cost is not None and fr.get("sale_usd") is not None:
                    landed = (cost * q + fr["sale_usd"]) * s["usd_ils"]
                    fr["landed_basis"] = "עלות × כמות + המשלוח המתוקן"
                else:
                    landed = rec_landed
                    fr["landed_basis"] = "הנחיתה שברשומה"
                comps = [x.get("price_ils") or x.get("price") for x in c.get("comps") or [] if isinstance(x, dict)]
                comps = [x for x in comps if isnum(x) and x > 0]
                if high:
                    hc, hsrc = float(high), "הרשומה (טקסט הנימוק)"
                elif comps:
                    hc, hsrc = float(max(comps)), "ההשוואה הגבוהה ברשומה"
                elif isnum(c.get("price_ils")) and c["price_ils"] > 0:
                    hc, hsrc = float(c["price_ils"]), "מחיר השווי שברשומה (אין השוואה)"
                else:
                    hc, hsrc = None, None
                be = round(break_even_for(landed, s), 2) if landed else None
                nl = charm_up(be) if be else None
                row.update({"sale_units": q, "cost_usd": cost, "freight": fr, "landed_ils": round(landed, 2) if landed else None,
                            "record_landed_ils": c.get("landed_ils"), "record_price_ils": c.get("price_ils"),
                            "break_even_ils": be, "no_loss_ils": nl, "highest_comp_ils": hc, "highest_comp_src": hsrc,
                            "ratio_to_highest_comp": round(nl / hc, 2) if nl and hc else None,
                            "scope_he": "שיטת ברירת המחדל (המטמון, אחרת המשלוח שברשומה), המכירה כולה; אין כרטיס, ולכן אפשרויות ויחידה בודדת לא נבדקו"})
                keep.append(row)
    # coverage gain: every kept candidate counted as a card with its fit (one listing per supplier item)
    base = coverage_counts()
    extra: dict = {}
    for r in keep:
        key = f"{str(r['source'] or 'x').lower()}:{r['id']}"
        for k in r["fit_7_plus"]:
            extra.setdefault(k, {}).setdefault(r["slot"], {})[key] = 1
    after = coverage_counts(extra)
    gain = {st: {"eligible": base[st]["eligible"], "ready_before": base[st]["ready"], "ready_after": after[st]["ready"],
                 "slots_gained": after[st]["ready"] - base[st]["ready"],
                 "pct_before": base[st]["pct_ready"], "pct_after": after[st]["pct_ready"],
                 "pct_points": round(after[st]["pct_ready"] - base[st]["pct_ready"], 1),
                 "one_ready_before": base[st]["one_ready"], "one_ready_after": after[st]["one_ready"]} for st in base}
    tot_e = sum(g["eligible"] for g in gain.values())
    tot = {"eligible": tot_e, "ready_before": sum(g["ready_before"] for g in gain.values()), "ready_after": sum(g["ready_after"] for g in gain.values())}
    tot["pct_before"] = round(100 * tot["ready_before"] / tot_e, 1)
    tot["pct_after"] = round(100 * tot["ready_after"] / tot_e, 1)
    gain["total"] = tot
    return {"reviewed": reviewed, "kept": keep, "unreviewed": unknown, "coverage": gain,
            "method_he": "כל מועמד בלי כרטיס בהתאמה 7+ שהרשומה שלו מפסידה נקרא ידנית: 'in' רק כשההפסד הוא סיבת הדחייה היחידה. "
                         "המשלוח: שיטת ברירת המחדל מהמטמון של הספק (המק\"ט שברשומה, אחרת הגרוע מבין המק\"טים), בחבילה משולבת לכמות; "
                         "בלי מטמון, המשלוח שברשומה. הרווח בכיסוי מחושב בכלל של final_round_coverage.py (פונקציות הסקריפט, בלי לכתוב קובץ), "
                         "כאילו לכל מועמד יש כרטיס באפשרות אחת (צבע אחד) בסגנונות שבהם ההתאמה 7+."}


# --------------------------------------------------------------------------- report

FORMULA_NOTES = [
    {"topic": "נוסחת התרומה", "studio": "studio/src/index.html econCalc: נטו = P/1.18; עמלה = 2%·P + ₪1.2; שמורה = 8% מהנטו; אריזה 0; תרומה = נטו − נחיתה − עמלה − שמורה",
     "site": "site/shared/src/pricing.ts unitEconomics: אותה נוסחה, באגורות (עיגול בכל שלב, הפרש של אגורות)", "same": True},
    {"topic": "הגדרות", "studio": "data/economics/settings.json + ברירות המחדל של ECON_META (שער 3.3, מע\"מ 18%, 2% + ₪1.2, החזרות 8%, יעד 40%)",
     "site": "site/shared/src/schema/economics.ts DEFAULT_SETTINGS + resolveSettings: אותם ערכים", "same": True},
    {"topic": "משלוח לכמות", "studio": "shipForQty: יחידה + (q − 1) × max(0, יחידה − $3.72); הצעה שנמדדה לכל המכירה (quoted_qty = q) נלקחת כמו שהיא. **זה הכלל של הדוח (תיקון 2)**",
     "site": "cogsAgorot = (עלות + משלוח ליחידה) × q: ליניארי, בלי חיסכון החבילה (שמרני יותר); build-catalog.ts", "same": False},
    {"topic": "שיטת המשלוח", "studio": "ידני (products.json) ← freight-cj / freight-zendrop / freight-aliexpress (cheapest) ← המק\"ט בכרטיס ← רשומת הסבב האחרון",
     "site": "ידני ← freight-cj.json cheapest ← ברירת מחדל $17 (resolveShippingUsd): למוצרי AliExpress ו-Zendrop בלי משלוח ידני האתר מחשב $17", "same": False},
    {"topic": "מקור המחיר", "studio": "עריכה בסטודיו (db) ← products.json retail_ils ← מחיר בכרטיס (price.retail_ils / suggested_retail) ← price_ils ברשומת הסבב",
     "site": "products.json retail_ils בלבד; בלי שורה: מחיר מומלץ ב-40% (זמני), ובבנייה קפדנית (--strict-prices) לא מוצג", "same": False},
    {"topic": "אפשרויות הספק (וריאנטים)", "studio": "רק המק\"ט שבחדר",
     "site": "options.ts skuRetail: sku_retail_ils של הסטודיו, אחרת P + (המומלץ של האפשרות − המומלץ של המק\"ט שבחדר); בבנייה קפדנית אפשרות בלי sku_retail_ils לא נמכרת", "same": False},
    {"topic": "יחידה אחת מסט (P1)", "studio": "לא מוצג", "site": "packs.ts unitPriceEstimateIls: ceil(P/N × 1.15) מעוגל מטה ל-9, או unit_retail_ils", "same": False},
]

PRICE_TRUTH = {
    "owner": "עריכה בסטודיו (db product_edits), מסונכרנת ל-products.json עם retail_src studio. לא משתנה",
    "products.json": "data/economics/products.json products.<id>.retail_ils: הסטודיו והאתר קוראים אותו",
    "card": "כרטיס המוצר price.suggested_retail או price.retail_ils: הסטודיו בלבד",
    "leads": "price_ils ברשומת הסבב האחרון (data/leads/final-2026-10-13/results/*.json): הסטודיו בלבד, דרך room_boards.Context; בהחלה המחיר החדש נרשם בכרטיס (price.retail_ils), שהסטודיו קורא לפני הרשומה",
    "none": "אין מחיר: כרטיס שנספר בכיסוי בלי מחיר בשום מקום",
    "pricing": "data/economics/pricing/*-2026-10-11.json: המקור שממנו נבנה products.json; אף אחד לא קורא אותו היום (היסטוריה)",
}


def _median(xs):
    xs = sorted(xs)
    if not xs:
        return None
    k = len(xs) // 2
    return xs[k] if len(xs) % 2 else (xs[k - 1] + xs[k]) / 2


def build_report(res: dict, date: str) -> dict:
    ctx: Ctx = res["ctx"]
    s = ctx.s
    rows = res["rows"]
    rej = rejected_loss_only(s)
    raises = [r for r in rows if r.get("status") == "raise"]
    ratios = [r["raise_ratio"] for r in raises]
    above = sorted([r for r in rows if r.get("flag") == "above-market"], key=lambda r: -(r.get("ratio_to_highest_comp") or 0))
    express = [r for r in rows if r.get("status") == "express-only"]
    owner = [r for r in rows if r.get("status") == "owner-set-loses"]
    cannot = [r for r in rows if r.get("status") in ("cannot-compute", "no-card")]
    noprice = [r for r in rows if r.get("status") == "no-price"]
    priced = [r for r in rows if isnum(r.get("current_price_ils"))]
    pj = [r for r in priced if "products.json" in r["scope"]]
    thr = VAT_THRESHOLD_ILS
    above247 = {
        "threshold_ils": thr, "why": "$75 × 3.3: תקרת הפטור ממע\"מ ביבוא אישי (docs/tax/README.md)",
        "products_json_rows": {"before": sum(1 for r in pj if r["current_price_ils"] > thr),
                               "after": sum(1 for r in pj if (r.get("proposed_price_ils") or r["current_price_ils"]) > thr),
                               "rows": len(pj)},
        "all_priced": {"before": sum(1 for r in priced if r["current_price_ils"] > thr),
                       "after": sum(1 for r in priced if (r.get("proposed_price_ils") or r["current_price_ils"]) > thr),
                       "products": len(priced)},
        "crossing": sorted([r["id"] for r in priced if r["current_price_ils"] <= thr < (r.get("proposed_price_ils") or 0)]),
        "note_he": "'אחרי' = המחירים המוצעים; מחיר המשתמש ומוצרי אקספרס-בלבד נשארים במחירם הנוכחי",
    }
    cause = Counter((r["worst_at_current"]["kind"]) for r in raises)
    est = Counter(f for r in rows for f in (r.get("flags") or []))
    truth = Counter(r["price_source"]["kind"] for r in rows if "price_source" in r)
    def brief(r):
        w = r.get("worst_at_current") or {}
        ap = r.get("at_proposed") or {}
        return {"id": r["id"], "slot": r.get("slot"), "scope": r["scope"], "price_source": r["price_source"]["kind"],
                "current_price_ils": r.get("current_price_ils"), "sale_units": r.get("sale_units"),
                "worst_scenario": {k: w.get(k) for k in ("scenario", "kind", "method", "quantity", "variant", "variant_sku", "sold_at_ils", "landed_ils", "freight_usd", "freight_estimated")} if w else None,
                "worst_contribution_ils": w.get("contribution_ils"), "worst_margin_pct": w.get("margin_pct"),
                "break_even_ils": r.get("break_even_ils"), "no_loss_ils": r.get("no_loss_ils"), "no_loss_floor_ils": r.get("no_loss_floor_ils"),
                "no_loss_room_sku_ils": r.get("no_loss_room_sku_ils"), "proposed_price_ils": r.get("proposed_price_ils"),
                "raise_ratio": r.get("raise_ratio"), "margin_at_proposed_pct": ap.get("sale_margin_pct"),
                "worst_margin_at_proposed_pct": (ap.get("worst") or {}).get("margin_pct"),
                "highest_comp_ils": r.get("highest_comp_ils"), "ratio_to_highest_comp": r.get("ratio_to_highest_comp"),
                "flag": r.get("flag"), "status": r.get("status"), "flags": r.get("flags"), "missing": r.get("missing"),
                "express": r.get("express"), "owner_set": r.get("owner_set"), "if_one_unit": r.get("if_one_unit")}
    out = {
        "date": date, "mode": "report (nothing changed)",
        "rule": "docs/studio-rules.md ה.13 (2026-10-20): אין מוצר מפסיד בשום צורה; יכול להיות יקר ללקוח. תיקון הכללים: BRIEF-no-loss-2026-10-20.md, Correction",
        "script": "python3 -I scripts/economics/no_loss.py --report [--db DIR]",
        "settings": s, "studio_db": res.get("db"),
        "corrected_rules_he": [
            "שיטת משלוח: רק שיטת ברירת המחדל, הזולה לישראל, עם מעקב כשהספק מציע (בדרך כלל CJ Eub או השיטה של AliExpress בכרטיס). לא To Door, DHL או אקספרס כשיש זולה יותר; אקספרס-בלבד נרשם בנפרד",
            "כמות: החבילה המשולבת של הסטודיו, משלוח ל-q = יחידה + (q−1) × max(0, יחידה − $3.72)",
            "kitchen-sconce-aliexpress-rustic-wooden-wall-sconce-632957: יחידה אחת",
            "וריאנטים, צבעים וגדלים נשארים בתרחיש הגרוע; משלוח מוערך בתרחיש הגרוע שלו",
            "מחיר מוצע = max(הנוכחי, המחיר שלא מפסיד), מעוגל למעלה לסיומת 9. לא יורד. הכרית של המשתמש (₪69) מדווחת ולא משתנה"],
        "formula": {"contribution": "net − landed − (card_pct·P + card_fixed) − returns_pct·net − packaging; net = P/(1+vat); landed = (unit cost·q + freight for q)·usd_ils",
                    "price_endings": "שקל שלם שנגמר ב-9 (charmRoundUpIls של האתר)", "compare": FORMULA_NOTES,
                    "agree_he": "נוסחת התרומה וההגדרות זהות בסטודיו ובאתר; הקלטים שונים (משלוח לכמות, מקור המשלוח, מקור המחיר, האפשרויות והיחידה הבודדת). "
                                "הדוח הולך לפי הסטודיו במשלוח לכמות (תיקון 2) ולפי האתר במחיר האפשרויות והיחידה הבודדת (זה מה שנמכר שם)"},
        "price_truth": {"counts": dict(truth), "where": PRICE_TRUTH},
        "summary": {"audited": len(rows), "by_status": dict(Counter(r.get("status") for r in rows)), "by_flag": dict(Counter(r.get("flag") for r in rows)),
                    "raises": len(raises),
                    "raise_ratio_min": round(min(ratios), 2) if ratios else None, "raise_ratio_median": round(_median(ratios), 2) if ratios else None,
                    "raise_ratio_max": round(max(ratios), 2) if ratios else None,
                    "current_price_range_ils": [min(r["current_price_ils"] for r in raises), max(r["current_price_ils"] for r in raises)] if raises else None,
                    "proposed_price_range_ils": [min(r["proposed_price_ils"] for r in raises), max(r["proposed_price_ils"] for r in raises)] if raises else None,
                    "raise_bound_by": dict(cause),
                    "raises_room_sku_only_would_suffice": sum(1 for r in raises if r.get("no_loss_room_sku_ils") is not None and r["no_loss_room_sku_ils"] <= r["current_price_ils"]),
                    "above_market": len(above), "above_market_max_ratio": above[0].get("ratio_to_highest_comp") if above else None,
                    "express_only": len(express), "owner_set_losing": len(owner), "cannot_compute": len(cannot), "no_price": len(noprice),
                    "ok_at_current": sum(1 for r in rows if r.get("status") == "ok")},
        "above_247": above247,
        "raises": [brief(r) for r in sorted(raises, key=lambda r: -(r["raise_ratio"] or 0))],
        "above_market": [{k: brief(r)[k] for k in ("id", "current_price_ils", "proposed_price_ils", "highest_comp_ils", "ratio_to_highest_comp", "worst_scenario")} for r in above],
        "express_only": [brief(r) for r in express],
        "owner_set": [brief(r) for r in owner],
        "cannot_compute": [{"id": r["id"], "scope": r.get("scope"), "current_price_ils": r.get("current_price_ils"), "missing": r.get("missing"), "flags": r.get("flags")} for r in cannot],
        "no_price": [{"id": r["id"], "slot": r.get("slot"), "counted_in": r.get("counted_in"), "no_loss_ils": r.get("no_loss_ils"), "break_even_ils": r.get("break_even_ils"),
                      "flag": r.get("flag"), "flags": r.get("flags")} for r in noprice],
        "quantity_checks": [{"id": r["id"], "studio_units": r.get("studio_units"), "sale_units": r["sale_units"], "current_price_ils": r["current_price_ils"],
                             "proposed_price_ils": r.get("proposed_price_ils"), "if_one_unit": r.get("if_one_unit"), "flags": r.get("flags")}
                            for r in rows if {"qty-inferred-from-landed", "unit-override", "price-qty-mismatch"} & set(r.get("flags") or [])],
        "row_margin_check": {"rows_compared": sum(1 for r in rows if r.get("studio_shown") and isnum((ctx.rows.get(r["id"]) or {}).get("margin_pct"))),
                             "differ_over_1pt": [r["id"] for r in rows if "row-margin-differs" in (r.get("flags") or [])],
                             "note_he": "margin_pct של צוות התמחור ב-products.json מול קריאת הסטודיו של הדוח באותו מחיר: בדיקת הנוסחה והקלטים"},
        "flag_counts": dict(est),
        "rejected_candidates": rej,
        "products": [brief(r) for r in rows],
        "rows": rows,
    }
    return out


def _ils(x):
    return "—" if x is None else f"₪{x:,.0f}" if float(x).is_integer() else f"₪{x:,.2f}"


def _ws(w: dict | None) -> str:
    if not w:
        return "—"
    q = w.get("quantity")
    v = w.get("variant")
    return f"{w.get('method')}; {q} יח'; {v}" + (f" (נמכר ב-{_ils(w.get('sold_at_ils'))})" if w.get("kind") != "sale" else "")


def render_md(o: dict) -> str:
    S = o["summary"]
    A = o["above_247"]
    L = [f"# אין מוצר מפסיד: דוח (מצב דיווח, {o['date']})", "",
         "הכלל (ה.13, תיקון 2026-10-20): \"בא נוודא שאין דבר כזה מוצר מפסיד בשום צורה! יכול להיות יקר ללקוח אבל אין מפסיד!\". "
         "לכל מוצר שהסטודיו או האתר יכולים למכור חושבה התרומה בתרחיש הגרוע ביותר לפי הכללים המתוקנים, ומוצע מחיר = max(הנוכחי, המחיר שלא מפסיד). "
         "**שום דבר לא שונה**: לא products.json, לא הכרטיסים, לא הסטודיו ולא האתר. המנהל קורא, ובריף קצר שני מחיל.", "",
         f"הסקריפט: `python3 -I scripts/economics/no_loss.py --report --db <ייצוא db של הסטודיו>` (הדוח הזה; הקובץ המלא: `no-loss-report-{o['date']}.json`), "
         "`--check` (אינווריאנטים; יוצא ב-1 כל עוד יש מוצר שמפסיד במחירו הנוכחי), `--apply` (לבריף ההחלה; לא הורץ).", "",
         "## הכללים המתוקנים", ""] + [f"{i + 1}. {x}" for i, x in enumerate(o["corrected_rules_he"])]
    L += ["", "## בקצרה", "",
          f"- נבדקו {S['audited']} מוצרים: כל שורה ב-products.json, כל כרטיס שסקריפט הכיסוי סופר, וכל כרטיס שיש לו מחיר בסטודיו. "
          f"לפי סטטוס: {', '.join(f'{k} {v}' for k, v in S['by_status'].items())}.",
          (f"- **הועלות מוצעות: {S['raises']}** (מתוך {S['ok_at_current'] + S['raises'] + S['owner_set_losing'] + S['express_only']} מוצרים עם מחיר שאפשר לחשב). "
           f"מ-{_ils(S['current_price_range_ils'][0])}–{_ils(S['current_price_range_ils'][1])} ל-{_ils(S['proposed_price_range_ils'][0])}–{_ils(S['proposed_price_range_ils'][1])}; "
           f"פי {S['raise_ratio_min']} עד פי {S['raise_ratio_max']}, חציון פי {S['raise_ratio_median']}.") if S["raises"] else "- לא מוצעת אף העלאה.",
          f"- מה קבע את ההעלאה: {', '.join(f'{k} {v}' for k, v in S['raise_bound_by'].items())} "
          f"(sale = המכירה במק\"ט שבחדר; variant = אפשרות ספק במחיר שהאתר נותן לה; single = יחידה אחת מסט במחיר ההערכה של האתר). "
          f"ב-{S['raises_room_sku_only_would_suffice']} מהן המחיר הנוכחי לא מפסיד במק\"ט שבחדר, וההעלאה באה רק מהאפשרויות או מהיחידה הבודדת כפי שהאתר מתמחר אותן.",
          f"- **יקר מהשוק: {S['above_market']}** (המחיר שלא מפסיד מעל ההשוואה הגבוהה); היחס הגבוה פי {S['above_market_max_ratio']}.",
          f"- **אקספרס בלבד: {S['express_only']}** (לספק אין שיטה רגילה למוצר); רשומים בנפרד, בלי העלאה מוצעת.",
          f"- מחיר של המשתמש שמפסיד: {S['owner_set_losing']} (הכרית, NL1). אי אפשר לחשב: {S['cannot_compute']}. כרטיסים שנספרים בכיסוי בלי מחיר בכלל: {S['no_price']}.",
          f"- בדיקת הנוסחה: ב-{o['row_margin_check']['rows_compared'] - len(o['row_margin_check']['differ_over_1pt'])} מתוך {o['row_margin_check']['rows_compared']} שורות products.json "
          f"המרווח של צוות התמחור שווה לקריאת הסטודיו של הדוח (עד נקודה); שונה ב-{len(o['row_margin_check']['differ_over_1pt'])}: "
          + ", ".join(f"`{x}`" for x in o["row_margin_check"]["differ_over_1pt"]) + " (מחיר, מק\"ט או כמות אחרים; `row-margin-differs`).",
          f"- **מעל ₪{A['threshold_ils']}** ({A['why']}): שורות products.json {A['products_json_rows']['before']} → {A['products_json_rows']['after']} "
          f"(מתוך {A['products_json_rows']['rows']}); כל המוצרים עם מחיר {A['all_priced']['before']} → {A['all_priced']['after']} (מתוך {A['all_priced']['products']}). "
          f"{A['note_he']}.", "",
          "## הנוסחה, ואיפה המחיר חי", "",
          f"- תרומה = נטו − נחיתה − (2% מהמחיר + ₪1.2) − 8% מהנטו; נטו = מחיר ÷ 1.18; נחיתה = (עלות ליחידה × כמות + משלוח לכמות) × 3.3. לפני CAC. "
          "דמי המשלוח שהלקוח משלם לא נספרים, כמו בסטודיו. סיומת המחיר: שקל שלם שנגמר ב-9.",
          f"- הגדרות: {', '.join(f'{k} {v}' for k, v in o['settings'].items())} (data/economics/settings.json + ברירות המחדל של הסטודיו).",
          f"- ייצוא ה-db של הסטודיו שנקרא: `{o.get('studio_db') or 'לא נמסר'}` (עריכות מחיר של המשתמש).", "",
          "| מקור המחיר | מוצרים | מי קורא אותו |", "| --- | --- | --- |"]
    for k in ("owner", "products.json", "card", "leads", "none"):
        L.append(f"| {k} | {o['price_truth']['counts'].get(k, 0)} | {PRICE_TRUTH[k]} |")
    L += ["", f"- {PRICE_TRUTH['pricing']}", "", "### הסטודיו מול האתר", "", "| נושא | הסטודיו | האתר | זהה |", "| --- | --- | --- | --- |"]
    for d in o["formula"]["compare"]:
        L.append(f"| {d['topic']} | {d['studio']} | {d['site']} | {'כן' if d['same'] else 'לא'} |")
    L += ["", f"מסקנה: {o['formula']['agree_he']}.", "",
          "## ההעלאות המוצעות", "",
          "\"מק\"ט בלבד\" = המחיר שלא מפסיד כשבודקים רק את המכירה במק\"ט שבחדר (בלי אפשרויות ויחידה בודדת): כשהוא שווה למחיר הנוכחי, ההעלאה באה מתמחור האפשרויות באתר (skuRetail) או מהיחידה הבודדת. "
          "\"מרווח\" = המרווח במחיר המוצע במכירה הרגילה (מק\"ט שבחדר, שיטת ברירת המחדל). הדגל: ok ≥40%, below-floor 0–40%, above-market = המחיר שלא מפסיד מעל ההשוואה הגבוהה.", "",
          "| מוצר | מקור | נוכחי | מוצע | פי | התרחיש הגרוע (שיטה; כמות; וריאנט) | תרומה היום | נקודת איזון | מק\"ט בלבד | מרווח | השוואה גבוהה | פי מההשוואה | דגל |",
          "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for r in o["raises"]:
        L.append(f"| `{r['id']}` | {r['price_source']} | {_ils(r['current_price_ils'])} | {_ils(r['proposed_price_ils'])} | {r['raise_ratio']:.2f} | "
                 f"{_ws(r['worst_scenario'])} | {_ils(r['worst_contribution_ils'])} | {_ils(r['break_even_ils'])} | {_ils(r['no_loss_room_sku_ils'])} | "
                 f"{r['margin_at_proposed_pct']}% | {_ils(r['highest_comp_ils'])} | {r['ratio_to_highest_comp'] if r['ratio_to_highest_comp'] is not None else '—'} | {r['flag']} |")
    L += ["", "## יקר מהשוק", "", f"{S['above_market']} מוצרים: המחיר שלא מפסיד מעל ההשוואה הישראלית הגבוהה. מסומנים `above-market` (הסטודיו עוד לא מציג תווית כזו).", "",
          "| מוצר | נוכחי | מוצע | השוואה גבוהה | יחס | התרחיש הגרוע |", "| --- | --- | --- | --- | --- | --- |"]
    for a in o["above_market"]:
        L.append(f"| `{a['id']}` | {_ils(a['current_price_ils'])} | {_ils(a['proposed_price_ils'])} | {_ils(a['highest_comp_ils'])} | פי {a['ratio_to_highest_comp']} | {_ws(a['worst_scenario'])} |")
    L += ["", "## אקספרס בלבד", "", "לספק אין שיטה רגילה למוצר: המשלוח היחיד הוא To Door, DHL או FedEx. לא מוצעת העלאה; המחיר שלא מפסיד כאן הוא במשלוח האקספרס היחיד, להחלטת המנהל "
          "(להציע עם משלוח בנפרד, לסמן \"המלאי אינו זמין כעת\", או לחפש רישום אחר).", "",
          "| מוצר | נוכחי | השיטה היחידה | משלוח למכירה | מפסיד היום | מחיר שלא מפסיד באקספרס | השוואה גבוהה | יחס |", "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for r in o["express_only"]:
        x = r["express"] or {}
        L.append(f"| `{r['id']}` | {_ils(r['current_price_ils'])} | {x.get('method')}{' (חינם)' if x.get('free') else ''} | ${x.get('freight_usd'):g} | "
                 f"{'כן' if x.get('loses_at_current') else ('אין מחיר' if r['current_price_ils'] is None else 'לא')} | {_ils(x.get('no_loss_at_express_ils'))} | {_ils(r['highest_comp_ils'])} | "
                 f"{x.get('ratio_to_highest_comp') if x.get('ratio_to_highest_comp') is not None else '—'} |")
    L += ["", "## מחיר שהמשתמש קבע ומפסיד (לא שונה; NL1)", ""]
    if o["owner_set"]:
        for r in o["owner_set"]:
            os_ = r["owner_set"]
            L.append(f"- `{r['id']}` ב-{_ils(r['current_price_ils'])} ({os_['where']}). התרחיש הגרוע: {_ws(r['worst_scenario'])}, תרומה {_ils(r['worst_contribution_ils'])}. "
                     f"**המחיר שלא מפסיד: {_ils(os_['no_loss_ils'])}** (נקודת איזון {_ils(os_['break_even_ils'])}); במק\"ט שבחדר בלבד: {_ils(r['no_loss_room_sku_ils'])}. "
                     f"אם יועלה: דגל {os_['flag_if_raised']}, פי {os_['ratio_to_highest_comp_if_raised']} מההשוואה הגבוהה ({_ils(r['highest_comp_ils'])}). להחלטת המשתמש.")
    else:
        L.append("- אין.")
    L += ["", "## אי אפשר לחשב", ""]
    for r in o["cannot_compute"]:
        L.append(f"- `{r['id']}` ({', '.join(r.get('scope') or [])}): {r.get('missing')}" + (f", מחיר {_ils(r['current_price_ils'])}" if r.get("current_price_ils") else ""))
    L += ["", f"כרטיסים שנספרים בכיסוי ואין להם מחיר בשום מקום ({S['no_price']}): המחיר שלא מפסיד לכל אחד ב-JSON (`no_price`), כרצפה למחיר התחלה. לא נכתב מחיר.", "",
          f"## מוצרים מעל ₪{A['threshold_ils']}", "",
          f"- {A['why']}. מעל הסף הלקוח עלול לשלם מע\"מ ועמלת שחרור בדלת (VAT1 פתוחה).",
          f"- שורות products.json: **{A['products_json_rows']['before']} לפני → {A['products_json_rows']['after']} אחרי** (מתוך {A['products_json_rows']['rows']}).",
          f"- כל המוצרים עם מחיר ({A['all_priced']['products']}): **{A['all_priced']['before']} לפני → {A['all_priced']['after']} אחרי**.",
          f"- חוצים את הסף בגלל ההעלאה ({len(A['crossing'])}): " + (", ".join(f"`{x}`" for x in A["crossing"]) or "אין") + ".",
          f"- {A['note_he']}.", "",
          "## כמות המכירה: בדיקות", "",
          "במוצרים האלה הסטודיו קרא את מספר היחידות במכירה מעלות הנחיתה שברשומה (studio/build.py lead_qty), לא משדה כמות, או שהמחיר בקובץ התמחור הוא לכמות אחרת "
          "מזו שהסטודיו מוכר (`price-qty-mismatch`). המחיר נבדק לפי הכמות שהסטודיו מוכר, חוץ ממנורת המטבח (תיקון 3: יחידה אחת). "
          "העמודה האחרונה: המחיר שלא מפסיד אילו המכירה הייתה יחידה אחת.", "",
          "| מוצר | יח' בסטודיו | יח' בדוח | נוכחי | מוצע | אם יחידה אחת | סימון |", "| --- | --- | --- | --- | --- | --- | --- |"]
    for q in o["quantity_checks"]:
        one = (q.get("if_one_unit") or {}).get("no_loss_ils")
        one_s = _ils(one) if one is not None else ("יחידה אחת בדוח" if q["sale_units"] == 1 else "—")
        fl = ", ".join(f for f in q.get("flags") or [] if f in ("qty-inferred-from-landed", "unit-override", "price-qty-mismatch"))
        L.append(f"| `{q['id']}` | {q['studio_units']} | {q['sale_units']} | {_ils(q['current_price_ils'])} | {_ils(q['proposed_price_ils'])} | {one_s} | {fl} |")
    L += ["", "## קלטים מוערכים וסימונים", ""]
    for k, v in sorted(o["flag_counts"].items(), key=lambda x: -x[1]):
        L.append(f"- `{k}`: {v} מוצרים")
    L += ["", "freight-estimated = אין הצעת משלוח, נלקחה ההערכה הגבוהה; qty-freight-estimated = משלוח לכמה יחידות לפי נוסחת החבילה המשולבת; "
          "freight-from-other-sku = המשלוח נמדד על מק\"ט אחר; freight-from-cache-only = לסטודיו אין משלוח, נלקח ממטמון הספק; freight-quote-other-qty = ההצעה לכמות אחרת, "
          "תורגמה ליחידה; qty-inferred-from-landed = הכמות הוסקה מעלות הנחיתה; unit-override = כמות שהמנהל קבע; price-qty-mismatch = המחיר בקובץ לכמות אחרת מהמכירה; "
          "sale-cost-from-leads = עלות המכירה מהרשומה (בהחלה צריך שורה ב-products.json עם sale_cost_usd); options-are-set-parts = האפשרויות הן חלקי הסט, לא וריאנטים; "
          "express-only = רק אקספרס; no-route = הספק לא שולח לישראל; cost-not-usd = העלות לא בדולר.", ""]
    rj = o["rejected_candidates"]
    L += ["## מועמדים שנדחו רק בגלל הפסד (סבבים 5 ו-6, התאמה 7+)", "",
          f"נקראו {len(rj['reviewed'])} מועמדים בלי כרטיס שהרשומה שלהם מפסידה; **{len(rj['kept'])} נדחו רק בגלל ההפסד**. {rj['method_he']} "
          "דיווח בלבד: לא שונה אף קובץ תוצאות ולא סקריפט הכיסוי. להחלטת המשתמש.", "",
          "| עמדה | מוצר | סגנונות 7+ | יח' | משלוח (שיטה) | נחיתה | נקודת איזון | מחיר שלא מפסיד | השוואה גבוהה | יחס | הערה |",
          "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for r in sorted(rj["kept"], key=lambda r: (r["slot"], r["ratio_to_highest_comp"] or 0)):
        fr = r.get("freight") or {}
        rs = fr.get("record_ship_usd")
        rec_s = f"; ברשומה ${rs:g}" if (rs is not None and fr.get("sale_usd") is not None and abs(rs - fr["sale_usd"]) > 0.01) else ""
        if rec_s and fr.get("sku_match") is False:
            rec_s += ", מק\"ט אחר במטמון"
        L.append(f"| {r['slot']} | {r['source']} {r['id']} | {', '.join(f'{k} {v:g}' for k, v in r['fit_7_plus'].items())} | {r['sale_units']} | "
                 f"{'$' + format(fr.get('sale_usd'), 'g') if fr.get('sale_usd') is not None else '—'} ({fr.get('method') or fr.get('src')}{'; אקספרס' if fr.get('express') else ''}{rec_s}) | "
                 f"{_ils(r.get('landed_ils'))} | {_ils(r.get('break_even_ils'))} | {_ils(r.get('no_loss_ils'))} | {_ils(r.get('highest_comp_ils'))} | "
                 f"{r.get('ratio_to_highest_comp') if r.get('ratio_to_highest_comp') is not None else '—'} | {r.get('note_he') or ''} |")
    L += ["", "### הרווח בכיסוי אם ייספרו", "", "| סגנון | עמדות | 3 אפשרויות היום | אם ייספרו | נוספו |", "| --- | --- | --- | --- | --- |"]
    for st, g in rj["coverage"].items():
        if st == "total":
            continue
        L.append(f"| {st} | {g['eligible']} | {g['ready_before']} ({g['pct_before']}%) | {g['ready_after']} ({g['pct_after']}%) | +{g['slots_gained']} (+{g['pct_points']} נק') |")
    tt = rj["coverage"]["total"]
    L.append(f"| **סה\"כ** | {tt['eligible']} | {tt['ready_before']} ({tt['pct_before']}%) | {tt['ready_after']} ({tt['pct_after']}%) | +{tt['ready_after'] - tt['ready_before']} |")
    L += ["", "שאר המועמדים שנקראו נדחו גם מסיבה אחרת (מעטפת, CE או IP44, קליעה פתוחה, מלאי, כפילות); הסיבה לכל אחד ב-JSON (`rejected_candidates.reviewed`).", "",
          "## מה בריף ההחלה יעשה (לא בוצע)", "",
          "- products.json: retail_ils של כל שורה שמועלית (הישן נשמר ב-retail_before_no_loss_ils, retail_src initial-no-loss-<תאריך>), ועדכון flag/flags/no_loss.",
          "- כרטיס עם מחיר משלו (price.suggested_retail / price.retail_ils): השדה בכרטיס; מחיר מרשומת הסבב: price.retail_ils בכרטיס (הרשומה לא משתנה); "
          "רשומה שעלות המכירה שלה אינה N × הכרטיס: שורה חדשה ב-products.json עם sale_cost_usd.",
          "- הכרית של המשתמש: לפי NL1. אקספרס-בלבד: לפי החלטת המנהל.",
          "- אחר כך: build הסטודיו, 7 בדיקות העשן, ספירת המוצרים מעל ₪247 שוב.", ""]
    return "\n".join(L)


def _dump(path: Path, data) -> None:
    """Write JSON (validated before it is written)."""
    txt = json.dumps(data, ensure_ascii=False, indent=1) + "\n"
    json.loads(txt)
    path.write_text(txt, encoding="utf-8")


def write_report(res: dict, date: str) -> tuple[Path, Path]:
    out = build_report(res, date)
    jp = ECO / f"no-loss-report-{date}.json"
    _dump(jp, out)
    mp = ECO / f"no-loss-report-{date}.md"
    mp.write_text(render_md(out), encoding="utf-8")
    return jp, mp


# --------------------------------------------------------------------------- check

def check(res: dict) -> tuple[list[str], list[dict]]:
    """Invariants of the computation (exit 2 when one fails) and the products whose headline (the room SKU in its sale
    units, by the default method) loses at the current sale price (exit 1)."""
    s = res["settings"]
    ctx: Ctx = res["ctx"]
    bad = []
    P, Lnd = 100.0, 50.0
    want = P / 1.18 - Lnd - (P * 0.02 + 1.2) - 0.08 * P / 1.18
    if abs(contribution(P, Lnd, {**STUDIO_DEFAULTS}) - want) > 1e-9:
        bad.append("contribution() differs from the Studio formula")
    if charm_up(183.2) != 189 or charm_up(190) != 199 or charm_up(9) != 9 or charm_down(115) != 109 or charm_down(189) != 189:
        bad.append("charm rounding differs from pricing.ts / packs.ts")
    if abs(ship_for_qty(8.77, 3) - (8.77 + 2 * (8.77 - 3.72))) > 1e-9 or ship_for_qty(1.99, 4) != 1.99:
        bad.append("ship_for_qty differs from shipForQty")
    if unit_price_estimate(199, 3) != 69 or unit_price_estimate(63, 2) != 39:
        bad.append("unit_price_estimate differs from packs.ts")
    if abs(break_even_for(50, STUDIO_DEFAULTS) - (50 + 1.2) / ((1 - 0.08) / 1.18 - 0.02)) > 1e-9:
        bad.append("break_even_for differs from the formula")
    for r in res["rows"]:
        if r.get("status") in ("cannot-compute", "no-card"):
            continue
        P0, Ps, Pp = r.get("current_price_ils"), r.get("current_sale_price_ils"), r.get("proposed_price_ils")
        if Pp is not None and Ps is not None and Pp < Ps - 1e-9:
            bad.append(f"{r['id']}: proposed {Pp} < current sale price {Ps}")
        if r.get("raised") and Pp % 10 != 9:
            bad.append(f"{r['id']}: proposed {Pp} does not end in 9")
        ap = r.get("at_proposed")
        if r.get("status") in ("raise", "ok", "no-price") and ap and ap["sale_contribution_ils"] < -0.005:
            bad.append(f"{r['id']}: headline contribution at proposed {Pp} is {ap['sale_contribution_ils']}")
        h = r.get("headline_at_current")
        if r.get("status") == "raise" and h and h["contribution_ils"] >= 0 and "price-qty-mismatch" not in (r.get("flags") or []):
            bad.append(f"{r['id']}: status raise but the headline does not lose at the current sale price")
        if r.get("status") == "ok" and h and h["contribution_ils"] < -0.005:
            bad.append(f"{r['id']}: status ok but the headline loses at the current sale price")
        if r.get("id") in UNIT_OVERRIDES and r.get("sale_units") != UNIT_OVERRIDES[r["id"]][0]:
            bad.append(f"{r['id']}: unit override not applied")
        if r["id"] in ctx.owner_edits and Pp != P0:
            bad.append(f"{r['id']}: an owner-set price was changed")
    for r in res["rows"]:
        if r.get("status") != "raise" or "price-qty-mismatch" in (r.get("flags") or []):
            continue
        p = ctx.by_id[r["id"]]
        sc = product_scenarios(p, ctx.E.get(r["id"], {}), ctx)
        lower = r["proposed_price_ils"] - 10
        if lower > r["current_sale_price_ils"] and worst_case(lower, _pick(sc["scenarios"], HEADLINE_KINDS), s)[0] >= -EPS:
            bad.append(f"{r['id']}: {lower} would also not lose; proposed {r['proposed_price_ils']} is not minimal")
    losing = [r for r in res["rows"] if r.get("status") == "raise"]
    return bad, losing


# --------------------------------------------------------------------------- apply (the apply brief, 2026-10-20)

def _dump_like(path: Path, data) -> None:
    """Write JSON in the file's own format (indent, trailing newline), validated before it is written."""
    indent, nl = 1, "\n"
    if path.exists():
        old = path.read_text(encoding="utf-8")
        m = re.match(r"[{\[]\n( +)", old)
        indent = len(m.group(1)) if m else 1
        nl = "\n" if old.endswith("\n") else ""
    txt = json.dumps(data, ensure_ascii=False, indent=indent) + nl
    json.loads(txt)
    path.write_text(txt, encoding="utf-8")


def _record_il_value(p: dict, date: str) -> dict | None:
    """The final round's comparables of a card as products.json il_value (retailer, title, price, url)."""
    lr = p.get("_lead_rec") or {}
    comps = []
    for c in (lr.get("rec") or {}).get("comps") or []:
        if not isinstance(c, dict):
            continue
        price = next((c[k] for k in ("price_ils", "price") if isnum(c.get(k))), None)
        title = str(c.get("title") or c.get("name") or c.get("shop_title") or "")
        retailer = str(c.get("retailer") or (title.split(" – ")[0].split(" - ")[0].split(",")[0] if title else ""))[:80]
        comps.append({"retailer": retailer, "title": title[:200], "price": price, "url": c.get("url")})
    if not comps:
        return None
    return {"comps": comps, "note": f"ההשוואות מהליקוט האחרון ({lr.get('file')}), ליחידה; הועתקו ב-{date} (אין מוצר מפסיד)"}


def _above_247(rows: list[dict], prices: dict | None = None) -> dict:
    """Products above the VAT threshold: products.json rows and every priced product; `prices` overrides id -> price."""
    thr = VAT_THRESHOLD_ILS
    out = {"threshold_ils": thr, "products_json_rows": 0, "all_priced": 0, "rows": 0, "priced": 0}
    for r in rows:
        P = (prices or {}).get(r["id"], r.get("current_price_ils"))
        if not isnum(P):
            continue
        out["priced"] += 1
        out["all_priced"] += P > thr
        if "products.json" in (r.get("scope") or []):
            out["rows"] += 1
            out["products_json_rows"] += P > thr
    return out


def apply(res: dict, date: str) -> dict:
    """Raise every losing headline (status raise) to its proposed price in its source of truth:
      products.json row   -> its retail_ils (the old one kept as retail_before_no_loss_ils, retail_src initial-no-loss-<date>);
                             a price-qty-mismatch row is rewritten for the sale units (price_for_qty, sell_qty)
      the card's own price -> that field (price.retail_ils or price.suggested_retail)
      the final round's record -> a price.retail_ils on the card, which the Studio reads before the record
                              (studio/build.py card_economics); the results file is left as it is
      a record whose sale cost is not N x the card's (a mixed set) -> a products.json row with that sale_cost_usd
    The unit overrides (rule 3) are written to the card (sell_qty). A price the owner set is never changed; express-only
    products are not changed; both are listed."""
    ctx: Ctx = res["ctx"]
    pj_path = ctx.eco_dir / "products.json"
    pj = json.loads(pj_path.read_text(encoding="utf-8"))
    rows = pj["products"]
    changes, owner, cannot, express, qty_fixes = [], [], [], [], []
    card_edits: dict[str, dict] = {}
    for r in res["rows"]:
        st = r.get("status")
        if r.get("owner_set"):
            owner.append(r)
        if st == "express-only":
            express.append(r)
            continue
        if st in ("cannot-compute", "no-card"):
            cannot.append(r)
            continue
        if r["id"] in UNIT_OVERRIDES:
            p = ctx.by_id[r["id"]]
            if (p.get("sell_qty") or None) != UNIT_OVERRIDES[r["id"]][0]:
                qty_fixes.append({"id": r["id"], "file": p["_path"], "field": "sell_qty", "old": p.get("sell_qty"), "new": UNIT_OVERRIDES[r["id"]][0],
                                  "studio_units_before": r.get("studio_units"), "reason_he": UNIT_OVERRIDES[r["id"]][1], "date": date})
        if st != "raise":
            continue
        new, old, old_sale = r["proposed_price_ils"], r["current_price_ils"], r["current_sale_price_ils"]
        if new is None or not new > old:
            continue
        src = r["price_source"]
        h = r["headline_at_current"]
        p = ctx.by_id[r["id"]]
        e = ctx.E.get(r["id"], {})
        kind = src["kind"]
        mismatch = "price-qty-mismatch" in r["flags"]
        if kind == "leads" and "sale-cost-from-leads" in r["flags"]:
            target, fld = "products.json (שורה חדשה)", f"products.{r['id']}"
        elif kind == "leads":
            target, fld = src["card"], "price.retail_ils"
        elif kind == "card":
            target, fld = src["where"], src["field"]
        else:
            target, fld = "data/economics/products.json", src["field"]
        if mismatch:
            reason = (f"המחיר ₪{old:g} בקובץ הוא ליחידה אחת והסטודיו מוכר {r['sale_units']} יח': מחיר המכירה ₪{old_sale:g}; "
                      f"בתרחיש הכותרת ({h['label_he']}; {h['method']}) התרומה ₪{h['contribution_ils']:g}; "
                      f"המחיר שלא מפסיד ל-{r['sale_units']} יח': ₪{new:g} (נקודת איזון ₪{r['break_even_ils']:g})")
        else:
            reason = (f"בתרחיש הכותרת ({h['label_he']}; {h['method']}) התרומה ₪{h['contribution_ils']:g} במחיר ₪{old:g}; "
                      f"המחיר הנמוך שלא מפסיד במק\"ט שבחדר: ₪{new:g} (נקודת איזון ₪{r['break_even_ils']:g})")
        hc = r.get("highest_comp_ils")
        ch = {"id": r["id"], "price_source": kind, "file": target, "field": fld,
              "old_price_ils": old, "old_sale_price_ils": old_sale, "new_price_ils": new, "sale_units": r["sale_units"],
              "ratio": round(new / old_sale, 3),
              "scenario": h["scenario"], "scenario_he": h["label_he"], "method": h["method"], "quantity": h["quantity"],
              "variant": h["variant"], "landed_ils": h["landed_ils"], "freight_usd": h["freight_usd"], "freight_src": h["freight_src"],
              "freight_estimated": h["freight_estimated"], "contribution_at_old_ils": h["contribution_ils"],
              "break_even_ils": r["break_even_ils"], "margin_at_new_pct": r["at_proposed"]["sale_margin_pct"],
              "no_loss_all_scenarios_ils": r.get("no_loss_ils"), "derived_losing_at_new": r.get("derived_losing_at_proposed"),
              "highest_comp_ils": hc, "highest_comp_src": r.get("highest_comp_src"),
              "ratio_to_highest_comp": round(new / hc, 2) if hc else None, "flag": r.get("flag"),
              "flags": r["flags"], "reason_he": reason, "date": date}
        if kind == "leads":
            ch["record_unchanged"] = src["where"]
        changes.append(ch)
        if kind == "products.json":
            row = rows[r["id"]]
            row.setdefault("retail_before_no_loss_ils", old)
            row["retail_ils"] = new
            row["retail_src"] = f"initial-no-loss-{date}"
            if row.get("price_for_qty") != r["sale_units"]:
                ch["price_for_qty"] = {"old": row.get("price_for_qty"), "new": r["sale_units"]}
                row["price_for_qty"] = r["sale_units"]
            if mismatch:
                row["sell_qty"] = r["sale_units"]
                ch["sell_qty_written"] = r["sale_units"]
        elif target.startswith("products.json"):
            rec = (p.get("_lead_rec") or {}).get("rec") or {}
            row = {"retail_ils": new, "retail_src": f"initial-no-loss-{date}", "retail_before_no_loss_ils": old,
                   "price_for_qty": r["sale_units"], "sell_qty": r["sale_units"],
                   "sale_cost_usd": round(float(e["sale_cost_usd"]), 4),
                   "sale_contains": (p.get("name") or "")[:200] or None,
                   "price_note": (str(rec.get("price_basis_he") or "").strip()[:400] or None),
                   "source": {"record": src["where"], "card": p["_path"], "added": date,
                              "why": "המחיר הועלה (אין מוצר מפסיד); הסטודיו שומר את עלות המכירה מהליקוט רק כשהמחיר הוא של הרשומה, "
                                     "ולכן העלות של הסט כולו נכתבת כאן (sale_cost_usd)"},
                   "ship_estimated": any("estimated" in f for f in r["flags"])}
            iv = _record_il_value(p, date)
            if iv:
                row["il_value"] = iv
            rows[r["id"]] = {k: v for k, v in row.items() if v is not None}
        else:
            card_edits[target] = {"field": fld, "new": new, "old": old, "id": r["id"]}
    for q in qty_fixes:
        card_edits.setdefault(q["file"], {"id": q["id"]})["sell_qty"] = q["new"]
    for f, ed in card_edits.items():
        path = ROOT / f
        card = json.loads(path.read_text(encoding="utf-8"))
        notes = card.get("notes") or ""
        note = ""
        if ed.get("field"):
            fld = ed["field"].split(".", 1)[1]
            card.setdefault("price", {})[fld] = ed["new"]
            note = (f"[no-loss {date}] מחיר לצרכן ₪{ed['new']:g} (היה ₪{ed['old']:g}): המחיר הנמוך שבו המק\"ט שבחדר לא מפסיד "
                    f"(ה.13, 2026-10-20; data/economics/no-loss-changes-{date}.json).")
        if "sell_qty" in ed:
            card["sell_qty"] = ed["sell_qty"]
            note = (note + " " if note else "") + f"[no-loss {date}] כמות למכירה {ed['sell_qty']} (המנהל, 2026-10-20: {UNIT_OVERRIDES[ed['id']][1]})."
        if note and f"[no-loss {date}]" not in notes:
            card["notes"] = (notes.rstrip() + "\n" + note) if notes.strip() else note
        _dump_like(path, card)
    return {"changes": changes, "owner": owner, "cannot": cannot, "express": express, "qty_fixes": qty_fixes, "pj": pj, "pj_path": pj_path}


def refresh_rows(res: dict, pj: dict, date: str, before: dict) -> list[dict]:
    """products.json after the raise: margin and contribution at the row's price as the Studio reads it, the policy's flag
    (ok >= 40%, below-floor 0-40%, above-market = above the highest comp; express-only; cannot-compute; "loss" only where
    the Studio's own reading is still negative, which the audit reports) and the no-loss facts. Returns the rows that changed."""
    ctx: Ctx = res["ctx"]
    s = ctx.s
    out = []
    by = {r["id"]: r for r in res["rows"]}
    for pid, row in pj["products"].items():
        r = by.get(pid)
        old = {k: (before.get(pid) or {}).get(k) for k in ("retail_ils", "flag", "margin_pct", "contribution_ils")}
        if not r:
            continue
        P = row["retail_ils"]
        flags = []
        if r.get("status") in ("cannot-compute", "no-card"):
            row["flag"] = "cannot-compute"
            flags = ["cannot-compute"]
            row["no_loss"] = {"date": date, "cannot_compute": r.get("missing"), "flags": r.get("flags")}
        elif r.get("status") == "express-only":
            x = r.get("express") or {}
            row["flag"] = "express-only"
            flags = ["express-only", "not-for-sale"]
            st = r.get("studio_shown")
            if st:
                row["contribution_ils"] = st["contribution_ils"]
                row["margin_pct"] = st["margin_pct"]
            row["no_loss"] = {"date": date, "express_only": True, "for_sale": False, "pending": "NL2", "method": x.get("method"),
                              "freight_usd": x.get("freight_usd"), "no_loss_at_express_ils": x.get("no_loss_at_express_ils"),
                              "highest_comp_ils": r.get("highest_comp_ils"), "ratio_to_highest_comp": x.get("ratio_to_highest_comp"),
                              "note_he": x.get("note_he")}
        else:
            st = r.get("studio_shown")
            h = r.get("headline_at_current") or {}
            # the margin at the row's price: the Studio's own reading, else the audit's headline (the Studio has no freight
            # of its own for the product: it came from the supplier's cache)
            ms = st or (h if isnum(h.get("contribution_ils")) else None)
            if ms:
                row["contribution_ils"] = ms["contribution_ils"]
                row["margin_pct"] = ms["margin_pct"]
                row["margin_src"] = "studio" if st else "no-loss headline (the Studio has no freight for the product)"
            hc = r.get("highest_comp_ils")
            raised = row.get("retail_src") == f"initial-no-loss-{date}"
            if ms and ms["contribution_ils"] < -0.005:
                row["flag"] = "loss"   # the Studio's own reading still loses: reported, never expected here
            elif hc and P > hc + 1e-9:
                row["flag"] = "above-market"
            else:
                m = ms["margin_pct"] / 100 if ms else None
                row["flag"] = "ok" if m is not None and m >= s["target_margin_pct"] / 100 - EPS else "below-floor"
            flags = [row["flag"]]
            if r.get("derived_losing_at_proposed"):
                flags.append("variant-loses-on-site")
            if r.get("owner_set"):
                flags.append("owner-set")
            row["customer_total_ils"] = P if P >= 299 else P + 29
            iv = row.get("il_value") or {}
            if isnum(iv.get("typical")) and iv["typical"] > 0:
                row["vs_typical_pct"] = round(100 * (row["customer_total_ils"] - iv["typical"]) / iv["typical"])
            h = (r.get("at_proposed") or {}).get("headline") or r.get("headline_at_current") or {}
            nl = {"date": date, "policy": "headline = room SKU, sale units, default method (BRIEF Apply 2026-10-20)",
                  "headline_scenario": h.get("label_he"), "method": h.get("method"), "units": h.get("quantity"),
                  "landed_ils": h.get("landed_ils"), "contribution_ils": h.get("contribution_ils"), "margin_pct": h.get("margin_pct"),
                  "break_even_ils": r.get("break_even_ils"), "no_loss_room_sku_ils": r.get("no_loss_room_sku_floor_ils"),
                  "no_loss_all_scenarios_ils": r.get("no_loss_floor_ils"),
                  "variants_losing_on_site": [{k: v.get(k) for k in ("variant", "variant_sku", "sold_at_ils", "landed_ils", "contribution_ils", "own_no_loss_ils")}
                                              for v in r.get("derived_losing_at_proposed") or []],
                  "highest_comp_ils": hc, "ratio_to_highest_comp": round(P / hc, 2) if hc else None, "above_market": row["flag"] == "above-market",
                  "estimated_inputs": [f for f in r["flags"] if "estimated" in f or "missing" in f or "other-sku" in f or "cache" in f],
                  "scenarios": r.get("scenarios"), "variants_checked": r.get("variants_checked")}
            if r.get("owner_set"):
                nl["owner_set"] = True
            if raised:
                nl["raised_from_ils"] = row.get("retail_before_no_loss_ils")
            row["no_loss"] = nl
        row["flags"] = flags
        new = {"retail_ils": P, "flag": row.get("flag"), "margin_pct": row.get("margin_pct"), "contribution_ils": row.get("contribution_ils")}
        if old != new:
            out.append({"id": pid, "old": old, "new": new, "flags": flags})
    return out


# --------------------------------------------------------------------------- audit files (after the apply)

def build_audit(res: dict, date: str, tests: dict | None) -> dict:
    """The audit of the state after the apply: the changes log, the policy's lists (NL2, SITE1, express-only, cannot
    compute, the owner's price, the quantity checks), the VAT-threshold counts and the test results."""
    ctx: Ctx = res["ctx"]
    s = ctx.s
    rows = res["rows"]
    log_p = ECO / f"no-loss-changes-{date}.json"
    log = json.loads(log_p.read_text(encoding="utf-8")) if log_p.exists() else {"changes": []}
    ch = log.get("changes") or []
    by_ch = {c["id"]: c for c in ch}
    ratios = [c["ratio"] for c in ch if not c.get("sell_qty_written")]
    above = sorted([r for r in rows if r.get("flag") == "above-market"], key=lambda r: -(r.get("ratio_to_highest_comp") or 0))
    nl2 = [r for r in above if (r.get("ratio_to_highest_comp") or 0) > 2]
    express = [r for r in rows if r.get("status") == "express-only"]
    cannot = [r for r in rows if r.get("status") in ("cannot-compute", "no-card")]
    owner = [r for r in rows if r.get("owner_set")]
    still = [r for r in rows if r.get("status") == "raise" or (r.get("studio_shown") and r["studio_shown"]["contribution_ils"] < -0.005
                                                                 and r.get("status") not in ("express-only",))]
    site1 = [r for r in rows if r.get("derived_losing_at_proposed")]
    report_66 = set(log.get("report_variant_driven_ids") or [])
    rej = rejected_loss_only(s)

    def brief(r):
        h = r.get("headline_at_current") or {}
        w = r.get("worst_at_current") or {}
        c = by_ch.get(r["id"]) or {}
        return {"id": r["id"], "slot": r.get("slot"), "scope": r["scope"], "price_source": r["price_source"]["kind"],
                "price_ils": r.get("current_price_ils"), "raised_from_ils": c.get("old_price_ils"), "ratio": c.get("ratio"),
                "sale_units": r.get("sale_units"),
                "headline": {k: h.get(k) for k in ("method", "quantity", "landed_ils", "contribution_ils", "margin_pct")} if h else None,
                "worst_any_scenario": {k: w.get(k) for k in ("kind", "variant", "sold_at_ils", "contribution_ils")} if w else None,
                "break_even_ils": r.get("break_even_ils"), "no_loss_room_sku_ils": r.get("no_loss_room_sku_floor_ils"),
                "no_loss_all_scenarios_ils": r.get("no_loss_floor_ils"),
                "highest_comp_ils": r.get("highest_comp_ils"), "ratio_to_highest_comp": r.get("ratio_to_highest_comp"),
                "flag": r.get("flag"), "status": r.get("status"), "flags": r.get("flags"), "missing": r.get("missing"),
                "express": r.get("express"), "owner_set": r.get("owner_set"), "if_one_unit": r.get("if_one_unit"),
                "derived_losing": r.get("derived_losing_at_proposed")}
    out = {
        "date": date, "mode": "audit after the apply",
        "rule": "docs/studio-rules.md ה.13 (2026-10-20); BRIEF-no-loss-2026-10-20.md Correction + Apply",
        "policy_he": ["מחיר הכותרת = max(הנוכחי, המחיר שלא מפסיד במק\"ט שבחדר, ביחידות המכירה, בשיטת ברירת המחדל), מעוגל ל-9",
                      "מחירי וריאנטים שהאתר גוזר (skuRetail) אינם סיבה להעלאה; התיקון באתר: מחיר נגזר לא יורד מתחת למחיר שלא מפסיד של הוריאנט (SITE1)",
                      "price-qty-mismatch: מחיר ליחידה כשהעמדה מוכרת יותר יחידות = מחיר × יחידות; נבדק ידנית",
                      "אקספרס-בלבד: בלי העלאה, דגל express-only, לא למכירה עד NL2", "הכרית של המשתמש: לא משתנה (NL1)",
                      "אי אפשר לחשב: דגל ורשימה", "דגלים: ok (40%+), below-floor (0–40%), above-market (מעל ההשוואה הגבוהה, עם היחס); יחס מעל 2 ל-NL2"],
        "settings": s, "studio_db": res.get("db"), "changes_file": str(log_p.relative_to(ROOT)),
        "summary": {"audited": len(rows), "by_status": dict(Counter(r.get("status") for r in rows)), "by_flag": dict(Counter(r.get("flag") for r in rows)),
                    "raised": len(ratios), "rewritten_for_sale_units": sum(1 for c in ch if c.get("sell_qty_written")),
                    "raised_by_source": dict(Counter(c["price_source"] for c in ch)),
                    "ratio_min": round(min(ratios), 2) if ratios else None, "ratio_median": round(_median(ratios), 2) if ratios else None,
                    "ratio_max": round(max(ratios), 2) if ratios else None,
                    "old_price_range_ils": [min(c["old_sale_price_ils"] for c in ch), max(c["old_sale_price_ils"] for c in ch)] if ch else None,
                    "new_price_range_ils": [min(c["new_price_ils"] for c in ch), max(c["new_price_ils"] for c in ch)] if ch else None,
                    "above_market": len(above), "above_market_ratio_over_2": len(nl2),
                    "above_market_max_ratio": above[0].get("ratio_to_highest_comp") if above else None,
                    "express_only": len(express), "cannot_compute": len(cannot), "owner_set": len(owner),
                    "site1_rows_with_losing_derived_price": len(site1), "still_losing": [r["id"] for r in still],
                    "quantity_fixes": log.get("quantity_fixes")},
        "above_247": log.get("above_247"),
        "raised": ch,
        "above_market": [{k: brief(r)[k] for k in ("id", "price_ils", "raised_from_ils", "highest_comp_ils", "ratio_to_highest_comp", "headline", "flags")} for r in above],
        "nl2_ratio_over_2": [{k: brief(r)[k] for k in ("id", "price_ils", "raised_from_ils", "highest_comp_ils", "ratio_to_highest_comp", "headline")} for r in nl2],
        "site1_variant_floor": {
            "rule_he": "מחיר וריאנט שהאתר גוזר (options.ts skuRetail: P + המומלץ של האפשרות − המומלץ של המק\"ט שבחדר) לא יורד מתחת למחיר שלא מפסיד של "
                       "הוריאנט עצמו (נקודת האיזון של הנחיתה שלו, מעוגלת ל-9); אותו דבר להערכת היחידה הבודדת (packs.ts unitPriceEstimateIls)",
            "report_variant_driven_ids": sorted(report_66),
            "rows": [{"id": r["id"], "price_ils": r["current_price_ils"], "in_report_66": r["id"] in report_66,
                      "losing": [{k: v.get(k) for k in ("kind", "variant", "variant_sku", "sold_at_ils", "landed_ils", "contribution_ils", "own_no_loss_ils")}
                                 for v in r["derived_losing_at_proposed"]]} for r in site1]},
        "express_only": [brief(r) for r in express],
        "owner_set": [brief(r) for r in owner],
        "cannot_compute": [{"id": r["id"], "scope": r.get("scope"), "price_ils": r.get("current_price_ils"), "missing": r.get("missing"), "flags": r.get("flags")} for r in cannot],
        "quantity_checks": [{"id": r["id"], "studio_units": r.get("studio_units"), "sale_units": r["sale_units"], "price_ils": r["current_price_ils"],
                             "sale_price_basis": r.get("sale_price_basis"), "if_one_unit": r.get("if_one_unit"), "flags": r.get("flags"),
                             "change": by_ch.get(r["id"])}
                            for r in rows if {"qty-inferred-from-landed", "unit-override", "price-qty-mismatch"} & set(r.get("flags") or [])],
        "mismatch_hand_check": log.get("mismatch_hand_check"),
        "flag_counts": dict(Counter(f for r in rows for f in (r.get("flags") or []))),
        "tests": tests,
        "rejected_candidates_coverage": rej["coverage"], "rejected_candidates_kept": len(rej["kept"]),
        "products": [brief(r) for r in rows],
        "rows": rows,
    }
    return out


def render_audit_md(o: dict) -> str:
    S = o["summary"]
    A = o.get("above_247") or {}
    L = [f"# אין מוצר מפסיד: ביקורת אחרי ההחלה ({o['date']})", "",
         "הכלל (ה.13, תיקון 2026-10-20): \"בא נוודא שאין דבר כזה מוצר מפסיד בשום צורה! יכול להיות יקר ללקוח אבל אין מפסיד!\". "
         "הוחל לפי מדיניות המנהל (BRIEF-no-loss-2026-10-20.md, Apply), אחרי דוח מצב הדיווח (no-loss-report-2026-10-20.md).", "",
         f"יומן השינויים: `{o['changes_file']}`. הסקריפט: `python3 -I scripts/economics/no_loss.py --apply`, ואז `--check` ו-`--audit --tests F`.", "",
         "## המדיניות", ""] + [f"{i + 1}. {x}" for i, x in enumerate(o["policy_he"])]
    L += ["", "## בקצרה", "",
          f"- נבדקו {S['audited']} מוצרים. לפי סטטוס אחרי ההחלה: {', '.join(f'{k} {v}' for k, v in S['by_status'].items())}.",
          (f"- **הועלו {S['raised']} מחירים** ({', '.join(f'{k} {v}' for k, v in S['raised_by_source'].items())}), ועוד {S['rewritten_for_sale_units']} שורות נכתבו מחדש ליחידות המכירה. "
           f"מ-{_ils(S['old_price_range_ils'][0])}–{_ils(S['old_price_range_ils'][1])} ל-{_ils(S['new_price_range_ils'][0])}–{_ils(S['new_price_range_ils'][1])}; "
           f"פי {S['ratio_min']} עד פי {S['ratio_max']}, חציון פי {S['ratio_median']}.") if S["raised"] else "- לא הועלה אף מחיר.",
          f"- **יקר מהשוק: {S['above_market']}** (המחיר מעל ההשוואה הגבוהה); **{S['above_market_ratio_over_2']} ביחס מעל 2 → NL2**; היחס הגבוה פי {S['above_market_max_ratio']}.",
          f"- **אקספרס בלבד: {S['express_only']}**, בלי העלאה, דגל express-only, לא למכירה עד NL2. אי אפשר לחשב: {S['cannot_compute']}. הכרית של המשתמש: לא שונתה (NL1).",
          f"- **SITE1:** ב-{S['site1_rows_with_losing_derived_price']} מוצרים מחיר וריאנט או יחידה בודדת שהאתר גוזר עדיין מפסיד במחיר הכותרת; התיקון באתר (רצפה למחיר הנגזר), הרשימה למטה.",
          f"- **עדיין מפסיד (כותרת או קריאת הסטודיו):** {', '.join(f'`{x}`' for x in S['still_losing']) or 'אין'}."]
    if A:
        L.append(f"- **מעל ₪{A['before']['threshold_ils']}** ($75 × 3.3, תקרת הפטור ממע\"מ): שורות products.json {A['before']['products_json_rows']} → {A['after']['products_json_rows']} "
                 f"(מתוך {A['after']['rows']}); כל המוצרים עם מחיר {A['before']['all_priced']} → {A['after']['all_priced']} (מתוך {A['after']['priced']}).")
    t = o.get("tests") or {}
    L += ["", "## בדיקות", ""]
    if t:
        for k, v in t.items():
            L.append(f"- {k}: {v}")
    else:
        L.append("- לא צורפו תוצאות (ראו את סיכום הסוכן).")
    L += ["", "## מה הועלה", "",
          "התרחיש = המק\"ט שבחדר ביחידות המכירה, בשיטת ברירת המחדל. \"כל התרחישים\" = המחיר שלא מפסיד גם בוריאנטים וביחידה בודדת כפי שהאתר מתמחר אותם (לא הוחל; SITE1).", "",
          "| מוצר | מקור | היה | עכשיו | פי | שיטה; יח' | נחיתה | תרומה היום | נקודת איזון | מרווח עכשיו | כל התרחישים | השוואה גבוהה | יחס | דגל |",
          "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for c in sorted(o["raised"], key=lambda c: -c["ratio"]):
        old = _ils(c["old_sale_price_ils"]) + (f" ({_ils(c['old_price_ils'])} ליח')" if c.get("sell_qty_written") else "")
        L.append(f"| `{c['id']}` | {c['price_source']} | {old} | {_ils(c['new_price_ils'])} | {c['ratio']:.2f} | {c['method']}; {c['quantity']} | {_ils(c['landed_ils'])} | "
                 f"{_ils(c['contribution_at_old_ils'])} | {_ils(c['break_even_ils'])} | {c['margin_at_new_pct']}% | {_ils(c.get('no_loss_all_scenarios_ils'))} | "
                 f"{_ils(c.get('highest_comp_ils'))} | {c.get('ratio_to_highest_comp') if c.get('ratio_to_highest_comp') is not None else '—'} | {c.get('flag')} |")
    mh = o.get("mismatch_hand_check") or []
    L += ["", "## price-qty-mismatch: בדיקה ידנית (2 שורות)", ""]
    for m in mh:
        L.append(f"- `{m['id']}`: {m['text_he']}")
    if not mh:
        L.append("- אין.")
    L += ["", "## יקר מהשוק", "", f"{S['above_market']} מוצרים שמחירם מעל ההשוואה הישראלית הגבוהה (דגל `above-market`; הסטודיו מעביר רק ok/below-floor/loss, SITE1). "
          f"**{S['above_market_ratio_over_2']} ביחס מעל 2 מסומנים ל-NL2.**", "",
          "| מוצר | מחיר | היה | השוואה גבוהה | יחס | NL2 | שיטה; יח' |", "| --- | --- | --- | --- | --- | --- | --- |"]
    for a in o["above_market"]:
        h = a.get("headline") or {}
        L.append(f"| `{a['id']}` | {_ils(a['price_ils'])} | {_ils(a['raised_from_ils']) if a.get('raised_from_ils') else 'לא הועלה'} | {_ils(a['highest_comp_ils'])} | "
                 f"פי {a['ratio_to_highest_comp']} | {'**כן**' if (a['ratio_to_highest_comp'] or 0) > 2 else ''} | {h.get('method')}; {h.get('quantity')} |")
    L += ["", "## אקספרס בלבד (לא למכירה עד NL2)", "",
          "| מוצר | מחיר | השיטה היחידה | משלוח | מפסיד היום | לא מפסיד באקספרס | השוואה גבוהה | יחס |", "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for r in o["express_only"]:
        x = r["express"] or {}
        L.append(f"| `{r['id']}` | {_ils(r['price_ils'])} | {x.get('method')}{' (חינם)' if x.get('free') else ''} | ${x.get('freight_usd'):g} | "
                 f"{'כן' if x.get('loses_at_current') else ('אין מחיר' if r['price_ils'] is None else 'לא')} | {_ils(x.get('no_loss_at_express_ils'))} | {_ils(r['highest_comp_ils'])} | "
                 f"{x.get('ratio_to_highest_comp') if x.get('ratio_to_highest_comp') is not None else '—'} |")
    L += ["", "## מחיר שהמשתמש קבע (NL1, לא שונה)", ""]
    for r in o["owner_set"]:
        os_ = r["owner_set"]
        h = r.get("headline") or {}
        dl = os_.get("derived_losing") or []
        L.append(f"- `{r['id']}` ב-{_ils(r['price_ils'])} ({os_['where']}). במק\"ט שבחדר ({h.get('method')}): תרומה {_ils(h.get('contribution_ils'))}, מרווח {h.get('margin_pct')}%: "
                 f"{'מפסיד' if os_['room_sku_loses'] else 'לא מפסיד'}; המחיר שלא מפסיד במק\"ט שבחדר {_ils(os_['no_loss_room_sku_ils'])}. "
                 + (f"מפסיד רק בוריאנט שהאתר גוזר: " + "; ".join(f"{v['variant']} ב-{_ils(v['sold_at_ils'])} (תרומה {_ils(v['contribution_ils'])}, רצפה {_ils(v['own_no_loss_ils'])})" for v in dl)
                    + f". בכל התרחישים: {_ils(os_['no_loss_all_scenarios_ils'])}. לפי המדיניות זה תיקון SITE1, לא העלאה." if dl else "לא מפסיד באף תרחיש."))
    L += ["", "## אי אפשר לחשב", ""]
    for r in o["cannot_compute"]:
        L.append(f"- `{r['id']}` ({', '.join(r.get('scope') or [])}): {r.get('missing')}" + (f", מחיר {_ils(r['price_ils'])}" if r.get("price_ils") else "") + " (דגל cannot-compute)")
    L += ["", "## SITE1: רצפה למחיר וריאנט שהאתר גוזר", "", f"- {o['site1_variant_floor']['rule_he']}.",
          f"- {len(o['site1_variant_floor']['report_variant_driven_ids'])} השורות שבדוח הדיווח נקבעו מוריאנט: " + ", ".join(f"`{x}`" for x in o["site1_variant_floor"]["report_variant_driven_ids"]) + ".",
          f"- אחרי ההחלה, ב-{len(o['site1_variant_floor']['rows'])} מוצרים מחיר נגזר עדיין מפסיד (הרשימה המלאה ב-JSON, `site1_variant_floor.rows`); הגרוע בכל מוצר:", "",
          "| מוצר | מחיר הכותרת | וריאנט | מחיר באתר | נחיתה | תרומה | רצפה (לא מפסיד) |", "| --- | --- | --- | --- | --- | --- | --- |"]
    for r in sorted(o["site1_variant_floor"]["rows"], key=lambda r: min(v["contribution_ils"] for v in r["losing"])):
        v = min(r["losing"], key=lambda v: v["contribution_ils"])
        L.append(f"| `{r['id']}` | {_ils(r['price_ils'])} | {v['variant']} ({v['kind']}) | {_ils(v['sold_at_ils'])} | {_ils(v['landed_ils'])} | {_ils(v['contribution_ils'])} | {_ils(v['own_no_loss_ils'])} |")
    L += ["", "## כמות המכירה", "",
          "| מוצר | יח' בסטודיו | יח' בדוח | מחיר | בסיס | אם יחידה אחת | סימון |", "| --- | --- | --- | --- | --- | --- | --- |"]
    for q in o["quantity_checks"]:
        one = (q.get("if_one_unit") or {}).get("no_loss_ils")
        one_s = _ils(one) if one is not None else ("יחידה אחת" if q["sale_units"] == 1 else "—")
        fl = ", ".join(f for f in q.get("flags") or [] if f in ("qty-inferred-from-landed", "unit-override", "price-qty-mismatch"))
        L.append(f"| `{q['id']}` | {q['studio_units']} | {q['sale_units']} | {_ils(q['price_ils'])} | {q.get('sale_price_basis')} | {one_s} | {fl} |")
    qf = S.get("quantity_fixes") or []
    for q in qf:
        L.append(f"\n- תיקון כמות בכרטיס: `{q['id']}` sell_qty {q['old']} → {q['new']} ({q['reason_he']}).")
    L += ["", "## קלטים מוערכים וסימונים", ""]
    for k, v in sorted(o["flag_counts"].items(), key=lambda x: -x[1]):
        L.append(f"- `{k}`: {v} מוצרים")
    cv = o["rejected_candidates_coverage"]
    L += ["", "## מועמדים שנדחו רק בגלל הפסד", "",
          f"{o['rejected_candidates_kept']} מועמדים (סבבים 5 ו-6, התאמה 7+) נדחו רק בגלל ההפסד; הרשימה המלאה בדוח הדיווח (no-loss-report-2026-10-20.md). "
          "אם ייספרו: " + ", ".join(f"{st} +{g['slots_gained']} ({g['pct_before']}→{g['pct_after']}%)" for st, g in cv.items() if st != "total") + "; "
          f"סה\"כ {cv['total']['ready_before']} → {cv['total']['ready_after']} עמדות ({cv['total']['pct_before']}→{cv['total']['pct_after']}%). להחלטת המשתמש.", "",
          "## מה עוד צריך", "",
          "- NL2: המוצרים ביחס מעל 2, ומוצרי האקספרס-בלבד (העלאה, או \"המלאי אינו זמין כעת\" לפי PRE1).",
          "- SITE1: רצפה למחיר וריאנט נגזר וליחידה בודדת; הסטודיו מציג רק ok/below-floor/loss (above-market, express-only ו-cannot-compute לא מוצגים כתווית); "
          "האתר לא קורא את flag (מוצר שמסומן לא למכירה נמכר באתר).",
          "- ממשיכים לחפש חלופה זולה יותר באותו מראה למוצרים שהועלו הרבה (ה.13).", ""]
    return "\n".join(L)


def write_audit(res: dict, date: str, tests: dict | None) -> tuple[Path, Path]:
    out = build_audit(res, date, tests)
    jp = ECO / f"no-loss-audit-{date}.json"
    _dump(jp, out)
    mp = ECO / f"no-loss-audit-{date}.md"
    mp.write_text(render_audit_md(out), encoding="utf-8")
    return jp, mp


def mismatch_hand_check(res: dict) -> list[dict]:
    """Policy 3, stated in words: the two price-qty-mismatch rows at price x units."""
    s = res["settings"]
    out = []
    for r in res["rows"]:
        if "price-qty-mismatch" not in (r.get("flags") or []) or r.get("status") not in ("raise", "ok"):
            continue
        h = r["headline_at_current"]
        n, P0, Ps = r["sale_units"], r["current_price_ils"], r["current_sale_price_ils"]
        net = Ps / (1 + s["vat_pct"] / 100)
        text = (f"המחיר ₪{P0:g} הוא ליחידה (price_for_qty 1) והסטודיו מוכר {n} יח' (העמדה זוג): מחיר המכירה ₪{P0:g} × {n} = ₪{Ps:g}. "
                f"נחיתה ל-{n} יח' ({h['method']}, משלוח ${h['freight_usd']:g} בחבילה משולבת) ₪{h['landed_ils']:g}; "
                f"נטו ₪{net:.2f}, עמלות ₪{Ps * s['card_pct'] / 100 + s['card_fixed_ils']:.2f}, שמורה ₪{net * s['returns_pct'] / 100:.2f} → "
                f"תרומה ₪{h['contribution_ils']:g} ({h['margin_pct']}%): {'מפסיד' if h['contribution_ils'] < 0 else 'לא מפסיד'}. "
                f"נקודת האיזון ל-{n} יח' ₪{r['break_even_ils']:g}; נכתב ₪{r['proposed_price_ils']:g} ל-{n} יח' (price_for_qty {n}, sell_qty {n}).")
        out.append({"id": r["id"], "units": n, "unit_price_ils": P0, "sale_price_ils": Ps, "landed_ils": h["landed_ils"],
                    "contribution_ils": h["contribution_ils"], "break_even_ils": r["break_even_ils"], "written_ils": r["proposed_price_ils"], "text_he": text})
    return out


# --------------------------------------------------------------------------- CLI

def summary(res: dict) -> dict:
    st = Counter(r.get("status") for r in res["rows"])
    fl = Counter(r.get("flag") for r in res["rows"])
    return {"products": len(res["rows"]), "by_status": dict(st), "by_flag": dict(fl)}


def main(argv: list[str]) -> int:
    def arg(name):
        return argv[argv.index(name) + 1] if name in argv and argv.index(name) + 1 < len(argv) else None
    db = Path(arg("--db")) if arg("--db") else None
    date = arg("--date") or dt.date.today().isoformat()
    res = audit(ECO, db)
    print(json.dumps(summary(res), ensure_ascii=False))
    if arg("--json"):
        Path(arg("--json")).write_text(json.dumps({"settings": res["settings"], "db": res.get("db"), "rows": res["rows"]}, ensure_ascii=False, indent=1) + "\n",
                                       encoding="utf-8")
    rc = 0
    if "--apply" in argv:
        pj_path = ECO / "products.json"
        before = json.loads(pj_path.read_text(encoding="utf-8"))["products"]
        above_before = _above_247(res["rows"])
        hand = mismatch_hand_check(res)
        variant_driven = sorted(r["id"] for r in res["rows"] if (r.get("worst_at_current") or {}).get("kind") in ("variant", "variant-single")
                                and (r.get("worst_at_current") or {}).get("contribution_ils", 0) < 0 and r.get("status") in ("raise", "ok", "owner-set-loses"))
        a = apply(res, date)
        _dump_like(a["pj_path"], a["pj"])                  # 1. the prices (and the new rows)
        res1 = audit(ECO, db)                              # 2. the Studio's reading of the new prices
        pj = json.loads(pj_path.read_text(encoding="utf-8"))
        fc = refresh_rows(res1, pj, date, before)          # 3. margins, flags and no-loss facts at the new prices
        pj["updated"] = date
        n_rows = len([c for c in a["changes"] if c["price_source"] == "products.json"])
        add = (f" {date} (אין מוצר מפסיד, ה.13 בתיקון 2026-10-20, מדיניות ההחלה): {n_rows} מחירים הועלו למחיר הנמוך שבו המק\"ט שבחדר, ביחידות המכירה, "
               f"בשיטת ברירת המחדל, לא מפסיד (retail_src initial-no-loss-{date}; המחיר הקודם ב-retail_before_no_loss_ils). flag: ok ≥40%, below-floor 0–40%, "
               "above-market = מעל ההשוואה הגבוהה, express-only = רק אקספרס (לא למכירה עד NL2), cannot-compute; flags מוסיף variant-loses-on-site (SITE1) ו-owner-set; "
               f"no_loss = תרחיש הכותרת, נקודת האיזון, הוריאנטים שמפסידים באתר והיחס להשוואה (data/economics/no-loss-changes-{date}.json).")
        if f"{date} (אין מוצר מפסיד" not in pj.get("note", ""):
            pj["note"] = pj.get("note", "") + add
        src = f"data/economics/no-loss-changes-{date}.json"
        if src not in pj.get("sources", []):
            pj.setdefault("sources", []).append(src)
        _dump_like(pj_path, pj)
        res2 = audit(ECO, db)                              # 4. verify: no headline loses (but express-only)
        left = [r["id"] for r in res2["rows"] if r.get("status") == "raise"]
        above_after = _above_247(res2["rows"])
        log = {"date": date, "rule": "docs/studio-rules.md ה.13 (2026-10-20): אין מוצר מפסיד בשום צורה; BRIEF-no-loss-2026-10-20.md Correction + Apply",
               "policy_he": "מחיר הכותרת = max(הנוכחי, המחיר שלא מפסיד במק\"ט שבחדר ביחידות המכירה בשיטת ברירת המחדל), מעוגל ל-9; וריאנטים נגזרים ל-SITE1; "
                            "אקספרס-בלבד בלי העלאה; הכרית לא משתנה; price-qty-mismatch = מחיר × יחידות",
               "script": "python3 -I scripts/economics/no_loss.py --apply", "settings": res["settings"], "studio_db": res.get("db"),
               "changes": a["changes"], "quantity_fixes": a["qty_fixes"], "mismatch_hand_check": hand,
               "report_variant_driven_ids": variant_driven, "products_json_rows_refreshed": fc,
               "owner_set_not_changed": [{"id": r["id"], "price_ils": r["current_price_ils"], "where": r["price_source"]["where"],
                                          "owner_set": r.get("owner_set")} for r in a["owner"]],
               "express_only_not_changed": [{"id": r["id"], "price_ils": r["current_price_ils"], "express": r.get("express")} for r in a["express"]],
               "cannot_compute": [{"id": r["id"], "price_ils": r.get("current_price_ils"), "missing": r.get("missing"), "flags": r.get("flags")}
                                  for r in a["cannot"]],
               "above_247": {"before": above_before, "after": above_after},
               "verified_after": {"audited": len(res2["rows"]), "by_status": summary(res2)["by_status"], "by_flag": summary(res2)["by_flag"], "still_losing": left}}
        _dump_like(ECO / f"no-loss-changes-{date}.json", log)
        print(f"applied: {len(a['changes'])} prices changed, {len(a['qty_fixes'])} quantity fixes, {len(fc)} products.json rows refreshed, "
              f"{len(a['owner'])} owner-set listed, {len(a['express'])} express-only listed, {len(a['cannot'])} cannot be computed; still losing after: {len(left)}")
        res = res2
    if "--report" in argv:
        jp, mp = write_report(res, date)
        print(f"report: {jp.relative_to(ROOT)}, {mp.relative_to(ROOT)}")
    if "--audit" in argv:
        tests = json.loads(Path(arg("--tests")).read_text(encoding="utf-8")) if arg("--tests") else None
        jp, mp = write_audit(res, date, tests)
        print(f"audit: {jp.relative_to(ROOT)}, {mp.relative_to(ROOT)}")
    if "--check" in argv:
        bad, losing = check(res)
        for b in bad:
            print("INVARIANT", b)
        for r in losing:
            h = r["headline_at_current"]
            print(f"LOSS {r['id']} sale price ₪{r['current_sale_price_ils']:g} headline ₪{h['contribution_ils']:g} ({h['method']}; {h['quantity']} יח') -> ₪{r['proposed_price_ils']:g}")
        print(f"check: {len(bad)} invariant failures, {len(losing)} products lose at their current price")
        rc = 2 if bad else 1 if losing else 0
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
