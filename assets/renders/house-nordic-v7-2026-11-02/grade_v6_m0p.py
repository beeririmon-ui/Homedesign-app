#!/usr/bin/env python3
"""
grade_v6_m0p.py: grading v6 (grade_v6_m0.py, the designer's review section 4) on M0p 1.2 from the seedream route
(pose-m0p-1-2-shell-seedream-fix.png: m0p_seedream.py, the paid 2026-11-05 job fetched 2026-11-06). render-agent, 2026-11-06, 0 tokens.
The same chain and the same targets as M0 (the same wall points in the room, projected with the M0p camera: one light for the P0 pan);
the M0p clay index (m0_clay_passes.py, CLAY_FRAME=M0p); the right wall (in frame here only) takes the back wall's right-end exposure so
the back-right corner stays continuous; no window in this frame (the glass steps are skipped).
New files: v9/pose-m0p-1-2-shell-seedream-graded-fix-v6.png, -frame-fix-v6.png, -graded-os6-fix-v6.png, -measurements-fix-v6.json,
-masks-fix-v6.jpg, and the sheet assets/renders/house-nordic-m0p-grade-v6-sheet-2026-11-06.jpg (M0p v5 | M0p v6 | M0 v6).
  python3 grade_v6_m0p.py masks | grade
"""
import json
import os
import sys
import time

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import art_m0_12 as A  # noqa: E402
import grade_v6_m0 as G  # noqa: E402

REPO, OD, OD_REL = G.REPO, G.OD, G.OD_REL
DATE = "2026-11-06"
JID = "pose-m0p-1-2-shell-seedream"
G.JID = JID
G.SRC = os.path.join(OD, JID + "-fix.png")
G.V5 = os.path.join(OD, JID + "-graded-fix-v5.png")
G.INDEX = os.path.join(OD, "m0p-clay-r5b-index.png")
G.CAM = A.CAMS["pose-m0p-v8b"]
G.SP = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/v6-m0p/"
SHEET = os.path.join(REPO, "assets/renders/house-nordic-m0p-grade-v6-sheet-2026-11-06.jpg")
M0_V6 = os.path.join(OD, "m0-1-2-shell-seedream-frame-fix-v6.png")
G.WB_UV = (0.1221, 0.4036)                                    # the Bible corner point (-1.75, 0, 1.60) in M0p
G.LOCAL_BOXES = [("sofa, cushions, throw", (0.15, 0.60, 0.52, 0.90), 40), ("pendant and cord", (0.26, 0.42, 0.0, 0.26), 40)]
G.TEXTURE_BOXES = [("throw drape", (0.48, 0.60, 0.60, 0.86), 2.5, [1, 41])]
G.CUBE_BOXES = [(0.215, 0.262, 0.325, 0.400), (0.505, 0.555, 0.325, 0.400)]
G.HEM_POLY = [(0, 0), (1, 0), (1, 1)]                          # no curtain hem in this frame (a 1 px no-op on the ceiling)
G.LEFT_STRIP = (0.0, 0.0)


def art_round_masks(H, W):
    """as grade_v6_m0.art_round_masks, but the round where it is rendered (M0p kept the seedream round: 0.98 of the 38 cm circle, 4 / 10 px off
    its projected centre, so the projected circle would leave a crescent of it on the wall's exposure)"""
    n = json.load(open(os.path.join(OD, JID + "-fix.json")))
    art = np.zeros((H, W), np.uint8)
    for q in n["placement"]["targets_px"]:
        cv2.fillConvexPoly(art, np.round(np.array(q) * 4).astype(np.int32), 1, lineType=cv2.LINE_8, shift=2)
    b = json.load(open(os.path.join(OD, JID + "-fix-base.json")))["wall_round"]["rendered"]
    rnd = np.zeros((H, W), np.uint8)
    (cx, cy), (ax, ay) = b["centre_px"], b["axes_px"]
    cv2.ellipse(rnd, ((cx, cy), (ax + 8, ay + 8), 0), 1, -1)
    return art.astype(bool), rnd.astype(bool)


