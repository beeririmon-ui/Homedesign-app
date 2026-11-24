#!/usr/bin/env python3
"""
checks.py: the brief's checks on stage one (render-agent, 2026-11-20; 0 tokens), written to checks.json:
  - RND2: outside every alpha, shadow and light, each frame is its plate pixel for pixel (and the same for every variant frame);
  - every shadow sits one z below its product; every light layer is screen at z 90;
  - WM-G1: the black point (p0.5 of L* on the 16:9 frame) in 11-14, on the plates and the frames;
  - the count: the manager's way (each sold product once in the room, in the frame where it is biggest) and V7Q6 (0.5 % of the frame,
    or 0.15 % with 6 % of the frame height; 50 % visible against its clay; a set of three counts once), per frame;
  - D1 / D2 one house: per material dE00 between the two plates on the surfaces both frames see (the overlap, through the homography),
    and the homography residual on the shared lock lines.
"""
import json
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kd_common as K  # noqa: E402
from kd_passes import FILLERS  # noqa: E402

C = K.C
ST = K.ST
H, W = K.H, K.W


def bp(path):
    lab = C.to_lab(C.load(path))
    return round(float(np.percentile(lab[..., 0][K.frame_mask()], 0.5)), 2)


def one_house():
    """the two plates on the surfaces both frames see: D1's plate warped into D2, per material (D2's clay ids), median Lab and dE00"""
    out = {}
    p1, p2 = C.load(os.path.join(ST, "plate-D1.png")), C.load(os.path.join(ST, "plate-D2.png"))
    maps = K.map_between("D1", "D2")
    w1 = K.warp(p1, "D1", "D2", maps=maps)
    fm = K.warp(K.frame_mask(), "D1", "D2", maps=maps) & K.frame_mask()
    ids2 = K.ids("D2-plate")
    l1, l2 = C.to_lab(np.clip(w1, 0, 1)), C.to_lab(p2)
    for name, g in (("plaster (south wall)", (2,)), ("hood plaster", (37,)), ("limestone (worktop, splash)", (32, 33)), ("taupe lowers", (30,)),
                    ("walnut shelves", (38,)), ("oak floor", (10,)), ("walnut table / bench", (20, 24))):
        m = C.ero(np.isin(ids2, g), 6) & C.ero(fm, 8)
        if m.sum() < 300:
            continue
        a, b = np.median(l1[m], 0), np.median(l2[m], 0)
        out[name] = dict(D1=[round(float(x), 1) for x in a], D2=[round(float(x), 1) for x in b], dE00=round(float(C.de00(tuple(a), tuple(b))), 2),
                         px=int(m.sum()))
    # the homography: D1's lock lines that D2 also sees, measured on both plates (compose_plate's residuals), offsets in px
    r = {}
    for fr in ("D1", "D2"):
        J = json.load(open(os.path.join(ST, f"plate-{fr}-compose.json")))
        r[fr] = J.get("lock_lines_after", {})
    shared = sorted(set(r["D1"]) & set(r["D2"]))
    out["lock_lines_shared"] = {k: dict(D1_px=r["D1"][k]["median_px"], D2_px=r["D2"][k]["median_px"],
                                        diff_px=round(abs(r["D1"][k]["median_px"] - r["D2"][k]["median_px"]), 1)) for k in shared}
    return out


def counts(man):
    fm = K.frame_mask()
    farea = fm.sum()
    x0, y0, x1, y1 = (int(round(v)) for v in K.FRAME)
    rows = {}
    union = {"D1": np.zeros((H, W), bool), "D2": np.zeros((H, W), bool)}
    for l in man["layers"]:
        if not l["default"] or l.get("retired") or l["frame"] not in ("D1", "D2"):       # D2o is a source frame, not shipped
            continue
        a = np.asarray(Image.open(os.path.join(ST, l["layer"])))[..., 3] > 127
        a &= fm
        union[l["frame"]] |= a
        clay = np.isin(K.ids(l["frame"], new=True), [l["clay_id"]] + [f for f, o in FILLERS.items() if o == l["clay_id"]]) & fm
        if a.sum() == 0:
            continue
        ys = np.nonzero(a.any(1))[0]
        pct = 100 * a.sum() / farea
        hpct = 100 * (ys.max() - ys.min() + 1) / (y1 - y0)
        vis = min(1.0, a.sum() / max(clay.sum(), 1))
        ok = (pct >= 0.5 or (pct >= 0.15 and hpct >= 6.0))
        rows.setdefault(l["product"], {})[l["frame"]] = dict(slot=l["slot"], frame_pct=round(pct, 3), height_pct=round(hpct, 2),
                                                             v7q6=bool(ok), alpha_vs_clay=round(vis, 2))
    manager = {"D1": [], "D2": []}
    for pid, fr in rows.items():
        best = max(fr, key=lambda f: fr[f]["frame_pct"])
        manager[best].append(pid)
    v7 = {f: sorted(pid for pid, fr in rows.items() if f in fr and fr[f]["v7q6"]) for f in ("D1", "D2")}
    over1 = {f: sorted((pid, fr[f]["frame_pct"]) for pid, fr in rows.items() if f in fr and fr[f]["frame_pct"] >= 1.0) for f in ("D1", "D2")}
    return dict(per_product=rows, manager_way={f: dict(n=len(v), products=sorted(v)) for f, v in manager.items()},
                coverage_pct={f: round(100 * float(u.sum()) / farea, 2) for f, u in union.items()},
                over_1pct={f: dict(n=len(v), products=v) for f, v in over1.items()},
                manager_total=sum(len(v) for v in manager.values()),
                v7q6={f: dict(n=len(v), products=v) for f, v in v7.items()},
                note="a set (the three mugs, the three canisters, the mill pair) is one product here; V7Q6 'visible 50 %' is the alpha against the clay "
                     "proxy (alpha_vs_clay), the model's product may be a little smaller or larger than the clay box")


