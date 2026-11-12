#!/usr/bin/env python3
"""
table_group_wm_t3.py: the clay check of the designer's WM-T3 proposal for the warm-modern table group (render-agent, 2026-11-12;
0 tokens, code only, no var2). Source: docs/proposals/wm-r7-table-decisions-2026-11-12.md section 1.4 (the points), 1.6 (what is run,
the acceptance, the levers and their order). NOTHING IS MOVED: no layer, no slot, no plan; projected card bodies only.

The method is R7's (table_group_r7.py): step0_clay_checks.main() run AS IT IS once per combination, with its DEFAULTS' "bowl" and
"candle-holders" bodies replaced by the card-sized bodies (table_group_r7.BOWLS / HOLDERS, unchanged) at the WM-T3 points, and the
pair's inner gap A x B by table_group_r7.a_vs_b(). Added here (the brief's list, same helpers S0.raster / S0.min_dist, frame-width
units, F3 0.02):
  * the bowl against each cushion set: F3's gap AND the vertical gap (per image column shared by the bowl and the set: the bowl's top
    to the lowest set pixel above it), with where the nearest set pixel lies;
  * every table piece against the curtains and the floor lamp, always measured (F3 skips pairs that are far apart): against the step-0
    placeholders (full silhouettes: conservative) and against the R7 layers themselves (the three curtains at their sold lengths, the
    floor lamp), alpha > 127 scaled to the clay canvas as step 0 scales the cushion sets;
  * the bowl inside the table's straight front edge (Y 2.07): >= 2 cm.

The rule (WM-T3, section 1.4): B's right edge at X = r; the pair keeps its 1.9.4 form (B at Y 1.68, A at Y 1.74, 8 cm clear between
them), so every holder moves by r - 0.39 in X; the bowl at (r + 0.25, 1.94) for all three bowls.
  r = 0.21 (proposed), then the designer's lever order 0.20, 0.22, 0.19; lever 2 (iron B candle 16 instead of 18) for the iron pair.
  The point is the FIRST r at which every pair of the bowls and holders that remain in the tool passes (black D20 and white belly D21;
  travertine and ceramic trays). The speckled bowl (bowl 3) and the iron plates are out of the tool for now (section 2): measured for
  information only, they do not choose the point.
  Also for information: the travertine pair as its R7 layer stands (A with the pre-approved 9 cm lever: A 1 cm further left).

Writes step0/wm-t3/table-group-wm-t3.json, step0/wm-t3/table-group-wm-t3-overlay.jpg and, for the chosen point, the per-combination
step-0 outputs step0/wm-t3/<bowl>__<holders>/ (f3-checks.json, placeholders.json / .npz, f3-overlay.jpg). The other points' per-
combination outputs go to the scratch folder (their numbers are in the summary).        python3 table_group_wm_t3.py
"""
import copy
import json
import os
import shutil
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import step0_clay_checks as S0  # noqa: E402
import table_group_r7 as TG  # noqa: E402

OUT = os.path.join(HERE, "wm-t3")
SCRATCH = os.path.join(S0.SCR, "wm-t3-clay")
P2 = os.path.dirname(HERE)
LAY = os.path.join(P2, "layers")
T = S0.TABLE_TOP
R_194 = 0.39                     # B's right edge at the 1.9.4 points (travertine 0.355 + 0.035; trays 0.305 + 0.085; iron 0.34 + 0.0525)
POINTS = [0.21, 0.20, 0.22, 0.19]  # section 1.6: the proposal first, then the designer's lever order
BOWL_DX = 0.25
BOWL_Y = 1.94
FRONT_Y = 2.07
IN_TOOL = dict(bowls=["black-d20", "white-belly-d21"], holders=["travertine", "ceramic-trays"])
INFO = dict(bowls=["speckled-wide-d21"], holders=["iron-plates"])
H194 = copy.deepcopy({k: dict(A=v["A"], B=v["B"], candles=v["candles"]) for k, v in TG.HOLDERS.items()})
RULE = 0.02


