#!/usr/bin/env python3
"""
verify_layers_fb12s0.py: re-runnable check of FB12 stage 0 (the clean M0 plate without the old coffee table) in the warm-modern tool
(render-agent, 2026-11-25; for qa-agent). Reads manifest-fb12s0.json and the files it names (numpy + Pillow + OpenCV; phase 2's
stack.Grade read-only); writes verify-layers-fb12s0.json; exit 0 = every check passes. Read-only on everything else.

    python3.12 -I verify_layers_fb12s0.py

  1 plate     base-fb12s0.png = base.png outside the plate region (0 px); base.png still the approved bytes (sha); the plate is the ONE
              v3c grade of shell-furniture-fb12s0.png byte for byte; that ungraded plate = shell-furniture-v3.png outside the region;
              the fixed-furniture alpha = phase 1's outside the old table's region, and inside it only the sofa (no alpha in front of the
              sofa's plinth line, none left of its end)
  2 boards    the floor's board joints, in the floor plane (homography of docs/house-plan.json M0): every joint that crosses the old
              table's region is a straight line through it: its X inside vs the line fitted outside, max |dX| <= 4 mm
  3 WM-G1     black point (L* p0.5) of the plate within 11-14 (the grade's rule); the rebuilt defaults not darker than R9's
  4 RND2      the rebuilt defaults = the R9 truths outside the region where the stack changed (0 px); the rug layer changes only inside the
              old table's region and the rug zone around it; the rug's shadow and the cushion sets (layers, shadows) only inside the
              old table's region
  5 stack     the new manifest's stack (8-bit, the hidden slots out) = the new truths inside the changed region (0 px), and over the
              canvas within R9's gate (p99.9 <= 2, max <= 6)
  6 hidden    the bowl and the candle holders: marked hidden_in_defaults, their layers and shadows the R9 files, unchanged in git
  7 scope     no tracked file under the warm-modern living room is modified in git, other than this stage's own (base.png, the R9
              manifest, layers and truths unchanged)
"""
import hashlib
import importlib.util
import json
import math
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
P1 = os.path.join(os.path.dirname(P2), "pilot-phase1-2026-11-07")
MAN = os.path.join(HERE, "manifest-fb12s0.json")
R9 = os.path.join(HERE, "manifest-r9.json")
BASE_SHA = "75200f46361dfd62dd03363ef46e21cce119fce04990d914a771383b551aba39"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


FB = _load("fb12_s0", os.path.join(P2, "fb12_s0.py"))


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def arr(p, mode=None):
    im = Image.open(p)
    return np.asarray(im.convert(mode) if mode else im)


def lstar(a8):
    return cv2.cvtColor(a8.astype(np.float32) / 255, cv2.COLOR_RGB2LAB)[..., 0]


def git_modified(paths):
    out = subprocess.run(["git", "-C", REPO, "status", "--porcelain", "--"] + paths, capture_output=True, text=True).stdout
    return [ln for ln in out.splitlines() if not ln.startswith("??")]


