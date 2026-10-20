#!/usr/bin/env python3
"""No product loses money, in any scenario (owner, 2026-10-20; docs/studio-rules.md ה.13, amended 2026-10-20).

"בא נוודא שאין דבר כזה מוצר מפסיד בשום צורה! יכול להיות יקר ללקוח אבל אין מפסיד!"

For every product the Studio or the site can sell, this computes the worst-case contribution (before CAC, in the
Studio formula) over all its scenarios, the break-even price, and the no-loss price: the lowest price on the Studio's
usual endings (a whole shekel that ends in 9: 19, 29 ... 149, 159 ...) whose contribution is zero or more in every
scenario. A price is never lowered, and a price the owner set in the Studio is never changed (it is listed instead).

The Studio formula (studio/src/index.html econCalc, the same as site/shared/src/pricing.ts unitEconomics):
    net = P / (1 + vat)            fees = P * card_pct + card_fixed       reserve = net * returns_pct
    landed = (unit cost * q + freight for q) * usd_ils
    contribution = net - landed - fees - reserve - packaging            margin = contribution / net
The customer's delivery fee (₪29 under ₪299, express ₪59 on the site) is not revenue in the Studio formula, so it is
not counted here either (the conservative side).

What the Studio sells is read the way the Studio reads it: studio/build.py is imported and its own loaders run
(load_products, sell_qty_default, lead_records, load_economics), so the unit count, the cost of the sale, the freight
source and the starting price are exactly the Studio's.

Scenarios of one product (every one must give a contribution >= 0):
  * the sale (the units the Studio sells, sell_qty), by every shipping method offered: economy (the cheapest quote)
    and fast (the cheapest quote within 20 days, ה.4), when the supplier has one;
  * one piece of a set (ה.6, P1: a set is also sold singly), at unit_retail_ils or the site's estimate
    (site/shared/src/packs.ts unitPriceEstimateIls), with the freight of one piece;
  * every other supplier option (card `options.skus`, in stock, USD), at the price the site gives it
    (site/shared/src/options.ts skuRetail: the room SKU's price moved by the difference of the 40% recommendations),
    with its own cost and freight, and its single piece;
  * more than one sale in a cart is never worse per sale: freight for more units is at most the sum of the parts.
Freight: every quote found for the room SKU (the Studio's freight file or card SKU, the pricing team's manual figure,
the cached supplier answers in data/sources/aliexpress and data/sources/cj, the final-round record) and the worst of
them per method. A freight for several units that is an estimate (the Studio's $3.72-per-parcel saving) is taken at
its worst case: one parcel per unit (N x the unit quote), unless a real quote for those units exists. A product with
no quote at all takes the worst of the estimates written for it (card notes, the pricing file, the final round), and
is flagged.

  python3 -I scripts/economics/no_loss.py                     # audit, summary on stdout
  python3 -I scripts/economics/no_loss.py --json FILE         # the full audit as JSON
  python3 -I scripts/economics/no_loss.py --apply             # raise the prices in their source of truth, write the
                                                              # change log data/economics/no-loss-changes-<date>.json
  python3 -I scripts/economics/no_loss.py --report [--tests F] # write data/economics/no-loss-audit-<date>.json and .md
                                                              # (F: a JSON of test results to include)
  python3 -I scripts/economics/no_loss.py --check             # exit 1 when a product (not owner-set) still loses
  --db DIR      a Studio db export (DIR/product_edits/<id>.json): prices the owner set there are never changed
  --date YYYY-MM-DD   the date written on changes (default: today)

Importable: audit(), product_scenarios(), worst_case(), no_loss_price(), break_even_price(), contribution().
Only the standard library. Reads cached data only; no supplier is contacted.
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
FAST_DAYS = 20           # ה.4: the fast method = the cheapest option that arrives within 20 days (Studio "under20")
EPS = 1e-9


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
    """The Studio's estimate (shipForQty): unit + (q - 1) * max(0, unit - 3.72)."""
    return unit_usd + (q - 1) * max(0.0, unit_usd - PARCEL_FIXED_USD)


# --------------------------------------------------------------------------- the Studio's view

class Ctx:
    """The Studio's own reading of the repo: cards, sell quantities, economics entries (studio/build.py loaders)."""

    def __init__(self, eco_dir: Path = ECO, db: Path | None = None):
        self.eco_dir = eco_dir
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

def _days_max(d) -> int | None:
    if isnum(d):
        return int(d)
    nums = [int(x) for x in re.findall(r"\d+", str(d or ""))]
    return max(nums) if nums else None


def _methods(options: list[dict]) -> dict:
    """{economy: (usd, label), fast: (usd, label) or None} from [{usd, days, name}] quotes."""
    ok = [o for o in options if isnum(o.get("usd"))]
    if not ok:
        return {}
    eco = min(ok, key=lambda o: o["usd"])
    fast_ok = [o for o in ok if (_days_max(o.get("days")) or 999) <= FAST_DAYS]
    fast = min(fast_ok, key=lambda o: o["usd"]) if fast_ok else None
    lab = lambda o: f"{o.get('name') or ''} {o.get('days') or ''}".strip()
    return {"economy": (float(eco["usd"]), lab(eco)), "fast": (float(fast["usd"]), lab(fast)) if fast else None}


def _ae_item(url: str) -> str | None:
    m = re.search(r"aliexpress\.[a-z.]+/item/(\d+)\.html", url or "", re.I)
    return m.group(1) if m else None


def _cj_pid(url: str) -> str | None:
    m = re.search(r"-p-([^./?#]+)\.html", url or "")
    return m.group(1) if m else None


_SRC_CACHE: dict = {}


def source_quotes(kind: str, pid: str | None) -> dict:
    """{(sku or vid, qty): [{usd, days, name}]} from the cached supplier answers (data/sources/<kind>/<id>.json)."""
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
                                 "name": o.get("company") or o.get("code")})
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