G.art_round_masks = art_round_masks
# the wall points: the same room points as M0 (house plan 1.2.3 projection with the M0p camera), canvas uv
WALL_PTS = [("back wall by the corner (-1.75, 0, 1.60) [90-94]", (0.1221, 0.4036), (90, 94), "corner"),
            ("back wall behind the picture (0.20, 0, 1.95) [88-91]", (0.3863, 0.3193), (88, 91), "centre"),
            ("centre above the triptych (-0.13, 0, 2.03) [88-91] (QA's M0 point)", (0.3416, 0.30), (88, 91), "centre"),
            ("centre between triptych and sofa (-0.13, 0, 0.99) [88-91] (QA's M0 point)", (0.3416, 0.5506), (88, 91), "centre"),
            ("back wall right end (1.85, 0, 1.60) [82-86]", (0.6099, 0.4036), (82, 86), "right"),
            ("right edge (1.93, 0, 1.84) [82-86] (QA's M0 point)", (0.6208, 0.3458), (82, 86), "right"),
            ("right wall (2.50, 1.50, 1.60) [no Bible number]", (0.806, 0.358), None, "rightwall"),
            ("ceiling (0.40, 0.03) [no Bible number]", (0.40, 0.03), None, "ceiling")]
BOX = {"charcoal cushion": (0.415, 0.495, 0.645, 0.690), "sage cushion": (0.290, 0.345, 0.620, 0.690), "sage runner": (0.240, 0.290, 0.790, 0.830),
       "table top oak": (0.325, 0.370, 0.790, 0.830), "floor left": (0.0, 0.06, 0.795, 0.835), "floor right": (0.58, 0.70, 0.795, 0.835),
       "rug left": (0.02, 0.10, 0.86, 0.90), "rug right": (0.58, 0.68, 0.86, 0.90)}


