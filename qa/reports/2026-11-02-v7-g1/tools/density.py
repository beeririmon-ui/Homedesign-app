"""
G1.6 density (F10, S11) on the round-4 clay of every master: Bible 1.7.1 counting rule (D1: >= 50 % visible and >= 0.5 % of the
frame; sets once) with D1B (fixed-product furniture counts), own-room products only, stand-in rugs reported separately (not for
sale), at least 4 of 5 categories (C0: 3). The re-count on the render is by eye (boxes overlay); it is written in the report.
Writes data/density.json.
"""
import ast
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402

src = open(os.path.join(C.REPO, "assets/blockout/house/framing_r2.py")).read()


def grab(name):
    """The literal dict assigned to `name` in framing_r2.py (brace-matched; entries added later by code are not included)."""
    i = src.find("\n%s = {" % name)
    if i < 0:
        return None
    j = src.find("{", i)
    depth, k = 0, j
    while k < len(src):
        depth += src[k] == "{"
        depth -= src[k] == "}"
        if depth == 0:
            break
        k += 1
    try:
        return ast.literal_eval(src[j:k + 1])
    except (ValueError, SyntaxError):
        return None


# CATEGORY is filled by loops in framing_r2.py (lines after "CATEGORY = {}" up to "CATS4 = ["): run that slice only
_i, _j = src.find("\nCATEGORY = {}"), src.find("\nCATS4 = [")
_ns = {}
exec(src[_i:_j], _ns)  # noqa: S102 (studio code, a literal-only slice)
CATEGORY = _ns["CATEGORY"]
CATS4 = ["textile", "lighting", "ceramics/tableware", "storage/function"]
MIN = {"M0": 14, "D1": 14, "D2": 14, "MB0": 14, "H0": 11, "W0": 11, "K-boy": 11, "K-girl": 11, "B1": 11, "B2": 11, "C0": 5}
ROOM_PREFIX = {"M0": "living/", "D1": "kitchen-dining/", "D2": "kitchen-dining/", "H0": "hall/", "C0": "corridor/", "MB0": "master/",
               "K-boy": "boy/", "K-girl": "girl/", "B1": "bath/", "B2": "bath/", "W0": "work/"}
STAND_IN = {"living/rug", "kitchen-dining/dining-rug", "kitchen-dining/kitchen-runner", "boy/rug", "girl/rug", "work/rug"}
FIXED_PRODUCT = {"M0": ["sofa (fixed-product)", "coffee table (fixed-product)", "armchair (fixed-product)"],
                 "D1": ["dining table 160x85 (fixed)", "dining chairs (fixed, window side)", "dining bench (fixed)"],
                 "D2": ["dining table 160x85 (fixed)", "dining bench (fixed)"], "H0": ["fixed:hall-bench", "hall console"], "C0": [],
                 "MB0": ["master bed 180x200", "nightstands 45"], "K-boy": ["boy bed 96x196 (fixed)", "boy desk 90x50 (fixed)"],
                 "K-girl": ["girl bed 96x196 (fixed)", "girl desk 90x50 (fixed)"], "B1": ["bath vanity 110 (fixed)"], "B2": ["bath vanity 110 (fixed)"],
                 "W0": ["built-in oak desk + shelf", "desk chair"]}
FIXED_CAT = "furniture"

out = {}
for f in C.MASTERS:
    d = C.load(f)
    sc = d["sc"]
    Wc, Hc = sc["resolution"]
    frame_px = 3840 * 2160                     # the 16:9 frame at the canvas scale (the overscan canvas adds rows and columns outside it)
    iv = sc.get("items_visible", {})
    rows = []
    for nm, b in sc.get("boxes", {}).items():
        if b["kind"] not in ("proxy", "proxy-transit") or not nm.startswith(ROOM_PREFIX[f]):
            continue
        slot = nm.split("/", 1)[1]
        area = b["px"] / frame_px
        vis = iv.get(nm, {}).get("visible_pct")
        vis_ok = True if vis is None else vis >= 50.0          # round 4 ray-cast only part of the boxes: None = assumed visible (eye check)
        ok = vis_ok and area >= 0.005
        rows.append(dict(slot=slot, category=CATEGORY.get(slot, "other"), area_pct=round(100 * area, 2), visible_pct=vis,
                         visibility_assumed=vis is None, stand_in=nm in STAND_IN,
                         counted=bool(ok and nm not in STAND_IN), counted_if_stand_in_sold=bool(ok),
                         why_not=None if ok else ("visible < 50 %" if not vis_ok else "area < 0.5 %")))
    fixed = []
    for nm in FIXED_PRODUCT[f]:
        b = sc.get("boxes", {}).get(nm)
        if b is None and f == "M0":
            u0, u1, v0, v1 = C.M0_FURNITURE[nm]
            fixed.append(dict(name=nm, area_pct=round(100 * (u1 - u0) * (v1 - v0), 2), visible_pct=None, counted=True, note="pilot box; visibility assumed (not ray-cast in round 4)"))
            continue
        area = b["px"] / frame_px
        vis = iv.get(nm, {}).get("visible_pct")
        ok = (True if vis is None else vis >= 50.0) and area >= 0.005
        fixed.append(dict(name=nm, area_pct=round(100 * area, 2), visible_pct=vis, visibility_assumed=vis is None, counted=bool(ok)))
    n_prod = sum(r["counted"] for r in rows)
    n_fixed = sum(x["counted"] for x in fixed)
    n_sold_standin = sum(r["counted_if_stand_in_sold"] for r in rows)
    cats = sorted({r["category"] for r in rows if r["counted"]} | ({FIXED_CAT} if n_fixed else set()))
    have4 = [c for c in CATS4 if c in cats]
    need_cats = 3 if f == "C0" else 4
    out[f] = dict(minimum=MIN[f], products_counted=n_prod, fixed_product_counted=n_fixed, total=n_prod + n_fixed,
                  total_if_stand_in_rugs_sold=n_sold_standin + n_fixed, categories=cats, categories_of_4=len(have4), categories_ok=len(have4) >= need_cats,
                  pass_=bool(n_prod + n_fixed >= MIN[f] and len(have4) >= need_cats), rows=rows, fixed=fixed,
                  render_recount="by eye on the boxes overlay; see the report")
    print(f"{f:7s} min {MIN[f]:2d} products {n_prod:2d} + fixed {n_fixed} = {n_prod + n_fixed:2d} (with stand-in rugs {n_sold_standin + n_fixed:2d})  cats {cats} 4of5={len(have4)} -> {'pass' if out[f]['pass_'] else 'FAIL'}")
json.dump(out, open(os.path.join(C.OUT, "data", "density.json"), "w"), indent=1, ensure_ascii=False)