def freight(p: dict, e: dict, ctx: Ctx, n: int) -> dict:
    """The room SKU's freight evidence, per method: unit (one piece), sale (n pieces), single (one piece of the set),
    with where each number comes from and whether it is an estimate."""
    pid, flags, notes = p["id"], [], []
    fr = e.get("freight") or {}
    manual = (e.get("manual") or {}).get("shipping_cost_usd")
    unit = {"economy": [], "fast": []}   # [(usd, source)] quotes for ONE piece
    sale = {"economy": [], "fast": []}   # [(usd, source)] quotes for exactly n pieces (n > 1)
    if fr.get("status") == "no_route":
        return {"no_route": True, "flags": ["no-route"], "notes": [f"{fr.get('src')}: אין משלוח לישראל"]}
    qq = int(fr.get("quoted_qty") or 1)
    for m, key in (("economy", "cheapest"), ("fast", "under20")):
        o = fr.get(key) if m == "fast" else (fr.get("cheapest") or fr.get("under20"))
        if isinstance(o, dict) and isnum(o.get("usd")):
            src = f"Studio {fr.get('src')}: {o.get('name') or ''} {o.get('days') or ''}".strip()
            if qq > 1:
                if qq == n:
                    sale[m].append((float(o["usd"]), src + f" (ל-{qq} יח')"))
                else:  # a quote for qq pieces: per piece at most the whole quote (worst case)
                    unit[m].append((float(o["usd"]), src + f" (ל-{qq} יח', נלקח ליחידה)"))
                    flags.append("freight-quote-other-qty")
            else:
                unit[m].append((float(o["usd"]), src))
    if isnum(manual):
        for m in ("economy", "fast"):  # the Studio uses the manual figure for both methods
            unit[m].append((float(manual), "ידני (data/economics/products.json shipping_cost_usd)"))
    # the cached supplier answers for the room SKU (qty 1 and qty n): the worst quote of each method the Studio offers for
    # this product. A method the Studio does not offer (no quote within 20 days in its freight data) is not added from
    # the cache: "every shipping method offered" is the Studio's (an AliExpress Premium or DHL line it never shows is not)
    offered = {m for m in ("economy", "fast") if unit[m] or sale[m]}
    from_cache = not offered
    if from_cache:
        offered = {"economy"}  # no freight in the Studio: a cached quote beats an estimate, economy only
    sup = p.get("supplier") or {}
    url = sup.get("product_url") or ""
    o = p.get("options") if isinstance(p.get("options"), dict) else {}
    room_sku = str(o.get("default_sku") or sup.get("sku") or "")
    cache = []
    ae = _ae_item(url)
    if ae:
        cache += [(f"מטמון AliExpress {ae} sku {sku}", sku, qty, opts) for (sku, qty), opts in source_quotes("aliexpress", ae).items()
                  if sku == room_sku]
    cj_entry = ctx.freight_files.get("cj", {}).get(pid) or {}
    cpid, vid = cj_entry.get("pid") or _cj_pid(url), cj_entry.get("vid")
    if cpid and not vid:
        vid = cj_vid(cpid, room_sku)
    if cpid and vid:
        cache += [(f"מטמון CJ vid {v}", v, qty, opts) for (v, qty), opts in source_quotes("cj", cpid).items() if v == str(vid)]
    n_cache = 0
    for lab, _sku, qty, opts in cache:
        ms = _methods(opts)
        # no freight in the Studio: a CJ quote is read the way freight-cj.json is (cheapest, and cheapest within 20 days)
        for m in (offered | ({"fast"} if from_cache and lab.startswith("מטמון CJ") else set())):
            if ms.get(m):
                tgt = unit if qty == 1 else sale if qty == n else None
                if tgt is not None:
                    tgt[m].append((ms[m][0], f"{lab} ×{qty}: {ms[m][1]}"))
                    n_cache += 1
    if from_cache and n_cache:
        flags.append("freight-from-cache-only")
        notes.append("לסטודיו אין משלוח למוצר; נלקח ממטמון הספק (חסכוני בלבד)")
    m_other = re.search(r"estimated from SKU (\d+)", p.get("notes") or "")
    if m_other and m_other.group(1) != room_sku and not any("מטמון" in x[1] for x in unit["economy"]):
        flags.append("freight-from-other-sku")
        notes.append(f"המשלוח נמדד על מק\"ט אחר ({m_other.group(1)}), לא על המק\"ט שבחדר: הערכה")
    estimated = False
    if not unit["economy"] and not sale["economy"]:
        # no quote at all: the worst of the estimates written for this product
        ests = []
        t = _est_from_text(p.get("notes") or "")
        if t is not None:
            ests.append((t, "הערות הכרטיס (הערכה)"))
        pr = ctx.pricing.get(pid) or {}
        if isnum(pr.get("ship_usd_per_unit_used")):
            ests.append((float(pr["ship_usd_per_unit_used"]), f"קובץ התמחור: {str(pr.get('ship_src_used') or '')[:80]} (הערכה)"))
        rec = (p.get("_lead_rec") or {}).get("rec") or {}
        if isnum(rec.get("ship_usd")) and rec["ship_usd"] >= 0:
            rq = next((int(rec[k]) for k in ("qty_in_sale", "qty") if isnum(rec.get(k)) and rec[k] >= 1), 1)
            src = f"הליקוט האחרון {p['_lead_rec'].get('file')} (ל-{rq} יח', הערכה)"
            if rq == 1:
                ests.append((float(rec["ship_usd"]), src))
            elif rq == n:
                sale["economy"].append((float(rec["ship_usd"]), src))
        if ests:
            u = max(ests, key=lambda x: x[0])
            unit["economy"].append(u)
            notes.append("משלוח מוערך: " + "; ".join(f"${x[0]:g} {x[1]}" for x in ests))
        if ests or sale["economy"]:
            estimated = True
            flags.append("freight-estimated")
    out = {"no_route": False, "flags": flags, "notes": notes, "estimated": estimated, "methods": {}}
    for m in ("economy", "fast"):
        u = max(unit[m], key=lambda x: x[0]) if unit[m] else None
        sq = max(sale[m], key=lambda x: x[0]) if sale[m] else None
        if u is None and sq is None:
            out["methods"][m] = None
            continue
        if n == 1:
            sale_usd, sale_src, sale_est = u[0], u[1], False
        elif sq is not None:
            sale_usd, sale_src, sale_est = max(sq[0], u[0] if u else 0.0), sq[1], False
        else:  # an estimate for n pieces: its worst case, one parcel per piece
            sale_usd, sale_src, sale_est = n * u[0], f"{n} × {u[1]}", True
        if u is not None:
            single_usd, single_src, single_est = u[0], u[1], False
        else:  # only a quote for the whole set: one piece costs at most that
            single_usd, single_src, single_est = sq[0], sq[1] + " (חבילה אחת לסט, נלקח ליחידה)", True
        studio_usd = None
        if isnum(manual):
            studio_usd = ship_for_qty(float(manual), n) if n > 1 else float(manual)
        out["methods"][m] = {"unit_usd": u[0] if u else None, "unit_src": u[1] if u else None,
                             "sale_usd": round(sale_usd, 4), "sale_src": sale_src, "sale_estimated": sale_est,
                             "single_usd": round(single_usd, 4), "single_src": single_src, "single_estimated": single_est,
                             "all_unit": unit[m], "all_sale": sale[m], "studio_manual_sale_usd": studio_usd}
    if out["methods"].get("economy") is None and out["methods"].get("fast") is None:
        out["missing"] = True
        out["flags"].append("freight-missing")
    elif out["methods"].get("fast") is None:
        out["flags"].append("no-fast-method")
    if n > 1 and any((out["methods"].get(m) or {}).get("sale_estimated") for m in ("economy", "fast")):
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


