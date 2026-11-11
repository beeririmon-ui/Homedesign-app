#!/usr/bin/env python3
"""
qa-agent 2026-11-11, box check of render-agent's R4 code fixes (warm-modern living-room tool, phase 2). QA's own code: nothing imported
from render-agent; from the manifests only the file names, the compose order and the blend of each layer are read.

  1. Files: which layer / shadow files differ between manifest-r3.json and manifest-r4.json (sha256), and that every other file is the
     same file; base.png against the approved phase-1 v3c base (bytes).
  2. Recomposite base + 12 products + cushion set X against graded/default-scene-r4-set-X-graded-v3c.png, X = A, B, C, three paths:
       P1  manifest formula, one rounding per product: round(below*sh/255*(1-a) + rgb*a)
       P2  two 8-bit passes: m = round(below*sh/255); out = round(m*(1-a) + rgb*a)
       P4  browser / gl.ts: premultiplied ImageBitmap, multiply = round(src*dst/255), normal = round(src_pm + dst*(1-a/255))
     gate: p99.9 <= 2 and max <= 6 (worst channel, 8-bit levels).
  3. Swap-diff: every product off with all others on (sets A, B, C), and the three set swaps with all 12 products on.
  4. r4 against r3, per set: the changed pixels of the scene, and how many lie outside the five fixed products' regions
     (region = alpha > 0 or any shadow channel < 255, the union of the r3 and the r4 files of that product). Also with a tight
     definition (the r4 region only, and the r3 region only), and per product.
  5. The five layers r4 against r3, file by file: alpha changed, RGB changed under alpha > 0, shadow changed; their bounding boxes and
     where they fall (the floor lamp: inside the shade rows only? the pendant: above row 62 only? ...).
Writes data/integrity.json.   ~/.venvs/motion/bin/python -I r4_integrity.py
"""
import hashlib
import json
import os

import numpy as np
from PIL import Image

REPO = "/home/user/homedesign-app"
P2 = os.path.join(REPO, "assets/renders/living-room/warm-modern/phase2-2026-11-10")
P1 = os.path.join(REPO, "assets/renders/living-room/warm-modern/pilot-phase1-2026-11-07")
OUT = os.path.join(REPO, "qa/reports/2026-11-11-wm-tool-phase2-r4")
LD = os.path.join(P2, "layers")
FIVE = ["floor-lamp", "vase", "planter", "basket", "pendant"]


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def u8(p):
    return np.asarray(Image.open(p))


m3 = json.load(open(os.path.join(LD, "manifest-r3.json")))
m4 = json.load(open(os.path.join(LD, "manifest-r4.json")))
order = m4["compose"]["order"]
assert order == m3["compose"]["order"]
b3 = {l_["id"]: l_ for l_ in m3["layers"]}
b4 = {l_["id"]: l_ for l_ in m4["layers"]}
products = [i for i in order if i != "base" and not i.endswith("-shadow")]
res = {"manifest_r3": "layers/manifest-r3.json", "manifest_r4": "layers/manifest-r4.json"}

# ---------------------------------------------------------------- 1. files
files = {}
for i in order:
    if i == "cushions" or i == "cushions-shadow":
        continue
    f3, f4 = b3[i]["file"], b4[i]["file"]
    s3, s4 = sha(os.path.join(LD, f3)), sha(os.path.join(LD, f4))
    files[i] = dict(r3=f3, r4=f4, same_name=f3 == f4, same_bytes=s3 == s4)
for s in "ABC":
    for kind in ("layer", "shadow"):
        f3, f4 = m3["slot_cushions"]["sets"][s][kind], m4["slot_cushions"]["sets"][s][kind]
        files[f"cushions {s} {kind}"] = dict(r3=f3, r4=f4, same_bytes=sha(os.path.join(LD, f3)) == sha(os.path.join(LD, f4)))
res["files"] = files
res["files_changed"] = sorted(k for k, v in files.items() if not v["same_bytes"])
res["base_same_bytes_as_approved"] = sha(os.path.join(LD, "base.png")) == sha(os.path.join(P1, "layers-v3c/base.png"))
print("changed files:", res["files_changed"], "base ok:", res["base_same_bytes_as_approved"])

# ---------------------------------------------------------------- load (uint8)
base = u8(os.path.join(LD, "base.png"))[..., :3]
H, W = base.shape[:2]


