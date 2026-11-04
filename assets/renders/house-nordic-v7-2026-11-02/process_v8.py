#!/usr/bin/env python3
"""
process_v8.py: the successor of process_v7.py for the v7 stills (render-agent, 2026-11-03), after the designer's review
(docs/render-v7-review-2026-11-02.md) and QA's gate G1 (qa/reports/2026-11-02-v7-g1.md sections 4 and 5). process_v7.py is
untouched; both old behaviours stay here under flags.

What changed (defaults), and the flag that restores v7:
  --grade-order v2   QA section 4: the v7 chain was roll-off (asymptote L 97.25) -> S curve -> black point, and the last two
                     lift the capped highlights again (0.9725 -> 0.9755 by the S curve, -> 0.978 by the black-point blend),
                     so the window p99 landed at 97.4-97.6 in 7 stills against the 97 ceiling. v2 order: white balance ->
                     exposure (cap +-0.2 stop, unchanged: V7Q4 is open) -> chroma -10 % -> S curve 0.12 -> black point ->
                     roll-off LAST (knee L 94, asymptote L 97.0, max channel, hue kept). The roll-off is then the ceiling:
                     L <= 97.0 everywhere by construction.             (--grade-order v1 = the v7 chain)
  --wb-point auto    QA section 4, B2: process_v7 sampled white balance and exposure at `hero_wall_mid` and fell back to
                     (0.5, 0.3) when a still had none; in B2 that is the mirror, so B2's "-0.12 stop, within cap" was not a
                     wall reading. auto: hero_wall_mid -> else the clay's `reference_*` patch (the group reference wall the
                     clay was exposed on; a pose gets it only when its own clay reads a wall there) -> else (0.5, 0.3), flagged
                     NOT VALID. M0 keeps the Bible corner point.            (--wb-point legacy = the v7 rule)
  --lock v2          lock_v2.py (register + bands + ECC tiles + fixed edges, gate G1.4) instead of the phase-correlation
                     `clay_lock`; the v7 numbers are still written for comparison (`clay_lock_v1`).   (--lock v1)
  --suffix -v2       every output gets the suffix: <id>-graded-v2.png, -frame-v2.png, -graded-os6-v2.png, -measurements-v2.json,
                     -lock-v2.json. Nothing of v7 is overwritten.

Inputs are the normalised 16:9 stills process_v7 already wrote (<out_dir>/<id>.png, 2736x1539 canvas), so step (1)-(2) of
process_v7 (raw copy, non-uniform resize) are not repeated.

v3 (render-agent, 2026-11-03; briefs/render-v7-retakes-2026-11-03.md task 1; V7Q4 = yes and BIB1 = all six, 2026-11-03):
  --exposure bible   grades to the Bible targets instead of the +-0.2 stop ceiling (the test page only, V7Q4). The lift is the
                     stops the reference wall needs (sanity cap +-1.5 stop, flagged). Targets (BIBLE_TARGET): M0 group: the corner
                     (0.467, 0.385) L 93 [92-95]; the other rooms: the wall by the window L 92 [90-94] ("אור" 1.4); H0: exposed on
                     the living vista through the door, L 93 [92-95], and the hall wall measured 2/3 stop under it (B5, pass 0.47-
                     0.87 stop); H0x / H0e and (G1.8 proposal, not a Bible number) C0 / S1': the hall wall at L 75.8 [71.5-80.4]
                     = 93 minus 2/3 stop; B1: the wall beside the window L 88 [86-90] (Bible 1.6 bath). B2 has no white wall at
                     the clay's reference uv (it is the shower limestone there), so B2 reads the wall beside the mirror at
                     (0.535, 0.33) for the record and inherits B1's stops (one exposure per camera point, P-B pan); M0x, K-boy-0
                     and K-girl-0 (no clay wall patch) inherit their master's stops (--stops). CB-0's hero_wall_mid is the wall B1
                     reads at hero_wall_mid, so its target is B1's graded value there (--target).
                     Also in this mode: black point 12-15 both ways (lift below 12 as before, and a shadow-only pull when the
                     darkest 0.5 % patch sits above 15); near-white chroma guard (B4: Lab chroma of the L > 80 population before
                     and after, the lift may not add more than +1.5 C; if it does, the near-white chroma is pulled back); the
                     window wall (M0 window_wall patch) reported against L 80-88 (B1 of BIB1); the v2 roll-off last (ceiling 97,
                     zero 255); the hall / living delta for H0. Default stays `cap` (= the v2 behaviour).
  --lock none        skip the lock (a re-grade does not move edges; the -lock-v2.json next to the still stays the record).
  --stops <float>    apply exactly these stops (inherit from the group reference), --target <L> override the target.

v4 (render-agent, 2026-11-04; briefs/render-retakes-code-fixes-2026-11-04.md task 2; QA qa/reports/2026-11-03-retakes-g1.md §4, §11.2):
  --grade v4         the v3 Bible grade (implies --exposure bible) plus:
                     (a) WALL HUE: the reference wall's HSL H after the lift is reported; when it is above 40 a masked hue
                         correction in CIELAB moves the warm-white walls toward the Bible white (HSL 36/20/93, h_ab ~85 deg) and caps
                         their chroma at 6.5: only pixels with L* 80-97.3 (not the glass, L* > 98), a C* ramp 10-18 (not the oak, the
                         rope, the lamp glows' cores; QA's 14-18 left a white ring round a sconce glow) and a hue yellower than the target, and outside the product boxes and the upholstered
                         fixed furniture (sofa, armchair, beds: feathered 30 px; the oak and the plaster are gated by C* and L*). QA's qa_wall rule, m0_1_2_pipeline.py.
                     (b) B4 ABSOLUTE: CIELAB C* <= 7 on the reference wall patch (warm white, Bible 'טווחי סבילות'), checked, next
                         to the v3 relative guard (which stays).
                     (c) WINDOW WALL: L 80-88 (Bible 1.8 B1 (2)) read at QA's points in M0, K-boy, K-girl, W0, MB0 (and their fixes).
                     (d) C0 inherits S1''s stops (QA §4: G1.14 fails with C0 on its own G1.8 number; until the Bible has a corridor
                         number). (e) CB-0 is exposed and measured on the white wall beside the fluted window (= B1's wall,
                         0.419 / 0.174, Bible bath L 86-90), not on the limestone hero_wall_mid.
                     Default stays v3; nothing of v3 changes.

  python3 process_v8.py <id> [--render <png>] [--suffix -v2] [--grade-order v1|v2] [--wb-point auto|legacy] [--lock v1|v2|none]
                        [--exposure cap|bible] [--grade v3|v4] [--stops S] [--target L] [--out-dir <dir>] [--label <text>]
"""
import argparse
import colorsys
import json
import os
import sys

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import v7_frames as VF  # noqa: E402
import lock_v2 as LK  # noqa: E402

# per-frame grade targets, unchanged from process_v7 (Bible: M0 corner 92-95; hall / corridor 2/3 stop under the living;
# lamp-lit bath 84-88; the rest 90, the agent's working value: G1.8 / BIB1 open)
TARGET_L = {"M0": 93.0, "H0": 82.0, "C0": 82.0, "B1": 86.0, "B2": 86.0}
POSE_BASE = {"H0x": "H0", "H0e": "H0", "M0p": "M0", "M0x": "M0", "PD-35": "D1", "W0-in": "W0", "S1prime": "C0", "R2m": "C0",
             "K-boy-0": "K-boy", "K-girl-0": "K-girl", "CB-0": "B1", "MB-in": "MB0"}