def product_scenarios(p: dict, e: dict, ctx: Ctx, n_override: int | None = None) -> dict:
    """Inputs and scenarios of one product. Each scenario: {id, kind, method, label_he, landed_ils, price(P) -> ILS}."""
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
    if n_override:
        n = n_override
    cur = str(pr.get("currency") or "USD").upper()
    sale_cost = e.get("sale_cost_usd") if isnum(e.get("sale_cost_usd")) and e["sale_cost_usd"] > 0 else None
    if cur != "USD" and sale_cost is None:
        return {"n": n, "missing": f"עלות במטבע {cur}, לא בדולר", "flags": ["cost-not-usd"], "scenarios": []}
    unit_cost = sale_cost / n if sale_cost is not None else pr.get("cost")
    if not isnum(unit_cost):
        return {"n": n, "missing": "אין עלות", "flags": ["cost-missing"], "scenarios": []}
    unit_cost = float(unit_cost)
    costs = [("cost", unit_cost, "עלות המכירה מקובץ התמחור" if e.get("sale_cost_src") == "pricing" else
              "עלות המכירה מהליקוט" if e.get("sale_cost_src") == "leads" else "עלות הכרטיס")]
    if e.get("sale_cost_src") == "leads":
        # the whole sale's cost comes from the final round's record, and the Studio keeps it only while the price is the
        # record's (card_economics): a raised price goes to a products.json row that carries sale_cost_usd (apply())
        flags.append("sale-cost-from-leads")
    fr = freight(p, e, ctx, n)
    flags += fr["flags"]
    notes += fr["notes"]
    if fr.get("no_route"):
        return {"n": n, "missing": "הספק לא שולח לישראל", "flags": flags, "notes": notes, "scenarios": []}
    if fr.get("missing"):
        return {"n": n, "missing": "אין משלוח ואין הערכה", "flags": flags, "notes": notes, "scenarios": []}
    unit_retail = (ctx.rows.get(pid) or {}).get("unit_retail_ils")
    unit_retail = unit_retail if isnum(unit_retail) and unit_retail > 0 else None
    scen = []
    for m in ("economy", "fast"):
        fm = fr["methods"].get(m)
        if not fm:
            continue
        mh = "חסכוני" if m == "economy" else "מהיר (עד 20 יום)"
        for ck, c, ch in costs:
            scen.append({"id": f"sale/{m}" + ("" if ck == "cost" else f"/{ck}"), "kind": "sale", "method": m,
                         "label_he": f"המכירה ({n} יח'), משלוח {mh}" + ("" if ck == "cost" else f", {ch}"),
                         "landed_ils": (c * n + fm["sale_usd"]) * fx, "freight_usd": fm["sale_usd"],
                         "freight_src": fm["sale_src"], "estimated": fm["sale_estimated"], "price": lambda P: P})
            if n > 1:
                up = (lambda P, n=n: unit_retail) if unit_retail else (lambda P, n=n: unit_price_estimate(P, n))
                scen.append({"id": f"single/{m}" + ("" if ck == "cost" else f"/{ck}"), "kind": "single", "method": m,
                             "label_he": f"יחידה אחת מהסט, משלוח {mh}" + ("" if unit_retail else " (מחיר היחידה: ההערכה של האתר)"),
                             "landed_ils": (c + fm["single_usd"]) * fx, "freight_usd": fm["single_usd"],
                             "freight_src": fm["single_src"], "estimated": fm["single_estimated"], "price": up})
    # the other supplier options, at the price the site gives them (skuRetail with the Studio's price)
    o = p.get("options") if isinstance(p.get("options"), dict) else None
    n_var = 0
    if o and sale_cost is not None and n > 1:
        # a mixed set (the sale's cost is not n x the room SKU's: plates, side plates and bowls, two of each): the card's
        # options are the set's parts, not variants of the sale, so they are not priced as the sale
        flags.append("options-are-set-parts")
        o = None
    if o and cur == "USD":
        skus = [x for x in o.get("skus") or [] if isinstance(x, dict)]
        dflt = next((x for x in skus if x.get("id") == o.get("default_sku")), None)
        dprice = ((dflt or {}).get("price") or {})
        if dflt and str(dprice.get("currency") or "").upper() == "USD" and isnum(dprice.get("amount")):
            dq = (dflt.get("shipping_il") or {})
            eco_unit = (fr["methods"].get("economy") or fr["methods"].get("fast"))["single_usd"]
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
                ov = (((ctx.rows.get(pid) or {}).get("sku_retail_ils")) or {}).get(str(x.get("id")))
                if isnum(ov) and ov > 0:
                    xprice = (lambda P, v=ov: v)
                elif rec_x is None or rec_d is None:
                    continue
                else:
                    xprice = (lambda P, rx=rec_x, rd=rec_d: (P + (rx - rd)) if P + (rx - rd) > 0 else rx)
                n_var += 1
                own = {}
                for (sku, qty), opts in cache.items():
                    if sku == str(x.get("id")) and qty == 1:
                        own = _methods(opts)
                lab = ", ".join(f"{k}={v}" for k, v in (x.get("values") or {}).items())[:80]
                for m in ("economy", "fast"):
                    fm = fr["methods"].get(m)
                    if not fm:
                        continue
                    # the room SKU's (worst-case) freight moved by the SKU's own difference, never below the SKU's own quote
                    u = max(0.0, fm["single_usd"] + delta)
                    sale_usd = max(0.0, fm["sale_usd"] + n * delta)
                    if own.get(m):
                        u = max(u, own[m][0])
                        sale_usd = max(sale_usd, n * own[m][0])
                    mh = "חסכוני" if m == "economy" else "מהיר"
                    scen.append({"id": f"variant/{x.get('id')}/{m}", "kind": "variant", "method": m, "sku": x.get("id"),
                                 "label_he": f"אפשרות {lab}, משלוח {mh} (מחיר האפשרות לפי האתר)",
                                 "landed_ils": (xc * n + sale_usd) * fx, "freight_usd": sale_usd,
                                 "freight_src": "ההפרש של המק\"ט + " + str(fm["single_src"]), "estimated": n > 1 or not own.get(m),
                                 "price": xprice})
                    if n > 1:
                        scen.append({"id": f"variant-single/{x.get('id')}/{m}", "kind": "variant-single", "method": m,
                                     "sku": x.get("id"), "label_he": f"יחידה אחת, אפשרות {lab}, משלוח {mh}",
                                     "landed_ils": (xc + u) * fx, "freight_usd": u, "freight_src": "ההפרש של המק\"ט",
                                     "estimated": True,
                                     "price": (lambda P, f=xprice, n=n: unit_price_estimate(f(P), n))})
    # what the Studio itself shows (its own freight: the manual figure or the method's quote, shipForQty for n units)
    studio = studio_shown(p, e, ctx, n, unit_cost)
    return {"n": n, "unit_cost_usd": unit_cost, "costs": costs, "freight": fr, "scenarios": scen, "flags": sorted(set(flags)),
            "notes": notes, "variants": n_var, "studio": studio, "unit_retail_ils": unit_retail}


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
    return {"freight_usd": round(tot, 4), "src": src, "landed_ils": (unit_cost * n + tot) * ctx.s["usd_ils"]}


def worst_case(P: float, scen: list[dict], s: dict) -> tuple[float, dict | None, float | None]:
    """(lowest contribution over the scenarios at price P, that scenario, the price it is sold at)."""
    best = (math.inf, None, None)
    for x in scen:
        R = x["price"](P)
        c = contribution(R, x["landed_ils"], s)
        if c < best[0]:
            best = (c, x, R)
    return best


def _pick(scen, kinds=None, methods=None):
    return [x for x in scen if (kinds is None or x["kind"] in kinds) and (methods is None or x["method"] in methods)]


def no_loss_price(P0: float | None, scen: list[dict], s: dict, kinds: set | None = None, methods: set | None = None) -> int | None:
    """The lowest price >= P0 (never lower) on the ...9 endings with a contribution >= 0 in every scenario."""
    sc = _pick(scen, kinds, methods)
    if not sc:
        return None
    P = P0 if (P0 and worst_case(P0, sc, s)[0] >= -EPS) else None
    if P is not None:
        return P0
    P = charm_up((P0 or 9) + (1 if P0 else 0))
    while P < 1_000_000:
        if worst_case(P, sc, s)[0] >= -EPS:
            return P
        P += 10
    return None


def break_even_price(scen: list[dict], s: dict, kinds: set | None = None, methods: set | None = None) -> float | None:
    """The (continuous) product price at which the worst scenario breaks even."""
    sc = _pick(scen, kinds, methods)
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

def coverage_counted() -> dict:
    """card id -> [(slot, style)] the coverage script counts (final_round_coverage.py results() + the packs' picks)."""
    cwd = os.getcwd()
    out: dict = {}
    try:
        spec = importlib.util.spec_from_file_location("final_round_coverage_for_no_loss", COVERAGE_PY)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)  # it moves to the repo root; restored below
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
            rows.append({"id": pid, "scope": scope, "status": "no-card", "missing": "אין כרטיס במוצרים"})
            continue
        e = ctx.E.get(pid, {})
        src = price_source(p, e, ctx)
        P0 = src.get("retail_ils")
        P0 = P0 if isnum(P0) and P0 > 0 else None
        sc = product_scenarios(p, e, ctx)
        r = {"id": pid, "card": p["_path"], "slot": p.get("_slot_key"), "scope": scope,
             "counted_in": sorted({f"{a}:{b}" for a, b in counted.get(pid, [])}),
             "price_source": {k: v for k, v in src.items() if k != "retail_ils"}, "price_ils": P0, "sale_units": sc["n"],
             "flags": sc.get("flags", []), "notes": sc.get("notes", [])}
        if not sc["scenarios"]:
            r.update(status="cannot-compute", missing=sc.get("missing"))
            rows.append(r)
            continue
        scen = sc["scenarios"]
        sale_kinds = {"sale"}
        P_sale = no_loss_price(P0, scen, s, sale_kinds)
        P_single = no_loss_price(P0, scen, s, {"sale", "single"})
        P_all = no_loss_price(P0, scen, s)
        P_eco = no_loss_price(P0, scen, s, methods={"economy"})
        P_eco_sale = no_loss_price(P0, scen, s, kinds=sale_kinds, methods={"economy"})
        w0 = worst_case(P0, scen, s) if P0 else (None, None, None)
        be = break_even_price(scen, s)
        hc, hc_src = highest_comp(p, e, ctx, sc["n"])
        if "qty-inferred-from-landed" in sc.get("flags", []):
            one = product_scenarios(p, e, ctx, n_override=1)
            r["if_one_unit"] = {"no_loss_ils": no_loss_price(None, one["scenarios"], s) if one["scenarios"] else None,
                                "note_he": f"הסטודיו מניח {sc['n']} יח' לפי עלות הנחיתה ברשומה; אם המכירה היא יחידה אחת, זה המחיר שלא מפסיד"}
        r.update({
            "unit_cost_usd": round(sc["unit_cost_usd"], 4), "variants_checked": sc["variants"],
            "scenarios": len(scen), "freight": {m: ({k: v for k, v in (sc["freight"]["methods"].get(m) or {}).items()
                                                      if k in ("unit_usd", "unit_src", "sale_usd", "sale_src", "sale_estimated", "single_usd", "single_estimated")}
                                                     if sc["freight"]["methods"].get(m) else None) for m in ("economy", "fast")},
            "studio_shown": None,
            "worst_at_price": None if w0[1] is None else {"contribution_ils": round(w0[0], 2), "scenario": w0[1]["id"],
                                                          "label_he": w0[1]["label_he"], "sold_at_ils": w0[2],
                                                          "landed_ils": round(w0[1]["landed_ils"], 2), "freight_src": w0[1]["freight_src"]},
            "break_even_ils": be, "no_loss_ils": P_all, "no_loss_sale_only_ils": P_sale, "no_loss_with_single_ils": P_single,
            "no_loss_economy_only_ils": P_eco, "no_loss_economy_sale_ils": P_eco_sale,
            "highest_comp_ils": round(hc, 2) if hc else None, "highest_comp_src": hc_src,
        })
        st = sc.get("studio")
        if st and P0:
            r["studio_shown"] = {"contribution_ils": round(contribution(P0, st["landed_ils"], s), 2),
                                 "margin_pct": round(100 * margin(P0, st["landed_ils"], s), 1), "freight_usd": st["freight_usd"],
                                 "src": st["src"], "landed_ils": round(st["landed_ils"], 2),
                                 "contribution_with_fee_ils": round(contribution(P0 + 29, st["landed_ils"], s), 2) if P0 < 299 else None}
        if P0 is None:
            r["status"] = "no-price"
        elif w0[0] >= -EPS:
            r["status"] = "ok"
        elif src["kind"] == "owner":
            r["status"] = "owner-set-loses"
        else:
            r["status"] = "raise"
        rows.append(r)
    return {"settings": s, "rows": rows, "ctx": ctx}