def measure(img, Mk, label):
    H, W = img.shape[:2]
    L = G.Lmap(img)
    lab = cv2.cvtColor(img.astype(np.float32), cv2.COLOR_RGB2LAB)
    Ls, C = lab[..., 0], np.hypot(lab[..., 1], lab[..., 2])
    S = cv2.cvtColor(img.astype(np.float32), cv2.COLOR_RGB2HLS)[..., 2] * 100
    I = Mk["I"]
    r = dict(label=label, walls={}, fall_off={}, floor_rug={}, frame={}, shadows={}, products={}, triptych={}, lamps={})
    vals = {}
    for nm, (u, v), rng, grp in WALL_PTS:
        h_, s_, l_ = G.hsl(G.patch(img, u, v))
        r["walls"][nm] = dict(L=l_, H=h_, S=s_, range=list(rng) if rng else None, ok=(bool(rng[0] <= l_ <= rng[1]) if rng else None))
        vals.setdefault(grp, []).append(l_)
    c_, m_, rt = vals["corner"][0], float(np.mean(vals["centre"])), float(np.mean(vals["right"]))
    r["fall_off"] = dict(corner=c_, centre_mean=round(m_, 1), right_mean=round(rt, 1), corner_minus_centre=round(c_ - m_, 1),
                         centre_minus_right=round(m_ - rt, 1), ok=bool(c_ - m_ >= 1 and m_ - rt >= 3))
    fl = (I == 8) & (Mk["shell"] > 0.9)
    rug = (I == 521) & (Mk["shell"] < 0.1)
    for side in ("left", "right"):
        f = G.boxm(H, W, BOX["floor " + side]) & fl
        g = G.boxm(H, W, BOX["rug " + side]) & rug
        r["floor_rug"][f"floor {side}: median L / S"] = [round(float(np.median(L[f])), 1), round(float(np.median(S[f])), 1)]
        r["floor_rug"][f"rug {side}: median L"] = round(float(np.median(L[g])), 1)
        r["floor_rug"][f"rug minus floor, {side} [6-10]"] = round(float(np.median(L[g]) - np.median(L[f])), 1)
    r["floor_rug"]["all visible oak planks: median L / S"] = [round(float(np.median(L[fl])), 1), round(float(np.median(S[fl])), 1)]
    walls = np.isin(Mk["shell_kind"], ["back_wall", "right_wall"]) & (Mk["shell"] > 0.95)
    nowash = np.ones((H, W), bool)
    for z in G.wash_zones(Mk, H, W):
        nowash &= ~cv2.dilate((z["up"] | z["down"] | z["face"]).astype(np.uint8), np.ones((41, 41), np.uint8)).astype(bool)
    r["frame"] = dict(mean_L=round(float(L.mean()), 1), share_Lstar_over_90=round(float((Ls > 90).mean()), 3), mean_Cstar=round(float(C.mean()), 2),
                      max_L=round(float(L.max()), 1), px_255=int((img.max(2) >= 254.5 / 255).sum()), walls_p99_5=round(float(np.percentile(L[walls & nowash], 99.5)), 1))
    kk = 32
    mu = cv2.blur(Ls, (kk, kk))
    sd = np.sqrt(np.maximum(cv2.blur(Ls * Ls, (kk, kk)) - mu * mu, 0))
    r["frame"]["local_contrast_median"] = round(float(np.median(sd)), 2)
    from numpy.lib.stride_tricks import sliding_window_view
    k = max(4, int(0.005 * W))
    pm = sliding_window_view(L, (k, k))[::4, ::4].mean((2, 3))
    iy, ix = np.unravel_index(int(np.argmin(pm)), pm.shape)
    sofa = (I == 1).astype(np.uint8)
    below = cv2.dilate(sofa, np.ones((31, 1), np.uint8), anchor=(0, 0)).astype(bool) & ~sofa.astype(bool) & ~(I == 2) & G.boxm(H, W, (0.19, 0.56, 0.70, 0.90))
    Lm = cv2.medianBlur((L * 2.55).astype(np.uint8), 3).astype(np.float32) / 2.55
    r["shadows"] = {"under the sofa (30 px band under the clay sofa, not the table): p1 [18-22]": round(float(np.percentile(Lm[below], 1)), 1),
                    "darkest 0.5 % patch [12-15]": round(float(pm.min()), 1), "darkest patch at (u, v)": [round((ix * 4 + k / 2) / W, 3), round((iy * 4 + k / 2) / H, 3)]}
    for nm in ("charcoal cushion", "sage cushion", "sage runner", "table top oak"):
        m = G.boxm(H, W, BOX[nm])
        h_, s_, l_ = G.hsl(img[m].mean(0))
        r["products"][nm] = dict(H=h_, S=s_, L=l_)
    ar = G.art_regions(H, W)
    for i in range(3):
        d = {kx: round(float(np.median(L[ar[kx][i]])), 1) for kx in ("board", "passe-partout", "oak frame", "wall above")}
        mk = ar["marks"][i] & (L < 50)
        d["marks"] = round(float(np.median(L[mk])), 1) if mk.sum() > 20 else None
        d["wall minus oak frame"] = round(d["wall above"] - d["oak frame"], 1)
        r["triptych"][f"print {i + 1}"] = d
    for i, z in enumerate(G.wash_zones(Mk, H, W)):
        slot = np.percentile(L[z["face"]], 97)
        wash = max(np.percentile(L[z["up"]], 90), np.percentile(L[z["down"]], 90))
        beside = np.median(L[z["beside"] & walls])
        r["lamps"][["left cube", "right cube"][i]] = dict(glowing_slot_p97_L=round(float(slot), 1), wash_p90_L=round(float(wash), 1), wall_beside_L=round(float(beside), 1),
                                                          wash_minus_wall=round(float(wash - beside), 1))
    return r


P0 = dict(G.P0, right_wall=0.45, window_wall=0.67, glass=0.0)
# the P0 pan (M0 <-> M0p) shares the floor right of the sofa and the rug: M0p's floor is set on M0 v6's graded floor in that strip (no lit floor by
# the window is in this frame, the M0 floor check has no place here) and the rug keeps M0's exposure; the right wall (in frame only here) has no
# Bible number: 90 at its middle (under the corner's 91, over the back wall's right end 84; it faces the window) keeps it under the 94 ceiling
M0_MEAS = json.load(open(os.path.join(OD, "m0-1-2-shell-seedream-measurements-fix-v6.json")))
M0_FLOOR_RIGHT = M0_MEAS["measured"]["v6"]["floor_rug"]["floor right strip [L 68-78, S 30-45]: median L / S"][0]
M0_P = M0_MEAS["solve"]["params"]
RIGHT_WALL_TARGET = 90.0


