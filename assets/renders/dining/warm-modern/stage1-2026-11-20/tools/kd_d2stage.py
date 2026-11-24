#!/usr/bin/env python3
"""
kd_d2stage.py: 10.9 "D2 takes the stage" in code (render-agent, 2026-11-24; 0 tokens beyond the three edits).
Spec: docs/proposals/wm-kitchen-dining-render-2026-11-19.md 10.9, with the manager's rulings of 2026-11-24.
  migrate      once: the stage-one D2 (yaw -91) becomes "D2o": plate-D2* -> plate-D2o*, the layers cut there -> layers|shadows|light/D2o,
               the projected copies dropped (re-made by compose_edits.py project); plate-D1.png -> plate-D1-ungraded.png (the cut base
               of the D1 passes; plate-D1.png becomes the graded plate, KD-L4)
  plate        [KD-15] the D2 plate at yaw -86: every pixel is a ray from PD; it is read from plate-D2o where D2o's canvas sees it and
               from plate-D1-ungraded where only D1 does (the left 5 deg), with a 2 deg cross-fade inside D2o's canvas edge
               -> plate-D2-composed.png (scratchpad: an intermediate, re-made in 7 s; inputs/N-niche-base.png is the same image)
  niche-prep   [KD-16] the niche edit: the composed plate with the new clay's niche (ids 42 / 39 inside the niche box) as the placeholder,
               cropped 4:3 round the niche -> inputs/N-niche-input.png, inputs/N-niche-crop.png
  niche-apply  the niche of the edit (kd_crop.py assemble N-niche) inside the clay's niche, feathered 2 px, into the composed plate
               -> plate-D2-niche.png (scratchpad: an intermediate)
  grade        KD-L4: the oak floor in world space (one field for D1 and D2: the same patch reads the same in both frames), and the plaster
               (walls and ceiling) C* +2.5 toward h 85 -> plate-D1.png (from plate-D1-ungraded.png), plate-D2.png (from plate-D2-niche.png)
  jar          the moon jar moved to Y 1.735 (10.9.2 row 3): the D2o layer warped to D2, then moved on the shelf -> a D2 layer
  base <pass> <ids...> x0 y0 x1 y1
               an edit's input: the D2 frame as it is now (the plate and every live layer, the lights) without the products this pass
               replaces, and with the new clay's placeholders for <ids> -> inputs/<pass>-base.png, inputs/<pass>-input.png, the crop
"""
import json
import os
import shutil
import sys

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kd_common as K  # noqa: E402
import compose_edits as CE  # noqa: E402

C = K.C
ST = K.ST
H, W = K.H, K.W
REC = os.path.join(ST, "d2stage.json")


def rec_load():
    return json.load(open(REC)) if os.path.exists(REC) else {}


def rec_save(r):
    json.dump(r, open(REC, "w"), indent=1, default=str)


def migrate():
    r = rec_load()
    if r.get("migrated"):
        print("already migrated")
        return
    for a, b in (("plate-D2.png", "plate-D2o.png"), ("plate-D2-frame.png", "plate-D2o-frame.png"), ("plate-D2-compose.json", "plate-D2o-compose.json")):
        if os.path.exists(os.path.join(ST, a)):
            os.replace(os.path.join(ST, a), os.path.join(ST, b))
    shutil.copy(os.path.join(ST, "plate-D1.png"), os.path.join(ST, "plate-D1-ungraded.png"))
    man = json.load(open(os.path.join(ST, "manifest.json")))
    keep = []
    for l in man["layers"]:
        if l.get("projected_from"):
            continue
        if l["frame"] == "D2":
            for key in ("layer", "shadow"):
                old = os.path.join(ST, l[key])
                new = old.replace(f"{os.sep}D2{os.sep}", f"{os.sep}D2o{os.sep}")
                os.makedirs(os.path.dirname(new), exist_ok=True)
                os.replace(old, new)
                l[key] = os.path.relpath(new, ST)
            l["frame"] = "D2o"
        keep.append(l)
    man["layers"] = keep
    lights = []
    for li in man["light"]:
        if li.get("projected_from"):
            p = os.path.join(ST, li["file"])
            if os.path.exists(p):
                os.remove(p)
            continue
        if li["frame"] == "D2":
            old = os.path.join(ST, li["file"])
            new = old.replace(f"{os.sep}D2{os.sep}", f"{os.sep}D2o{os.sep}")
            os.makedirs(os.path.dirname(new), exist_ok=True)
            os.replace(old, new)
            li["file"] = os.path.relpath(new, ST)
            li["frame"] = "D2o"
        lights.append(li)
    man["light"] = lights
    for d in ("layers/D2", "shadows/D2", "light/D2"):
        p = os.path.join(ST, d)
        if os.path.isdir(p):
            shutil.rmtree(p)
    man["bases"] = {"D1": "plate-D1.png", "D2": "plate-D2.png"}
    man["cameras"]["D2"] = dict(man["cameras"]["D2"], yaw=-86.0)
    man["cameras"]["D2o"] = dict(man["cameras"]["D2"], yaw=-91.0, role="stage one's D2: the source the D2 plate and its layers are composed from")
    json.dump(man, open(os.path.join(ST, "manifest.json"), "w"), indent=1)
    J = json.load(open(os.path.join(ST, "passes.json")))
    for p, v in J.items():
        if v.get("base") == "plate-D2.png":
            v["base"] = "plate-D2o.png"
        if v.get("base") == "plate-D1.png":
            v["base"] = "plate-D1-ungraded.png"
    json.dump(J, open(os.path.join(ST, "passes.json"), "w"), indent=1)
    r["migrated"] = dict(date="2026-11-24", rule="stage one's D2 is D2o (yaw -91); its cut layers and plate are the sources of the new D2 (yaw -86)")
    rec_save(r)
    print("migrated")


GROUPS = {"floor": (10, 11), "plaster": (1, 2, 3, 4, 5, 9, 12, 16), "ceiling": (6, 7, 8), "table": (20, 21), "chairs": (22, 23),
          "bench": (24,), "lower units": (30, 31), "worktop / splash": (32, 33, 38, 39), "hood": (37,), "window": (13, 14, 15)}