def set_point(r, iron_B=0.18, trav_A_extra=0.0):
    """the WM-T3 rule at B's right edge r: every holder moves by r - 0.39 in X (Y unchanged); the bowl at (r + 0.25, 1.94)"""
    s = r - R_194
    for h, d in H194.items():
        TG.HOLDERS[h]["A"] = (round(d["A"][0] + s - (trav_A_extra if h == "travertine" else 0.0), 4), d["A"][1])
        TG.HOLDERS[h]["B"] = (round(d["B"][0] + s, 4), d["B"][1])
        TG.HOLDERS[h]["candles"] = d["candles"]
    TG.HOLDERS["iron-plates"]["candles"] = (H194["iron-plates"]["candles"][0], iron_B)
    return (round(r + BOWL_DX, 4), BOWL_Y)


def cushion_masks():
    out = {}
    for s in "ABC":
        a = np.asarray(Image.open(os.path.join(S0.P1, f"layers-v3c/cushions-set-{s}.png")))[..., 3]
        out[s] = cv2.resize((a > 127).astype(np.uint8), (S0.GW, S0.GH), interpolation=cv2.INTER_NEAREST).astype(bool)
    return out


def layer_mask(rel):
    a = np.asarray(Image.open(os.path.join(LAY, rel)))[..., 3]
    return cv2.resize((a > 127).astype(np.uint8), (S0.GW, S0.GH), interpolation=cv2.INTER_NEAREST).astype(bool)


def real_layers():
    man = json.load(open(os.path.join(LAY, "manifest-r7.json")))
    by = {l_["id"]: l_ for l_ in man["layers"]}
    out = {"curtains (default 180502, 270)": by["curtains"]["file"], "floor-lamp (default)": by["floor-lamp"]["file"]}
    for v in man["variants"]["curtains"]:
        out[f"curtains ({v['id']}, {v['product']['card_id'].split('-')[-1]})"] = v["file"]
    return {k: (f, layer_mask(f)) for k, f in out.items()}


def gap(a, b):
    if not a.any() or not b.any():
        return None
    return round(S0.min_dist(a, b) / S0.CW, 4)


def vertical_gap(bowl, cm):
    """per column shared by the bowl and the set: the bowl's top row minus the lowest set row above it (frame-width units); the min,
    the column (frame u) and whether any column is shared at all"""
    cols = np.nonzero(bowl.any(0) & cm.any(0))[0]
    best = None
    for c in cols:
        bt = int(np.nonzero(bowl[:, c])[0].min())
        above = np.nonzero(cm[:bt, c])[0]
        if not len(above):
            continue
        g = (bt - int(above.max()) - 1) / S0.CW
        if best is None or g < best[0]:
            best = (g, c, bt)
    if best is None:
        return dict(shared_columns=int(len(cols)), vertical_gap=None, note="no set pixel above the bowl in any shared column")
    g, c, bt = best
    return dict(shared_columns=int(len(cols)), vertical_gap=round(g, 4), at_u=round((c - S0.CX) / S0.CW, 4), bowl_top_v=round((bt - S0.CY) / S0.CH, 4))


def nearest_point(a, b):
    """the pixel of b nearest to a (frame u / v)"""
    dt, lab_ = cv2.distanceTransformWithLabels((~a).astype(np.uint8), cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL)
    ys, xs = np.nonzero(b)
    i = int(np.argmin(dt[ys, xs]))
    return [round((xs[i] - S0.CX) / S0.CW, 4), round((ys[i] - S0.CY) / S0.CH, 4)]