def load_set(man, byid):
    lay, shd = {}, {}
    for pid in products:
        if pid == "cushions":
            continue
        lay[pid] = u8(os.path.join(LD, byid[pid]["file"]))
        shd[pid] = u8(os.path.join(LD, byid[pid + "-shadow"]["file"]))[..., :3]
    for s in "ABC":
        lay["set-" + s] = u8(os.path.join(LD, man["slot_cushions"]["sets"][s]["layer"]))
        shd["set-" + s] = u8(os.path.join(LD, man["slot_cushions"]["sets"][s]["shadow"]))[..., :3]
    return lay, shd


lay, shd = load_set(m4, b4)


def region_of(L, S):
    return (L[..., 3] > 0) | (S.min(2) < 255)


reg4 = {k: region_of(lay[k], shd[k]) for k in lay}


def stack(s, skip=(), path="P1", L=None, S=None):
    L = L or lay
    S = S or shd
    out = base.astype(np.float32)
    for pid in products:
        k = "set-" + s if pid == "cushions" else pid
        if k in skip or pid in skip:
            continue
        rgb = L[k][..., :3].astype(np.float32)
        a = L[k][..., 3:4].astype(np.float32) / 255.0
        sh = S[k].astype(np.float32)
        if path == "P1":
            out = np.floor(out * sh / 255.0 * (1 - a) + rgb * a + 0.5)
        elif path == "P2":
            m = np.floor(out * sh / 255.0 + 0.5)
            out = np.floor(m * (1 - a) + rgb * a + 0.5)
        else:
            pm = np.floor(rgb * a + 0.5)
            m = np.floor(sh * out / 255.0 + 0.5)
            out = np.floor(pm + m * (1 - a) + 0.5)
        out = np.clip(out, 0, 255)
    return out


# ---------------------------------------------------------------- 2. recomposite
rec, comps = {}, {}
for s in "ABC":
    G = u8(os.path.join(P2, f"graded/default-scene-r4-set-{s}-graded-v3c.png"))[..., :3].astype(np.float32)
    reg = np.zeros((H, W), bool)
    for k in lay:
        if k.startswith("set-") and k != "set-" + s:
            continue
        reg |= reg4[k]
    rec[s] = {}
    for path in ("P1", "P2", "P4"):
        c = stack(s, path=path)
        if path == "P1":
            comps[s] = c
        d = np.abs(c - G).max(2)
        r = dict(p999_region=float(np.percentile(d[reg], 99.9)), p999_canvas=float(np.percentile(d, 99.9)), max=float(d.max()),
                 max_at=[int(v) for v in np.unravel_index(int(d.argmax()), d.shape)[::-1]], px_gt0=int((d > 0).sum()),
                 px_gt2=int((d > 2).sum()), px_gt4=int((d > 4).sum()), px_gt6=int((d > 6).sum()), outside_region_gt0=int(((d > 0) & ~reg).sum()))
        own = {}
        for k in lay:
            if k.startswith("set-") and k != "set-" + s:
                continue
            n = int(((d > 2) & reg4[k]).sum())
            if n:
                own[k] = n
        r["gt2_by_layer"] = own
        own5 = {k: dict(p999=float(np.percentile(d[reg4[k]], 99.9)), max=float(d[reg4[k]].max())) for k in FIVE}
        r["five_products"] = own5
        rec[s][path] = r
    print("recomposite", s, {p: (rec[s][p]["p999_region"], rec[s][p]["max"], rec[s][p]["px_gt2"]) for p in rec[s]})
res["recomposite"] = rec
res["recomposite_pass"] = all(rec[s][p]["p999_region"] <= 2 and rec[s][p]["max"] <= 6 for s in "ABC" for p in rec[s])

# ---------------------------------------------------------------- 3. swap-diff
sw = {}
for s in "ABC":
    full = comps[s]
    for pid in products:
        k = "set-" + s if pid == "cushions" else pid
        c = stack(s, skip=(pid,))
        ch = np.abs(c - full).max(2) > 0
        sw[f"{pid} [set {s}]"] = dict(changed=int(ch.sum()), changed_outside_region=int((ch & ~reg4[k]).sum()))
for x, y in (("A", "B"), ("A", "C"), ("B", "C")):
    ch = np.abs(comps[x] - comps[y]).max(2) > 0
    u = reg4["set-" + x] | reg4["set-" + y]
    sw[f"cushions {x}<->{y}"] = dict(changed=int(ch.sum()), changed_outside_union=int((ch & ~u).sum()))