def aniso_nconv(v, w, sx, sy):
    k = lambda a: cv2.GaussianBlur(a.astype(np.float32), (0, 0), sigmaX=sx, sigmaY=sy).astype(np.float64)
    return k(v * w), k(w)


def lowres_nconv(v, w, sg, f=4):
    """a normalised convolution at 1/f resolution (the fields are smooth): blur(v w) and blur(w), back at full size"""
    hs, ws = H // f, W // f
    vw = cv2.resize((v * w).astype(np.float32), (ws, hs), interpolation=cv2.INTER_AREA)
    ww = cv2.resize(w.astype(np.float32), (ws, hs), interpolation=cv2.INTER_AREA)
    vw = cv2.GaussianBlur(vw, (0, 0), sg / f)
    ww = cv2.GaussianBlur(ww, (0, 0), sg / f)
    up = lambda x: cv2.resize(x, (W, H), interpolation=cv2.INTER_LINEAR).astype(np.float64)
    return up(vw), up(ww)


def plate():
    """[KD-15]: a ray of D2 is read from plate-D2o where D2o's canvas has it; on the left (D2o's canvas ends 5 deg in) from
    plate-D1-ungraded, matched to D2o per material by the ratio of the two on the overlap next to the seam (linear light,
    anisotropic: along the rows), with a 2 deg cross-fade along D2o's left canvas edge only"""
    pO = C.load(os.path.join(ST, "plate-D2o.png"))
    p1 = C.load(os.path.join(ST, "plate-D1-ungraded.png"))
    mxO, myO, okO = K.map_between("D2o", "D2")
    mx1, my1, ok1 = K.map_between("D1", "D2")
    rem = lambda img, mx, my: cv2.remap(C.lin(img).astype(np.float32), mx, my, cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REPLICATE).astype(np.float64)
    wO = np.clip(rem(pO, mxO, myO), 0, 1)
    w1 = np.clip(rem(p1, mx1, my1), 0, 1)
    feather = 2.0 * K.F_ * np.pi / 180                      # 2 deg in pixels at the centre
    # only D2o's 16:9 frame is used (its canvas margin is not graded content): 0 at D2o's frame edge, 1 two degrees in (left), and
    # 20 px in from its top and bottom edge (the pan moves D2's bottom-left rows below D2o's frame by up to 55 px)
    fx0, fy0, fx1, fy1 = K.FRAME
    a_h = np.clip((mxO - (fx0 + 1.0)) / feather, 0, 1)
    a_v = np.clip((myO - (fy0 - 20.0)) / 20.0, 0, 1) * np.clip(((fy1 + 20.0) - myO) / 20.0, 0, 1)
    a = a_h * a_v
    ids2 = K.ids("D2-plate")
    fm = K.frame_mask()
    strip0 = (a < 1) & fm
    near = C.dil(strip0, 260)
    band = (a >= 1) & ok1 & fm & near                       # the overlap round the strip: both plates valid, D2o's alone used
    strip = a < 1
    gain = np.ones((H, W, 3))
    grec = {}
    for name, g in GROUPS.items():
        mg = np.isin(ids2, g)
        wb = (band & C.ero(mg, 2)).astype(np.float64)
        if wb.sum() < 300 or not (strip & mg).any():
            continue
        r_ = np.full((H, W, 3), np.nan)
        for sg in (200.0, 45.0):                            # a wide field, then the near one where it has support
            for c in range(3):
                nO, d_ = lowres_nconv(wO[..., c], wb, sg)
                n1, _ = lowres_nconv(w1[..., c], wb, sg)
                r_[..., c] = np.where(d_ > 0.02, nO / np.maximum(n1, 1e-5), r_[..., c])
        med = np.nanmedian(r_[band & mg], 0)
        r_ = np.where(np.isnan(r_), med[None, None, :], r_)
        r_ = np.clip(r_, 0.6, 1.6)
        gain[mg] = r_[mg]
        grec[name] = [round(float(v), 3) for v in med]
    rest = ~np.isin(ids2, sum(GROUPS.values(), ()))
    wb = (band & C.ero(rest, 2)).astype(np.float64)
    if wb.sum() > 300:
        med = np.median(wO[band & rest] / np.maximum(w1[band & rest], 1e-4), 0)
        gain[rest] = np.clip(med, 0.6, 1.6)
        grec["other"] = [round(float(v), 3) for v in med]
    g_s = np.stack([C.blur(gain[..., c], 1.0) for c in range(3)], -1)
    w1m = np.clip(w1 * g_s, 0, 1)
    out = C.srgb(np.clip(wO * a[..., None] + w1m * (1 - a[..., None]), 0, 1))
    K.save(os.path.join(K.SCR, "plate-D2-composed.png"), out)
    seam = (a > 0) & (a < 1) & fm
    xs = np.nonzero(seam.any(0))[0]
    lO, l1, l1m = C.to_lab(C.srgb(wO)), C.to_lab(C.srgb(w1)), C.to_lab(C.srgb(w1m))
    rows = {}
    for name, g in (("floor", (10, 11)), ("plaster", (1, 2, 3, 4, 5, 9, 16)), ("bench", (24,)), ("table", (20, 21)), ("all", None)):
        m = seam & (np.isin(ids2, g) if g else True) & ok1
        if m.sum() > 200:
            A_, B_, M_ = np.median(lO[m], 0), np.median(l1[m], 0), np.median(l1m[m], 0)
            rows[name] = dict(D2o=[round(float(v), 1) for v in A_], D1=[round(float(v), 1) for v in B_], D1_matched=[round(float(v), 1) for v in M_],
                              dE00_before=round(float(C.de00(tuple(A_), tuple(B_))), 2), dE00=round(float(C.de00(tuple(A_), tuple(M_))), 2), px=int(m.sum()))
    r = rec_load()
    r["plate"] = dict(out="plate-D2-composed.png", feather_px=round(float(feather), 1), seam_x_px=[int(xs.min()), int(xs.max())] if xs.size else None,
                      from_D1_px=int((strip & fm).sum()), D1_gain_per_material=grec, outside_both_px=int((~okO & ~ok1 & fm).sum()), seam=rows,
                      rule="each pixel of D2 (-86) is a ray from PD: plate-D2o where D2o's canvas sees it, plate-D1-ungraded on the left 5 deg "
                           "(matched to D2o per material on the overlap next to the seam, linear light), a 2 deg cross-fade along D2o's left edge")
    rec_save(r)
    K.frame_crop(C.q(out)).save(os.path.join(K.SCR, "plate-D2-composed-frame.png"))
    # the D2 plate's record: its sources' steps, and the toe (step 3) the new cuts in D2 take: D2o's (most of the plate is D2o's)
    sO = json.load(open(os.path.join(ST, "plate-D2o-compose.json")))
    s1 = json.load(open(os.path.join(ST, "plate-D1-compose.json")))
    toe = [x for x in sO["steps"] if x.get("step") == 3][0]
    json.dump(dict(frame="D2", source="plate-D2o.png (stage one's D2, yaw -91) + plate-D1-ungraded.png, by the rotation about PD (tools/kd_d2stage.py)",
                   out="plate-D2.png",
                   steps=[dict(step="KD-15", what="D2 at yaw -86 composed from the two approved plates", **{k: v for k, v in r["plate"].items() if k != "out"}),
                          dict(step="KD-16", what="the niche: one crop edit (N-niche) inside the new clay's niche (tools/kd_d2stage.py niche-apply)"),
                          dict(step="KD-L4", what="the floor and the plaster graded (tools/kd_d2stage.py grade)"),
                          dict(toe, source="plate-D2o-compose.json step 3 (D1's: xp " + json.dumps([x for x in s1["steps"] if x.get("step") == 3][0]["xp"]) + ")")],
                   mandatory_for_derived=sO.get("mandatory_for_derived")),
              open(os.path.join(ST, "plate-D2-compose.json"), "w"), indent=1)
    print(json.dumps(r["plate"]))