def run_combo(bowl, h, bowl_xy, dest_root, tag, CM, REAL):
    TG.OUT = dest_root
    rr = TG.run(bowl, h, bowl_xy=bowl_xy, suffix=tag)
    sub = os.path.join(HERE, rr["folder"]) if not os.path.isabs(rr["folder"]) else rr["folder"]
    sub = os.path.normpath(sub)
    z = np.load(os.path.join(sub, "placeholders.npz"))
    f3 = json.load(open(os.path.join(sub, "f3-checks.json")))
    dep = {k: f3["placeholders"][k]["depth_m"] for k in ("bowl", "candle-holders")}
    sil = {k: z[f"sil_{k}"] for k in ("bowl", "candle-holders", "curtains", "floor-lamp")}
    vis = {"bowl": sil["bowl"] & ~sil["candle-holders"] if dep["candle-holders"] < dep["bowl"] else sil["bowl"].copy(),
           "candle-holders": sil["candle-holders"] & ~sil["bowl"] if dep["bowl"] < dep["candle-holders"] else sil["candle-holders"].copy()}
    canvas = z["canvas"]
    lvis = {k: canvas == S0.LABEL[k] for k in ("curtains", "floor-lamp")}
    ab = TG.a_vs_b(h)
    extra = dict(a_vs_b=dict(kind=ab["kind"], gap_frame=ab.get("gap_frame"), verdict=ab["verdict"], box_A=ab["box_A"], box_B=ab["box_B"]))
    extra["bowl_vs_sets"] = {s: dict(f3_gap=gap(vis["bowl"], CM[s]), nearest_set_px_uv=nearest_point(vis["bowl"], CM[s]), **vertical_gap(vis["bowl"], CM[s]))
                             for s in "ABC"}
    extra["holders_vs_sets"] = {s: dict(f3_gap=gap(vis["candle-holders"], CM[s]), nearest_set_px_uv=nearest_point(vis["candle-holders"], CM[s])) for s in "ABC"}
    far = {}
    for k in ("bowl", "candle-holders"):
        for j in ("curtains", "floor-lamp"):
            far[f"{k} x {j} (placeholder, full silhouette)"] = gap(vis[k], sil[j])
            far[f"{k} x {j} (placeholder, visible)"] = gap(vis[k], lvis[j])
        for nm, (_, m) in REAL.items():
            far[f"{k} x {nm} (R7 layer)"] = gap(vis[k], m)
    extra["vs_curtains_and_floor_lamp"] = far
    D = TG.BOWLS[bowl]["D"]
    extra["bowl_inside_front_edge_m"] = round(FRONT_Y - bowl_xy[1] - D / 2, 4)
    uB = S0.P(TG.HOLDERS[h]["B"][0], TG.HOLDERS[h]["B"][1], T + 0.05)[0]
    uA = S0.P(TG.HOLDERS[h]["A"][0], TG.HOLDERS[h]["A"][1], T + 0.05)[0]
    ub = S0.P(bowl_xy[0], bowl_xy[1], T + 0.03)[0]
    extra["frame_u"] = dict(A_centre=round(uA, 4), B_centre=round(uB, 4), bowl_centre=round(ub, 4),
                            pendant_cable=round(S0.P(0.20, 1.72, 2.5)[0], 4), bowl_box=rr["boxes"]["bowl"], holders_box=rr["boxes"]["candle-holders"])
    # the verdict of this combination: every measured gap >= 0.02 (F3 pairs and edges as step 0 rules them, A x B, the explicit lists)
    low = []
    for nm, p in rr["pairs"].items():
        if str(p["verdict"]).startswith("FAIL") or p["sets_failing"]:
            low.append(f"{nm} {p['min_frame']} (set {p['min_set']})")
    for k, e in rr["edges"].items():
        if e["verdict"] != "ok":
            low.append(f"edge {k}")
    if ab["verdict"].startswith("FAIL"):
        low.append(f"A x B {ab.get('gap_frame', ab.get('overlap_thickness'))}")
    for s, v in extra["bowl_vs_sets"].items():
        if v["f3_gap"] is not None and v["f3_gap"] < RULE:
            low.append(f"bowl x set {s} {v['f3_gap']}")
        if v.get("vertical_gap") is not None and v["vertical_gap"] < RULE:
            low.append(f"bowl x set {s} vertical {v['vertical_gap']}")
    for s, v in extra["holders_vs_sets"].items():
        if v["f3_gap"] is not None and v["f3_gap"] < RULE:
            low.append(f"holders x set {s} {v['f3_gap']}")
    for nm, g in far.items():
        if g is not None and g < RULE:
            low.append(f"{nm} {g}")
    if extra["bowl_inside_front_edge_m"] < 0.02:
        low.append(f"bowl inside the front edge {extra['bowl_inside_front_edge_m']} m")
    return dict(folder=sub, pairs=rr["pairs"], edges=rr["edges"], boxes=rr["boxes"], **extra, below_rule=low, pass_=not low,
                bodies=dict(bowl=dict(card=TG.BOWLS[bowl]["card"], centre=list(bowl_xy), D=TG.BOWLS[bowl]["D"], H=TG.BOWLS[bowl]["H"]),
                            holders=dict(card=TG.HOLDERS[h]["card"], A=list(TG.HOLDERS[h]["A"]), B=list(TG.HOLDERS[h]["B"]),
                                         candles_m=list(TG.HOLDERS[h]["candles"]))))


