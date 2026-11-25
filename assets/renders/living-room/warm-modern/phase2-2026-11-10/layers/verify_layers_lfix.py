#!/usr/bin/env python3
"""
verify_layers_lfix.py: re-runnable check of the lfix round (the owner's three defects in M0, code only, 2026-11-25; render-agent, for
qa-agent). Reads manifest-lfix.json, manifest-fb12s1.json and the files they name; writes verify-layers-lfix.json; exit 0 = all pass.

    python3.12 -I -B verify_layers_lfix.py

  1 RND2     each rebuilt default = fb12s1's truth outside the changed layers' regions (0 px): the cushion set (old and new layer and
             shadow) and the basket (old and new layer and shadow); every other layer file is fb12s1's own
  2 WM-G1    the plate is stage 0's (sha); no default's black point (L* p0.5) below R9's - 0.05 (the fb12s1 rule)
  3 stack    this manifest's 8-bit stack = the truths inside the changed region (0 px), over the canvas within R9's gate (p99.9 <= 2, max <= 6)
  4 fixes    (a) the cushion: right of the left cushion, above its bottom, the shadow's mean darkening <= 0.05 and max <= 0.31 (was 0.65);
             (b) the basket: no shadow on the wall, the skirting or the pot (only on the floor and the rug; a 3 px
             anti-aliased edge at the skirting's foot); the handles' loops open
             (the R3a render's wall px inside its alpha <= 10); (c) the throw: no visible sofa between its cut edge and Olia's top
             (columns x < 2130 with a gap > 3 px: <= 5, the fringe's tip); (d) the stripe on throws A and C: no row in its box darker
             than 0.8 of the knit 7 px above and below (the stripe was 0.69-0.76)
  5 scan     scan_edge_bleed.py on this manifest: no SHADOW or EDGE patch of the cushion sets or the basket inside the three defects' boxes
  6 scope    no tracked file under the warm-modern living room is modified in git (only new files; the folder's README.md allowed)
"""
import hashlib
import importlib.util
import json
import os
import subprocess
import sys

import cv2
import numpy as np
from PIL import Image

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
P2 = os.path.dirname(HERE)
REPO = os.path.abspath(os.path.join(P2, *[".."] * 4))
PLATE_SHA = "7f83091908fb5331e3491598839d790129d36ced1ce01dec3f65f1d75cc265cd"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


FB = _load("fb12_s0", os.path.join(P2, "fb12_s0.py"))
SCAN = _load("scan_edge_bleed", os.path.join(HERE, "scan_edge_bleed.py"))


def arr(p, mode=None):
    im = Image.open(p)
    return np.asarray(im.convert(mode) if mode else im)


def L(p):
    return os.path.normpath(os.path.join(HERE, p))


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def lstar(a8):
    return cv2.cvtColor(a8.astype(np.float32) / 255, cv2.COLOR_RGB2LAB)[..., 0]


def region(lf, sf):
    return (arr(lf)[..., 3] > 0) | (arr(sf, "RGB") < 255).any(2)


def stack(man, st):
    by = {l_["id"]: l_ for l_ in man["layers"]}
    out = []
    for l_ in man["layers"]:
        k = l_["id"]
        if k == "base" or k.endswith("-shadow"):
            continue
        if k == "cushions":
            v = man["slot_cushions"]["sets"][st]
            out.append((k, L(v["layer"]), L(v["shadow"])))
        else:
            out.append((k, L(l_["file"]), L(by[k + "-shadow"]["file"])))
    return out