def retire():
    """10.9: mark the retired layers in the manifest (kd_passes.RETIRED); only cut layers (a projection is re-made by project)"""
    from kd_passes import RETIRED
    man = CE.load_man()
    n = []
    for l in man["layers"]:
        if l.get("projected_from"):
            continue
        why = RETIRED.get((l["frame"], l["slot"])) or RETIRED.get((l["frame"], f"{l['slot']}/{l['product']}"))
        if why and (l["default"] or (l["frame"], f"{l['slot']}/{l['product']}") in RETIRED):
            l["retired"] = why
            n.append(f"{l['frame']} {l['slot']} {l['product']}")
    json.dump(man, open(os.path.join(ST, "manifest.json"), "w"), indent=1)
    print("retired", n)


NICHE_BOX = (1646, 66, 2286, 919)      # 3:4 round the new niche (clay id 42: x 1758-2174, y 228-755), with the oven's edge and the doors' grooves


def niche_mask():
    """the new niche's opening in the plate clay: the walnut lining and the LED profiles (ids 42, 39) inside the box, holes filled"""
    ids = K.ids("D2-plate")
    m = np.isin(ids, (42, 39)) & C.box_mask([(1740, 210, 2190, 770)])
    return CE.fill_holes(m, 20000)


def niche_prep():
    base = C.load(os.path.join(K.SCR, "plate-D2-composed.png"))
    clay = C.load(K.clay_file("D2-plate", ".png"))
    m = niche_mask()
    inp = base.copy()
    inp[m] = clay[m]
    K.save(os.path.join(ST, "inputs", "N-niche-base.png"), base)
    ip = os.path.join(ST, "inputs", "N-niche-input.png")
    K.save(ip, inp)
    x0, y0, x1, y1 = NICHE_BOX
    crop = Image.fromarray(C.q(inp)).crop((x0, y0, x1, y1))
    s = 2048 / max(crop.size)
    cp = os.path.join(ST, "inputs", "N-niche-crop.png")
    crop.resize((int(round(crop.size[0] * s)), int(round(crop.size[1] * s))), Image.LANCZOS).save(cp)
    # the old niche as the material reference (scratchpad: it is our own render, it could go in the repo, but it is only a reference)
    oldc = Image.open(os.path.join(ST, "plate-D2o.png")).convert("RGB").crop((1660, 390, 2060, 800))
    oldc.save(os.path.join(K.SCR, "N-niche-ref-old-niche.jpg"), quality=92)
    rec = dict(pass_="N-niche", frame="D2", base="inputs/N-niche-base.png", crop_box=list(NICHE_BOX), crop_aspect=round((x1 - x0) / (y1 - y0), 4),
               upscale=round(s, 4), placeholder_ids=[42, 39], placeholder_px=int(m.sum()), input="inputs/N-niche-input.png",
               crop="inputs/N-niche-crop.png", crop_sha256=K.sha(cp), reference="the stage-one niche (plate-D2o crop), scratchpad")
    json.dump(rec, open(os.path.join(ST, "inputs", "N-niche-prep.json"), "w"), indent=1)
    print(json.dumps(rec))