def mins(res, keys):
    """the worst value per measure over the given combinations"""
    w = {}

    def upd(nm, v, at):
        if v is None:
            return
        if nm not in w or v < w[nm][0]:
            w[nm] = (v, at)
    for k in keys:
        r = res[k]
        upd("A x B", r["a_vs_b"]["gap_frame"], k)
        for nm, p in r["pairs"].items():
            upd(nm, p["min_frame"], f"{k} set {p['min_set']}")
        for s in "ABC":
            upd("bowl x cushion set (F3)", r["bowl_vs_sets"][s]["f3_gap"], f"{k} set {s}")
            upd("bowl x cushion set (vertical)", r["bowl_vs_sets"][s].get("vertical_gap"), f"{k} set {s}")
            upd("candles x cushion set", r["holders_vs_sets"][s]["f3_gap"], f"{k} set {s}")
        for nm, g in r["vs_curtains_and_floor_lamp"].items():
            short = ("bowl" if nm.startswith("bowl") else "holders") + " x " + ("floor lamp" if "floor-lamp" in nm else "curtains") + \
                    (" (R7 layers)" if "R7 layer" in nm else " (placeholder)")
            upd(short, g, f"{k}: {nm}")
        upd("bowl inside front edge (m)", r["bowl_inside_front_edge_m"], k)
    return {nm: dict(min=v[0], at=at) for nm, (v, at) in sorted(w.items())}