def solve(a, Mk, X, prof, iters=6):
    P = json.loads(json.dumps(P0))
    hist = []
    for it in range(iters):
        g, _ = G.grade(a, Mk, P, X, prof)
        m = measure(g, Mk, "iter")
        wv = m["walls"]
        cen = np.mean([v["L"] for k, v in wv.items() if "88-91" in k])
        rgt = np.mean([v["L"] for k, v in wv.items() if "82-86" in k])
        cor = wv[WALL_PTS[0][0]]["L"]
        fl, fS = m["floor_rug"]["floor left: median L / S"]
        rw = m["floor_rug"]["rug left: median L"]
        tb = m["products"]["table top oak"]["L"]
        wmw = min(v["wash_minus_wall"] for v in m["lamps"].values())
        hist.append(dict(it=it, floor_right=m["floor_rug"]["floor right: median L / S"][0], right_wall=m["walls"][WALL_PTS[6][0]]["L"], corner=cor, centre=round(float(cen), 1), right=round(float(rgt), 1), floor=fl, floor_S=fS, rug=rw, table=tb, wash_min=wmw,
                         mean=m["frame"]["mean_L"], walls_max=m["frame"]["walls_p99_5"]))
        print(hist[-1], flush=True)
        P["wall_ctrl"] = [G.step(cor, G.TGT["corner"], P["wall_ctrl"][0]), G.step(cen, G.TGT["centre"], P["wall_ctrl"][1]), G.step(rgt, G.TGT["right"], P["wall_ctrl"][2])]
        P["right_wall"] = G.step(m["walls"][WALL_PTS[6][0]]["L"], RIGHT_WALL_TARGET, P["right_wall"])
        flr = m["floor_rug"]["floor right: median L / S"][0]
        P["floor"] = G.step(flr, M0_FLOOR_RIGHT, P["floor"])
        P["floor_chroma"] = M0_P["floor_chroma"]
        P["rug"] = M0_P["rug"]
        P["table"] = float(np.clip(G.step(tb, G.TGT["table"], P["table"]), -0.6, 0.2))
        if wmw < 6.0:
            P["glow"] = float(min(P["glow"] + 0.25, 1.0))
    return P, hist


def rows_of(mb, m5, m6):
    rows = []
    for nm, _, rng, _ in WALL_PTS:
        rows.append((nm.split(" [")[0], f"{rng[0]}-{rng[1]}" if rng else "-", mb["walls"][nm]["L"], m5["walls"][nm]["L"], m6["walls"][nm]["L"], m6["walls"][nm]["ok"]))
    for k, t, f in (("corner_minus_centre", ">= 1", lambda x: x >= 1), ("centre_minus_right", ">= 3", lambda x: x >= 3)):
        rows.append(("fall-off: " + k.replace("_", " "), t, mb["fall_off"][k], m5["fall_off"][k], m6["fall_off"][k], f(m6["fall_off"][k])))
    k = "floor right: median L / S"
    rows.append(("oak floor right of the sofa (= M0's strip), L", f"M0 {M0_FLOOR_RIGHT}", mb["floor_rug"][k][0], m5["floor_rug"][k][0], m6["floor_rug"][k][0],
                 abs(m6["floor_rug"][k][0] - M0_FLOOR_RIGHT) <= 2))
    for side in ("left", "right"):
        k = f"floor {side}: median L / S"
        rows.append((f"oak floor {side}, L / S", "-", f"{mb['floor_rug'][k][0]} / {mb['floor_rug'][k][1]}", f"{m5['floor_rug'][k][0]} / {m5['floor_rug'][k][1]}",
                     f"{m6['floor_rug'][k][0]} / {m6['floor_rug'][k][1]}", None))
        k2 = f"rug {side}: median L"
        rows.append((f"rug {side}, L (M0's rug exposure)", "-", mb["floor_rug"][k2], m5["floor_rug"][k2], m6["floor_rug"][k2], None))
    rows.append(("frame mean L (M0's 76-80; this frame is ~60 % wall)", "-", mb["frame"]["mean_L"], m5["frame"]["mean_L"], m6["frame"]["mean_L"], None))
    rows.append(("walls p99.5 (outside the washes)", "<= 94", mb["frame"]["walls_p99_5"], m5["frame"]["walls_p99_5"], m6["frame"]["walls_p99_5"], m6["frame"]["walls_p99_5"] <= 94))
    rows.append(("share over L* 90", "-", mb["frame"]["share_Lstar_over_90"], m5["frame"]["share_Lstar_over_90"], m6["frame"]["share_Lstar_over_90"], None))
    k = "under the sofa (30 px band under the clay sofa, not the table): p1 [18-22]"
    rows.append(("contact shadow under the sofa, p1", "18-22", mb["shadows"][k], m5["shadows"][k], m6["shadows"][k], 18 <= m6["shadows"][k] <= 22))
    k = "darkest 0.5 % patch [12-15]"
    rows.append(("darkest 0.5 % patch", "12-15", mb["shadows"][k], m5["shadows"][k], m6["shadows"][k], 12 <= m6["shadows"][k] <= 15))
    for nm, key, rng in (("charcoal cushion", "L", (25, 32)), ("sage cushion", "S", (8, 22)), ("sage runner", "S", (8, 22)), ("table top oak", "L", (60, 72))):
        rows.append((f"{nm}, {key}", f"{rng[0]}-{rng[1]}", mb["products"][nm][key], m5["products"][nm][key], m6["products"][nm][key], rng[0] <= m6["products"][nm][key] <= rng[1]))
    for i in (1, 2, 3):
        p_ = f"print {i}"
        for k, t, f in (("board", "80-86", lambda x: 80 <= x <= 86), ("passe-partout", "92-95", lambda x: 92 <= x <= 95), ("marks", "<= 28", lambda x: x is not None and x <= 28),
                        ("oak frame", "62-72", lambda x: 62 <= x <= 72)):
            rows.append((f"triptych {p_}: {k}", t, mb["triptych"][p_][k], m5["triptych"][p_][k], m6["triptych"][p_][k], f(m6["triptych"][p_][k])))
    for c in ("left cube", "right cube"):
        rows.append((f"{c}: glowing slot L", "93-97", mb["lamps"][c]["glowing_slot_p97_L"], m5["lamps"][c]["glowing_slot_p97_L"], m6["lamps"][c]["glowing_slot_p97_L"],
                     93 <= m6["lamps"][c]["glowing_slot_p97_L"] <= 97))
        rows.append((f"{c}: wash minus wall", ">= 6", mb["lamps"][c]["wash_minus_wall"], m5["lamps"][c]["wash_minus_wall"], m6["lamps"][c]["wash_minus_wall"],
                     m6["lamps"][c]["wash_minus_wall"] >= 6))
    rows.append(("max L / px at 255", "<= 97 / 0", f"{mb['frame']['max_L']} / {mb['frame']['px_255']}", f"{m5['frame']['max_L']} / {m5['frame']['px_255']}",
                 f"{m6['frame']['max_L']} / {m6['frame']['px_255']}", m6["frame"]["max_L"] <= 97.05 and m6["frame"]["px_255"] == 0))
    return rows