def niche_apply():
    J = json.load(open(os.path.join(ST, "passes.json")))["N-niche"]
    base = C.load(os.path.join(K.SCR, "plate-D2-composed.png"))
    e, rl = K.ecc_lock(J["raw"], os.path.join(ST, J["input"]), C.ero(np.isin(K.ids("D2-plate"), CE.ARCH), 3) & ~C.dil(niche_mask(), 60) & C.box_mask([NICHE_BOX]))
    m = C.dil(niche_mask(), 3)
    keep = C.box_mask([NICHE_BOX]) & ~C.dil(m, 40)
    g = C.gain_field(e, base, keep)
    e = C.srgb(np.clip(C.lin(e) * g, 0, 1))
    a = np.clip(C.blur(m.astype(np.float64), 1.2), 0, 1)
    a[~C.dil(m, 3)] = 0
    # the walnut as the stage-one niche's (10.9 QA 3): the edit drew it lighter and yellower (L* 51 h 60 under the LED against 32 h 54).
    # One linear gain per channel on the niche, from the lit back panel under the top LED in each (the old niche: rows 520-600; the
    # new one: both compartments' lit bands); the LED lines themselves (L* over 70) keep their light
    old = C.load(os.path.join(ST, "plate-D2o.png"))
    io, i2 = K.ids("D2o-plate"), K.ids("D2-plate")
    z_old = C.box_mask([(1760, 520, 1960, 600)]) & C.ero(io == 42, 3)
    z_new = C.box_mask([(1850, 320, 2080, 460), (1850, 560, 2080, 640)]) & C.ero(i2 == 42, 3)
    gw = np.median(C.lin(old)[z_old], 0) / np.median(C.lin(e)[z_new], 0)
    Le = C.to_lab(e)[..., 0]
    keep_led = np.clip((Le - 70.0) / 12.0, 0, 1)
    gm = gw[None, None, :] * (1 - keep_led[..., None]) + keep_led[..., None]
    e = C.srgb(np.clip(C.lin(e) * gm, 0, 1))
    le = C.to_lab(e)
    le[..., 0] = wmg1_toe(le[..., 0])                    # WM-G1: the darkened walnut's corners not under L* 11
    e = np.clip(C.from_lab(le), 0, 1)
    out = e * a[..., None] + base * (1 - a[..., None])
    K.save(os.path.join(K.SCR, "plate-D2-niche.png"), out)
    r = rec_load()
    lab = C.to_lab(out)
    wal_new = np.median(lab[z_new], 0)
    wal_old = np.median(C.to_lab(old)[z_old], 0)
    wal_new_all = np.median(lab[C.ero(i2 == 42, 3)], 0)
    wal_old_all = np.median(C.to_lab(old)[C.ero(io == 42, 3)], 0)
    r["niche"] = dict(lock=rl, mask_px=int(m.sum()), gain_p1_p50_p99=[round(float(v), 3) for v in np.percentile(g, [1, 50, 99])],
                      walnut_gain_rgb_linear=[round(float(v), 3) for v in gw],
                      walnut_lit_panel_new=[round(float(v), 1) for v in wal_new], walnut_lit_panel_old=[round(float(v), 1) for v in wal_old],
                      dE00_walnut=round(float(C.de00(tuple(wal_new), tuple(wal_old))), 2),
                      walnut_all_new=[round(float(v), 1) for v in wal_new_all], walnut_all_old=[round(float(v), 1) for v in wal_old_all],
                      rule="the edit's niche inside the new clay's niche (ids 42 / 39) + 3 px, feathered, its walnut matched to the stage-one niche "
                           "(the lit back panel under the top LED, one linear gain per channel, the LED lines kept); the rest is plate-D2-composed")
    rec_save(r)
    print(json.dumps(r["niche"]))


# ---------------------------------------------------------------------------------------------------------------- KD-L4
FLOOR_TARGET = (41.0, 44.0)               # 10.9.6 KD-L4: M0 does not see the opening (HC7), so L* 41-44 in D1 by the opening
PLASTER_DC = (0.0, 2.5, 85.0)


def floor_world(fr):
    """for the floor pixels of a frame: their world (X, Y) on Z 0"""
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float64)
    d = K.rays(fr, xx + 0.5, yy + 0.5)
    t = -K.LOC[2] / np.where(d[..., 2] < -1e-6, d[..., 2], -1e-6)
    return K.LOC[0] + t * d[..., 0], K.LOC[1] + t * d[..., 1]


def wmg1_toe(L):
    """WM-G1 on what this stage darkened (the graded oak, the niche's walnut): a Hermite toe from (0, 11, slope 0.2) to (18, 18, slope 1),
    the identity above 18; monotone, so the darkest oak under the bench keeps its grain and nothing reads under L* 11"""
    t = np.clip(L / 18.0, 0, 1)
    h00, h10, h01, h11 = 2 * t ** 3 - 3 * t ** 2 + 1, t ** 3 - 2 * t ** 2 + t, -2 * t ** 3 + 3 * t ** 2, t ** 3 - t ** 2
    T = h00 * 11.0 + h10 * 18.0 * 0.2 + h01 * 18.0 + h11 * 18.0 * 1.0
    return np.where(L < 18.0, T, L)


def floor_L(Yl, Yw, g0, k_far):
    f = g0 * (1 - k_far * np.clip((Yw - 2.0) / 4.0, 0, 1))
    Yn = Yl * f
    return wmg1_toe(np.where(Yn > 0.008856, 116 * np.cbrt(Yn) - 16, 903.3 * Yn))


def grade_one(rgb, lab, ids, Yw, g0, k_far):
    """one world-space gain on the oak (luminance, linear light; a* b* kept), WM-G1's toe on it, and the plaster's warmth"""
    lab = lab.copy()
    floor = np.isin(ids, (10, 11))
    L2 = floor_L(C.luma(C.lin(rgb)), Yw, g0, k_far)
    # the clay's floor grown 2 px (the plate sits on the clay within ECC's 1-2 px): no bright rim of ungraded oak round a leg
    fl = np.clip(C.blur(C.dil(floor, 2).astype(np.float64), 0.8) * 1.25, 0, 1)
    lab[..., 0] = np.where(fl > 0, lab[..., 0] * (1 - fl) + L2 * fl, lab[..., 0])
    wall = np.isin(ids, (1, 2, 3, 4, 5, 6, 7, 9, 12, 16, 37))
    wl = C.blur(wall.astype(np.float64), 0.8)
    h = np.radians(PLASTER_DC[2])
    lab[..., 1] += wl * PLASTER_DC[1] * np.cos(h)
    lab[..., 2] += wl * PLASTER_DC[1] * np.sin(h)
    return np.clip(C.from_lab(lab), 0, 1), floor, wall


def floor_reading(rgb, floor, box):
    lab = C.to_lab(rgb)
    m = floor & C.box_mask([box]) & K.frame_mask()
    return [round(float(v), 1) for v in np.median(lab[m], 0)], int(m.sum())