def main():
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(SCRATCH, exist_ok=True)
    CM = cushion_masks()
    REAL = real_layers()
    combos_tool = [(b, h) for b in IN_TOOL["bowls"] for h in IN_TOOL["holders"]]
    combos_info = [(b, h) for b in TG.BOWLS for h in TG.HOLDERS if (b, h) not in combos_tool]
    per_point, chosen = {}, None
    for r in POINTS:
        bxy = set_point(r)
        res = {}
        for b, h in combos_tool + combos_info:
            set_point(r)
            res[f"{b}__{h}"] = run_combo(b, h, bxy, os.path.join(SCRATCH, f"r{r:g}"), "", CM, REAL)
            print(r, b, h, "PASS" if res[f"{b}__{h}"]["pass_"] else res[f"{b}__{h}"]["below_rule"], flush=True)
        # lever 2 (pre-approved): the iron B candle 16 (information: the iron pair is out of the tool)
        for b in TG.BOWLS:
            set_point(r, iron_B=0.16)
            res[f"{b}__iron-plates__B16"] = run_combo(b, "iron-plates", bxy, os.path.join(SCRATCH, f"r{r:g}"), "__B16", CM, REAL)
        tool_keys = [f"{b}__{h}" for b, h in combos_tool]
        ok = all(res[k]["pass_"] for k in tool_keys)
        per_point[r] = dict(B_right_edge_x=r, bowl_centre=list(bxy), holders={h: dict(A=list(set_point(r) and TG.HOLDERS[h]["A"]), B=list(TG.HOLDERS[h]["B"]))
                                                                               for h in TG.HOLDERS},
                            in_tool_pass=ok, in_tool_below_rule={k: res[k]["below_rule"] for k in tool_keys if res[k]["below_rule"]},
                            info_pass={k: res[k]["pass_"] for k in res if k not in tool_keys},
                            info_below_rule={k: res[k]["below_rule"] for k in res if k not in tool_keys and res[k]["below_rule"]},
                            worst_in_tool=mins(res, tool_keys), worst_info=mins(res, [k for k in res if k not in tool_keys]), combinations=res)
        if ok and chosen is None:
            chosen = r
    # information: the travertine pair as its R7 layer stands (A with the 9 cm lever) at the chosen point (or the proposal)
    rr_ = chosen if chosen is not None else POINTS[0]
    trav9 = {}
    for b in IN_TOOL["bowls"]:
        bxy = set_point(rr_, trav_A_extra=0.01)
        trav9[b] = run_combo(b, "travertine", bxy, os.path.join(SCRATCH, f"r{rr_:g}"), "__A9cm", CM, REAL)
    set_point(rr_)
    # the chosen point's per-combination step-0 outputs into step0/wm-t3/
    if chosen is not None:
        for k, r in per_point[chosen]["combinations"].items():
            dst = os.path.join(OUT, k)
            if os.path.exists(dst):
                shutil.rmtree(dst)
            shutil.copytree(r["folder"], dst)
            r["folder"] = os.path.relpath(dst, HERE)
    for p in per_point.values():
        for r in p["combinations"].values():
            if os.path.isabs(r["folder"]):
                r["folder"] = "scratch (not kept): " + os.path.relpath(r["folder"], S0.SCR)
    for r in trav9.values():
        r["folder"] = "scratch (not kept): " + os.path.relpath(r["folder"], S0.SCR)
    out = dict(
        id="wm-t3-table-group-clay", date="2026-11-12", author="render-agent", tokens=0, script=os.path.relpath(__file__, S0.REPO),
        source="docs/proposals/wm-r7-table-decisions-2026-11-12.md sections 1.4 (the points) and 1.6 (the check, the acceptance, the levers)",
        moved_nothing="no layer, slot, plan or selection changed; projected card bodies only (the owner answers WM-T3 first)",
        method="step0_clay_checks.main() unchanged, once per combination (table_group_r7.run, the R7 card bodies unchanged) at the WM-T3 "
               "points; A x B by table_group_r7.a_vs_b; the bowl's vertical gap to each cushion set and every table piece against the "
               "curtains and the floor lamp added with the same helpers (S0.raster, S0.min_dist), frame-width units",
        rule="nothing below 0.02 of the frame width (F3, house plan section 12); the bowl >= 2 cm inside the straight front edge (Y 2.07)",
        wm_t3_rule="B's right edge at X r; B Y 1.68, A Y 1.74, 8 cm clear between them (every holder moves by r - 0.39 in X); the bowl at (r + 0.25, 1.94)",
        lever_order=POINTS, levers_allowed=["B's right edge r in 0.19-0.22, the bowl always r + 0.25", "iron B candle 16 instead of 18"],
        in_tool=IN_TOOL, information_only=dict(INFO, why="out of the tool until sourcing verifies the SKUs (section 2); measured, not deciding"),
        chosen_point=None if chosen is None else dict(B_right_edge_x=chosen, bowl_centre=per_point[chosen]["bowl_centre"],
                                                       holders=per_point[chosen]["holders"], levers_used=[] if chosen == 0.21 else [f"B's right edge {chosen}"]),
        verdict=("PASS at the proposal (r 0.21): every pair of the in-tool bowls and holders >= 0.02" if chosen == 0.21 else
                 (f"PASS at the lever point r {chosen}" if chosen is not None else "NO POINT PASSES: back to the designer with the table")),
        summary_in_tool={f"{r:g}": dict(pass_=p["in_tool_pass"], worst=p["worst_in_tool"], below_rule=p["in_tool_below_rule"]) for r, p in per_point.items()},
        summary_info={f"{r:g}": dict(pass_=p["info_pass"], worst=p["worst_info"], below_rule=p["info_below_rule"]) for r, p in per_point.items()},
        travertine_A_9cm_info=dict(note="the travertine pair as its R7 layer stands (A 1 cm further left, the pre-approved 9 cm lever), at the chosen point",
                                   per_bowl={b: dict(a_vs_b=v["a_vs_b"], pass_=v["pass_"], below_rule=v["below_rule"], worst=mins({b: v}, [b])) for b, v in trav9.items()}),
        points={f"{r:g}": p for r, p in per_point.items()},
        real_layers_measured={k: f for k, (f, _) in REAL.items()},
        files=dict(summary="wm-t3/table-group-wm-t3.json", overlay="wm-t3/table-group-wm-t3-overlay.jpg",
                   per_combination="wm-t3/<bowl>__<holders>/ (the chosen point; step 0's own outputs)"),
    )
    json.dump(out, open(os.path.join(OUT, "table-group-wm-t3.json"), "w"), indent=1, ensure_ascii=False)
    overlay(out, per_point, chosen if chosen is not None else POINTS[0])
    print(json.dumps(dict(chosen=out["chosen_point"], verdict=out["verdict"], in_tool=out["summary_in_tool"]), indent=1))