M0_PTS = {"back wall near corner (0.467,0.385) [target 92-95]": (0.467, 0.385), "back wall behind sofa (0.69,0.22) [88-91]": (0.69, 0.22),
          "back wall right edge (0.97,0.31) [82-86]": (0.97, 0.31), "window wall (0.10,0.30)": (0.10, 0.30), "ceiling (0.55,0.04)": (0.55, 0.04),
          "sofa back (0.70,0.60)": (0.70, 0.60), "armchair seat (0.31,0.75)": (0.31, 0.75), "table top oak (0.62,0.715)": (0.62, 0.715)}
M0_WIN = (0.19, 0.375, 0.025, 0.553)
Y = np.array([0.2126, 0.7152, 0.0722])


def s2l(x):
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


def l2s(x):
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(np.clip(x, 0, None), 1 / 2.4) - 0.055)


def L_minus_stops(L, stops):
    """HSL L (0-100, neutral) of a surface `stops` darker than L."""
    return round(float(l2s(s2l(np.array(L / 100.0)) * 2 ** (-stops))) * 100, 1)


# --- v3: the Bible targets (--exposure bible); (target, lo, hi, source) -------------------------------------------------------
HALL_STOPS = 2.0 / 3.0
BIBLE_TARGET = {
    "M0": (93.0, 92.0, 95.0, "Bible 'אור' / 'דעיכת האור בקיר האחורי': back wall by the corner (0.467, 0.385) L 92-95"),
    "H0": (93.0, 92.0, 95.0, "B5 (BIB1): the living vista through the door is the brightest, the living back wall L 92-95; hall walls 2/3 stop under it"),
    "HALL": (L_minus_stops(93.0, HALL_STOPS), L_minus_stops(93.0, HALL_STOPS + 0.2), L_minus_stops(93.0, HALL_STOPS - 0.2),
             "B5 (BIB1): hall walls 2/3 stop under the living back wall (93) = L 75.8, +-0.2 stop"),
    "C0": (L_minus_stops(93.0, HALL_STOPS), L_minus_stops(93.0, HALL_STOPS + 0.2), L_minus_stops(93.0, HALL_STOPS - 0.2),
           "G1.8 PROPOSAL (not a Bible number): entrance and corridor walls 2/3 stop under the living; the Bible 1.6 corridor has no L target"),
    "B1": (88.0, 86.0, 90.0, "Bible 1.6 bath: the wall beside the fluted window L 86-90 (4000 K)"),
    "DEFAULT": (92.0, 90.0, 94.0, "Bible 'אור' 1.4: the wall by the window L 90-94"),
}
BIBLE_KEY = {"M0": "M0", "M0p": "M0", "M0x": "M0", "H0": "H0", "H0x": "HALL", "H0e": "HALL", "C0": "C0", "S1prime": "C0", "R2m": "C0",
             "B1": "B1", "B2": "B1", "CB-0": "B1"}
# frames whose own clay wall reading is not a wall (B2: shower limestone at the group uv; the three poses: no patch): inherit stops
INHERIT_STOPS = {"B2": "B1", "M0x": "M0", "K-boy-0": "K-boy"}
K_GIRL_0_WALL = (0.22, 0.08)     # canvas uv: the white upper wall of the desk (east) wall, left of the prints, above the ledges = the wall K-girl
                                 # reads at hero_wall_mid (0.404, 0.158); a pose sample differs in brightness from its master, so its own wall is
                                 # read instead of inheriting the stops (render-agent, 2026-11-03, after the K-girl-0 r2 retake)
B2_WALL = (0.53, 0.42)           # canvas uv: the white wall left of the mirror frame, below the left sconce's fan (render-agent, 2026-11-03; v2 reads L 88, S 38)
B1_WALL = (0.419, 0.174)         # canvas uv: the clay patch wall_beside_window (xyz 4.55, 9.95, 2.00) = the group CB reference wall
W0_IN_WALL = (0.50, 0.40)        # frame uv: the bare desk wall between the shelf (y 0.12-0.18) and the desk top (y 0.71); the clay's reference_W0
                                 # uv (0.5, 0.121) sits on the shelf's edge in this close pose and read the oak in the r2 still (render-agent, 2026-11-03)
H0_VISTA = (0.35, 0.40)          # the living back wall through the door (clay patch living_vista)
H0_HALL_WALL = (0.681, 0.12)     # the hall wall over the console (clay hero_wall_mid)
WINDOW_WALL_RANGE = (80.0, 88.0)  # B1 of BIB1
# --- v4 ---------------------------------------------------------------------------------------------------------------
# QA's window-wall points (qa/reports/2026-11-03-retakes-g1/data/light-<frame>.json "window_wall"), in the graded file's uv
# (the canvas for the overscan stills K-boy / K-girl, the frame otherwise)
WINDOW_WALL_PTS_V4 = {"M0": (0.10, 0.30), "K-boy": (0.275, 0.30), "K-girl": (0.275, 0.30), "W0": (0.21, 0.30), "MB0": (0.17, 0.30)}
INHERIT_STOPS_V4 = dict(INHERIT_STOPS, C0="S1prime")
CB0_WALL_V4 = B1_WALL
WALL_TARGET_HSL = (36.0, 20.0, 93.0)
WALL_C_MAX = 7.0
WALL_H_RANGE = (32.0, 40.0)
STOPS_SANITY = 1.5
# --- v5 (2026-11-04, Bible 1.8.4; briefs/render-m0-composite-and-cleanup-2026-11-04.md task 3) ---------------------------------
# (1) the living back wall L 90-94 (Bible 1.8 B1 (1); v3 / v4 still judged M0 / M0p / H0's vista against 1.0's 92-95)
BIBLE_TARGET_V5 = {
    "M0": (92.0, 90.0, 94.0, "Bible 1.8 B1 (1) / 1.8.4: the living back wall by the corner L 90-94 (1.0's 92-95 retired)"),
    "H0": (92.0, 90.0, 94.0, "Bible 1.8.4 (3): the living back wall through the door at target (1), L 90-94; the hall walls L* 75-78"),
}
# (3) BIB2: the corridor walls CIELAB L* 72-75 at the right-wall points, projected with the plan cameras (C0 (2.397, 17.11, 1.20), S1' (2.641, 13.00,
# 1.20), yaw 0, u0 0.50, v0 0.46, 24 mm) and checked on the round-4 clay (a clean wall patch, L* std 0.03, no edge within 64 px): the frame uv
LSTAR_TARGET_V5 = {
    "C0": (73.5, 72.0, 75.0, (0.8578, 0.3695), "Bible 1.8.4 BIB2: corridor right wall at plan (3.10, 15.80, 1.30), L* 72-75 (verified on the clay: frame (0.8578, 0.3695))"),
    "S1prime": (73.5, 72.0, 75.0, (0.7550, 0.3612), "Bible 1.8.4 BIB2: corridor right wall at plan (3.10, 11.80, 1.30), L* 72-75 (verified on the clay: frame (0.7550, 0.3612))"),
}
HALL_LSTAR_V5 = (75.0, 78.0)
# the view at the corridor's end (the living through the hall), frame uv boxes read on the clay: it must stay the brightest surface
VISTA_BOX_V5 = {"C0": (0.435, 0.495, 0.30, 0.56), "S1prime": (0.325, 0.455, 0.24, 0.58), "H0": (0.26, 0.44, 0.05, 0.95)}
SILHOUETTE_FRAMES_V5 = {"D1"}      # QA 2026-11-04 §4: D1's protected boxes left 1.5-2.5 dE steps on the wall at their edges
CHROMA_GUARD_DC = 1.5            # B4: the lift may add at most +1.5 Lab chroma to the near-white population