COLOUR_TARGETS = {
    "table-runner": "10.2: h 51-69, C* up to 55 (target h 52 +-4 relative to the photo, L*59 C*49 h52)",
    "tea-towel": "10.1 / 6.5-6: the caramel box; photo L*37 C*38 h50",
    "cutting-boards": "10.4: the second caramel carrier in D1; photo L*39 C*25 h54",
    "paper-towel-holder": "10.4: the second caramel carrier in D2; photo Style C L*50 C*41 h62",
    "canisters": "6.5-5: L* up to 92 on the lit side (no pure white)",
    "floor-vase": "6.5-5: L* up to 92",
    "open-shelf-ceramics": "10.4: the espresso carrier, L* 15-35 (photo L*20)",
    "candle-holders": "10.4: the espresso carrier in D1 (iron, photo L*24)",
    "counter-vessel": "10.9 row 4: the white textured jar, photo warm white L*71 (work-room sheet); no pure white",
    "serving-boards": "10.9 / ch. 7: dark on purpose (the 'dark walnut boards' rejection applies to cutting-boards only)",
    "tableware-set": "the cream plates with the honey-amber rim (photo)",
}


def colours(man):
    out = {}
    for l in man["layers"]:
        if not l["default"] or l.get("projected_from") or l.get("retired") or l["slot"] not in COLOUR_TARGETS:
            continue
        rgba = np.asarray(Image.open(os.path.join(ST, l["layer"]))).astype(np.float64) / 255
        m = C.ero(rgba[..., 3] > 0.99, 2)
        if m.sum() < 30:
            continue
        lab = C.to_lab(rgba[..., :3])[m]
        L, A, B = np.median(lab, 0)
        out[l["product"]] = dict(frame=l["frame"], L_p50=round(float(L), 1), C_p50=round(float(np.hypot(A, B)), 1),
                                 h_p50=round(float(np.degrees(np.arctan2(B, A))), 1), L_p95=round(float(np.percentile(lab[:, 0], 95)), 1),
                                 L_p05=round(float(np.percentile(lab[:, 0], 5)), 1), target=COLOUR_TARGETS[l["slot"]])
    return out


def lock_residuals(rgb, fr):
    """per lock line of the clay (D2 at -86: the clay of 2026-11-24): the strongest gradient across the line near its analytic position
    (+-12 px), its median offset (kd_plate.py's measure)"""
    import cv2
    J = json.load(open(K.clay_file(fr, "-lock-target.json")))
    y = cv2.GaussianBlur(C.luma(rgb).astype(np.float32), (0, 0), 1.0)
    gx, gy = cv2.Sobel(y, cv2.CV_32F, 1, 0), cv2.Sobel(y, cv2.CV_32F, 0, 1)
    out = {}
    for name, L in J["lines"].items():
        (x0, y0), (x1, y1) = L["px_ends"]
        d = np.array([x1 - x0, y1 - y0], float)
        n = np.array([-d[1], d[0]]) / max(np.hypot(*d), 1e-6)
        offs = []
        for x, yy, seen in L["samples"]:
            if not seen:
                continue
            best, bo = 0, None
            for o in np.arange(-12, 12.5, 0.5):
                px, py = x + n[0] * o, yy + n[1] * o
                if 1 <= px < W - 1 and 1 <= py < H - 1:
                    g = abs(gx[int(py), int(px)] * n[0] + gy[int(py), int(px)] * n[1])
                    if g > best:
                        best, bo = g, o
            if bo is not None and best > 4:
                offs.append(bo)
        if len(offs) >= 5:
            out[name] = dict(median_px=round(float(np.median(offs)), 1), n=len(offs))
    return out