def floor_flag(m: float | None, s: dict) -> str:
    return "ok" if m is not None and m >= s["target_margin_pct"] / 100 - EPS else "below-floor"


# --------------------------------------------------------------------------- apply

def _dump(path: Path, data) -> None:
    """Write JSON in the file's own format (indent, trailing newline), validated before it is written."""
    indent, nl = 1, "\n"
    if path.exists():
        old = path.read_text(encoding="utf-8")
        m = re.match(r"[{\[]\n( +)", old)
        indent = len(m.group(1)) if m else 1
        nl = "\n" if old.endswith("\n") else ""
    txt = json.dumps(data, ensure_ascii=False, indent=indent) + nl
    json.loads(txt)  # valid JSON before it is written
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


def apply(res: dict, date: str) -> dict:
    """Raise every losing price to its no-loss price in its source of truth:
      products.json row   -> its retail_ils (the old one kept as retail_before_no_loss_ils, retail_src initial-no-loss-<date>)
      the card's own price -> that field (price.retail_ils or price.suggested_retail)
      the final round's record -> a price.retail_ils on the card, which the Studio reads before the record
                              (studio/build.py card_economics); the results file is left as it is
      a record whose sale cost is not N x the card's (a mixed set) -> a products.json row with that sale_cost_usd, so the
                              Studio keeps the whole sale's cost (it drops the record's cost once the price differs)
    A price the owner set is never changed; it is listed."""
    ctx: Ctx = res["ctx"]
    pj_path = ctx.eco_dir / "products.json"
    pj = json.loads(pj_path.read_text(encoding="utf-8"))
    rows = pj["products"]
    changes, owner, cannot = [], [], []
    card_edits: dict[str, dict] = {}
    for r in res["rows"]:
        st = r.get("status")
        if st == "owner-set-loses":
            owner.append(r)
            continue
        if st in ("cannot-compute", "no-card"):
            cannot.append(r)
            continue
        if st != "raise":
            continue
        new, old = r["no_loss_ils"], r["price_ils"]
        if new is None or not new > old:
            continue
        src = r["price_source"]
        w = r["worst_at_price"]
        p = ctx.by_id[r["id"]]
        e = ctx.E.get(r["id"], {})
        kind = src["kind"]
        if kind == "leads" and "sale-cost-from-leads" in r["flags"]:
            target, fld = "products.json (שורה חדשה)", f"products.{r['id']}"
        elif kind == "leads":
            target, fld = src["card"], "price.retail_ils"
        elif kind == "card":
            target, fld = src["where"], src["field"]
        else:
            target, fld = "data/economics/products.json", src["field"]
        reason = (f"בתרחיש הגרוע ({w['label_he']}) התרומה ₪{w['contribution_ils']:g} במחיר ₪{old:g}; "
                  f"המחיר הנמוך שלא מפסיד באף תרחיש: ₪{new:g} (נקודת איזון ₪{r['break_even_ils']:g})")
        hc = r.get("highest_comp_ils")
        ch = {"id": r["id"], "price_source": kind, "file": target, "field": fld,
              "old_price_ils": old, "new_price_ils": new, "sale_units": r["sale_units"],
              "worst_scenario": w["scenario"], "worst_scenario_he": w["label_he"], "worst_sold_at_ils": w["sold_at_ils"],
              "worst_contribution_at_old_ils": w["contribution_ils"], "worst_landed_ils": w["landed_ils"],
              "worst_freight_src": w["freight_src"], "break_even_ils": r["break_even_ils"],
              "no_loss_economy_only_ils": r.get("no_loss_economy_only_ils"), "no_loss_sale_only_ils": r.get("no_loss_sale_only_ils"),
              "highest_comp_ils": hc, "highest_comp_src": r.get("highest_comp_src"),
              "ratio_to_highest_comp": round(new / hc, 2) if hc else None, "above_market": bool(hc and new > hc),
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
                row["price_for_qty"] = r["sale_units"]  # the price is now for the sale as the Studio sells it
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
    # the cards (their own price, or a price over the final round's record)
    for f, ed in card_edits.items():
        path = ROOT / f
        card = json.loads(path.read_text(encoding="utf-8"))
        fld = ed["field"].split(".", 1)[1]
        card.setdefault("price", {})[fld] = ed["new"]
        note = (f"[no-loss {date}] מחיר לצרכן ₪{ed['new']:g} (היה ₪{ed['old']:g}): המחיר הנמוך שלא מפסיד באף תרחיש "
                f"(ה.13, 2026-10-20; data/economics/no-loss-changes-{date}.json).")
        notes = card.get("notes") or ""
        if f"[no-loss {date}]" not in notes:
            card["notes"] = (notes.rstrip() + "\n" + note) if notes.strip() else note
        _dump(path, card)
    return {"changes": changes, "owner": owner, "cannot": cannot, "pj": pj, "pj_path": pj_path}


def refresh_rows(res: dict, pj: dict, date: str, before: dict) -> list[dict]:
    """products.json, from the audit AFTER the raise: margin, contribution and flags at the row's price as the Studio reads
    it, and the no-loss facts. `flag` stays the floor flag the Studio, the boards and the site read (ok >= 40%,
    below-floor 0-40%; "loss" only where the Studio's own reading is still negative), and `flags` adds "above-market"
    (raised above the highest comparable) and "loses-in-worst-case" (an owner-set price that loses in a scenario).
    Returns the rows whose flag, margin or contribution changed against `before` (the file as it was)."""
    ctx: Ctx = res["ctx"]
    s = ctx.s
    out = []
    by = {r["id"]: r for r in res["rows"]}
    for pid, row in pj["products"].items():
        r = by.get(pid)
        old = {k: (before.get(pid) or {}).get(k) for k in ("retail_ils", "flag", "margin_pct", "contribution_ils")}
        if not r or r.get("status") in ("cannot-compute", "no-card", "no-price"):
            if r and r.get("status") == "cannot-compute":
                row["no_loss"] = {"date": date, "cannot_compute": r.get("missing"), "flags": r.get("flags")}
            continue
        P = row["retail_ils"]
        st = r.get("studio_shown")
        if st:
            row["contribution_ils"] = st["contribution_ils"]
            row["margin_pct"] = st["margin_pct"]
            row["contribution_with_fee_ils"] = st.get("contribution_with_fee_ils")
        loses = r.get("status") in ("owner-set-loses", "raise")
        raised = row.get("retail_src") == f"initial-no-loss-{date}"
        hc = r.get("highest_comp_ils")
        if st and st["contribution_ils"] < 0:
            row["flag"] = "loss"
        else:
            row["flag"] = floor_flag(st["margin_pct"] / 100 if st else None, s)
        flags = [row["flag"]]
        above = bool(raised and hc and P > hc)
        if above:
            flags.append("above-market")
        if loses:
            flags.append("loses-in-worst-case")
        row["flags"] = flags
        row["customer_total_ils"] = P if P >= 299 else P + 29
        iv = row.get("il_value") or {}
        if isnum(iv.get("typical")) and iv["typical"] > 0:
            row["vs_typical_pct"] = round(100 * (row["customer_total_ils"] - iv["typical"]) / iv["typical"])
        w = r.get("worst_at_price") or {}
        nl = {"date": date, "worst_contribution_ils": w.get("contribution_ils"), "worst_scenario": w.get("scenario"),
              "worst_scenario_he": w.get("label_he"), "break_even_ils": r["break_even_ils"], "no_loss_ils": r["no_loss_ils"],
              "no_loss_economy_only_ils": r.get("no_loss_economy_only_ils"),
              "highest_comp_ils": hc, "ratio_to_highest_comp": round(P / hc, 2) if hc else None, "above_market": above,
              "estimated_inputs": [f for f in r["flags"] if "estimated" in f or "missing" in f or "other-sku" in f or "cache" in f],
              "scenarios": r.get("scenarios"), "variants_checked": r.get("variants_checked")}
        if r.get("status") == "owner-set-loses":
            nl["owner_set"] = True
        if raised:
            nl["raised_from_ils"] = row.get("retail_before_no_loss_ils")
        row["no_loss"] = nl
        new = {"retail_ils": P, "flag": row.get("flag"), "margin_pct": row.get("margin_pct"), "contribution_ils": row.get("contribution_ils")}
        if old != new:
            out.append({"id": pid, "old": old, "new": new, "flags": flags})
    return out


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


def _coverage_module():
    spec = importlib.util.spec_from_file_location("final_round_coverage_for_no_loss_gain", COVERAGE_PY)
    m = importlib.util.module_from_spec(spec)
    cwd = os.getcwd()
    try:
        spec.loader.exec_module(m)
    finally:
        os.chdir(cwd)
    return m


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


def rejected_loss_only(s: dict) -> dict:
    """Round-5 and round-6 candidates without a card, fit 7+, rejected only because they lost money: their no-loss price
    (economy, the record's own freight for the sale), the ratio to the highest Israeli price, and the coverage gain per
    style if they were counted. Report only: no result file and no coverage file is written."""
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
                landed = c.get("landed_ils") if isnum(c.get("landed_ils")) and c["landed_ils"] > 0 else None
                if landed is None and isnum(c.get("cost_usd")) and isnum(c.get("ship_usd")) and c["cost_usd"] > 0:
                    landed = (c["cost_usd"] * q + c["ship_usd"]) * s["usd_ils"]
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
                row.update({"sale_units": q, "landed_ils": round(landed, 2) if landed else None, "record_price_ils": c.get("price_ils"),
                            "break_even_ils": be, "no_loss_ils": nl, "highest_comp_ils": hc, "highest_comp_src": hsrc,
                            "ratio_to_highest_comp": round(nl / hc, 2) if nl and hc else None,
                            "scope_he": "חסכוני בלבד, לפי המשלוח שברשומה; אין כרטיס, ולכן משלוח מהיר, אפשרויות ויחידה בודדת לא נבדקו"})
                keep.append(row)
    # coverage gain: every kept candidate counted as a card with its fit (one listing per supplier item)
    base = coverage_counts()
    extra: dict = {}
    for r in keep:
        key = f"{str(r['source'] or 'x').lower()}:{r['id']}"
        rec_vf = {}
        for k, v in r["fit_7_plus"].items():
            extra.setdefault(k, {}).setdefault(r["slot"], {})[key] = 1
            rec_vf[k] = 1
    after = coverage_counts(extra)
    gain = {st: {"eligible": base[st]["eligible"], "ready_before": base[st]["ready"], "ready_after": after[st]["ready"],
                 "slots_gained": after[st]["ready"] - base[st]["ready"],
                 "pct_before": base[st]["pct_ready"], "pct_after": after[st]["pct_ready"],
                 "pct_points": round(after[st]["pct_ready"] - base[st]["pct_ready"], 1),
                 "one_ready_before": base[st]["one_ready"], "one_ready_after": after[st]["one_ready"]} for st in base}
    tot_e = sum(g["eligible"] for g in gain.values())
    gain["total"] = {"eligible": tot_e, "ready_before": sum(g["ready_before"] for g in gain.values()),
                     "ready_after": sum(g["ready_after"] for g in gain.values() if isinstance(g, dict) and "ready_after" in g)}
    gain["total"]["pct_before"] = round(100 * gain["total"]["ready_before"] / tot_e, 1)
    gain["total"]["pct_after"] = round(100 * gain["total"]["ready_after"] / tot_e, 1)
    return {"reviewed": reviewed, "kept": keep, "unreviewed": unknown, "coverage": gain,
            "method_he": "כל מועמד בלי כרטיס בהתאמה 7+ שהרשומה שלו מפסידה נקרא ידנית: 'in' רק כשההפסד הוא סיבת הדחייה היחידה. "
                         "הרווח בכיסוי מחושב בכלל של final_round_coverage.py (פונקציות הסקריפט, בלי לכתוב קובץ), כאילו לכל מועמד יש כרטיס "
                         "באפשרות אחת (צבע אחד) בסגנונות שבהם ההתאמה 7+."}


# --------------------------------------------------------------------------- report

FORMULA_DIFFS = [
    {"topic": "נוסחת התרומה", "studio": "studio/src/index.html econCalc: נטו = P/1.18; עמלה = 2%·P + ₪1.2; שמורה = 8% מהנטו; אריזה 0; תרומה = נטו − נחיתה − עמלה − שמורה",
     "site": "site/shared/src/pricing.ts unitEconomics: אותה נוסחה, באגורות (עיגול בכל שלב, הפרש של אגורות)", "same": True},
    {"topic": "הגדרות", "studio": "data/economics/settings.json + ברירות המחדל של ECON_META (שער 3.3, מע\"מ 18%, 2% + ₪1.2, החזרות 8%, יעד 40%)",
     "site": "site/shared/src/schema/economics.ts DEFAULT_SETTINGS + resolveSettings: אותם ערכים", "same": True},
    {"topic": "משלוח לכמות", "studio": "יחידה + (q − 1) × max(0, יחידה − $3.72) (הערכה); הצעה שנמדדה לכל המכירה (quoted_qty = q) נלקחת כמו שהיא",
     "site": "cogs = (עלות + משלוח) × q: ליניארי, בלי חיסכון החבילה; הצעה לכל המכירה (משלוח הליקוט, sale_shipping) נכפלת ב-q", "same": False},
    {"topic": "מקור המשלוח", "studio": "ידני (products.json) ← freight-cj / freight-zendrop / freight-aliexpress ← המק\"ט בכרטיס ← רשומת הסבב האחרון",
     "site": "ידני ← freight-cj.json בלבד ← ברירת מחדל $17: למוצרי AliExpress ו-Zendrop בלי משלוח ידני האתר מחשב $17", "same": False},
    {"topic": "מקור המחיר", "studio": "עריכה בסטודיו (db) ← products.json retail_ils ← מחיר בכרטיס (price.retail_ils / suggested_retail) ← price_ils ברשומת הסבב",
     "site": "products.json retail_ils בלבד; בלי שורה: מחיר מומלץ ב-40% (זמני), ובבנייה קפדנית לא מוצג. מחירי הכרטיס והסבב לא מגיעים לאתר", "same": False},
    {"topic": "אפשרויות הספק (וריאנטים)", "studio": "רק המק\"ט שבחדר",
     "site": "options.ts skuRetail: P + (המומלץ של האפשרות − המומלץ של המק\"ט שבחדר). אפשרות זולה יורדת במחיר פי ~2.4 מהירידה בעלות, ומפסידה ~0.8 מהפרש העלות; בבנייה קפדנית אפשרות בלי sku_retail_ils לא נמכרת", "same": False},
    {"topic": "יחידה אחת מסט (P1)", "studio": "לא מוצג", "site": "packs.ts unitPriceEstimateIls: ceil(P/N × 1.15) מעוגל מטה ל-9, או unit_retail_ils", "same": False},
    {"topic": "דמי משלוח ללקוח", "studio": "לא נספרים כהכנסה", "site": "₪29 (חינם מ-₪299), מהיר ₪59; לא נספרים בתרומה", "same": True},
]


def write_reports(res: dict, date: str, tests: dict | None) -> tuple[Path, Path]:
    ctx: Ctx = res["ctx"]
    s = ctx.s
    log_p = ECO / f"no-loss-changes-{date}.json"
    log = json.loads(log_p.read_text(encoding="utf-8")) if log_p.exists() else {"changes": []}
    ch = log.get("changes") or []
    rej = rejected_loss_only(s)
    rows = res["rows"]
    from collections import Counter
    by_src = Counter(c["price_source"] for c in ch)
    above = sorted([c for c in ch if c.get("above_market")], key=lambda c: -(c.get("ratio_to_highest_comp") or 0))
    still = [r for r in rows if r.get("status") == "raise"]
    owner = [r for r in rows if r.get("status") == "owner-set-loses"]
    cannot = [r for r in rows if r.get("status") == "cannot-compute"]
    noprice = [r for r in rows if r.get("status") == "no-price"]
    truth = Counter(r["price_source"]["kind"] for r in rows if "price_source" in r)
    # where each price lived before this change (a final-round price now on the card or in a new products.json row)
    truth_before = Counter(truth)
    for c in ch:
        if c["price_source"] == "leads":
            truth_before["leads"] += 1
            truth_before["products.json" if str(c["file"]).startswith("products.json") else "card"] -= 1
    checks = [r for r in rows if "qty-inferred-from-landed" in (r.get("flags") or []) and r["id"] in {c["id"] for c in ch}]
    est = Counter(f for r in rows if r.get("status") in ("ok", "owner-set-loses") for f in (r.get("flags") or [])
                  if "estimated" in f or "other-sku" in f or "cache" in f or "no-fast" in f)
    ratios = [c["new_price_ils"] / c["old_price_ils"] for c in ch]
    cause = Counter()
    for c in ch:
        sc = c["worst_scenario"].split("/")
        cause[(sc[0], sc[-1] if sc[-1] in ("economy", "fast") else sc[1] if len(sc) > 1 else "")] += 1
    fast_only = [c for c in ch if c.get("no_loss_economy_only_ils") is not None and c["no_loss_economy_only_ils"] <= c["old_price_ils"]]
    out = {
        "date": date, "rule": "docs/studio-rules.md ה.13 (2026-10-20): אין מוצר מפסיד בשום צורה; יכול להיות יקר ללקוח",
        "script": "python3 -I scripts/economics/no_loss.py --apply / --report / --check",
        "settings": s,
        "formula": {"contribution": "net − landed − (card_pct·P + card_fixed) − returns_pct·net − packaging; net = P/(1+vat); landed = (unit cost·q + freight for q)·usd_ils",
                    "price_endings": "שקל שלם שנגמר ב-9 (charmRoundUpIls של האתר)", "compare": FORMULA_DIFFS,
                    "agree": "נוסחת התרומה וההגדרות זהות; הקלטים שונים: משלוח לכמות, מקור המשלוח, מקור המחיר, האפשרויות והיחידה הבודדת (ראו compare)"},
        "price_truth": {"counts_after": dict(truth), "counts_before": {k: v for k, v in truth_before.items() if v}, "where": {
            "products.json": "data/economics/products.json products.<id>.retail_ils: הסטודיו והאתר",
            "owner": "עריכה בסטודיו (db product_edits), מסונכרנת ל-products.json עם retail_src studio",
            "card": "כרטיס המוצר price.suggested_retail או price.retail_ils: הסטודיו בלבד",
            "leads": "price_ils ברשומת הסבב האחרון (data/leads/final-2026-10-13/results/*.json): הסטודיו בלבד, דרך room_boards.Context; מחיר חדש נרשם בכרטיס (price.retail_ils), שהסטודיו קורא לפני הרשומה, והרשומה לא משתנה",
            "pricing": "data/economics/pricing/*-2026-10-11.json: המקור שממנו נבנה products.json; אף אחד לא קורא אותו היום (היסטוריה)"}},
        "scenarios_he": ["המכירה (sell_qty) במשלוח חסכוני ובמשלוח מהיר (עד 20 יום) כשהסטודיו מציע אותו",
                         "יחידה אחת מסט (P1), במחיר היחידה של האתר",
                         "כל אפשרות ספק במלאי, במחיר שהאתר נותן לה, ויחידה אחת ממנה",
                         "כמה מכירות בסל: לא גרוע יותר (משלוח לכמה יחידות ≤ סכום החלקים)",
                         "משלוח: ההצעה הגרועה מכל המקורות לכל שיטה; משלוח לכמה יחידות שהוא הערכה = חבילה לכל יחידה; בלי הצעה בכלל = ההערכה הגבוהה, מסומן"],
        "summary": {"audited": len(rows), "by_status": dict(Counter(r.get("status") for r in rows)),
                    "raised": len(ch), "raised_by_source": dict(by_src),
                    "raise_ratio_min": round(min(ratios), 2) if ratios else None, "raise_ratio_median": round(sorted(ratios)[len(ratios) // 2], 2) if ratios else None,
                    "raise_ratio_max": round(max(ratios), 2) if ratios else None,
                    "old_price_range_ils": [min(c["old_price_ils"] for c in ch), max(c["old_price_ils"] for c in ch)] if ch else None,
                    "new_price_range_ils": [min(c["new_price_ils"] for c in ch), max(c["new_price_ils"] for c in ch)] if ch else None,
                    "binding_scenario": {f"{k[0]}/{k[1]}": v for k, v in cause.items()},
                    "raised_only_for_fast_method": len(fast_only),
                    "above_market": len(above), "above_market_max_ratio": above[0]["ratio_to_highest_comp"] if above else None,
                    "still_losing_not_owner": len(still), "owner_set_losing": len(owner), "cannot_compute": len(cannot),
                    "counted_without_price": len(noprice)},
        "raised": ch,
        "above_market": [{k: c.get(k) for k in ("id", "old_price_ils", "new_price_ils", "highest_comp_ils", "highest_comp_src", "ratio_to_highest_comp", "worst_scenario_he")} for c in above],
        "owner_set": [{"id": r["id"], "price_ils": r["price_ils"], "where": r["price_source"]["where"], "worst": r.get("worst_at_price"),
                       "no_loss_ils": r.get("no_loss_ils"), "break_even_ils": r.get("break_even_ils"),
                       "studio_shown": r.get("studio_shown")} for r in owner],
        "cannot_compute": [{"id": r["id"], "price_ils": r.get("price_ils"), "missing": r.get("missing"), "flags": r.get("flags"), "scope": r.get("scope")} for r in cannot],
        "counted_without_price": [{"id": r["id"], "slot": r.get("slot"), "break_even_ils": r.get("break_even_ils"), "no_loss_ils": r.get("no_loss_ils"),
                                   "flags": r.get("flags")} for r in noprice],
        "quantity_checks": [{"id": r["id"], "studio_units": r["sale_units"], "price_ils": r["price_ils"],
                             "raised_from_ils": next((c["old_price_ils"] for c in ch if c["id"] == r["id"]), None),
                             "if_one_unit": r.get("if_one_unit")} for r in checks],
        "estimated_inputs": dict(est),
        "tests": tests,
        "rejected_candidates": rej,
        "rows": rows,
    }
    jp = ECO / f"no-loss-audit-{date}.json"
    _dump(jp, out)
    mp = ECO / f"no-loss-audit-{date}.md"
    mp.write_text(render_md(out), encoding="utf-8")
    return jp, mp


def _ils(x):
    return "—" if x is None else f"₪{x:,.0f}" if float(x).is_integer() else f"₪{x:,.2f}"


def render_md(o: dict) -> str:
    S = o["summary"]
    L = [f"# אין מוצר מפסיד: ביקורת ותיקון מחירים ({o['date']})", "",
         "הכלל (ה.13, תיקון 2026-10-20): \"בא נוודא שאין דבר כזה מוצר מפסיד בשום צורה! יכול להיות יקר ללקוח אבל אין מפסיד!\". "
         "לכל מוצר שהסטודיו או האתר יכולים למכור חושבה התרומה בתרחיש הגרוע ביותר, ומחיר שמפסיד הועלה למחיר הנמוך שלא מפסיד, "
         "גם מעל ההשוואה הישראלית הגבוהה. שום מחיר לא ירד, ומחיר שהמשתמש קבע בסטודיו לא שונה.", "",
         "הסקריפט: `python3 -I scripts/economics/no_loss.py` (ביקורת), `--apply` (תיקון), `--report` (הדוח הזה), `--check` (יוצא ב-1 אם נשאר מוצר מפסיד).", "",
         "## בקצרה", "",
         f"- נבדקו {S['audited']} מוצרים: כל שורה ב-products.json, כל כרטיס שסקריפט הכיסוי סופר, וכל כרטיס שיש לו מחיר בסטודיו.",
         f"- הועלו {S['raised']} מחירים ({', '.join(f'{k} {v}' for k, v in S['raised_by_source'].items())}). "
         f"מ-{_ils(S['old_price_range_ils'][0])}–{_ils(S['old_price_range_ils'][1])} ל-{_ils(S['new_price_range_ils'][0])}–{_ils(S['new_price_range_ils'][1])}; "
         f"פי {S['raise_ratio_min']} עד פי {S['raise_ratio_max']} (חציון פי {S['raise_ratio_median']})." if S.get("raised") else "- לא הועלה אף מחיר.",
         f"- {S['above_market']} מוצרים יקרים מהשוק עכשיו (מעל ההשוואה הגבוהה), היחס הגבוה פי {S['above_market_max_ratio']}.",
         f"- {S['raised_only_for_fast_method']} מהמחירים הועלו רק בגלל המשלוח המהיר: במשלוח חסכוני בלבד המחיר הקודם לא הפסיד.",
         f"- מוצרים שעדיין מפסידים (לא של המשתמש): {S['still_losing_not_owner']}. מחיר של המשתמש שמפסיד: {S['owner_set_losing']}. "
         f"אי אפשר לחשב: {S['cannot_compute']}. כרטיסים שנספרים בכיסוי בלי מחיר בכלל: {S['counted_without_price']}.", "",
         "## הנוסחה, ואיפה המחיר חי", "",
         f"- תרומה = נטו − נחיתה − (2% מהמחיר + ₪1.2) − 8% מהנטו; נטו = מחיר ÷ 1.18; נחיתה = (עלות ליחידה × כמות + משלוח לכמות) × 3.3. "
         "לפני CAC. דמי המשלוח שהלקוח משלם (₪29, מהיר ₪59) לא נספרים, כמו בסטודיו.",
         "- סיומת המחיר: שקל שלם שנגמר ב-9 (19, 29 … 149, 159), כמו המחירים בקובץ התמחור ו-charmRoundUpIls של האתר.", ""]
    L += ["| מקור המחיר | לפני | אחרי | מי קורא אותו |", "| --- | --- | --- | --- |"]
    who = o["price_truth"]["where"]
    cb, ca = o["price_truth"]["counts_before"], o["price_truth"]["counts_after"]
    for k in ("products.json", "owner", "card", "leads", "none"):
        L.append(f"| {k} | {cb.get(k, 0)} | {ca.get(k, 0)} | {who.get(k, 'אין מחיר: כרטיס שנספר בכיסוי או שאין לו משלוח')} |")
    L += ["", f"- {who['pricing']}", "", "### הסטודיו מול האתר", "", "| נושא | הסטודיו | האתר | זהה |", "| --- | --- | --- | --- |"]
    for d in o["formula"]["compare"]:
        L.append(f"| {d['topic']} | {d['studio']} | {d['site']} | {'כן' if d['same'] else 'לא'} |")
    L += ["", f"מסקנה: {o['formula']['agree']}. לא נבחרה אחת מהן בשקט: הביקורת לוקחת את הגרוע מבין השתיים בכל נקודה "
          "(משלוח לכמות כחבילה לכל יחידה, מחיר האפשרות והיחידה הבודדת כמו באתר, משלוח מכל המקורות של הסטודיו).", "",
          "## התרחישים", ""] + [f"- {x}" for x in o["scenarios_he"]]
    L += ["", "## מה הועלה", "",
          "\"חסכוני בלבד\" = המחיר שהיה מספיק אילו המשלוח המהיר לא היה מוצע במוצר (לא הוחל; להחלטת המשתמש).", "",
          "| מוצר | מקור | היה | עכשיו | חסכוני בלבד | התרחיש הגרוע | השוואה גבוהה | פי מההשוואה |", "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for c in sorted(o["raised"], key=lambda c: -c["new_price_ils"] / c["old_price_ils"]):
        L.append(f"| `{c['id']}` | {c['price_source']} | {_ils(c['old_price_ils'])} | {_ils(c['new_price_ils'])} | {_ils(c.get('no_loss_economy_only_ils'))} | "
                 f"{c['worst_scenario_he']} | {_ils(c.get('highest_comp_ils'))} | {c.get('ratio_to_highest_comp') or '—'} |")
    L += ["", f"התרחיש שקבע את המחיר: " + ", ".join(f"{k} {v}" for k, v in S["binding_scenario"].items()) + ".", "",
          "## יקר מהשוק", "", f"{S['above_market']} מוצרים. מסומנים `above-market` ב-`flags` וב-`no_loss` של השורה (הסטודיו עוד לא מציג תווית כזו: build.py מעביר רק ok, below-floor ו-loss).", "",
          "| מוצר | מחיר חדש | השוואה גבוהה | יחס |", "| --- | --- | --- | --- |"]
    for a in o["above_market"]:
        L.append(f"| `{a['id']}` | {_ils(a['new_price_ils'])} | {_ils(a['highest_comp_ils'])} | פי {a['ratio_to_highest_comp']} |")
    L += ["", "## מחיר שהמשתמש קבע ומפסיד (לא שונה)", ""]
    if o["owner_set"]:
        for r in o["owner_set"]:
            w = r.get("worst") or {}
            st = r.get("studio_shown") or {}
            L.append(f"- `{r['id']}` ב-{_ils(r['price_ils'])} ({r['where']}). במק\"ט שבחדר התרומה {_ils(st.get('contribution_ils'))} "
                     f"(מרווח {st.get('margin_pct')}%), אבל בתרחיש הגרוע ({w.get('label_he')}) {_ils(w.get('contribution_ils'))}. "
                     f"המחיר שלא מפסיד באף תרחיש: {_ils(r.get('no_loss_ils'))} (נקודת איזון {_ils(r.get('break_even_ils'))}). להחלטת המשתמש.")
    else:
        L.append("- אין.")
    L += ["", "## לבדוק: כמות המכירה", "",
          "במוצרים האלה הסטודיו קרא את מספר היחידות במכירה מעלות הנחיתה שברשומה (studio/build.py lead_qty), לא משדה כמות. "
          "המחיר הועלה לפי הכמות שהסטודיו מוכר. ברשימה רק מוצרים שבהם המחיר הקודם לא היה מפסיד אילו המכירה הייתה יחידה אחת (העמודה האחרונה: המחיר הנמוך שלא מפסיד ליחידה אחת)."]
    L += ["", "| מוצר | יח' בסטודיו | היה | עכשיו | אם יחידה אחת |", "| --- | --- | --- | --- | --- |"]
    for q in o.get("quantity_checks") or []:
        one = (q.get("if_one_unit") or {}).get("no_loss_ils")
        if one is None or q.get("raised_from_ils") is None or one > q["raised_from_ils"]:
            continue  # at one unit the old price would lose too: the quantity does not change the verdict
        if "pair" in q["id"]:
            continue  # a pair by its own name: the Studio's two units are right
        L.append(f"| `{q['id']}` | {q['studio_units']} | {_ils(q.get('raised_from_ils'))} | {_ils(q['price_ils'])} | {_ils((q.get('if_one_unit') or {}).get('no_loss_ils'))} |")
    L += ["", "`kitchen-sconce-aliexpress-rustic-wooden-wall-sconce-632957`: עלות הנחיתה ברשומה (₪100.6) היא בדיוק יחידה אחת ועוד משלוח ($8.01 + $22.49 במטמון AliExpress, × 3.3), "
          "והעמדה היא מנורה אחת: כנראה הסטודיו טועה ב-4 יח'. מומלץ לקבוע כמות 1 ולהחזיר את המחיר ל-₪229 בהחלטת המשתמש. "
          "`toy-cars-aliexpress-wooden-toys-beech-wood-138166`: הנחיתה ברשומה (₪115) מתאימה ל-3 יח' ב-$1.99, אבל הנימוק אומר \"פריט בודד (יש SKU סט)\": לבדוק מה נמכר.",
          "", "## קלטים מוערכים", ""]
    for k, v in sorted((o.get("estimated_inputs") or {}).items(), key=lambda x: -x[1]):
        L.append(f"- `{k}`: {v} מוצרים")
    L += ["", "freight-estimated = אין הצעת משלוח, נלקחה ההערכה הגבוהה; qty-freight-estimated = משלוח לכמה יחידות לפי חבילה לכל יחידה; "
          "freight-from-other-sku = המשלוח נמדד על מק\"ט אחר; freight-from-cache-only = לסטודיו אין משלוח, נלקח ממטמון הספק; "
          "no-fast-method = אין לספק משלוח עד 20 יום בנתוני הסטודיו (אם יוצע מהיר במוצר כזה, הוא לא נבדק).", "",
          "## אי אפשר לחשב", ""]
    for r in o["cannot_compute"]:
        L.append(f"- `{r['id']}` ({', '.join(r.get('scope') or [])}): {r.get('missing')}" + (f", מחיר {_ils(r['price_ils'])}" if r.get("price_ils") else ""))
    L += ["", f"כרטיסים שנספרים בכיסוי ואין להם מחיר בכלל ({S['counted_without_price']}): המחיר שלא מפסיד לכל אחד ב-JSON (`counted_without_price`), כמחיר התחלה מוצע. לא נכתב מחיר.", "",
          "## בדיקות", ""]
    t = o.get("tests") or {}
    if t:
        for k, v in t.items():
            L.append(f"- {k}: {v}")
    else:
        L.append("- לא הורצו בדוח הזה.")
    rj = o["rejected_candidates"]
    L += ["", "## מועמדים שנדחו רק בגלל הפסד (סבבים 5 ו-6, התאמה 7+)", "",
          f"נקראו {len(rj['reviewed'])} מועמדים בלי כרטיס שהרשומה שלהם מפסידה; {len(rj['kept'])} נדחו רק בגלל ההפסד. {rj['method_he']} "
          "המחיר שלא מפסיד כאן הוא במשלוח שברשומה בלבד. דיווח בלבד: לא שונה אף קובץ תוצאות ולא סקריפט הכיסוי.", "",
          "| עמדה | מוצר | סגנונות 7+ | נחיתה | מחיר שלא מפסיד | השוואה גבוהה | יחס | הערה |", "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for r in sorted(rj["kept"], key=lambda r: (r["slot"], r["ratio_to_highest_comp"] or 0)):
        L.append(f"| {r['slot']} | {r['source']} {r['id']} | {', '.join(f'{k} {v:g}' for k, v in r['fit_7_plus'].items())} | {_ils(r.get('landed_ils'))} | "
                 f"{_ils(r.get('no_loss_ils'))} | {_ils(r.get('highest_comp_ils'))} | {r.get('ratio_to_highest_comp') or '—'} | {r.get('note_he') or ''} |")
    L += ["", "### הרווח בכיסוי אם ייספרו", "", "| סגנון | עמדות | 3 אפשרויות היום | אם ייספרו | נוספו |", "| --- | --- | --- | --- | --- |"]
    for st, g in rj["coverage"].items():
        if st == "total":
            continue
        L.append(f"| {st} | {g['eligible']} | {g['ready_before']} ({g['pct_before']}%) | {g['ready_after']} ({g['pct_after']}%) | +{g['slots_gained']} (+{g['pct_points']} נק') |")
    tt = rj["coverage"]["total"]
    L.append(f"| **סה\"כ** | {tt['eligible']} | {tt['ready_before']} ({tt['pct_before']}%) | {tt['ready_after']} ({tt['pct_after']}%) | +{tt['ready_after'] - tt['ready_before']} |")
    L += ["", "שאר המועמדים שנקראו נדחו גם מסיבה אחרת (מעטפת, CE או IP44, קליעה פתוחה, מלאי, כפילות); הסיבה לכל אחד ב-JSON (`rejected_candidates.reviewed`).", "",
          "## מה עוד צריך", "",
          "- המשתמש: לאשר או לשנות את המחירים שהועלו, ובמיוחד את היקרים מהשוק. אפשרות: לגבות משלוח מהיר בנפרד במוצרים כבדים, או לא להציע אותו בהם, "
          "ואז המחיר לפי החסכוני מספיק (`no_loss_economy_only_ils` לכל מוצר).",
          "- frontend-dev: מחיר האפשרויות באתר (skuRetail) מוריד אפשרות זולה יותר ממה שהעלות יורדת, והאתר מחשב משלוח $17 למוצרי AliExpress ו-Zendrop; "
          "תווית \"יקר מהשוק\" בסטודיו (build.py מעביר היום רק ok, below-floor ו-loss).",
          "- לוחות החדרים (scripts/boards/room_boards.py) קוראים את המרווח של כרטיסי הסבב מהרשומה, לא מהמחיר החדש בכרטיס.",
          "- ממשיכים לחפש חלופה זולה יותר באותו מראה למוצרים שהועלו הרבה (ה.13).", ""]
    return "\n".join(L)


# --------------------------------------------------------------------------- CLI

def summary(res: dict) -> dict:
    from collections import Counter
    st = Counter(r.get("status") for r in res["rows"])
    return {"products": len(res["rows"]), "by_status": dict(st)}


def main(argv: list[str]) -> int:
    def arg(name):
        return argv[argv.index(name) + 1] if name in argv and argv.index(name) + 1 < len(argv) else None
    db = Path(arg("--db")) if arg("--db") else None
    date = arg("--date") or dt.date.today().isoformat()
    res = audit(ECO, db)
    print(json.dumps(summary(res), ensure_ascii=False))
    if arg("--json"):
        Path(arg("--json")).write_text(json.dumps({"settings": res["settings"], "rows": res["rows"]}, ensure_ascii=False, indent=1) + "\n",
                                       encoding="utf-8")
    if "--apply" in argv:
        pj_path = ECO / "products.json"
        before = json.loads(pj_path.read_text(encoding="utf-8"))["products"]
        a = apply(res, date)
        _dump(a["pj_path"], a["pj"])                       # 1. the prices (and the new rows)
        res1 = audit(ECO, db)                              # 2. the Studio's reading of the new prices
        pj = json.loads(pj_path.read_text(encoding="utf-8"))
        fc = refresh_rows(res1, pj, date, before)          # 3. margins, flags and no-loss facts at the new prices
        pj["updated"] = date
        n_rows = len([c for c in a["changes"] if c["price_source"] == "products.json"])
        add = (f" {date} (אין מוצר מפסיד, ה.13 בתיקון 2026-10-20): {n_rows} מחירים הועלו למחיר הנמוך שלא מפסיד באף תרחיש "
               f"(retail_src initial-no-loss-{date}; המחיר הקודם ב-retail_before_no_loss_ils), ונוספו שורות לכרטיסי סבב שעלות המכירה שלהם "
               "אינה N × עלות הכרטיס. flag הוא רף הרווח כמו שהסטודיו קורא אותו (ok ≥40%, below-floor 0–40%); flags מוסיף above-market (הועלה מעל "
               "ההשוואה הגבוהה) ו-loses-in-worst-case (מחיר של המשתמש שמפסיד בתרחיש); no_loss = התרחיש הגרוע, נקודת האיזון והיחס להשוואה "
               f"(data/economics/no-loss-audit-{date}.json).")
        if f"{date} (אין מוצר מפסיד" not in pj.get("note", ""):
            pj["note"] = pj.get("note", "") + add
        src = f"data/economics/no-loss-changes-{date}.json"
        if src not in pj.get("sources", []):
            pj.setdefault("sources", []).append(src)
        _dump(pj_path, pj)
        res2 = audit(ECO, db)                              # 4. verify: nothing loses (but the owner's price)
        left = [r["id"] for r in res2["rows"] if r.get("status") == "raise"]
        log = {"date": date, "rule": "docs/studio-rules.md ה.13 (2026-10-20): אין מוצר מפסיד בשום צורה",
               "script": "python3 -I scripts/economics/no_loss.py --apply", "settings": res["settings"],
               "changes": a["changes"], "products_json_rows_refreshed": fc,
               "owner_set_not_changed": [{"id": r["id"], "price_ils": r["price_ils"], "where": r["price_source"]["where"],
                                          "worst": r.get("worst_at_price"), "no_loss_ils": r.get("no_loss_ils"),
                                          "break_even_ils": r.get("break_even_ils")} for r in a["owner"]],
               "cannot_compute": [{"id": r["id"], "price_ils": r.get("price_ils"), "missing": r.get("missing"), "flags": r.get("flags")}
                                  for r in a["cannot"]],
               "verified_after": {"audited": len(res2["rows"]), "by_status": summary(res2)["by_status"], "still_losing": left}}
        _dump(ECO / f"no-loss-changes-{date}.json", log)
        print(f"applied: {len(a['changes'])} prices raised, {len(fc)} products.json rows refreshed, "
              f"{len(a['owner'])} owner-set listed, {len(a['cannot'])} cannot be computed; still losing after: {len(left)}")
        res = res2
    if "--report" in argv:
        tests = json.loads(Path(arg("--tests")).read_text(encoding="utf-8")) if arg("--tests") else None
        jp, mp = write_reports(res, date, tests)
        print(f"report: {jp.relative_to(ROOT)}, {mp.relative_to(ROOT)}")
    if "--check" in argv:
        bad = [r for r in res["rows"] if r.get("status") == "raise"]
        for r in bad:
            print("LOSS", r["id"], r["price_ils"], r["worst_at_price"])
        return 1 if bad else 0
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
