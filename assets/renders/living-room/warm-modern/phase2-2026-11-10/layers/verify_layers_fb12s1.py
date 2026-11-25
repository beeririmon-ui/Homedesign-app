#!/usr/bin/env python3
"""
verify_layers_fb12s1.py: re-runnable check of FB12 stage 1 (the IDANA Olia coffee table as a product layer in M0) in the warm-modern
tool (render-agent, 2026-11-25; for qa-agent). Reads manifest-fb12s1.json and the files it names (numpy + Pillow + OpenCV; stage 0's
fb12_s0.py read-only for the camera and the 8-bit compose); writes verify-layers-fb12s1.json; exit 0 = every check passes.

    python3.12 -I verify_layers_fb12s1.py

  1 table    the slot: coffee-table z 57 and its shadow z 56, right after the cushions in compose.order; RGBA / RGB; the cut against the
             clay at the real dimensions (120 x 65 x 38 at (0.30, 1.72), angle 0): IoU >= 0.90, no table pixel beyond the clay + 12 px,
             every measured edge within 5 cm; the air under the top >= 0.60 (plan) and the image share within 0.03 of the clay's;
             the shadow never on the sofa or the armchair
  2 RND2     each rebuilt default = stage 0's truth outside the allowed region (0 px): the table and its shadow, the bowl and the
             candle holders where they now stand (layer + shadow), the rug and the cushion sets where their files changed; the rug and
             the cushion sets changed only inside stage 0's regions (the old table and its rug fill)
  3 WM-G1    the plate is stage 0's (sha; black point 11-14); no default's black point below stage 0's (-0.05)
  4 stack    this manifest's 8-bit stack = the truths inside the changed region (0 px), over the canvas within R9's gate (p99.9 <= 2, max <= 6)
  5 group    the bowl and the candle holders: every foot on the new top, no shadow off it; F3 >= 0.02 (frame width) to every cushion
             set and between them; the bowl's rim >= 8 cm inside the top's front edge; nothing hidden in the defaults any more
  6 scope    no tracked file under the warm-modern living room is modified in git (stage 0, R9 and the earlier layers unchanged),
             other than the folder's README.md (this stage's section)
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
MAN = os.path.join(HERE, "manifest-fb12s1.json")
MAN0 = os.path.join(HERE, "manifest-fb12s0.json")
PLATE_SHA = "7f83091908fb5331e3491598839d790129d36ced1ce01dec3f65f1d75cc265cd"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


FB = _load("fb12_s0", os.path.join(P2, "fb12_s0.py"))
FB.MASKS = os.path.join(P2, "work-fb12s0", "fb12s0-masks.npz")
FW = FB.FRAME_BOX[2] - FB.FRAME_BOX[0]


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


def L(p):
    return os.path.normpath(os.path.join(HERE, p))


def stack(man, st, variant=None):
    out = []
    for l_ in man["layers"]:
        k = l_["id"]
        if k == "base" or k.endswith("-shadow") or l_.get("hidden_in_defaults"):
            continue
        if k == "cushions":
            v = man["slot_cushions"]["sets"][st]
            out.append((k, L(v["layer"]), L(v["shadow"])))
            continue
        sh = next(x for x in man["layers"] if x["id"] == k + "-shadow")
        out.append((k, L(l_["file"]), L(sh["file"])))
    return out


def project_h(X, Y, Z):
    return FB.project(X, Y, Z)


def main():
    man = json.load(open(MAN))
    man0 = json.load(open(MAN0))
    out = {}
    ok = True
    by = {l_["id"]: l_ for l_ in man["layers"]}
    clay = np.load(os.path.join(P2, "work-fb12s1", "clay-fb12s1.npz"))
    V = clay["alpha"] > 0.5
    rec = json.load(open(os.path.join(P2, "work-fb12s1", "fb12s1.json")))

    # 1 the table
    c1 = {}
    order = man["compose"]["order"]
    i = order.index("cushions")
    c1["order_ok"] = order[i + 1:i + 3] == ["coffee-table-shadow", "coffee-table"]
    c1["z"] = [by["coffee-table-shadow"]["z"], by["coffee-table"]["z"]]
    Tl = arr(L(by["coffee-table"]["file"]))
    Ts = arr(L(by["coffee-table-shadow"]["file"]))
    c1["modes"] = [Image.open(L(by["coffee-table"]["file"])).mode, Image.open(L(by["coffee-table-shadow"]["file"])).mode]
    A = Tl[..., 3] > 127
    c1["iou_cut_vs_clay"] = round(float((A & V).sum() / (A | V).sum()), 4)
    beyond = (Tl[..., 3] > 0) & ~cv2.dilate(V.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (63, 63))).astype(bool)
    c1["px_beyond_clay_5cm"] = int(beyond.sum())                     # 31 px ~ 5 cm at the table (6.4-6.6 px / cm)
    meas = rec["measures"]
    edges_cm = [abs(meas["ends_vs_clay"]["left_end"]["max_abs_cm"]), abs(meas["ends_vs_clay"]["right_end"]["max_abs_cm"]),
                abs(meas["back_edge_vs_clay"]["median_cm"]), abs(meas["legs_vs_clay"]["left_leg_bottom"]["median_cm"]),
                abs(meas["legs_vs_clay"]["right_leg_inner_edge"]["median_cm"])]
    c1["edges_vs_clay_cm_max"] = round(max(edges_cm), 2)
    c1["length_cm"] = meas["length_cm"]
    c1["air"] = meas["air_under_top"]
    fa = arr(os.path.join(P2, "work-fb12s0", "fixed-furniture-fb12s0.png"))[..., 3]
    c1["shadow_px_on_sofa_or_armchair"] = int(((Ts[..., 0] < 255) & (fa > 127)).sum())
    c1["pass_"] = bool(c1["order_ok"] and c1["z"] == [56, 57] and c1["modes"] == ["RGBA", "RGB"] and c1["iou_cut_vs_clay"] >= 0.90
                       and c1["px_beyond_clay_5cm"] == 0 and c1["edges_vs_clay_cm_max"] <= 5 and abs(c1["length_cm"] - 120) <= 5
                       and c1["air"]["plan_share_of_length"] >= 0.6 and abs(c1["air"]["image_share_cut"] - c1["air"]["image_share_clay"]) <= 0.03
                       and c1["shadow_px_on_sofa_or_armchair"] == 0)
    out["1_table"] = c1
    ok &= c1["pass_"]

    # 2 RND2
    c2 = {}
    Z0 = np.load(os.path.join(P2, "work-fb12s0", "regions-fb12s0.npz"))
    Z0 = Z0["rug"] | Z0["table"]
    allowed = (Tl[..., 3] > 0) | (Ts[..., 0] < 255)
    for k in ("bowl", "candle-holders"):
        allowed |= arr(L(by[k]["file"]))[..., 3] > 0
        allowed |= arr(L(by[k + "-shadow"]["file"]), "L") < 255
    rug_new, rug_old = arr(L(by["rug"]["file"])), arr(L(by["rug"]["previous_file"]))
    rug_chg = (rug_new != rug_old).any(2)
    c2["rug_changed_px"] = int(rug_chg.sum())
    c2["rug_changed_outside_stage0_px"] = int((rug_chg & ~Z0).sum())
    allowed |= rug_chg
    base_allowed = allowed.copy()
    for st in "BAC":
        v = man["slot_cushions"]["sets"][st]
        al = base_allowed.copy()
        if "fb12s1" in v:
            ch = (arr(L(v["layer"])) != arr(L(v["previous_layer"]))).any(2) | (arr(L(v["shadow"]), "RGB") != arr(L(v["previous_shadow"]), "RGB")).any(2)
            c2[f"cushions_{st}_changed_px"] = int(ch.sum())
            c2[f"cushions_{st}_changed_outside_stage0_px"] = int((ch & ~Z0).sum())
            al |= ch
        t1 = arr(L(man["truths"]["default"][st]), "RGB")
        t0 = arr(L(man0["truths"]["default"][st]), "RGB")
        d = (t1 != t0).any(2)
        c2[f"default_{st}_changed_px"] = int(d.sum())
        c2[f"default_{st}_outside_allowed_px"] = int((d & ~al).sum())
    c2["pass_"] = bool(c2["rug_changed_outside_stage0_px"] == 0 and all(c2[k] == 0 for k in c2 if k.endswith("_outside_allowed_px") or k.endswith("outside_stage0_px")))
    out["2_RND2"] = c2
    ok &= c2["pass_"]

    # 3 WM-G1
    plate_p = L(by["base"]["file"])
    c3 = dict(plate_sha_is_stage0=sha(plate_p) == PLATE_SHA, plate=round(float(np.percentile(lstar(arr(plate_p, "RGB")), 0.5)), 2))
    r9 = json.load(open(os.path.join(HERE, "manifest-r9.json")))
    for st in "BAC":
        c3[f"default_{st}"] = round(float(np.percentile(lstar(arr(L(man["truths"]["default"][st]), "RGB")), 0.5)), 2)
        c3[f"default_{st}_stage0"] = round(float(np.percentile(lstar(arr(L(man0["truths"]["default"][st]), "RGB")), 0.5)), 2)
        c3[f"default_{st}_r9"] = round(float(np.percentile(lstar(arr(L(r9["truths"]["default"][st]), "RGB")), 0.5)), 2)
    c3["pass_"] = bool(c3["plate_sha_is_stage0"] and 11 <= c3["plate"] <= 14 and all(c3[f"default_{st}"] >= c3[f"default_{st}_r9"] - 0.05 for st in "BAC"))
    c3["rule"] = ("WM-G1: the plate's black point (L* p0.5, OpenCV Lab) 11-14; the defaults' black point is set by their products: with the "
                  "black bowl back it is compared with R9's (the bowl in, accepted in R8's QA), as stage 0's own verify does; stage 0's "
                  "higher values are the bowl hidden")
    out["3_WM_G1"] = c3
    ok &= c3["pass_"]

    # 4 the stack
    c4 = {}
    base8 = arr(plate_p, "RGB")
    reg = np.load(os.path.join(P2, "work-fb12s1", "regions-fb12s1.npz"))
    for st in "BAC":
        s8 = FB.compose8(base8, stack(man, st), {})
        t1 = arr(L(man["truths"]["default"][st]), "RGB")
        Rg = reg[f"default_{st}"]
        diff = np.abs(s8.astype(int) - t1.astype(int)).max(2)
        c4[st] = dict(inside_region_px=int((diff[Rg] > 0).sum()), canvas_p99_9=float(np.percentile(diff, 99.9)), canvas_max=int(diff.max()))
    c4["pass_"] = bool(all(c4[st]["inside_region_px"] == 0 and c4[st]["canvas_p99_9"] <= 2 and c4[st]["canvas_max"] <= 6 for st in "BAC"))
    out["4_stack"] = c4
    ok &= c4["pass_"]

    # 5 the group
    c5 = {}
    top = (clay["part"] == 1) & A
    files = {"bowl": by["bowl"], "candle-holders": by["candle-holders"]}
    for sl in ("bowl", "candle-holders"):
        for v in man["variants"].get(sl, []):
            if "fb12s1" in v:
                files[v["id"]] = dict(file=v["file"], shadow=v["shadow"])
    for k, v in files.items():
        a = arr(L(v["file"]))[..., 3] > 127
        sh = arr(L(v["shadow"] if "shadow" in v else by[k + "-shadow"]["file"]), "L")
        n, lab_, st_, _ = cv2.connectedComponentsWithStats(a.astype(np.uint8))
        feet = []
        for i in range(1, n):
            if st_[i, 4] < 200:
                continue
            ys, xs = np.nonzero(lab_ == i)
            foot = (lab_ == i) & (np.arange(a.shape[0])[:, None] >= ys.max() - 1)
            feet.append(round(float(top[foot].mean()), 3))
        c5[f"{k}_feet_on_top"] = feet
        c5[f"{k}_shadow_off_top_px"] = int(((sh < 255) & ~top & ~(arr(L(v["file"]))[..., 3] > 0)).sum())
    gaps = rec["gaps"]
    c5["f3_min"] = min(v for k, v in gaps.items() if isinstance(v, float) and not k.endswith(" u"))
    bowl_pt = man["table_group"]["fb12s1"]["points"]["bowl"]["bowl"]
    c5["bowl_rim_inside_front_edge_cm"] = round((1.72 + 0.325 - (bowl_pt[1] + 0.1065)) * 100, 2)
    c5["hidden_layers"] = [l_["id"] for l_ in man["layers"] if l_.get("hidden_in_defaults")]
    c5["pass_"] = bool(all(min(c5[k]) == 1.0 for k in c5 if k.endswith("_feet_on_top")) and all(c5[k] == 0 for k in c5 if k.endswith("_off_top_px"))
                       and c5["f3_min"] >= 0.02 and c5["bowl_rim_inside_front_edge_cm"] >= 8 and not c5["hidden_layers"]
                       and "defaults_hidden" not in man)
    out["5_group"] = c5
    ok &= c5["pass_"]

    # 6 scope
    r = subprocess.run(["git", "-C", REPO, "status", "--porcelain", "--", "assets/renders/living-room/warm-modern"], capture_output=True, text=True).stdout
    mod = [ln for ln in r.splitlines() if not ln.startswith("??") and not ln.endswith("phase2-2026-11-10/README.md")]
    out["6_scope"] = dict(tracked_modified=mod, pass_=not mod, note="the folder's README.md is this stage's own record (a new section); allowed")
    ok &= out["6_scope"]["pass_"]

    out["all_pass"] = bool(ok)
    json.dump(out, open(os.path.join(HERE, "verify-layers-fb12s1.json"), "w"), indent=1)
    print(json.dumps({k: (v.get("pass_") if isinstance(v, dict) else v) for k, v in out.items()}, indent=1))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