def overlay(out, per_point, r):
    """the R7 default scene (set B), the table zoomed: the WM-T3 card bodies at r (solid) and the 1.9.4 ones (thin grey), the three
    cushion sets' outlines, the measured minimum gaps"""
    K = 2720 / 4072
    bg = Image.open(os.path.join(P2, "graded/default-scene-r7-set-B-graded-v3c.png")).convert("RGB")
    a = np.asarray(bg).astype(np.float32)
    CM = cushion_masks()

    def to_work(m):
        return cv2.resize(m.astype(np.uint8), (2720, 1530), interpolation=cv2.INTER_NEAREST).astype(bool)

    def outline(m, col, w=1):
        e = S0.boundary(cv2.dilate(m.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool))
        if w > 1:
            e = cv2.dilate(e.astype(np.uint8), np.ones((w, w), np.uint8)).astype(bool)
        a[e] = col
    for s, col in zip("ABC", ((120, 200, 255), (255, 255, 255), (255, 170, 90))):
        outline(to_work(CM[s]), col, 1)
    cols = {"black-d20": (20, 20, 20), "white-belly-d21": (240, 240, 240), "speckled-wide-d21": (190, 150, 90),
            "travertine": (60, 220, 230), "ceramic-trays": (230, 80, 200), "iron-plates": (250, 210, 40)}
    # 1.9.4 (thin grey)
    for b, d in TG.BOWLS.items():
        outline(to_work(S0.raster([S0.cyl(0.62, 1.94, d["D"] / 2, T, T + d["H"])])), (150, 150, 150), 1)
    for h in TG.HOLDERS:
        TG.HOLDERS[h]["A"], TG.HOLDERS[h]["B"] = H194[h]["A"], H194[h]["B"]
        outline(to_work(S0.raster(TG.holder_parts(h))), (150, 150, 150), 1)
    bxy = set_point(r)
    for b, d in TG.BOWLS.items():
        outline(to_work(S0.raster([S0.cyl(*bxy, d["D"] / 2, T, T + d["H"])])), cols[b], 2)
    for h in TG.HOLDERS:
        outline(to_work(S0.raster(TG.holder_parts(h))), cols[h], 2)
    im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    box = (1380, 880, 2300, 1400)
    z = im.crop(box).resize(((box[2] - box[0]) * 2, (box[3] - box[1]) * 2), Image.LANCZOS)
    d = ImageDraw.Draw(z)
    f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)
    fs = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 19)
    p = per_point[r]
    lines = [f"WM-T3 clay at B right edge X {r:g}, bowl ({bxy[0]:g}, {bxy[1]:g})   [{out['verdict']}]",
             "in the tool (decide):"]
    for nm, v in p["worst_in_tool"].items():
        if any(t in nm for t in ("A x B", "bowl x candle", "cushion", "curtains", "floor lamp", "front")):
            lines.append(f"  {nm}: {v['min']}   ({v['at'].split(':')[0]})")
    y = 8
    for i, t in enumerate(lines):
        d.text((10, y), t, fill=(255, 255, 255), font=f if i == 0 else fs, stroke_width=2, stroke_fill=(0, 0, 0))
        y += 26
    leg = [("black D20", cols["black-d20"]), ("white belly D21", cols["white-belly-d21"]), ("speckled D21 (info)", cols["speckled-wide-d21"]),
           ("travertine", cols["travertine"]), ("ceramic trays", cols["ceramic-trays"]), ("iron (info)", cols["iron-plates"]),
           ("1.9.4 (now)", (150, 150, 150)), ("sets A / B / C", (120, 200, 255))]
    x = 10
    yy = z.size[1] - 34
    for t, c in leg:
        d.rectangle((x, yy + 4, x + 18, yy + 22), fill=c, outline=(0, 0, 0))
        d.text((x + 24, yy), t, fill=(255, 255, 255), font=fs, stroke_width=2, stroke_fill=(0, 0, 0))
        x += 24 + int(d.textlength(t, font=fs)) + 22
    z.save(os.path.join(OUT, "table-group-wm-t3-overlay.jpg"), quality=90)


if __name__ == "__main__":
    main()