def grade():
    ids1, ids2 = K.ids("D1-plate"), K.ids("D2-plate")
    fx0, fy0, fx1, fy1 = K.FRAME
    fw_, fh_ = fx1 - fx0, fy1 - fy0
    OPEN_BOX = (int(fx0), int(fy0 + 0.85 * fh_), int(fx0 + 0.25 * fw_), int(fy1))          # D1's bottom-left corner: by the opening
    _, Yw1 = floor_world("D1")
    WIN = Yw1 < 1.0                                         # D1's floor by the window: world Y under 1.0 (the window wall is Y 0)
    p1 = C.load(os.path.join(ST, "plate-D1-ungraded.png"))
    p2 = C.load(os.path.join(K.SCR, "plate-D2-niche.png"))
    before1 = floor_reading(p1, np.isin(ids1, (10, 11)), OPEN_BOX)
    before_win = round(float(np.median(C.to_lab(p1)[..., 0][np.isin(ids1, (10, 11)) & WIN & K.frame_mask()])), 1)
    before_d2 = round(float(np.median(C.to_lab(p2)[..., 0][np.isin(ids2, (10, 11)) & K.frame_mask()])), 1)
    # g0 so that D1 by the opening reads the middle of 41-44; k_far so that D2's floor is 2-4 under D1's by the window (on the floor
    # pixels only; the full images once at the end)
    fm = K.frame_mask()
    _, Yw2 = floor_world("D2")
    Y1, Y2 = C.luma(C.lin(p1)), C.luma(C.lin(p2))
    fo = np.isin(ids1, (10, 11)) & C.box_mask([OPEN_BOX]) & fm
    fw1 = np.isin(ids1, (10, 11)) & WIN & fm
    f2m = np.isin(ids2, (10, 11)) & fm
    tgt = sum(FLOOR_TARGET) / 2
    lo, hi = 0.2, 1.2
    for _ in range(40):
        g0 = (lo + hi) / 2
        Lm = np.median(floor_L(Y1[fo], Yw1[fo], g0, 0.0))
        if Lm > tgt:
            hi = g0
        else:
            lo = g0
    best = None
    for k_far in np.linspace(0.0, 0.5, 51):
        win = float(np.median(floor_L(Y1[fw1], Yw1[fw1], g0, k_far)))
        d2 = float(np.median(floor_L(Y2[f2m], Yw2[f2m], g0, k_far)))
        if best is None or abs((win - d2) - 3.0) < abs((best[1] - best[2]) - 3.0):
            best = (k_far, win, d2)
    k_far, win, d2 = best
    o1, fl1, _ = grade_one(p1, C.to_lab(p1), ids1, Yw1, g0, k_far)
    o2, fl2, _ = grade_one(p2, C.to_lab(p2), ids2, Yw2, g0, k_far)
    win = float(np.median(C.to_lab(o1)[..., 0][fl1 & WIN & fm]))
    d2 = float(np.median(C.to_lab(o2)[..., 0][fl2 & fm]))
    o1 = np.where((~np.isin(ids1, (0,)))[..., None], o1, p1)
    K.save(os.path.join(ST, "plate-D1.png"), o1)
    K.save(os.path.join(ST, "plate-D2.png"), o2)
    for f in ("D1", "D2"):
        K.frame_crop(C.q(C.load(os.path.join(ST, f"plate-{f}.png")))).save(os.path.join(ST, f"plate-{f}-frame.png"))
    lab1, lab2 = C.to_lab(o1), C.to_lab(o2)
    w1, w2 = np.isin(ids1, (1, 2, 4, 5, 9)), np.isin(ids2, (1, 2, 3, 4, 5, 9))
    r = rec_load()
    r["grade"] = dict(rule="KD-L4: one world-space gain on the oak (Y, linear light): g0 by the window and the opening, g0 (1 - k_far) at Y 6.2; "
                           "a* b* kept (h and C* unchanged); WM-G1's toe on the graded oak (wmg1_toe: nothing under L* 11); the plaster "
                           "(walls, ceiling, hood) C* +2.5 toward h 85",
                      g0=round(float(g0), 4), k_far=round(float(k_far), 3),
                      D1_by_opening_before=before1, D1_by_opening_after=floor_reading(o1, fl1, OPEN_BOX), target_by_opening=list(FLOOR_TARGET),
                      D1_by_window_before=before_win, D2_floor_median_before=before_d2,
                      D1_by_window_after=round(float(win), 1), D2_floor_median_after=round(float(d2), 1), D2_minus_D1_window=round(float(d2 - win), 1),
                      plaster_after_D1=[round(float(v), 1) for v in np.median(lab1[w1 & K.frame_mask()], 0)],
                      plaster_after_D2=[round(float(v), 1) for v in np.median(lab2[w2 & K.frame_mask()], 0)],
                      boxes=dict(opening=OPEN_BOX, window="D1 floor at world Y < 1.0"), note="M0 does not see the dining opening (house plan: HC7), so the fallback L* 41-44")
    rec_save(r)
    print(json.dumps(r["grade"]))


# ---------------------------------------------------------------------------------------------------------------- the jar
JAR_PID = "vase-cj-matte-moon-jar-white-styleg"