def checks_10_9(man):
    """10.9's QA list (only what changed): the seam, the homography, the niche, the branches, the D1 grade"""
    d2s = json.load(open(os.path.join(ST, "d2stage.json")))
    fx0, fy0, fx1, fy1 = K.FRAME
    out = dict(seam=d2s["plate"]["seam"], seam_rule="dE00 up to 2 on the floor, the bench and the plaster along the seam (D1-ungraded matched "
                                                     "to D2o against D2o, medians on the 2 deg cross-fade band)")
    out["homography"] = dict(camera_vs_clay_lock_lines_px=K.check_camera(),
                             plate_D2_lock_lines_px=lock_residuals(C.load(os.path.join(ST, "plate-D2.png")) * 255, "D2"),
                             plate_D2o_lock_lines_px=lock_residuals(C.load(os.path.join(ST, "plate-D2o.png")) * 255, "D2o"),
                             note="the composed plate's lines are D2o's within 1-2 px (the rotation adds no error); the hood's right vertical "
                                  "(-10 / -12) and the niche's top edge (the LED under it is the strongest edge) are the approved plates' own",
                             rule="the analytic camera against Blender's own projection of the lock lines; then the composed plate's edges against "
                                  "the -86 clay's lock lines (median offset per line, up to 2 px)")
    out["niche"] = {k: v for k, v in d2s["niche"].items() if k != "lock"}
    ves = [l for l in man["layers"] if l["frame"] == "D2" and l["slot"] == "counter-vessel" and not l.get("projected_from")][0]
    a = np.asarray(Image.open(os.path.join(ST, ves["layer"])))[..., 3] > 127
    ys, xs = np.nonzero(a)
    u = ((xs.min() - fx0) / (fx1 - fx0), (xs.max() - fx0) / (fx1 - fx0))
    v = ((ys.min() - fy0) / (fy1 - fy0), (ys.max() - fy0) / (fy1 - fy0))
    mug = [l for l in man["layers"] if l["frame"] == "D2" and l["slot"] == "mug-set"][0]
    am = np.asarray(Image.open(os.path.join(ST, mug["layer"])))[..., 3] > 0
    d1v = [l for l in man["layers"] if l["frame"] == "D1" and l["slot"] == "counter-vessel"]
    d1_in = 0
    if d1v:
        a1 = np.asarray(Image.open(os.path.join(ST, d1v[0]["layer"])))[..., 3] > 127
        d1_in = int((a1 & K.frame_mask()).sum())
    out["branches"] = dict(u=[round(float(x), 3) for x in u], v=[round(float(x), 3) for x in v], target_u=[0.565, 0.63], target_v=[0.17, 0.48],
                           over_mugs_px=int((a & am).sum()), over_niche=bool(u[1] >= 0.65), in_D1_frame_px=d1_in,
                           in_D1_frame_pct=round(100 * d1_in / K.frame_mask().sum(), 2),
                           note="the vessel is at (6.95, 3.88), not 10.9's (7.00, 4.00): that place collides with the paper towel holder (7.12, 4.05); "
                                "every place out of D1's frame (Y 4.0 and up) stands in front of the holder in D2",
                           decision="the manager, 2026-11-24: accepted as it is; physical consistency between D1 and D2 comes first. QA check 4 is "
                                    "updated: the vessel in D1 is the intended projection from D2, not a new object; the holder is not moved and the "
                                    "vessel is not hidden in D1")
    out["grade_KD_L4"] = d2s["grade"]
    rec = json.load(open(os.path.join(ST, "compose.json")))
    out["print_05"] = rec.get("print-05")
    return out


def main():
    man = json.load(open(os.path.join(ST, "manifest.json")))
    rec = json.load(open(os.path.join(ST, "compose.json")))
    out = {}
    out["rnd2"] = {k: v for k, v in rec.get("frames", {}).items()}
    zc = []
    for l in man["layers"]:
        zc.append(l["shadow_z"] == l["z"] - 1)
    out["shadows_one_z_below"] = dict(all=bool(all(zc)), n=len(zc))
    out["lights_screen_z90"] = dict(all=bool(all(li["blend"] == "screen" and li["z"] == 90 for li in man["light"])), n=len(man["light"]))
    out["black_point_p05"] = {}
    for f in sorted(os.listdir(ST)):
        if f.endswith(".png") and (f.startswith("plate-D") or f.startswith("D1-") or f.startswith("D2-")) and "frame" not in f:
            out["black_point_p05"][f] = bp(os.path.join(ST, f))
    out["black_point_ok"] = all(11.0 <= v <= 14.0 for v in out["black_point_p05"].values())
    out["count"] = counts(man)
    out["colours"] = colours(man)
    if os.path.exists(os.path.join(ST, "plate-D2.png")):
        out["one_house_D1_D2"] = one_house()
    out["stage_10_9"] = checks_10_9(man)
    json.dump(out, open(os.path.join(ST, "checks.json"), "w"), indent=1)
    print(json.dumps({k: v for k, v in out.items() if k != "count"}, indent=0)[:3000])
    print(json.dumps(out["count"]["manager_way"]), json.dumps(out["count"]["v7q6"]))


if __name__ == "__main__":
    main()