def sheet(g5, g6, rows):
    f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 19)
    fb = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)
    fs = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 17)
    w = 1280

    def fr(img):
        H, W = img.shape[:2]
        x0, y0, x1, y1 = int(round(116 / 4072 * W)), int(round(65 / 2290 * H)), int(round(3956 / 4072 * W)), int(round(2225 / 2290 * H))
        return Image.fromarray((img[y0:y1, x0:x1] * 255 + 0.5).astype(np.uint8)).resize((w, 720), Image.LANCZOS)
    rh = 25
    out = Image.new("RGB", (2 * w + 30, 60 + 760 + max(780, 60 + rh * (len(rows) + 1)) + 20), (255, 255, 255))
    d = ImageDraw.Draw(out)
    d.text((10, 14), f"M0p 1.2 (seedream, paid 2026-11-05, composite -fix): grading v5 -> v6 ({DATE}, the M0 chain and targets). Not QA'd.", fill=(0, 0, 0), font=fb)
    out.paste(fr(g5), (10, 60))
    out.paste(fr(g6), (w + 20, 60))
    d.text((14, 784), "M0p v5", fill=(0, 0, 0), font=f)
    d.text((w + 24, 784), "M0p v6", fill=(0, 0, 0), font=f)
    y0 = 820
    m0 = Image.open(M0_V6).convert("RGB").resize((w, 720), Image.LANCZOS)
    out.paste(m0, (10, y0))
    d.text((14, y0 + 724), "M0 v6 (the other end of the P0 pan), for the light of the pair", fill=(0, 0, 0), font=f)
    x = w + 20
    cols = [x, x + 560, x + 680, x + 820, x + 930, x + 1040]
    for c, t in zip(cols, ["target point", "target", "before", "v5", "v6", "v6 ok"]):
        d.text((c, y0), t, fill=(0, 0, 0), font=fb)
    for i, r in enumerate(rows):
        yy = y0 + 32 + i * rh
        if i % 2 == 0:
            d.rectangle([x - 4, yy - 2, x + 1270, yy + rh - 4], fill=(244, 244, 244))
        col = (0, 120, 0) if r[5] is True else ((190, 0, 0) if r[5] is False else (90, 90, 90))
        for c, t in zip(cols, [r[0][:58], str(r[1]), str(r[2]), str(r[3]), str(r[4]), "yes" if r[5] is True else ("NO" if r[5] is False else "-")]):
            d.text((c, yy), t, fill=col if c in (cols[4], cols[5]) else (0, 0, 0), font=fs)
    out.save(SHEET, quality=88)