def jar():
    man = CE.load_man()
    l = [x for x in man["layers"] if x["frame"] == "D2o" and x["product"] == JAR_PID and not x.get("projected_from")][0]
    maps = K.map_between("D2o", "D2")
    rgba = np.asarray(Image.open(os.path.join(ST, l["layer"]))).astype(np.float32)
    s8 = np.asarray(Image.open(os.path.join(ST, l["shadow"]))).astype(np.float32)
    mx, my, ok = maps
    prem = cv2.remap(rgba[..., :3] * (rgba[..., 3:4] / 255), mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    al = cv2.remap(rgba[..., 3], mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    sh = cv2.remap(s8, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=255)
    al[~ok] = 0
    # on the shelf (X 7.12, Z 1.59): from Y 1.55 to 1.735; scale by the depth ratio about the base centre
    zs = 1.59
    x0, y0 = K.proj("D2", 7.12, 1.55, zs)
    x1, y1 = K.proj("D2", 7.12, 1.735, zs)
    s = K.depth_of("D2", 7.12, 1.55) / K.depth_of("D2", 7.12, 1.735)
    A = np.array([[s, 0, x1 - s * x0], [0, s, y1 - s * y0]], np.float32)
    prem = cv2.warpAffine(prem, A, (W, H), flags=cv2.INTER_LINEAR)
    al = cv2.warpAffine(al, A, (W, H), flags=cv2.INTER_LINEAR)
    sh = cv2.warpAffine(sh, A, (W, H), flags=cv2.INTER_LINEAR, borderValue=255)
    col = prem / np.maximum(al[..., None] / 255, 1e-3)
    a8 = np.clip(np.rint(al), 0, 255).astype(np.uint8)
    out = np.dstack([np.clip(np.rint(col), 0, 255).astype(np.uint8), a8])
    out[..., :3][a8 == 0] = 0
    lp = os.path.join(ST, "layers", "D2", l["slot"], JAR_PID + ".png")
    sp = os.path.join(ST, "shadows", "D2", l["slot"], JAR_PID + ".png")
    os.makedirs(os.path.dirname(lp), exist_ok=True)
    os.makedirs(os.path.dirname(sp), exist_ok=True)
    Image.fromarray(out, "RGBA").save(lp, optimize=True)
    Image.fromarray(np.clip(np.rint(sh), 0, 255).astype(np.uint8)).save(sp, optimize=True)
    man["layers"] = [x for x in man["layers"] if not (x["frame"] == "D2" and x["product"] == JAR_PID and not x.get("projected_from"))]
    ys, xs = np.nonzero(a8 > 0)
    man["layers"].append(dict(l, frame="D2", layer=os.path.relpath(lp, ST), shadow=os.path.relpath(sp, ST), alpha_px=int((a8 > 0).sum()),
                              shadow_px=int((sh < 254.5).sum()), bbox_px=[int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1],
                              derived_from="D2o", retired=None, pass_="jar-move",
                              source=l["source"] + "; 10.9: warped D2o -> D2 and moved on the shelf from Y 1.55 to 1.735 in code (tools/kd_d2stage.py jar)"))
    json.dump(man, open(os.path.join(ST, "manifest.json"), "w"), indent=1)
    r = rec_load()
    r["jar"] = dict(from_y=1.55, to_y=1.735, shift_px=[round(float(x1 - x0), 1), round(float(y1 - y0), 1)], scale=round(float(s), 4))
    rec_save(r)
    print(json.dumps(r["jar"]))


# ---------------------------------------------------------------------------------------------------------------- edit inputs
def frame_now(exclude):
    """the D2 frame as composed now, without the layers in exclude (product ids)"""
    man = CE.load_man()
    rec = {}
    swap = None
    plate8 = np.asarray(Image.open(os.path.join(ST, "plate-D2.png")).convert("RGB"))
    out = plate8.astype(np.float64) / 255
    a_all = np.zeros((H, W))
    ls = [l for l in man["layers"] if l["frame"] == "D2" and l["default"] and not l.get("retired") and l["product"] not in exclude]
    ls.sort(key=lambda l: (l["z"], l.get("sub", 0), l["slot"]))
    for l in ls:
        rgba = np.asarray(Image.open(os.path.join(ST, l["layer"])))
        s8 = np.asarray(Image.open(os.path.join(ST, l["shadow"])))
        out = C.compose_one(out, rgba, s8)
        a_all = 1 - (1 - a_all) * (1 - rgba[..., 3] / 255)
    for li in [li for li in man["light"] if li["frame"] == "D2"]:
        L8 = np.asarray(Image.open(os.path.join(ST, li["file"]))).astype(np.float64)
        L8 = np.clip(np.rint(L8 * (1 - a_all)[..., None]), 0, 255).astype(np.uint8)
        out = C.light_one(out, L8)
    _ = (rec, swap)
    return out


def base(p, ids_, box, exclude):
    b = frame_now(exclude)
    bp = os.path.join(ST, "inputs", f"{p}-base.png")
    K.save(bp, b)
    clay = C.load(K.clay_file("D2", ".png"))
    m = np.isin(K.ids("D2"), ids_)
    inp = b.copy()
    inp[m] = clay[m]
    ip = os.path.join(ST, "inputs", f"{p}-input.png")
    K.save(ip, inp)
    x0, y0, x1, y1 = box
    crop = Image.fromarray(C.q(inp)).crop((x0, y0, x1, y1))
    s = 2048 / max(crop.size)
    cp = os.path.join(ST, "inputs", f"{p}-crop.png")
    crop.resize((int(round(crop.size[0] * s)), int(round(crop.size[1] * s))), Image.LANCZOS).save(cp)
    rec = dict(pass_=p, frame="D2", base=os.path.relpath(bp, ST), crop_box=list(box), crop_aspect=round((x1 - x0) / (y1 - y0), 4), upscale=round(s, 4),
               placeholder_ids=list(ids_), placeholder_px=int(m.sum()), excluded=list(exclude), input=os.path.relpath(ip, ST),
               crop=os.path.relpath(cp, ST), crop_sha256=K.sha(cp))
    json.dump(rec, open(os.path.join(ST, "inputs", f"{p}-prep.json"), "w"), indent=1)
    print(json.dumps(rec))


if __name__ == "__main__":
    a = sys.argv[1:]
    {"migrate": migrate, "retire": retire, "plate": plate, "niche-prep": niche_prep, "niche-apply": niche_apply, "grade": grade, "jar": jar}.get(a[0], lambda: None)()
    if a[0] == "base":
        n = a.index("--")
        base(a[1], [int(v) for v in a[2:n]], tuple(int(v) for v in a[n + 1:n + 5]), a[n + 5:])


# ---------------------------------------------------------------------------------------------------------------- Hb: the serving boards
BOARD_PID = "cutting-boards-aliexpress-2pcs-1pc-wooden-cutting-280363-l"
SERV = {"F": dict(y=1.93, w=0.195, h=0.34, x0=7.228, x1=7.243, col=(0x47, 0x31, 0x23)),
        "B": dict(y=2.07, w=0.185, h=0.39, x0=7.226, x1=7.243, col=(0x3E, 0x2A, 0x1E))}


def board_quads():
    """the front faces of the two serving boards (the clay's obox, KD-17), whole: the 280363 board in front is left out of this input"""
    out = {}
    for k, b in SERV.items():
        t = 0.009
        pts = [(b["x0"] - t, b["y"] - b["w"] / 2, 0.90), (b["x0"] - t, b["y"] + b["w"] / 2, 0.90),
               (b["x1"] - t, b["y"] + b["w"] / 2, 0.90 + b["h"]), (b["x1"] - t, b["y"] - b["w"] / 2, 0.90 + b["h"])]
        out[k] = np.array([K.proj("D2", *p) for p in pts], np.float32)
    return out


def base_boards(box):
    b = frame_now([BOARD_PID])
    bp = os.path.join(ST, "inputs", "Hb-boards-base.png")
    K.save(bp, b)
    inp = C.q(b).copy()
    q = board_quads()
    m = np.zeros((H, W), np.uint8)
    for k in ("F", "B"):                              # B is 2 mm nearer: drawn last
        cv2.fillConvexPoly(inp, np.rint(q[k]).astype(np.int32), SERV[k]["col"], lineType=cv2.LINE_AA)
        cv2.fillConvexPoly(m, np.rint(q[k]).astype(np.int32), 1)
    ip = os.path.join(ST, "inputs", "Hb-boards-input.png")
    Image.fromarray(inp).save(ip)
    np.save(os.path.join(K.SCR, "Hb-boards-placeholder.npy"), m.astype(bool))
    x0, y0, x1, y1 = box
    crop = Image.fromarray(inp).crop((x0, y0, x1, y1))
    s = 2048 / max(crop.size)
    cp = os.path.join(ST, "inputs", "Hb-boards-crop.png")
    crop.resize((int(round(crop.size[0] * s)), int(round(crop.size[1] * s))), Image.LANCZOS).save(cp)
    rec = dict(pass_="Hb-boards", frame="D2", base=os.path.relpath(bp, ST), crop_box=list(box), crop_aspect=round((x1 - x0) / (y1 - y0), 4),
               upscale=round(s, 4), placeholder_ids=[79], placeholder_px=int(m.sum()), excluded=[BOARD_PID],
               placeholder="the two boards' whole front faces from the clay geometry (tools/kd_d2stage.py board_quads), the 280363 board left out",
               quads_px={k: [[round(float(a), 1) for a in p] for p in v] for k, v in q.items()},
               input=os.path.relpath(ip, ST), crop=os.path.relpath(cp, ST), crop_sha256=K.sha(cp))
    json.dump(rec, open(os.path.join(ST, "inputs", "Hb-boards-prep.json"), "w"), indent=1)
    print(json.dumps(rec))


if __name__ == "__main__" and sys.argv[1] == "base-boards":
    base_boards(tuple(int(v) for v in sys.argv[2:6]))


def boards_fix(s=0.78):
    """Hb r1 drew the paddle B about 1.2x wide and 1.36x tall (its body filled the placeholder and the handle went on top): B alone is
    scaled by s about its bottom-left corner (its contact and its edge against F stay); s = 0.78 splits the error (height 41.4 cm
    against 39, width 17.4 against 18.5). Where B no longer covers F, F's hidden top-right corner is its own top-left corner mirrored. The pale
    flecks of splash the cut took between the boards go (the boards are walnut, L* under 55)."""
    man = CE.load_man()
    l = [x for x in man["layers"] if x["frame"] == "D2" and x["slot"] == "serving-boards" and not x.get("projected_from")][0]
    lp, sp = os.path.join(ST, l["layer"]), os.path.join(ST, l["shadow"])
    rgba = np.asarray(Image.open(lp)).astype(np.float64)
    sh = np.asarray(Image.open(sp)).astype(np.float64)
    a = rgba[..., 3] / 255
    rgb = rgba[..., :3] / 255
    pale = (C.to_lab(rgb)[..., 0] > 55) & (a > 0)
    a = np.where(pale, 0, a)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float64)
    bl = 842.0 + (741.0 - yy) / (741.0 - 596.0) * 4.0       # B's left edge in the edit: x 842 at the bottom, 846 at its shoulder
    Bm = (a > 0) & ((xx >= bl) & (yy >= 590) | (yy < 590) & (xx > 860))
    ax, ay = 842.0, 741.0
    A = np.array([[s, 0, ax - s * ax], [0, s, ay - s * ay]], np.float32)
    a0 = a.copy()
    pre = rgb * (a * Bm)[..., None]
    preB = cv2.warpAffine(pre.astype(np.float32), A, (W, H), flags=cv2.INTER_AREA).astype(np.float64)
    aB = cv2.warpAffine((a * Bm).astype(np.float32), A, (W, H), flags=cv2.INTER_AREA).astype(np.float64)
    Fm = (a > 0) & ~Bm
    aF = a * Fm
    rgbF = rgb.copy()
    # F behind the old B: F is a symmetric rounded rectangle (x 786-860, the clay's right edge), so its hidden top-right corner is its
    # own top-left corner mirrored about its centre line (the hanging hole, near the left, is not in the mirrored band)
    need = Bm & ~(aB > 0.5) & (xx <= 860)
    src_y, src_x = np.nonzero(need)
    sx = np.clip(2 * 823 - src_x, 0, W - 1)
    ok = Fm[src_y, sx] & (a[src_y, sx] > 0.5)
    rgbF[src_y[ok], src_x[ok]] = rgb[src_y[ok], sx[ok]]
    aF[src_y[ok], src_x[ok]] = a0[src_y[ok], sx[ok]]
    out_a = aB + aF * (1 - aB)
    out_rgb = (preB + rgbF * aF[..., None] * (1 - aB[..., None])) / np.maximum(out_a[..., None], 1e-4)
    # the shadow: B's part scaled with it
    shB = np.where((xx >= 842), sh, 255.0)
    shB = cv2.warpAffine(shB.astype(np.float32), A, (W, H), flags=cv2.INTER_LINEAR, borderValue=255).astype(np.float64)
    sh2 = np.where(xx >= 842, np.minimum(shB, 255.0), sh)
    a8 = C.q(out_a)
    o = np.dstack([C.q(np.clip(out_rgb, 0, 1)), a8])
    o[..., :3][a8 == 0] = 0
    Image.fromarray(o, "RGBA").save(lp, optimize=True)
    Image.fromarray(np.clip(np.rint(sh2), 0, 255).astype(np.uint8)).save(sp, optimize=True)
    ys, xs = np.nonzero(a8 > 0)
    l.update(alpha_px=int((a8 > 0).sum()), bbox_px=[int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1],
             shadow_px=int((sh2 < 254.5).sum()), size_fix=dict(board="B", scale=s, anchor_px=[ax, ay], F_filled_px=int(ok.sum()),
                                                                  pale_removed_px=int(pale.sum()), rule=boards_fix.__doc__.split(". ")[0]))
    json.dump(man, open(os.path.join(ST, "manifest.json"), "w"), indent=1)
    r = rec_load()
    r["boards_fix"] = l["size_fix"]
    rec_save(r)
    print(json.dumps(l["size_fix"]), l["bbox_px"])


if __name__ == "__main__" and sys.argv[1] == "boards-fix":
    boards_fix()


def vessel_fix():
    """Hv r1: kd_cut2's matte of the branches lost thin stems and the right-hand branch, and took the edit's soft leaf shade and its
    redrawn holder top as grey patches. The layer is re-cut here from the locked edit against its base (the known background):
    the jar's body (pale, low chroma, connected to the clay's jar) opaque with an anti-aliased edge; the branches by the exact
    difference matte (kd_fixes2.diff_matte) only on the leaves (C* over 16) and stems (L* under 60) that the edit changed, grown 2 px,
    opaque in the leaves' cores; below y 600 nothing right of the jar (the holder, a D2o layer, keeps its own pixels). The shadow is
    the jar's contact only. Then WM-G1 (the plate's toe and the floor), as kd_cut2.write2."""
    import kd_cut2 as CUT
    import kd_fixes2 as FX2
    man = CE.load_man()
    l = [x for x in man["layers"] if x["frame"] == "D2" and x["slot"] == "counter-vessel" and not x.get("projected_from")][0]
    lp, sp = os.path.join(ST, l["layer"]), os.path.join(ST, l["shadow"])
    sh = np.asarray(Image.open(sp)).astype(np.float64)
    e = np.load(os.path.join(K.SCR, "Hv-vessel-locked.npy")).astype(np.float64)
    B = C.load(os.path.join(ST, "inputs", "Hv-vessel-base.png"))
    ids = K.ids("D2")
    le, lb_ = C.to_lab(e), C.to_lab(B)
    d = np.linalg.norm(C.blur(le, 1.0) - C.blur(lb_, 1.0), axis=-1)
    Ce = np.hypot(le[..., 1], le[..., 2])
    body0 = (le[..., 0] > 58) & (Ce < 14) & C.dil(ids == 78, 10) & (d > 3)
    n, lb = cv2.connectedComponents(body0.astype(np.uint8), connectivity=8)
    keep_lb = set(np.unique(lb[C.ero(ids == 78, 3) & body0])) - {0}
    body = CE.fill_holes(np.isin(lb, list(keep_lb)), 4000)
    body = cv2.morphologyEx(body.astype(np.uint8), cv2.MORPH_OPEN, C.disk(2)).astype(bool)
    zone = C.dil(np.isin(ids, (78, 80)), 45) & C.box_mask([(1386, 240, 1758, 798)])
    zone &= ~(C.box_mask([(1590, 600, 1700, 798)]) & ~C.dil(body, 2))          # the holder's place
    seeds = zone & ~C.dil(body, 1) & (((Ce > 16) & (d > 8)) | ((le[..., 0] < 60) & (d > 10)))
    n2, lb2, st2, _ = cv2.connectedComponentsWithStats(seeds.astype(np.uint8), connectivity=8)
    seeds = np.isin(lb2, [i for i in range(1, n2) if st2[i, cv2.CC_STAT_AREA] >= 4])
    region = (C.dil(seeds, 2) & zone).astype(np.float64)
    a_est = np.where(C.ero(seeds, 1) & (d > 14), 1.0, 0.0)
    ab, cb = FX2.diff_matte(e, B, region, a_est)
    ab = np.where(ab < 0.12, 0.0, ab)
    a_body = FX2.aa_alpha(body, sigma=1.0, width=1.0)
    c_body = C.defringe(e, body, r=2)
    a = np.maximum(a_body, ab)
    col = np.where((a_body >= ab)[..., None], c_body, cb)
    tc = CE.toe("D2")
    lab = C.to_lab(col)
    if tc:
        lab[..., 0] = np.interp(lab[..., 0], tc[0], tc[1])
    lab[..., 0] = np.interp(lab[..., 0], CUT.BP_FLOOR[0], CUT.BP_FLOOR[1])
    col = np.clip(C.from_lab(lab), 0, 1)
    ys_b, xs_b = np.nonzero(body)
    low = np.arange(H)[:, None] >= ys_b.max() - 0.25 * (ys_b.max() - ys_b.min())     # the contact: round the jar's foot only
    sh2 = np.where(C.dil(body, 22) & ~body & low, sh, 255)
    a8 = C.q(a)
    o = np.dstack([C.q(col), a8])
    o[..., :3][a8 == 0] = 0
    Image.fromarray(o, "RGBA").save(lp, optimize=True)
    Image.fromarray(np.clip(np.rint(sh2), 0, 255).astype(np.uint8)).save(sp, optimize=True)
    ys, xs = np.nonzero(a8 > 0)
    l.update(alpha_px=int((a8 > 0).sum()), bbox_px=[int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1],
             shadow_px=int((sh2 < 254.5).sum()), toned=bool(tc),
             cut_fix=dict(body_px=int(body.sum()), branch_seed_px=int(seeds.sum()), branch_alpha_px=int((ab > 0).sum()),
                          rule="tools/kd_d2stage.py vessel_fix: the jar opaque, the branches by the exact difference matte on their base"))
    l.pop("size_fix", None)
    json.dump(man, open(os.path.join(ST, "manifest.json"), "w"), indent=1)
    r = rec_load()
    r["vessel_fix"] = l["cut_fix"]
    rec_save(r)
    print(json.dumps(l["cut_fix"]), l["bbox_px"])


if __name__ == "__main__" and sys.argv[1] == "vessel-fix":
    vessel_fix()