def lab_of(sr):
    """sRGB 0..1 (N x 3) -> CIE Lab (D65)."""
    lin = s2l(np.clip(sr, 0, 1))
    Mx = np.array([[0.4124564, 0.3575761, 0.1804375], [0.2126729, 0.7151522, 0.0721750], [0.0193339, 0.1191920, 0.9503041]])
    xyz = lin @ Mx.T / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    L = 116 * f[:, 1] - 16
    a = 500 * (f[:, 0] - f[:, 1])
    b = 200 * (f[:, 1] - f[:, 2])
    return L, a, b


def near_white_lch(sr, mask):
    sel = sr[mask].reshape(-1, 3)
    if sel.shape[0] < 100:
        return None
    sel = sel[:: max(1, sel.shape[0] // 60000)]
    L, a, b = lab_of(sel)
    C = np.hypot(a, b)
    h = np.degrees(np.arctan2(b, a)) % 360
    return dict(pixels=int(mask.sum()), L_lab=round(float(L.mean()), 2), C=round(float(C.mean()), 2), C_p95=round(float(np.percentile(C, 95)), 2),
                hue=round(float(h.mean()), 1))


def hsl_of(rgb):
    h, l, s = colorsys.rgb_to_hls(*[float(x) for x in rgb])
    return (round(h * 360, 1), round(s * 100, 1), round(l * 100, 1))


def Lmap(arr):
    return (arr.max(2) + arr.min(2)) / 2 * 100


class Still:
    def __init__(self, arr):
        self.a = arr
        self.H, self.W = arr.shape[:2]

    def patch(self, arr, u, v, w=0.01):
        hw = max(2, int(w * self.W / 2))
        x, y = int(u * self.W), int(v * self.H)
        return arr[max(0, y - hw):y + hw + 1, max(0, x - hw):x + hw + 1].reshape(-1, 3).mean(0)


# ---------------------------------------------------------------------------------------------------------------
# sample points
# ---------------------------------------------------------------------------------------------------------------
def choose_points(frame, kind, sc_frame, sc_all, mode, exposure="cap", v4=False):
    """(pts for the readings, white-balance / exposure point, its source, window box, warning)."""
    pts = {}
    for k, v in sc_frame.get("wall_patches", {}).items():
        if "L_hsl" in v:
            pts[f"{k} ({v['u']:.3f},{v['v']:.3f}) clay L {v['L_hsl']}"] = (v["u"], v["v"])
    warn = None
    wp = sc_frame.get("wall_patches", {})
    hero = wp.get("hero_wall_mid", {})
    if "L_hsl" in hero:
        wb_pt, src = (hero["u"], hero["v"]), "hero_wall_mid (clay selfcheck)"
    elif mode == "legacy":
        wb_pt, src = (0.5, 0.3), "default (0.5, 0.3): process_v7 fallback"
        warn = "legacy fallback point: not checked against a wall"
    else:
        refs = {k: v for k, v in wp.items() if k.startswith("reference_") and "L_hsl" in v}
        wb_pt, src = None, None
        if refs:
            k, v = next(iter(refs.items()))
            ok = True
            if kind == "pose":
                base = POSE_BASE.get(frame)
                bl = sc_all.get(base, {}).get("wall_patches", {}).get(k, {}).get("L_hsl")
                ok = bl is not None and abs(v["L_hsl"] - bl) <= 6.0 and 65 <= v["L_hsl"] <= 96
            if ok:
                wb_pt, src = (v["u"], v["v"]), f"{k} (clay reference patch, clay L {v['L_hsl']}, target {v.get('target')})"
        if wb_pt is None:
            wb_pt, src = (0.5, 0.3), "default (0.5, 0.3): no wall patch in the clay selfcheck"
            warn = "NOT VALID: no clay wall patch for this still; the exposure reading is not a wall reading"
    win_box = None
    for nm, b in sc_frame.get("boxes", {}).items():
        if b["kind"] == "window":
            win_box = tuple(b["box"])
    if frame == "H0":
        win_box = (0.26, 0.44, 0.05, 0.95)
    if frame == "M0":
        pts.update(M0_PTS)
        wb_pt, src = (0.467, 0.385), "Bible corner point (0.467, 0.385)"
        win_box = M0_WIN
    if exposure == "bible":
        if frame == "H0":
            wb_pt, src, warn = H0_VISTA, "living vista through the door (0.35, 0.40): B5, the brightest surface; the hall wall is measured against it", None
            pts["hall wall over the console (0.681,0.120) [B5: 2/3 stop under the vista]"] = H0_HALL_WALL
        elif frame == "B1":
            wb_pt, src = B1_WALL, "wall beside the fluted window (0.419, 0.174) = clay wall_beside_window / reference_CB (Bible 1.6 bath: L 86-90)"
            warn = None
        elif frame == "W0-in":
            wb_pt, src = W0_IN_WALL, "desk wall between shelf and desk (0.50, 0.40), render-agent point: the clay's reference_W0 uv is on the shelf edge in this pose"
            warn = None
            pts["desk wall between shelf and desk (0.500,0.400) [W0 group: L 90-94]"] = W0_IN_WALL
        elif frame == "K-girl-0":
            wb_pt, src = K_GIRL_0_WALL, "white upper wall of the desk wall, left of the prints (0.22, 0.08), render-agent point: the wall K-girl reads at hero_wall_mid"
            warn = None
            pts["upper white wall left of the prints (0.220,0.080) [Kg group: L 90-94]"] = K_GIRL_0_WALL
        elif frame == "B2":
            wb_pt, src = B2_WALL, "wall beside the mirror (0.53, 0.42), render-agent point: the clay reference uv is shower limestone in B2; stops inherited from B1"
            warn = None
            pts["wall beside the mirror (0.530,0.420) [reading only; B2 inherits B1's stops]"] = B2_WALL
        elif frame in INHERIT_STOPS and warn:
            warn = f"no clay wall patch: stops inherited from {INHERIT_STOPS[frame]} (one exposure per camera point); the default point is a reading only"
    if v4:
        if frame == "CB-0":
            wb_pt, src, warn = CB0_WALL_V4, "v4: the white wall beside the fluted window (0.419, 0.174) = B1's wall (Bible 1.6 bath L 86-90); v3 read the limestone at hero_wall_mid", None
            pts["white wall beside the fluted window (0.419,0.174) [B1 group: L 86-90]"] = CB0_WALL_V4
        if frame in WINDOW_WALL_PTS_V4 and frame != "M0":          # M0's (0.10, 0.30) is already in M0_PTS
            u, v = WINDOW_WALL_PTS_V4[frame]
            pts[f"window wall, QA point ({u:.3f},{v:.3f}) [Bible 1.8 B1 (2): 80-88]"] = (u, v)
    if win_box is None:
        win_box = (0.0, 1.0, 0.0, 1.0)
    return pts, wb_pt, src, win_box, warn


# ---------------------------------------------------------------------------------------------------------------
# readings
# ---------------------------------------------------------------------------------------------------------------
def measure(st, arr, pts, win_box, frame):
    W, H = st.W, st.H
    out = {k: hsl_of(st.patch(arr, *p)) for k, p in pts.items()}
    L = Lmap(arr)
    wx0, wx1, wy0, wy1 = int(win_box[0] * W), int(win_box[1] * W), int(win_box[2] * H), int(win_box[3] * H)
    wl = L[wy0:wy1, wx0:wx1]
    sat = arr.max(2) >= 254.5 / 255
    out["brightest area (window / door): L p50 / p99 / max"] = (round(float(np.median(wl)), 1), round(float(np.percentile(wl, 99)), 1), round(float(wl.max()), 1))
    out["pixels with a 255 channel: inside / outside that area"] = (int(sat[wy0:wy1, wx0:wx1].sum()), int(sat.sum() - sat[wy0:wy1, wx0:wx1].sum()))
    out["frame L p99 / max"] = (round(float(np.percentile(L, 99)), 1), round(float(L.max()), 1))
    k = max(4, int(0.005 * W))
    pm = sliding_window_view(L, (k, k))[::4, ::4].mean((2, 3))
    out["darkest 0.5% patch L [12-15]"] = round(float(pm.min()), 1)
    out["frame mean L"] = round(float(L.mean()), 1)
    if frame == "H0":
        yv = s2l(st.patch(arr, *H0_VISTA)).dot(Y)
        yh = s2l(st.patch(arr, *H0_HALL_WALL)).dot(Y)
        out["H0 hall wall under the living vista: stops [B5: 0.47-0.87]"] = round(float(np.log2(max(yv, 1e-6) / max(yh, 1e-6))), 3)
    if frame == "M0":
        reg = arr[int(0.87 * H):int(0.99 * H), int(0.42 * W):int(0.98 * W)].reshape(-1, 3)[::29]
        hls = np.array([colorsys.rgb_to_hls(*c) for c in reg])
        out["floor median HSL (u0.42-0.98,v0.87-0.99) [H30-40 S30-45 L68-78]"] = (round(float(np.median(hls[:, 0])) * 360, 1), round(float(np.median(hls[:, 2])) * 100, 1), round(float(np.median(hls[:, 1])) * 100, 1))
        Lm = np.asarray(Image.fromarray(L.astype(np.float32)).filter(ImageFilter.MedianFilter(3)))
        r = Lm[int(0.76 * H):int(0.83 * H), int(0.52 * W):int(0.84 * W)]
        out["contact shadow under sofa: min L / p1"] = (round(float(r.min()), 1), round(float(np.percentile(r, 1)), 1))
    return out


# ---------------------------------------------------------------------------------------------------------------
# the grade (recipe 2.6), v1 and v2 orders
# ---------------------------------------------------------------------------------------------------------------
def rolloff(lin, knee_L=0.94, asym_L=0.97):
    k_knee = float(s2l(np.array(knee_L)))
    cap = float(s2l(np.array(asym_L)))
    m = lin.max(2, keepdims=True)
    mc = np.where(m > k_knee, k_knee + (cap - k_knee) * (1 - np.exp(-(m - k_knee) / (cap - k_knee))), m)
    return lin * np.where(m > 0, mc / np.maximum(m, 1e-6), 1)


def s_curve(sr, mix=0.12):
    return (1 - mix) * sr + mix * (sr * sr * (3 - 2 * sr))


def darkest_patch(sr, W):
    Lg = Lmap(sr)
    kk = max(4, int(0.005 * W))
    return float(sliding_window_view(Lg, (kk, kk))[::4, ::4].mean((2, 3)).min())


def black_point(sr, W, both_ways=False):
    dmin = darkest_patch(sr, W)
    if dmin < 12.0:
        bp = (0.125 - dmin / 100) / (1 - dmin / 100)
        return bp + (1 - bp) * sr, {"darkest_patch_L_before": round(dmin, 1), "lift_to_L": 12.5, "blend": round(float(bp), 4)}
    if both_ways and dmin > 15.0:
        # shadow-only pull: sr' = sr - b * ((p - sr) / p)^2 below the pivot p, 0 at the pivot and above; b so the darkest patch lands at 13.5
        p, d = 0.45, dmin / 100
        b = (d - 0.135) / ((p - d) / p) ** 2
        w = np.clip((p - sr) / p, 0, 1) ** 2
        return np.clip(sr - b * w, 0, 1), {"darkest_patch_L_before": round(dmin, 1), "pull_to_L": 13.5, "pivot_sRGB": p, "b": round(float(b), 4),
                                           "note": "v3: shadow-only pull (Bible black point 12-15 both ways)"}
    return sr, {"darkest_patch_L_before": round(dmin, 1), "lift": "none (already >= 12)" + (" and <= 15" if both_ways else "")}


def chroma_guard(lin, sr_before, W, limit=CHROMA_GUARD_DC):
    """B4: the near-white population (HSL L > 80 after the grade) may not gain more than `limit` Lab chroma. Returns (lin, record)."""
    sr_now = np.clip(l2s(lin), 0, 1)
    m_after = Lmap(sr_now) > 80.0
    before, after = near_white_lch(sr_before, m_after), near_white_lch(sr_now, m_after)
    rec = {"population": "pixels with HSL L > 80 after the grade", "before": before, "after": after}
    if before is None or after is None:
        rec["delta_C"] = None
        return lin, rec
    dC = after["C"] - before["C"]
    rec["delta_C"] = round(float(dC), 2)
    rec["limit"] = limit
    if dC <= limit:
        rec["applied"] = "none (within +%.1f C)" % limit
        return lin, rec
    f = max(0.6, (before["C"] + 1.0) / max(after["C"], 1e-6))
    Ln = Lmap(sr_now)
    wgt = np.clip((Ln - 75.0) / 10.0, 0, 1)[..., None]           # feather 75 -> 85
    lum = (lin * Y).sum(2, keepdims=True)
    lin2 = lum + (lin - lum) * (1 - wgt * (1 - f))
    rec["applied"] = {"chroma_factor_near_white": round(float(f), 4), "feather_L": [75, 85]}
    rec["after_guard"] = near_white_lch(np.clip(l2s(lin2), 0, 1), m_after)
    return lin2, rec


def chain_L(patch_lin, stops):
    """HSL L of one patch (linear RGB after white balance) after exposure -> chroma -10 % -> S curve -> roll-off (the v2 chain
    without the black point, which moves a wall by < 0.2 L)."""
    lin = patch_lin * 2 ** stops
    lum = lin.dot(Y)
    lin = lum + 0.90 * (lin - lum)
    sr = np.clip(l2s(lin), 0, 1)
    sr = s_curve(sr, 0.12)
    lin2 = rolloff(s2l(sr)[None, None, :], 0.94, 0.97)[0, 0]
    sr2 = np.clip(l2s(lin2), 0, 1)
    return float((sr2.max() + sr2.min()) / 2 * 100)


def chain_Lstar(patch_lin, stops):
    """CIELAB L* of one patch after the chain_L chain (v5: the corridor targets are L*, as QA measures them)."""
    lin = patch_lin * 2 ** stops
    lum = lin.dot(Y)
    lin = lum + 0.90 * (lin - lum)
    sr = np.clip(l2s(lin), 0, 1)
    sr = s_curve(sr, 0.12)
    lin2 = rolloff(s2l(sr)[None, None, :], 0.94, 0.97)[0, 0]
    return float(lab_arr(np.clip(l2s(lin2), 0, 1)[None, :])[0, 0])


def solve_stops_lstar(patch_lin, target, lo=-2.5, hi=2.5):
    for _ in range(26):
        m = (lo + hi) / 2
        if chain_Lstar(patch_lin, m) < target:
            lo = m
        else:
            hi = m
    return (lo + hi) / 2


def solve_stops(patch_lin, target_L, lo=-2.5, hi=2.5):
    """The stops that put the patch's HSL L on target after the chain (bisection; the chain is monotonic in exposure)."""
    for _ in range(26):
        m = (lo + hi) / 2
        if chain_L(patch_lin, m) < target_L:
            lo = m
        else:
            hi = m
    return (lo + hi) / 2


def grade(st, wb_pt, target_L, order="v2", exposure="cap", fixed_stops=None, lstar=False):
    a = st.a
    lin = s2l(a)
    g = {"order": order, "exposure_mode": exposure}
    cur = st.patch(a, *wb_pt)
    h, l, s = colorsys.rgb_to_hls(*cur)
    tgt = np.array(colorsys.hls_to_rgb(36 / 360, l, s))
    cur_l, tgt_l = s2l(cur), s2l(tgt)
    gain = (tgt_l / tgt_l.dot(Y)) / (cur_l / cur_l.dot(Y))
    gain = np.clip(gain, 0.9, 1.1)
    g["white_balance"] = {"patch": list(wb_pt), "H_before": round(h * 360, 1), "H_target": 36, "gains_rgb": [round(float(x), 4) for x in gain], "gain_clip": "0.9-1.1"}
    lin = lin * gain
    pl = s2l(st.patch(l2s(lin), *wb_pt)).dot(Y)
    tl = s2l(np.array([target_L / 100] * 3)).dot(Y)
    need = float(np.log2(tl / max(pl, 1e-6)))
    if exposure == "bible":
        patch_lin = s2l(st.patch(l2s(lin), *wb_pt))
        need = solve_stops(patch_lin, target_L)          # on the chain's HSL L, not on the linear luminance (a warm white reads 1-4 L lower in HSL)
        if lstar:                                        # v5: the corridor's target is CIELAB L*
            need = solve_stops_lstar(patch_lin, target_L)
        if fixed_stops is not None:
            stops = float(fixed_stops)
            flag = f"stops inherited from the group reference ({stops:+.3f}); this frame's own need {need:+.3f}"
        else:
            stops = float(np.clip(need, -STOPS_SANITY, STOPS_SANITY))
            flag = "to the Bible target" if abs(need) <= STOPS_SANITY else f"SANITY CAP +-{STOPS_SANITY}: the still needs {need:+.3f}"
        g["exposure"] = {"patch": list(wb_pt), "target_L": target_L, "needed_stops": round(need, 3), "applied_stops": round(stops, 3), "flag": flag,
                         "solver": "bisection on the HSL L of the patch after exposure, chroma, S curve and roll-off (v3)",
                         "cap": f"none: the Bible target (V7Q4, test page only); sanity +-{STOPS_SANITY} stop"}
    else:
        stops = float(np.clip(need, -0.2, 0.2))
        g["exposure"] = {"patch": list(wb_pt), "target_L": target_L, "needed_stops": round(need, 3), "applied_stops": round(stops, 3),
                         "flag": ("DARK: needs more than +0.2 stop, not lifted further" if need > 0.2 else ("bright: needs more than -0.2 stop" if need < -0.2 else "within cap")),
                         "cap": "+-0.2 stop (recipe 2.6.2; V7Q4 open)"}
    lin = lin * 2 ** stops
    lum = (lin * Y).sum(2, keepdims=True)
    lin = lum + 0.90 * (lin - lum)
    g["saturation"] = "chroma x0.90 (linear, toward luminance)"
    if order == "v1":
        lin = rolloff(lin, 0.94, 0.9725)
        g["highlight_rolloff"] = {"knee_L": 94, "asymptote_L": 97.25, "on": "max channel, hue kept", "position": "before the S curve and the black point (v7)"}
        sr = np.clip(l2s(lin), 0, 1)
        sr = s_curve(sr, 0.12)
        g["s_curve"] = {"mix": 0.12, "shape": "smoothstep blend"}
        sr, g["black_point"] = black_point(sr, st.W)
    else:
        sr = np.clip(l2s(lin), 0, 1)
        sr = s_curve(sr, 0.12)
        g["s_curve"] = {"mix": 0.12, "shape": "smoothstep blend"}
        sr, g["black_point"] = black_point(sr, st.W, both_ways=(exposure == "bible"))
        lin2 = s2l(np.clip(sr, 0, 1))
        if exposure == "bible":
            lin2, g["near_white_chroma_guard_B4"] = chroma_guard(lin2, a, st.W)
        lin2 = rolloff(lin2, 0.94, 0.97)
        sr = np.clip(l2s(lin2), 0, 1)
        g["highlight_rolloff"] = {"knee_L": 94, "asymptote_L": 97.0, "on": "max channel, hue kept", "position": "last (v2): the ceiling of the chain"}
    g["grain"] = "none"
    g["vignette"] = "none"
    return np.clip(sr, 0, 1), g


# ---------------------------------------------------------------------------------------------------------------
def lab_arr(sr):
    lin = s2l(np.clip(sr, 0, 1))
    M = np.array([[0.4124564, 0.3575761, 0.1804375], [0.2126729, 0.7151522, 0.0721750], [0.0193339, 0.1191920, 0.9503041]])
    xyz = lin @ M.T / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def srgb_from_lab(lab):
    fy = (lab[..., 0] + 16) / 116
    fx, fz = fy + lab[..., 1] / 500, fy - lab[..., 2] / 200
    inv = lambda t: np.where(t ** 3 > 0.008856, t ** 3, (t - 16 / 116) / 7.787)  # noqa: E731
    xyz = np.stack([inv(fx) * 0.95047, inv(fy), inv(fz) * 1.08883], -1)
    Mi = np.array([[3.2404542, -1.5371385, -0.4985314], [-0.9692660, 1.8760108, 0.0415560], [0.0556434, -0.2040259, 1.0572252]])
    return np.clip(l2s(np.clip(xyz @ Mi.T, 0, 1)), 0, 1)


def wall_reading(st, arr, uv):
    """HSL and CIELAB (L*, C*, h_ab) of the 1 % patch at uv."""
    p = st.patch(arr, *uv)
    lab = lab_arr(p[None, :])[0]
    h, s_, l_ = hsl_of(p)
    return dict(H=h, S=s_, L=l_, L_star=round(float(lab[0]), 2), C_star=round(float(np.hypot(lab[1], lab[2])), 2),
                h_ab=round(float(np.degrees(np.arctan2(lab[2], lab[1]))), 1))


def protect_silhouettes(graded, boxes, H, W):
    """v5 (D1): inside each protected box only the object's silhouette, not the box: the pixels that differ from the wall around the
    box in the chroma plane (|d(a*, b*)| > 3 from the median of a 40 px ring outside every box), or textured (high-pass std > 1.6 grey levels),
    or dark (L* < 75); closed 9 px,
    holes filled, components >= 150 px; feathered 3 px. The wall inside a box is corrected like the wall outside it (QA §4: no step)."""
    import cv2
    lab = lab_arr(graded)
    allb = np.zeros((H, W), np.uint8)
    for u0, u1, v0, v1 in boxes:
        allb[max(0, int(v0 * H)):int(v1 * H), max(0, int(u0 * W)):int(u1 * W)] = 1
    g = (graded.mean(2) * 255).astype(np.float32)
    hp = g - cv2.GaussianBlur(g, (0, 0), 2.0)
    en = np.sqrt(cv2.GaussianBlur(hp * hp, (0, 0), 2.0))
    m = np.zeros((H, W), np.uint8)
    for u0, u1, v0, v1 in boxes:
        x0, x1, y0, y1 = max(0, int(u0 * W)), min(W, int(u1 * W)), max(0, int(v0 * H)), min(H, int(v1 * H))
        if x1 <= x0 or y1 <= y0:
            continue
        rx0, rx1, ry0, ry1 = max(0, x0 - 40), min(W, x1 + 40), max(0, y0 - 40), min(H, y1 + 40)
        ring = np.ones((ry1 - ry0, rx1 - rx0), bool) & (allb[ry0:ry1, rx0:rx1] == 0)
        if ring.sum() < 50:
            m[y0:y1, x0:x1] = 1
            continue
        ref = np.median(lab[ry0:ry1, rx0:rx1][ring], 0)
        # the wall's light falloff changes L*, not a* / b*: the object is what differs in the chroma plane (> 3), is textured, or is dark
        dab = np.sqrt(((lab[y0:y1, x0:x1, 1:] - ref[1:]) ** 2).sum(-1))
        m[y0:y1, x0:x1] |= ((dab > 3.0) | (en[y0:y1, x0:x1] > 1.6) | (lab[y0:y1, x0:x1, 0] < 75.0)).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    # holes: the background not reached from outside (a 1 px zero border, so the seed is always background)
    pad = np.pad(m, 1)
    mk = np.zeros((H + 4, W + 4), np.uint8)
    cv2.floodFill(pad, mk, (0, 0), 2)
    m = m | (pad[1:-1, 1:-1] == 0).astype(np.uint8)
    n, lab_, st, _ = cv2.connectedComponentsWithStats(m)
    keep = np.zeros_like(m)
    for i in range(1, n):
        if st[i, cv2.CC_STAT_AREA] >= 150:
            keep[lab_ == i] = 1
    return cv2.GaussianBlur(keep.astype(np.float32), (0, 0), 3.0)


def protect_mask(frame, fid, H, W, overscan, graded=None, silhouette=False):
    """The product boxes and the upholstered fixed furniture (sofa, armchair, beds) in the still's uv, feathered 30 px
    (v5, D1: their silhouettes, feathered 3 px)."""
    m = np.zeros((H, W), np.float32)
    boxes = [b for b in VF.product_boxes(frame, fid).values()]
    for nm, (kind, b) in VF.fixed_boxes(frame, False, fid).items():     # overscan False: the selfcheck's own uv = the still's uv
        if kind == "furniture" and any(w in nm.lower() for w in ("sofa", "armchair", "bed")):   # the upholstered ones (M0 1.2: from its clay);
            boxes.append(b)                                                                                     # oak and plaster are gated by C*
    if frame == "M0":
        boxes += list(VF.M0_FURNITURE.values())
    if silhouette and graded is not None:
        return protect_silhouettes(graded, boxes, H, W), len(boxes)
    for u0, u1, v0, v1 in boxes:
        m[max(0, int(v0 * H)):int(v1 * H), max(0, int(u0 * W)):int(u1 * W)] = 1
    from PIL import ImageFilter as _IF
    mi = Image.fromarray((m * 255).astype(np.uint8)).filter(_IF.GaussianBlur(30))
    return np.asarray(mi, np.float32) / 255.0, len(boxes)


def wall_hue_v4(st, graded, ref_uv, frame, fid, overscan, force=False, silhouette=False):
    """(a) of v4: the masked hue / chroma correction of the warm-white walls when the reference wall's H > 40 (QA qa_wall);
    force: apply whatever this frame reads (it inherits its group reference's stops and correction)."""
    before = wall_reading(st, graded, ref_uv)
    rec = {"rule": "QA 2026-11-03 §4 / §11.2: wall H after the lift reported; corrected when H > 40 (masked, walls only)", "reference_uv": list(ref_uv),
           "before": before, "applied": False}
    if force:
        rec["inherited_from_group_reference"] = True
    if before["H"] <= WALL_H_RANGE[1] and not force:
        rec["why_not"] = "H <= 40"
        return graded, rec
    ht = colorsys.hls_to_rgb(WALL_TARGET_HSL[0] / 360, WALL_TARGET_HSL[2] / 100, WALL_TARGET_HSL[1] / 100)
    lt = lab_arr(np.array(ht)[None, :])[0]
    h_t = np.arctan2(lt[2], lt[1])
    lab = lab_arr(graded)
    C = np.hypot(lab[..., 1], lab[..., 2])
    h = np.arctan2(lab[..., 2], lab[..., 1])
    ss = lambda x, e0, e1: np.clip((x - e0) / (e1 - e0), 0, 1) ** 2 * (3 - 2 * np.clip((x - e0) / (e1 - e0), 0, 1))  # noqa: E731
    # C* ramp 10 -> 18 (QA's qa_wall: 14 -> 18): a lamp's glow on the wall runs from C* ~20 at the shade down to the wall's ~8, and
    # the steep 14 -> 18 ramp turned it into a white ring round a yellow core (M0's left sconce, tried 2026-11-04); 8 -> 16 left the
    # walls at C* 9-10 (D1, MB-in) part-corrected; 10 -> 18 corrects them fully and keeps the glow smooth
    w = ss(lab[..., 0], 80, 84) * (1 - ss(lab[..., 0], 97.3, 98.5)) * (1 - ss(C, 10, 18))
    dh = np.angle(np.exp(1j * (h - h_t)))
    w = w * ss(dh, 0.0, np.radians(6))
    prot, nbox = protect_mask(frame, fid, st.H, st.W, overscan, graded=graded, silhouette=silhouette)
    w = w * (1 - prot)
    out = lab.copy()
    hn = h - dh * w
    Cn = C - (C - np.minimum(C, 6.5)) * w
    out[..., 1], out[..., 2] = Cn * np.cos(hn), Cn * np.sin(hn)
    b = np.where(w[..., None] > 1e-4, srgb_from_lab(out), graded)
    rec.update(applied=True, after=wall_reading(st, b, ref_uv), pixels_touched_pct=round(float((w > 0.05).mean() * 100), 1),
               protected_boxes=nbox, target=dict(hsl=list(WALL_TARGET_HSL), h_ab=round(float(np.degrees(h_t)), 1), C_cap=6.5),
               mask=("L* 80-97.3, C* ramp 10-18, hue yellower than the target (0-6 deg ramp), outside the product boxes and the sofa / armchair / bed boxes (feather 30 px)"
                     if not silhouette else "L* 80-97.3, C* ramp 10-18, hue yellower than the target (0-6 deg ramp), outside the SILHOUETTES of the protected objects (v5, feather 3 px)"))
    return b, rec


def v5_checks(st, graded, frame, overscan, lstar, pts, after):
    """Bible 1.8.4 additions: the corridor-end view the brightest surface (C0, S1'; H0's vista too), the hall walls L* 75-78 (H0)."""
    out = {"checks": {}}
    lab = lab_arr(graded)
    Ls = lab[..., 0]
    H, W = Ls.shape
    if frame in VISTA_BOX_V5:
        u0, u1, v0, v1 = VISTA_BOX_V5[frame]
        if overscan:
            u0, u1 = (u0 * 3840 + 116) / 4072, (u1 * 3840 + 116) / 4072
            v0, v1 = (v0 * 2160 + 65) / 2290, (v1 * 2160 + 65) / 2290
        box = np.zeros((H, W), bool)
        box[int(v0 * H):int(v1 * H), int(u0 * W):int(u1 * W)] = True
        import cv2
        Lm = cv2.medianBlur(np.clip(Ls, 0, 100).astype(np.float32), 5)
        surf = ~box
        surf[:int(0.12 * H)] = False                        # the ceiling band: lamps and the roof-light slot are sources, not surfaces
        surf &= Lm < 97.0                                    # any other emitter
        vista = float(np.percentile(Lm[box], 95))
        rest = float(np.percentile(Lm[surf], 99.5))
        out["vista"] = dict(box_uv=[round(x, 4) for x in (u0, u1, v0, v1)], vista_Lstar_p95=round(vista, 2), surfaces_Lstar_p99_5=round(rest, 2),
                            rule="Bible 1.8.4: the view at the corridor's end the brightest surface (p95 of the vista box above p99.5 of every other surface; "
                                 "the ceiling band v < 0.12 and emitters L* >= 97 left out)")
        out["checks"]["bible_vista_brightest_1_8_4"] = bool(vista >= rest)
    if frame == "H0":
        hk = "hall wall over the console (0.681,0.120) [B5: 2/3 stop under the vista]"
        if hk in pts:
            p = st.patch(graded, *pts[hk])
            Lh = round(float(lab_arr(p[None, :])[0, 0]), 2)
            out["hall_wall_Lstar"] = dict(L_star=Lh, range=list(HALL_LSTAR_V5))
            out["checks"]["bible_hall_Lstar_75_78_1_8_4"] = bool(HALL_LSTAR_V5[0] - 0.5 <= Lh <= HALL_LSTAR_V5[1] + 0.5)
    if lstar:
        out["scale"] = "CIELAB L* (BIB2), not HSL L"
    return out


def bible_target(frame):
    key = BIBLE_KEY.get(frame, "DEFAULT")
    t, lo, hi, src = BIBLE_TARGET[key]
    return t, (lo, hi), src


def process(fid, render_path=None, suffix="-v2", grade_order="v2", wb_mode="auto", lock_mode="v2", out_dir=None, label=None,
            exposure="cap", stops=None, target=None, grade_mode="v3", hue_force=None):
    """grade_mode "v4" (2026-11-04) implies exposure "bible" and adds the wall-hue correction, the absolute C* check, the window
    wall points, C0 / CB-0 as in the module docstring; hue_force True / False overrides the H > 40 trigger (a frame that inherits
    its group reference's stops inherits its correction too)."""
    v4 = grade_mode in ("v4", "v5")
    v5 = grade_mode == "v5"
    if v4:
        exposure = "bible"
    frame, kind, clay_file, pan, overscan, room = VF.frame(fid)
    od = out_dir or VF.out_dir(fid)
    render_path = render_path or os.path.join(od, fid + ".png")
    sc_all = VF.selfcheck()
    sc = sc_all[frame]
    im = Image.open(render_path).convert("RGB")
    a = np.asarray(im, float) / 255.0
    st = Still(a)
    lstar = False
    if exposure == "bible":
        target_L, target_range, target_src = bible_target(frame)
        if v5 and BIBLE_KEY.get(frame) in BIBLE_TARGET_V5:
            t_, lo_, hi_, target_src = BIBLE_TARGET_V5[BIBLE_KEY[frame]]
            target_L, target_range = t_, (lo_, hi_)
        if v5 and frame in LSTAR_TARGET_V5:
            t_, lo_, hi_, _pt, target_src = LSTAR_TARGET_V5[frame]
            target_L, target_range, lstar = t_, (lo_, hi_), True
        if target is not None:
            target_L, target_src = float(target), f"override --target {target}: the group reference's graded value on the same wall ({target_src})"
            target_range = (target_L - 2.0, target_L + 2.0)
    else:
        target_L, target_range, target_src = TARGET_L.get(POSE_BASE.get(frame, frame), 90.0), None, "process_v7 working value"
    pts, wb_pt, wb_src, win_box, warn = choose_points(frame, kind, sc, sc_all, wb_mode, exposure, v4)
    if lstar:
        wb_pt = LSTAR_TARGET_V5[frame][3]
        wb_src, warn = f"v5: corridor right wall {tuple(wb_pt)} (Bible 1.8.4 BIB2 point, projected with the plan camera and verified on the clay)", None
        pts[f"corridor right wall {tuple(wb_pt)} [BIB2: L* 72-75]"] = wb_pt
    before = measure(st, a, pts, win_box, frame)
    graded, g = grade(st, wb_pt, target_L, grade_order, exposure, stops, lstar=lstar)
    if lstar and stops is None:
        # the solver's chain leaves out the black point and the guard: the full chain is iterated on the measured L* (secant in log luminance)
        it = []
        for _ in range(4):
            Lm = float(lab_arr(st.patch(graded, *wb_pt)[None, :])[0, 0])
            it.append(dict(stops=g["exposure"]["applied_stops"], L_star=round(Lm, 2)))
            if abs(Lm - target_L) <= 0.15:
                break
            ylum = lambda L_: ((L_ + 16) / 116) ** 3        # noqa: E731
            s_new = float(g["exposure"]["applied_stops"]) + float(np.log2(ylum(target_L) / ylum(Lm)))
            need0 = g["exposure"]["needed_stops"]
            graded, g = grade(st, wb_pt, target_L, grade_order, exposure, s_new, lstar=True)
            g["exposure"]["needed_stops"] = need0
            g["exposure"]["flag"] = "to the Bible target (L*, the full chain iterated)"
        g["exposure"]["lstar_iterations"] = it
    if v4:
        g["wall_after_lift_v4"] = wall_reading(st, graded, wb_pt)
        if hue_force is False or (hue_force is None and warn):
            g["wall_hue_v4"] = {"applied": False, "why_not": ("the group reference was not corrected" if hue_force is False else "no wall at the reference point: " + warn),
                                "before": g["wall_after_lift_v4"]}
        else:
            graded, g["wall_hue_v4"] = wall_hue_v4(st, graded, wb_pt, frame, fid, overscan, force=bool(hue_force),
                                                   silhouette=(v5 and frame in SILHOUETTE_FRAMES_V5))
    g["white_balance"]["source"] = wb_src
    g["exposure"]["source"] = wb_src
    g["exposure"]["target_source"] = target_src
    if target_range:
        g["exposure"]["target_range"] = list(target_range)
    if warn:
        g["exposure"]["flag"] += " | " + warn
    gim = Image.fromarray((graded * 255 + 0.5).astype(np.uint8))
    base = os.path.join(od, fid)
    gim.save(base + "-graded" + suffix + ".png")
    after = measure(st, graded, pts, win_box, frame)
    files = {"graded": os.path.relpath(base + "-graded" + suffix + ".png", VF.REPO)}
    if overscan:
        x0, y0, x1, y1 = VF.frame_box_px(st.W, st.H)
        gim.crop((x0, y0, x1, y1)).save(base + "-frame" + suffix + ".png")
        gim.crop((x0, 0, x1, st.H)).save(base + "-graded-os6" + suffix + ".png")
        files["frame"] = os.path.relpath(base + "-frame" + suffix + ".png", VF.REPO)
        files["os6"] = os.path.relpath(base + "-graded-os6" + suffix + ".png", VF.REPO)
    # lock
    lock = None
    if lock_mode == "v2":
        lock = LK.run_frame(fid, render_path=render_path, out_path=base + "-lock" + suffix + ".json")
        files["lock"] = os.path.relpath(base + "-lock" + suffix + ".json", VF.REPO)
    old = {}
    mp = base + "-measurements.json"
    if os.path.exists(mp):
        m = json.load(open(mp))
        old = {"clay_lock_v1_worst_abs_shift_strong_peaks": m.get("clay_lock_worst_abs_shift_strong_peaks"),
               "grade_v1_exposure": m.get("grade", {}).get("exposure"), "measure_after_v1_window": m.get("measure_after", {}).get("brightest area (window / door): L p50 / p99 / max")}
    win_after = after["brightest area (window / door): L p50 / p99 / max"]
    checks = {"window_p99_le_97": bool(win_after[1] <= 97.0), "frame_L_max_le_97": bool(after["frame L p99 / max"][1] <= 97.0 + 1e-6),
              "no_255": bool(sum(after["pixels with a 255 channel: inside / outside that area"]) == 0),
              "black_point_12_15": bool(12.0 <= after["darkest 0.5% patch L [12-15]"] <= 15.0),
              "exposure_within_cap": bool(abs(g["exposure"]["needed_stops"]) <= 0.2), "exposure_point_valid": warn is None}
    bible = None
    if exposure == "bible":
        L_ref = hsl_of(st.patch(graded, *wb_pt))[2]
        if lstar:
            L_ref = round(float(lab_arr(st.patch(graded, *wb_pt)[None, :])[0, 0]), 2)
        lo, hi = target_range
        inherited = stops is not None
        bible = {"reference_point": list(wb_pt), "reference_source": wb_src, "target_L": target_L, "range": [lo, hi], "measured_L": L_ref,
                 "meets_target": (None if inherited else bool(lo - 0.5 <= L_ref <= hi + 0.5)), "target_source": target_src,
                 "judged_by": (f"the group reference {INHERIT_STOPS.get(frame)} (stops inherited; the reading here is not the reference wall)" if inherited else "own reference wall")}
        wall_hsl = hsl_of(st.patch(graded, *wb_pt))
        bible["reference_HSL"] = list(wall_hsl)
        bible["wall_hue_32_40_sat_15_28"] = bool(32 <= wall_hsl[0] <= 40 and 15 <= wall_hsl[1] <= 28) if frame != "B2" else None
        for k, v in pts.items():
            if "window_wall" in k or "window wall" in k:
                Lw = after[k][2]
                bible["window_wall"] = {"point": k, "L": Lw, "range": list(WINDOW_WALL_RANGE), "ok": bool(WINDOW_WALL_RANGE[0] <= Lw <= WINDOW_WALL_RANGE[1])}
        hk = "H0 hall wall under the living vista: stops [B5: 0.47-0.87]"
        if hk in after:
            bible["hall_under_living_stops"] = {"stops": after[hk], "ok": bool(0.47 <= after[hk] <= 0.87), "hall_wall_L": after.get("hall wall over the console (0.681,0.120) [B5: 2/3 stop under the vista]", [None, None, None])[2]}
        cg = g.get("near_white_chroma_guard_B4") or {}
        bible["near_white_chroma_B4"] = {"delta_C": cg.get("delta_C"), "ok": (cg.get("delta_C") is None) or (cg.get("after_guard") is not None) or (cg.get("delta_C") <= CHROMA_GUARD_DC)}
        if v4:
            wr = wall_reading(st, graded, wb_pt)
            judged = warn is None
            bible["wall_v4"] = dict(reading=wr, judged=judged, H_range=list(WALL_H_RANGE), C_max=WALL_C_MAX,
                                    hue_ok=(bool(WALL_H_RANGE[0] <= wr["H"] <= WALL_H_RANGE[1]) if judged else None),
                                    C_ok=(bool(wr["C_star"] <= WALL_C_MAX) if judged else None),
                                    correction=g.get("wall_hue_v4", {}).get("applied"),
                                    note=(None if judged else "the reference point is not a wall (no clay wall patch): hue and C* not judged here"))
        checks.update({"bible_black_12_15": checks["black_point_12_15"], "bible_no_clip": checks["no_255"] and checks["window_p99_le_97"],
                       "bible_chroma_B4": bible["near_white_chroma_B4"]["ok"]})
        if not inherited:
            checks["bible_target_met"] = bible["meets_target"]
        if "window_wall" in bible:
            checks["bible_window_wall_80_88"] = bible["window_wall"]["ok"]
        if "hall_under_living_stops" in bible:
            checks["bible_hall_2_3_stop_B5"] = bible["hall_under_living_stops"]["ok"]
        if v4 and bible["wall_v4"]["judged"]:
            checks["bible_wall_hue_32_40"] = bible["wall_v4"]["hue_ok"]
            checks["bible_wall_C_le_7_B4"] = bible["wall_v4"]["C_ok"]
        if v5:
            bible["v5"] = v5_checks(st, graded, frame, overscan, lstar, pts, after)
            for k_, v_ in bible["v5"]["checks"].items():
                checks[k_] = v_
        bible["meets_bible"] = bool(all(v for k, v in checks.items() if k.startswith("bible_")))
    res = {"asset_id": fid, "frame": frame, "kind": kind, "label": label, "date": ("2026-11-04" if v4 else "2026-11-03"), "script": "assets/renders/house-nordic-v7-2026-11-02/process_v8.py",
           "settings": {"grade_order": grade_order, "wb_point": wb_mode, "lock": lock_mode, "suffix": suffix, "exposure": exposure, "stops": stops, "target": target,
                        "grade": grade_mode, "hue_force": hue_force, "target_scale": ("CIELAB L*" if lstar else "HSL L")},
           "bible_v3": bible,
           "input": os.path.relpath(render_path, VF.REPO), "size_px": [st.W, st.H], "overscan": overscan, "outputs": files,
           "clay": os.path.relpath(os.path.join(VF.R4, clay_file), VF.REPO), "grade_target_L": target_L,
           "sample_point": {"uv": list(wb_pt), "source": wb_src, "warning": warn},
           "measure_before": before, "grade": g, "measure_after": after, "checks": checks, "v7_for_comparison": old,
           "lock_v2_summary": lock["summary"] if lock else None, "lock_v2_verdict": lock["verdict"] if lock else None,
           "product_boxes_clay": VF.product_boxes(frame, fid), "product_box_rule": "each product inside its clay box +-15 % of the box size; read visually"}
    json.dump(res, open(base + "-measurements" + suffix + ".json", "w"), indent=1, ensure_ascii=False)
    e = g["exposure"]
    print(f"== {fid:18s} wb/exp point {wb_src[:40]:40s} need {e['needed_stops']:+.3f} -> {e['applied_stops']:+.2f} {e['flag'][:14]} | "
          f"window p99 {old.get('measure_after_v1_window', ['', '', ''])[1] if old else '-'} -> {win_after[1]} max {win_after[2]} | frame max {after['frame L p99 / max'][1]} | "
          f"black {after['darkest 0.5% patch L [12-15]']} | 255 {after['pixels with a 255 channel: inside / outside that area']}")
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("id")
    ap.add_argument("--render")
    ap.add_argument("--suffix", default="-v2")
    ap.add_argument("--grade-order", default="v2", choices=["v1", "v2"])
    ap.add_argument("--wb-point", default="auto", choices=["auto", "legacy"])
    ap.add_argument("--lock", default="v2", choices=["v1", "v2", "none"])
    ap.add_argument("--exposure", default="cap", choices=["cap", "bible"])
    ap.add_argument("--grade", default="v3", choices=["v3", "v4", "v5"])
    ap.add_argument("--stops", type=float, default=None)
    ap.add_argument("--target", type=float, default=None)
    ap.add_argument("--out-dir")
    ap.add_argument("--label")
    a = ap.parse_args()
    process(a.id, a.render, a.suffix, a.grade_order, a.wb_point, a.lock, a.out_dir, a.label, a.exposure, a.stops, a.target, grade_mode=a.grade)