def run():
    t0 = time.time()
    a = G.load(G.SRC)
    H, W = a.shape[:2]
    Mk, mrec = G.load_masks()
    X, Z = G.wall_xz(H, W)
    xc, f, prec = G.wall_profile(G.s2l(a), Mk, X, Z)
    P, hist = solve(a, Mk, X, (xc, f))
    g, rec = G.grade(a, Mk, P, X, (xc, f))
    E, _ = G.exposure_map(P, Mk, X, (xc, f))
    base = os.path.join(OD, JID)
    gim = Image.fromarray((g * 255 + 0.5).astype(np.uint8))
    gim.save(base + "-graded-fix-v6.png")
    x0, y0, x1, y1 = int(round(116 / 4072 * W)), int(round(65 / 2290 * H)), int(round(3956 / 4072 * W)), int(round(2225 / 2290 * H))
    gim.crop((x0, y0, x1, y1)).save(base + "-frame-fix-v6.png")
    gim.crop((x0, 0, x1, H)).save(base + "-graded-os6-fix-v6.png")
    g8 = np.asarray(Image.open(base + "-graded-fix-v6.png")).astype(np.float32) / 255
    g5 = G.load(G.V5)
    mb, m5, m6 = measure(a, Mk, "composite"), measure(g5, Mk, "v5"), measure(g8, Mk, "v6")
    rows = rows_of(mb, m5, m6)
    G.mask_sheet(a, Mk, E, base + "-masks-fix-v6.jpg")
    sheet(g5, g8, rows)
    note = dict(asset_id=JID + "-graded-fix-v6", date=DATE, tokens=0, script="assets/renders/house-nordic-v7-2026-11-02/grade_v6_m0p.py",
                input=OD_REL + JID + "-fix.png", chain="grade_v6_m0.py (the M0 v6 chain), the M0 targets at the same room points; test page (V7Q4), not B3",
                masks=mrec, wall_profile=prec, solve=dict(params=P, targets=G.TGT, iterations=hist), grade=rec, measured=dict(composite=mb, v5=m5, v6=m6),
                table=[dict(point=r[0], target=r[1], composite=r[2], v5=r[3], v6=r[4], ok=r[5]) for r in rows], not_met=[r[0] for r in rows if r[5] is False],
                outputs=dict(graded=OD_REL + JID + "-graded-fix-v6.png", frame=OD_REL + JID + "-frame-fix-v6.png", os6=OD_REL + JID + "-graded-os6-fix-v6.png",
                             masks=OD_REL + JID + "-masks-fix-v6.jpg", sheet=os.path.relpath(SHEET, REPO), clay_index=OD_REL + "m0p-clay-r5b-index.png"),
                runtime_s=round(time.time() - t0))

    def clean(o):
        if isinstance(o, dict):
            return {str(k): clean(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)):
            return [clean(v) for v in o]
        if isinstance(o, np.floating):
            return float(o)
        if isinstance(o, np.integer):
            return int(o)
        if isinstance(o, np.bool_):
            return bool(o)
        return o
    json.dump(clean(note), open(base + "-measurements-fix-v6.json", "w"), indent=1, ensure_ascii=False)
    for r in rows:
        print(f"{r[0][:60]:60s} {str(r[1]):10s} {str(r[2]):>12s} {str(r[3]):>12s} {str(r[4]):>12s}  {r[5]}")
    print("params", json.dumps(clean(P)))


if __name__ == "__main__":
    os.makedirs(G.SP, exist_ok=True)
    w = sys.argv[1]
    if w in ("masks", "all"):
        M_, rec = G.masks(G.load(G.SRC))
        print(json.dumps(rec)[:1500])
    if w in ("grade", "all"):
        run()