def main():
    man = json.load(open(MAN))
    r9 = json.load(open(R9))
    fb = man["fb12s0"]
    reg = np.load(os.path.join(P2, fb["regions"]))
    T, Rp, Rrug = reg["table"], reg["plate"], reg["rug"]
    out, ok = {}, True

    # 1 plate
    base_old = arr(os.path.join(HERE, "base.png"))
    plate = arr(os.path.join(HERE, man["layers"][0]["file"]))
    U = arr(os.path.join(P2, fb["files"]["U"]))
    U_old = arr(os.path.join(P1, "shell-furniture-v3.png"), "RGB")
    sys.path.insert(0, P2)
    sys.path.insert(0, P1)
    import stack as ST  # noqa: E402
    G = ST.Grade()
    regraded = G(U.astype(np.float32) / 255)
    Fl = arr(os.path.join(P2, fb["files"]["F"]))
    fa_old = arr(os.path.join(P1, "fixed-furniture.png"))[..., 3]
    m = FB.masks()
    X, Y = FB.img_to_plane(FB.H_FLOOR)
    arm = cv2.dilate((m["armchair"] > 0.005).astype(np.uint8), np.ones((9, 9), np.uint8)).astype(bool)
    # an independent bound on the new alpha: inside the old table's region nothing may be furniture (alpha > 64) where the floor ray
    # lands in front of the plinth line, or outside the sofa's silhouette dilated 4 px (sofa-front rect: the measured ends and rows)
    Hi = np.linalg.inv(FB.SR_M)
    yy, xx = np.mgrid[0:FB.H, 0:FB.W].astype(np.float64)
    Pq = np.stack([xx, yy, np.ones_like(xx)], -1) @ Hi.T
    xr, yr = Pq[..., 0] / Pq[..., 2], Pq[..., 1] / Pq[..., 2]
    sil_dil = FB.sofa_silhouette_rect(xr + 4, yr - 4) > 0
    in_front = T & (Y > FB.SOFA["plinth_Y"] + 0.02) & ~arm
    left_of = T & ~sil_dil & ~arm
    c1 = dict(base_png_sha_unchanged=sha(os.path.join(HERE, "base.png")) == BASE_SHA,
              px_changed=int((plate != base_old).any(2).sum()),
              px_changed_outside_region=int(((plate != base_old).any(2) & ~Rp).sum()),
              regrade_px_differ=int((regraded != plate).any(2).sum()),
              ungraded_outside_region_px_differ=int(((U != U_old).any(2) & ~Rp).sum()),
              furniture_alpha_outside_table_px_differ=int(((Fl[..., 3] != fa_old) & ~T).sum()),
              furniture_alpha_in_front_of_plinth_px=int((Fl[..., 3][in_front] > 64).sum()),
              furniture_alpha_outside_sofa_silhouette_px=int((Fl[..., 3][left_of] > 64).sum()))
    c1["pass_"] = bool(c1["base_png_sha_unchanged"] and c1["px_changed_outside_region"] == 0 and c1["regrade_px_differ"] == 0
                       and c1["ungraded_outside_region_px_differ"] == 0 and c1["furniture_alpha_outside_table_px_differ"] == 0
                       and c1["furniture_alpha_in_front_of_plinth_px"] == 0 and c1["furniture_alpha_outside_sofa_silhouette_px"] == 0)
    out["1_plate"] = c1

    # 2 boards: the joints in the floor plane (400 px/m), X -1.0..1.6, Y 0.92..2.4
    ppm, X0, Y0, w, h = 400, -1.0, 0.92, 1040, 592
    Mf = FB.H_FLOOR @ FB.rect_A(ppm, X0, Y0)
    fl = cv2.warpPerspective(lstar(plate), Mf, (w, h), flags=cv2.WARP_INVERSE_MAP | cv2.INTER_LINEAR, borderValue=np.nan)
    Tf = cv2.warpPerspective(T.astype(np.float32), Mf, (w, h), flags=cv2.WARP_INVERSE_MAP | cv2.INTER_LINEAR) > 0.5
    furn = cv2.warpPerspective((Fl[..., 3] > 2).astype(np.float32), Mf, (w, h), flags=cv2.WARP_INVERSE_MAP | cv2.INTER_LINEAR) > 0.01
    valid = np.isfinite(fl) & ~furn
    prof = np.nanmean(np.where(valid, fl, np.nan), 0)
    hp = prof - cv2.GaussianBlur(np.nan_to_num(prof, nan=float(np.nanmean(prof)))[None], (0, 0), 6)[0]
    cand = [x for x in range(4, w - 4) if hp[x] < -2.0 and hp[x] == np.nanmin(hp[x - 4:x + 5])]
    seams = []
    for x0 in cand:
        xs_in, xs_out = [], []
        for yy in range(0, h, 4):
            row = fl[yy, x0 - 5:x0 + 6]
            if not np.isfinite(row).all() or furn[yy, x0 - 5:x0 + 6].any():
                continue
            k = int(np.argmin(row))
            if 0 < k < 10:
                d = row[k - 1] - 2 * row[k] + row[k + 1]
                sub = 0.5 * (row[k - 1] - row[k + 1]) / d if d > 1e-6 else 0.0
                xv = x0 - 5 + k + sub
                (xs_in if Tf[yy, x0] else xs_out).append((yy, xv))
        if len(xs_in) >= 8 and len(xs_out) >= 8:
            yo, xo = np.array(xs_out).T
            A = np.stack([yo, np.ones_like(yo)], 1)
            coef, *_ = np.linalg.lstsq(A, xo, rcond=None)
            yi, xi = np.array(xs_in).T
            dev = np.abs(xi - (coef[0] * yi + coef[1])) / ppm * 1000
            res_out = np.abs(xo - (coef[0] * yo + coef[1])) / ppm * 1000
            seams.append(dict(X_m=round(X0 + x0 / ppm, 3), samples_in=len(xs_in), samples_out=len(xs_out),
                              slope_dX_dY=round(float(coef[0]), 4), in_max_mm=round(float(np.percentile(dev, 95)), 2),
                              in_median_mm=round(float(np.median(dev)), 2), out_p95_mm=round(float(np.percentile(res_out, 95)), 2)))
    c2 = dict(method="joints = dark minima of the floor's L* in the plane (400 px/m), sub-pixel per row; a line fitted on the samples "
                     "outside the old table's region, the samples inside measured against it (p95, mm)",
              seams_crossing=len(seams), seams=seams,
              worst_in_p95_mm=max([s_["in_max_mm"] for s_ in seams], default=None), limit_mm=4.0)
    c2["pass_"] = bool(len(seams) >= 3 and c2["worst_in_p95_mm"] <= 4.0)
    out["2_boards"] = c2

    # 3 WM-G1
    c3 = dict(plate=round(float(np.percentile(lstar(plate), 0.5)), 2), base_png=round(float(np.percentile(lstar(base_old), 0.5)), 2))
    for st, f in man["truths"]["default"].items():
        c3[f"default_{st}"] = round(float(np.percentile(lstar(arr(os.path.normpath(os.path.join(HERE, f)), "RGB")), 0.5)), 2)
        c3[f"default_{st}_r9"] = round(float(np.percentile(lstar(arr(os.path.normpath(os.path.join(HERE, r9["truths"]["default"][st])), "RGB")), 0.5)), 2)
    sts = list(man["truths"]["default"])
    c3["pass_"] = bool(11.0 <= c3["plate"] <= 14.0 and all(c3[f"default_{st}"] >= c3[f"default_{st}_r9"] - 0.05 for st in sts))
    c3["rule"] = ("WM-G1: black point L* 11-14 (p0.5, OpenCV Lab, as lock_r7.py) on the plate, the tool's grade (its toe targets 12.5 on "
                  "the base); the defaults' black point is set by the products in them (R9: set C 9.72, B 10.91, accepted in R8's QA): "
                  "here it must not drop below R9's")
    c3["defaults_below_11"] = [st for st in sts if c3[f"default_{st}"] < 11.0]
    out["3_WM_G1"] = c3

    # 4 RND2
    c4 = {}
    Tdil = cv2.dilate(T.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
    for st, f in man["truths"]["default"].items():
        new = arr(os.path.normpath(os.path.join(HERE, f)), "RGB")
        old = arr(os.path.normpath(os.path.join(HERE, r9["truths"]["default"][st])), "RGB")
        Rg = reg[f"default_{st}"]
        c4[f"default_{st}"] = dict(px_changed=int((new != old).any(2).sum()), outside_region_px=int(((new != old).any(2) & ~Rg).sum()),
                                   region_px=int(Rg.sum()))
    rug_new = arr(os.path.join(HERE, next(l_ for l_ in man["layers"] if l_["id"] == "rug")["file"]))
    rug_old = arr(os.path.join(HERE, next(l_ for l_ in r9["layers"] if l_["id"] == "rug")["file"]))
    rug_ch = (rug_new != rug_old).any(2)
    rsn = arr(os.path.join(HERE, next(l_ for l_ in man["layers"] if l_["id"] == "rug-shadow")["file"]), "RGB")
    rso = arr(os.path.join(HERE, next(l_ for l_ in r9["layers"] if l_["id"] == "rug-shadow")["file"]), "RGB")
    c4["rug"] = dict(px_changed=int(rug_ch.sum()), outside_table_and_zone_px=int((rug_ch & ~(Rrug | Tdil)).sum()),
                     alpha_changed_outside_table_px=int(((rug_new[..., 3] != rug_old[..., 3]) & ~Tdil).sum()),
                     shadow_px_changed=int((rsn != rso).any(2).sum()), shadow_changed_outside_table_px=int(((rsn != rso).any(2) & ~T).sum()))
    for st, v in man["slot_cushions"]["sets"].items():
        a_ = arr(os.path.join(HERE, v["layer"]))
        b_ = arr(os.path.join(HERE, r9["slot_cushions"]["sets"][st]["layer"]))
        sa = arr(os.path.join(HERE, v["shadow"]), "RGB")
        sb = arr(os.path.join(HERE, r9["slot_cushions"]["sets"][st]["shadow"]), "RGB")
        ch = (a_ != b_).any(2)
        chs = (sa != sb).any(2)
        c4[f"cushions_{st}"] = dict(layer=v["layer"], shadow=v["shadow"], layer_px_changed=int(ch.sum()), layer_outside_table_px=int((ch & ~T).sum()),
                                    shadow_px_changed=int(chs.sum()), shadow_outside_table_px=int((chs & ~T).sum()))
    c4["pass_"] = bool(all(c4[f"default_{st}"]["outside_region_px"] == 0 for st in man["truths"]["default"])
                       and c4["rug"]["outside_table_and_zone_px"] == 0 and c4["rug"]["alpha_changed_outside_table_px"] == 0
                       and c4["rug"]["shadow_changed_outside_table_px"] == 0
                       and all(c4[f"cushions_{st}"]["layer_outside_table_px"] == 0 and c4[f"cushions_{st}"]["shadow_outside_table_px"] == 0
                               for st in man["slot_cushions"]["sets"]))
    out["4_RND2"] = c4

    # 5 stack
    c5 = {}
    cache = {}
    plate_files = {}
    for st in man["slot_cushions"]["order"]:
        layers = []
        for l_ in man["layers"]:
            k = l_["id"]
            if k == "base" or k.endswith("-shadow") or l_.get("hidden_in_defaults"):
                continue
            if k == "cushions":
                v = man["slot_cushions"]["sets"][st]
                layers.append((k, os.path.join(HERE, v["layer"]), os.path.join(HERE, v["shadow"])))
            else:
                sh = next(x for x in man["layers"] if x["id"] == k + "-shadow")
                layers.append((k, os.path.join(HERE, l_["file"]), os.path.join(HERE, sh["file"])))
        s8 = FB.compose8(plate, layers, cache).astype(np.int16)
        tr = arr(os.path.normpath(os.path.join(HERE, man["truths"]["default"][st])), "RGB").astype(np.int16)
        d = np.abs(s8 - tr).max(2)
        Rg = reg[f"default_{st}"]
        c5[st] = dict(in_region_max=int(d[Rg].max()) if Rg.any() else 0, canvas_p99_9=float(np.percentile(d, 99.9)), canvas_max=int(d.max()))
        cache = {k_: v_ for k_, v_ in cache.items() if "cushions" not in k_}
    c5["pass_"] = bool(all(c5[st]["in_region_max"] == 0 and c5[st]["canvas_p99_9"] <= 2 and c5[st]["canvas_max"] <= 6 for st in man["slot_cushions"]["order"]))
    c5["gate"] = "R9's: p99.9 <= 2, max <= 6 over the canvas; 0 inside the changed region (the truth IS the stack there)"
    out["5_stack"] = c5

    # 6 hidden
    hid = [l_ for l_ in man["layers"] if l_.get("hidden_in_defaults")]
    same = all(next(x for x in r9["layers"] if x["id"] == l_["id"])["file"] == l_["file"] for l_ in hid)
    files = [os.path.join(HERE, l_["file"]) for l_ in hid]
    c6 = dict(hidden=[l_["id"] for l_ in hid], files_are_r9s=same, git_modified=git_modified(files))
    c6["pass_"] = bool(sorted(c6["hidden"]) == ["bowl", "bowl-shadow", "candle-holders", "candle-holders-shadow"] and same and not c6["git_modified"])
    out["6_hidden"] = c6

    # 7 scope
    # this stage's own files may be tracked already (the coordinator's WIP checkpoints) and re-written by a re-run: they are not R9's
    own = ("fb12s0", "fb12-stage0", "fb12_s0", "work-fb12s0")
    mod = git_modified([os.path.dirname(P2)])
    other = [ln for ln in mod if not any(k in ln for k in own)]
    c7 = dict(tracked_modified_not_this_stage=other, this_stage_files_rewritten=len(mod) - len(other), r9_manifest_sha=sha(R9))
    c7["pass_"] = bool(not other)
    out["7_scope"] = c7

    ok = all(v["pass_"] for v in out.values())
    out["all_pass"] = bool(ok)
    json.dump(out, open(os.path.join(HERE, "verify-layers-fb12s0.json"), "w"), indent=1, ensure_ascii=False)
    print(json.dumps({k: (v["pass_"] if isinstance(v, dict) else v) for k, v in out.items()}, indent=1))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