def main():
    man = json.load(open(os.path.join(HERE, "manifest-lfix.json")))
    man1 = json.load(open(os.path.join(HERE, "manifest-fb12s1.json")))
    by, by1 = {l_["id"]: l_ for l_ in man["layers"]}, {l_["id"]: l_ for l_ in man1["layers"]}
    out, ok = {}, True

    # 1 RND2
    c1 = dict(other_layers_same_file=[k for k in by if k not in ("basket", "basket-shadow") and by[k].get("file") != by1[k].get("file")] == [])
    rb = region(L(by["basket"]["file"]), L(by["basket-shadow"]["file"])) | region(L(by1["basket"]["file"]), L(by1["basket-shadow"]["file"]))
    for st in "BAC":
        v, v1 = man["slot_cushions"]["sets"][st], man1["slot_cushions"]["sets"][st]
        al = rb | region(L(v["layer"]), L(v["shadow"])) | region(L(v1["layer"]), L(v1["shadow"]))
        d = (arr(L(man["truths"]["default"][st]), "RGB") != arr(L(man1["truths"]["default"][st]), "RGB")).any(2)
        c1[f"default_{st}_changed_px"] = int(d.sum())
        c1[f"default_{st}_outside_allowed_px"] = int((d & ~al).sum())
    c1["pass_"] = bool(c1["other_layers_same_file"] and all(c1[f"default_{st}_outside_allowed_px"] == 0 for st in "BAC"))
    out["1_RND2"] = c1
    ok &= c1["pass_"]

    # 2 WM-G1
    plate_p = L(by["base"]["file"])
    r9 = json.load(open(os.path.join(HERE, "manifest-r9.json")))
    c2 = dict(plate_sha_is_stage0=sha(plate_p) == PLATE_SHA)
    for st in "BAC":
        c2[f"default_{st}"] = round(float(np.percentile(lstar(arr(L(man["truths"]["default"][st]), "RGB")), 0.5)), 2)
        c2[f"default_{st}_fb12s1"] = round(float(np.percentile(lstar(arr(L(man1["truths"]["default"][st]), "RGB")), 0.5)), 2)
        c2[f"default_{st}_r9"] = round(float(np.percentile(lstar(arr(L(r9["truths"]["default"][st]), "RGB")), 0.5)), 2)
    c2["pass_"] = bool(c2["plate_sha_is_stage0"] and all(c2[f"default_{st}"] >= c2[f"default_{st}_r9"] - 0.05 for st in "BAC"))
    out["2_WM_G1"] = c2
    ok &= c2["pass_"]

    # 3 the stack
    c3 = {}
    base8 = arr(plate_p, "RGB")
    reg = np.load(os.path.join(P2, "work-lfix", "regions-lfix.npz"))
    for st in "BAC":
        s8 = FB.compose8(base8, stack(man, st), {})
        diff = np.abs(s8.astype(int) - arr(L(man["truths"]["default"][st]), "RGB").astype(int)).max(2)
        c3[st] = dict(inside_region_px=int((diff[reg[f"default_{st}"]] > 0).sum()), canvas_p99_9=float(np.percentile(diff, 99.9)), canvas_max=int(diff.max()))
    c3["pass_"] = bool(all(c3[st]["inside_region_px"] == 0 and c3[st]["canvas_p99_9"] <= 2 and c3[st]["canvas_max"] <= 6 for st in "BAC"))
    out["3_stack"] = c3
    ok &= c3["pass_"]

    # 4 the fixes
    c4 = {}
    T = arr(L(by["coffee-table"]["file"]))[..., 3] > 127
    OT = cv2.dilate((np.load(os.path.join(P2, "work-fb12s0", "fb12s0-masks.npz"))["table"] > 0).astype(np.uint8), np.ones((13, 13), np.uint8)) > 0
    for st in "BAC":
        v = man["slot_cushions"]["sets"][st]
        Lc, Sh = arr(L(v["layer"])), arr(L(v["shadow"]), "RGB")
        a = Lc[..., 3] > 127
        n, lab_, stt, _ = cv2.connectedComponentsWithStats(a.astype(np.uint8))
        i = min([j for j in range(1, n) if stt[j, 4] > 5000 and stt[j, 0] < 1500], key=lambda j: stt[j, 0])
        ys, xs = np.nonzero(lab_ == i)
        zone = np.zeros(a.shape, bool)
        for y in range(ys.min(), ys.max() - 4):
            xr = xs[ys == y].max()
            zone[y, xr + 1:xr + 60] = True
        zone &= ~a
        dk = 1 - Sh.mean(2) / 255
        gaps = []
        for x in range(1850, 2130):
            col = np.nonzero(a[1100:1400, x])[0]
            if not len(col):
                continue
            yb = 1100 + col.max()
            t = np.nonzero(T[yb + 1:yb + 140, x])[0]
            if len(t) and OT[yb + 2, x] and t[0] > 3:
                gaps.append(x)
        rgb = Lc[..., :3].astype(np.float32) @ np.array([0.2126, 0.7152, 0.0722], np.float32)
        stripe = None
        box = dict(A=(2150, 1252, 2260, 1282), C=(2174, 1252, 2203, 1282)).get(st)
        if box:
            x0, y0, x1, y1 = box
            ratio = rgb[y0:y1, x0:x1] / np.maximum(0.5 * (rgb[y0 - 7:y1 - 7, x0:x1] + rgb[y0 + 7:y1 + 7, x0:x1]), 1)
            stripe = int((np.median(ratio, 1) < 0.8).sum())      # the stripe was 0.69-0.76; the knit's own rows 0.87-0.95
        c4[st] = dict(cushion_zone_dark_mean=round(float(dk[zone].mean()), 4), cushion_zone_dark_max=round(float(dk[zone].max()), 4),
                      throw_gap_columns=len(gaps), throw_gap_x=gaps[:8], stripe_rows=stripe)
    Lb, Sb = arr(L(by["basket"]["file"])), arr(L(by["basket-shadow"]["file"]), "RGB")
    X_, Y_ = FB.img_to_plane(FB.H_FLOOR)
    floor = (Y_ > 0.004) & (X_ > -2.296) & (np.arange(FB.H)[:, None] > 900)
    pot = arr(L(by["planter"]["file"]))[..., 3] > 25
    wall_sh = (Sb < 252).any(2) & ~cv2.dilate(floor.astype(np.uint8), np.ones((7, 7), np.uint8)).astype(bool)     # the 3 px anti-aliased edge at the skirting
    pot_sh = (Sb < 252).any(2) & pot & ~(Lb[..., 3] > 0)
    lab_b = cv2.cvtColor(Lb[..., :3].astype(np.float32) / 255, cv2.COLOR_RGB2LAB)
    loops = (Lb[..., 3] > 200) & (np.hypot(lab_b[..., 1], lab_b[..., 2]) < 10) & (lab_b[..., 0] > 75) & (np.arange(FB.H)[:, None] <= 1066)
    c4["basket"] = dict(shadow_on_wall_px=int(wall_sh.sum()), shadow_on_pot_px=int(pot_sh.sum()), render_wall_px_in_handles=int(loops.sum()))
    c4["pass_"] = bool(all(c4[st]["cushion_zone_dark_mean"] <= 0.05 and c4[st]["cushion_zone_dark_max"] <= 0.31 and c4[st]["throw_gap_columns"] <= 5
                           and (c4[st]["stripe_rows"] in (None, 0)) for st in "BAC")
                       and c4["basket"]["shadow_on_wall_px"] == 0 and c4["basket"]["shadow_on_pot_px"] == 0 and c4["basket"]["render_wall_px_in_handles"] <= 10)
    out["4_fixes"] = c4
    ok &= c4["pass_"]

    # 5 the scan, in the three defects' boxes
    rows = SCAN.scan(os.path.join(HERE, "manifest-lfix.json"), variants=False)
    boxes = dict(cushion=(1600, 900, 1700, 1072), basket_wall=(940, 990, 1200, 1150), throw_gap=(1900, 1180, 2135, 1260))

    def inside(bb, b):
        return bb[0] >= b[0] and bb[1] >= b[1] and bb[2] <= b[2] and bb[3] <= b[3]
    hits = [dict(layer=r["layer"], check=r["check"], bbox=r["bbox"], box=k) for r in rows if r["layer"].startswith(("cushions", "basket"))
            for k, b in boxes.items() if inside(r["bbox"], b) and r["visibility"] == "x1-x2"]
    out["5_scan"] = dict(boxes=boxes, hits=hits, rows_total=len(rows), pass_=not hits)
    ok &= out["5_scan"]["pass_"]

    # 6 scope
    r = subprocess.run(["git", "-C", REPO, "status", "--porcelain", "--", "assets/renders/living-room/warm-modern"], capture_output=True, text=True).stdout
    mod = [ln for ln in r.splitlines() if not ln.startswith("??") and not ln.endswith("phase2-2026-11-10/README.md")]
    out["6_scope"] = dict(tracked_modified=mod, pass_=not mod)
    ok &= out["6_scope"]["pass_"]

    out["all_pass"] = bool(ok)
    json.dump(out, open(os.path.join(HERE, "verify-layers-lfix.json"), "w"), indent=1)
    print(json.dumps({k: (v.get("pass_") if isinstance(v, dict) else v) for k, v in out.items()}, indent=1))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
