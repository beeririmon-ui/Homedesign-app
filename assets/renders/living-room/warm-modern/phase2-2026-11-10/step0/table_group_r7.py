#!/usr/bin/env python3
"""
table_group_r7.py: R7, A.3 step 1, the clay checks of the warm-modern table group at the WM-T2 coordinates (render-agent, 2026-11-12;
0 tokens, code only). Brief: briefs/render-wm-tool-r7-2026-11-12.md; docs/proposals/owner-answers-applied-2026-11-12.md section 1.4;
slots 1.9.4 (by_style.warm-modern.bowl / candle-holders), house plan 1.3.6.

step0_clay_checks.py is run AS IT IS (its P(), raster(), visibility and F3 rule, main() unchanged) once per combination of the three bowls
x the three candle-holder pairs (9 runs), with its DEFAULTS' "bowl" and "candle-holders" bodies replaced by the card-sized bodies at the
1.9.4 points and its output folder redirected to step0/r7-table-group/<bowl>__<holders>/ (new files; step 0's own files are not
touched: a redirected run of the unchanged DEFAULTS reproduces step0/f3-checks.json byte for byte, checked 2026-11-12).
step0's F3 treats the holder pair as ONE item, so the pair's inner gap (A vs B) is measured here with the same helpers (S0.raster,
S0.min_dist, the 0.02 rule), on the visible silhouettes (the nearer piece hides the farther one).

The bodies (card sizes; candles are fillers, cream pillars; table top Z 0.38):
  bowls           black D20 x H8, white belly D21.2 x H6.4, speckled wide D21.3 x H5.2: a cylinder at the card's D and H (step 0's
                  convention: the convex hull of the solid, the widest silhouette), centre (0.62, 1.94)
  travertine      D7 x H11 pedestal; candle D6, A 7.5 / B 6 on the cup (step 0's body); A (0.205, 1.74), B (0.355, 1.68)
  ceramic trays   a walnut foot (D5 -> D7, H5), the tray D13.3 x 2.2 (top 7.2), two walnut balls D2.1 at the ends of the 17 cm span along X;
                  candle D6 on the tray, A 7.5 / B 6; A (0.055, 1.74), B (0.305, 1.68)
  iron plates     the dish D10.5 x H3 (feet included); candle D7 standing in it from Z +1.2, A 15 / B 18; A (0.15, 1.74), B (0.34, 1.68)
Acceptance (section 1.4): every pair >= 0.02 of the frame width (F3: gap, or contained contour gap); the bowl x holders, A x B, each x the
cushion sets A / B / C, the sofa and the rug. Levers (pre-approved, designer): A-B -> 9 cm clear (A 1 cm left); iron B candle vs a
cushion set -> 16; B-bowl -> bowl X 0.64.

Writes step0/r7-table-group/<combo>/{f3-checks.json, placeholders.json, placeholders.npz, f3-overlay.jpg} and
step0/r7-table-group/table-group-r7.json (the summary).     python3 table_group_r7.py
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import step0_clay_checks as S0  # noqa: E402

OUT = os.path.join(HERE, "r7-table-group")
T = S0.TABLE_TOP
BOWL_XY = (0.62, 1.94)
BOWLS = {
    "black-d20": dict(card="bowl-cj-matte-black-bowl-20", D=0.20, H=0.08),
    "white-belly-d21": dict(card="bowl-cj-glutinous-white-belly-bowl-21", D=0.212, H=0.064),
    "speckled-wide-d21": dict(card="bowl-cj-speckled-ivory-wide-bowl-21", D=0.213, H=0.052),
}


def trav(x, y, candle):
    return [S0.cyl(x, y, 0.035, T, T + 0.11, 48), S0.cyl(x, y, 0.03, T + 0.11, T + 0.11 + candle, 48)]


def ceramic(x, y, candle):
    return [S0.cone(x, y, 0.025, 0.035, T, T + 0.05, 48), S0.cyl(x, y, 0.0665, T + 0.05, T + 0.072, 64),
            S0.ellip(x - 0.0745, y, 0.0105, T + 0.0505, T + 0.0715, 24, 8), S0.ellip(x + 0.0745, y, 0.0105, T + 0.0505, T + 0.0715, 24, 8),
            S0.cyl(x, y, 0.03, T + 0.065, T + 0.065 + candle, 48)]


def iron(x, y, candle):
    return [S0.cyl(x, y, 0.0525, T, T + 0.03, 64), S0.cyl(x, y, 0.035, T + 0.012, T + 0.012 + candle, 48)]


HOLDERS = {
    "travertine": dict(card="candle-holders-cj-travertine-pedestal", A=(0.205, 1.74), B=(0.355, 1.68), candles=(0.075, 0.06), body=trav),
    "ceramic-trays": dict(card="candle-holders-cj-ceramic-pedestal-tray", A=(0.055, 1.74), B=(0.305, 1.68), candles=(0.075, 0.06), body=ceramic),
    "iron-plates": dict(card="candle-holders-aliexpress-matte-black-iron-pillar-set2", A=(0.15, 1.74), B=(0.34, 1.68), candles=(0.15, 0.18), body=iron),
}
ORIG = {k: dict(v) for k, v in S0.DEFAULTS.items()}


def holder_parts(h, which=("A", "B")):
    d = HOLDERS[h]
    out = []
    for w, c in zip(("A", "B"), d["candles"]):
        if w in which:
            out += d["body"](*d[w], c)
    return out


def a_vs_b(h):
    """the pair's inner gap (step 0's helpers, 4072 x 2290 canvas): the visible silhouettes (the nearer piece hides the farther)"""
    A, B = S0.raster(holder_parts(h, ("A",))), S0.raster(holder_parts(h, ("B",)))
    dA, dB = S0.depth_of(holder_parts(h, ("A",))), S0.depth_of(holder_parts(h, ("B",)))
    vA, vB = (A, B & ~A) if dA < dB else (A & ~B, B)
    if (A & B).any():
        th = S0.thickness(A & B) / S0.CW
        return dict(kind="overlap", overlap_thickness=round(th, 4), verdict="FAIL (overlap < 0.03)" if th < 0.03 else "decisive overlap",
                    box_A=S0.frame_box(A), box_B=S0.frame_box(B))
    g = S0.min_dist(vA, vB) / S0.CW
    return dict(kind="gap", gap_frame=round(g, 4), verdict="FAIL (kissing, < 0.02)" if g < 0.02 else "clear (>= 0.02)",
                box_A=S0.frame_box(A), box_B=S0.frame_box(B), depth_m=dict(A=round(dA, 3), B=round(dB, 3)))


def run(bowl, h, bowl_xy=BOWL_XY, suffix=""):
    b = BOWLS[bowl]
    S0.DEFAULTS["bowl"] = dict(ORIG["bowl"], card=b["card"], option={},
                               where=f"R7 (slots 1.9.4 WM-T2): centre {bowl_xy}, card D{b['D'] * 100:g} x H{b['H'] * 100:g}",
                               parts=[S0.cyl(*bowl_xy, b["D"] / 2, T, T + b["H"])])
    d = HOLDERS[h]
    S0.DEFAULTS["candle-holders"] = dict(ORIG["candle-holders"], card=d["card"], option={},
                                         where=f"R7 (slots 1.9.4 WM-T2): A {d['A']}, B {d['B']}, candles A {d['candles'][0] * 100:g} / B {d['candles'][1] * 100:g}",
                                         parts=holder_parts(h))
    sub = os.path.join(OUT, f"{bowl}__{h}" + ("" if bowl_xy == BOWL_XY else f"__bowl-x{bowl_xy[0]:g}") + suffix)
    os.makedirs(sub, exist_ok=True)
    S0.HERE = sub
    S0.main()
    r = json.load(open(os.path.join(sub, "f3-checks.json")))
    keep = {}
    for p in r["f3"]["pairs"]:
        if "bowl" in (p["a"], p["b"]) or "candle-holders" in (p["a"], p["b"]):
            nm = f"{p['a']} x {p['b']}"
            worst = None
            for s, q in p["by_set"].items():
                v = q.get("gap_frame", q.get("contour_gap_frame"))
                if v is not None and (worst is None or v < worst[1]):
                    worst = (s, v)
            keep[nm] = dict(kind=p["kind"], verdict=p["verdict"], sets_failing=p["sets_failing"],
                            min_frame=None if worst is None else worst[1], min_set=None if worst is None else worst[0],
                            by_set={s: q.get("gap_frame", q.get("contour_gap_frame", q.get("verdict"))) for s, q in p["by_set"].items()})
    edges = {k: v for k, v in r["f3"]["edges"].items() if k in ("bowl", "candle-holders")}
    return dict(folder=os.path.relpath(sub, HERE), pairs=keep, edges=edges, boxes={k: r["placeholders"][k]["frame_box"] for k in ("bowl", "candle-holders")})


def main():
    os.makedirs(OUT, exist_ok=True)
    res, fails = {}, []
    ab = {h: a_vs_b(h) for h in HOLDERS}
    for h, v in ab.items():
        if v["verdict"].startswith("FAIL"):
            fails.append(f"A x B {h}")
    for bowl in BOWLS:
        for h in HOLDERS:
            rr = run(bowl, h)
            res[f"{bowl}__{h}"] = rr
            for nm, p in rr["pairs"].items():
                if str(p["verdict"]).startswith("FAIL") or p["sets_failing"]:
                    fails.append(f"{bowl}__{h}: {nm}")
            for k, e in rr["edges"].items():
                if e["verdict"] != "ok":
                    fails.append(f"{bowl}__{h}: edge {k}")
            print(bowl, h, json.dumps({k: (v["min_frame"], v["verdict"]) for k, v in rr["pairs"].items()}), flush=True)
    # the table group's own pairs, worst over every combination
    table = {}
    for combo, rr in res.items():
        for nm, p in rr["pairs"].items():
            if p["min_frame"] is None:
                continue
            t = table.setdefault(nm, dict(min_frame=9.0))
            if p["min_frame"] < t["min_frame"]:
                t.update(min_frame=p["min_frame"], at=combo, set=p["min_set"], kind=p["kind"])
    out = dict(date="2026-11-12", author="render-agent", tokens=0, script=os.path.relpath(__file__, S0.REPO),
               brief="briefs/render-wm-tool-r7-2026-11-12.md (A.3 step 1)", source="docs/proposals/owner-answers-applied-2026-11-12.md section 1.4",
               method="step0_clay_checks.main() unchanged, once per combination, with the bowl and holder bodies replaced (card sizes, slots 1.9.4 "
                      "points) and the output redirected; the pair's inner gap A x B by the same helpers",
               rule="F3 (house plan section 12): every pair >= 0.02 of the frame width; nothing below 0.02 passes",
               bodies=dict(bowls={k: dict(v, centre=BOWL_XY) for k, v in BOWLS.items()},
                           holders={k: dict(card=v["card"], A=v["A"], B=v["B"], candles_m=v["candles"], body=v["body"].__name__) for k, v in HOLDERS.items()}),
               a_vs_b=ab, combinations=res, worst_per_pair=table, fails=fails, pass_=not fails, levers_used=[])
    json.dump(out, open(os.path.join(OUT, "table-group-r7.json"), "w"), indent=1, ensure_ascii=False)
    print(json.dumps(dict(a_vs_b={k: (v.get("gap_frame"), v["verdict"]) for k, v in ab.items()}, worst=table, fails=fails), indent=1))


if __name__ == "__main__":
    main()