res["swap_diff"] = sw
res["swap_diff_outside_total"] = int(sum(v.get("changed_outside_region", v.get("changed_outside_union", 0)) for v in sw.values()))
print("swap outside total", res["swap_diff_outside_total"], "toggles", len(sw))

# ---------------------------------------------------------------- 4. r4 vs r3 scenes
lay3, shd3 = load_set(m3, b3)
reg3 = {k: region_of(lay3[k], shd3[k]) for k in FIVE}
five_u = np.zeros((H, W), bool)
five_4 = np.zeros((H, W), bool)
five_3 = np.zeros((H, W), bool)
for k in FIVE:
    five_u |= reg3[k] | reg4[k]
    five_4 |= reg4[k]
    five_3 |= reg3[k]
vs = {}
for s in "ABC":
    G3 = u8(os.path.join(P2, f"graded/default-scene-r3-set-{s}-graded-v3c.png"))[..., :3].astype(np.int16)
    G4 = u8(os.path.join(P2, f"graded/default-scene-r4-set-{s}-graded-v3c.png"))[..., :3].astype(np.int16)
    d = np.abs(G4 - G3).max(2)
    ch = d > 0
    per = {}
    for k in FIVE:
        rk = reg3[k] | reg4[k]
        per[k] = dict(changed_px=int((ch & rk).sum()), max_level=int(d[rk].max()), region_union_px=int(rk.sum()))
    ys, xs = np.nonzero(ch)
    vs[s] = dict(changed_px=int(ch.sum()), changed_outside_five_union=int((ch & ~five_u).sum()),
                 changed_outside_five_r4_only=int((ch & ~five_4).sum()), changed_outside_five_r3_only=int((ch & ~five_3).sum()),
                 five_union_px=int(five_u.sum()), per_product=per, changed_in_two_products=int(sum(
                     ((ch & (reg3[a] | reg4[a]) & (reg3[b] | reg4[b])).sum()) for i, a in enumerate(FIVE) for b in FIVE[i + 1:])))
    print("r4 vs r3", s, vs[s]["changed_px"], vs[s]["changed_outside_five_union"])
res["r4_vs_r3_scenes"] = vs

# ---------------------------------------------------------------- 5. the five layer files, r4 vs r3
lf = {}
for k in FIVE:
    A3, A4 = lay3[k][..., 3].astype(np.int16), lay[k][..., 3].astype(np.int16)
    C3, C4 = lay3[k][..., :3].astype(np.int16), lay[k][..., :3].astype(np.int16)
    S3, S4 = shd3[k].astype(np.int16), shd[k].astype(np.int16)
    da = A4 != A3
    drgb = (np.abs(C4 - C3).max(2) > 0) & ((A4 > 0) | (A3 > 0))
    dsh = np.abs(S4 - S3).max(2) > 0

    def box(m):
        if not m.any():
            return None
        ys, xs = np.nonzero(m)
        return [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1]
    r = dict(alpha_changed_px=int(da.sum()), alpha_changed_box=box(da), rgb_changed_under_alpha_px=int(drgb.sum()), rgb_changed_box=box(drgb),
             shadow_changed_px=int(dsh.sum()), shadow_changed_box=box(dsh), alpha_px_r3=int((A3 > 0).sum()), alpha_px_r4=int((A4 > 0).sum()),
             alpha_sum_r3=round(float(A3.sum()) / 255, 1), alpha_sum_r4=round(float(A4.sum()) / 255, 1),
             shadow_dark_px_r3=int((S3.min(2) < 255).sum()), shadow_dark_px_r4=int((S4.min(2) < 255).sum()))
    if k == "floor-lamp":
        rows = np.zeros((H, W), bool)
        rows[574:706] = True     # the shade's rows (576-702 in QA's checkpoint mask) +- 2-3 px
        r["changed_outside_shade_rows_px"] = int(((da | drgb | dsh) & ~rows).sum())
        r["alpha_changed_px_note"] = "the alpha is expected unchanged"
    if k == "pendant":
        r["changed_below_row_62_px"] = int(((da | drgb | dsh)[62:]).sum())
    lf[k] = r
    print("layer", k, r)
res["five_layers_r4_vs_r3"] = lf
json.dump(res, open(os.path.join(OUT, "data/integrity.json"), "w"), indent=1)
print("written")
