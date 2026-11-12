#!/usr/bin/env python3
"""
qa-agent 2026-11-12 (R8): the scope, per pixel. QA's own code; from render-agent only the manifests' file names and compose order.
  1. Every default layer and shadow, every cushion set, every variant layer and shadow: manifest-r7 vs manifest-r8, sha256 and,
     where the bytes differ, the per-pixel change (RGB under alpha, alpha, shadow), its bbox and its max.
  2. The ungraded sources: work-r7/<kind>/<k>.png vs work-r8/<kind>/<k>.png for every file R8 wrote (and the R7 files R8 claims to
     byte-copy).
  3. The composites: default-scene-r7 vs -r8 (sets A, B, C) and the ten variant truths r7 vs r8 (set B): changed pixels and changed
     pixels outside the union of the regions (alpha > 0 or shadow < 255, in R7 or R8) of the products whose files changed in that
     scene (the scene's curtain option and its candle-holders option).
  4. Where each changed product changed (zones named by the fixes): the holders' mark box, the curtains' bench zone, curtain 3 as a whole.
Writes data/scope.json.     ~/.venvs/motion/bin/python3.12 -I r8_scope.py
"""
import hashlib
import json
import os

import numpy as np
from PIL import Image

REPO = "/home/user/homedesign-app"
P2 = os.path.join(REPO, "assets/renders/living-room/warm-modern/phase2-2026-11-10")
LD = os.path.join(P2, "layers")
OUT = os.path.join(REPO, "qa/reports/2026-11-12-wm-phase2-r8")


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def u8(p):
    return np.asarray(Image.open(p))


def box(m):
    if not m.any():
        return None
    ys, xs = np.nonzero(m)
    return [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]


m7 = json.load(open(os.path.join(LD, "manifest-r7.json")))
m8 = json.load(open(os.path.join(LD, "manifest-r8.json")))
assert m7["compose"]["order"] == m8["compose"]["order"]
b7 = {l_["id"]: l_ for l_ in m7["layers"]}
b8 = {l_["id"]: l_ for l_ in m8["layers"]}
V7 = {v["id"]: v for vs in m7["variants"].values() for v in vs}
V8 = {v["id"]: v for vs in m8["variants"].values() for v in vs}
res = {}

# ------------------------------------------------------------------ 1. the files the tool reads
pairs = {}
for i in m8["compose"]["order"]:
    if i in ("cushions", "cushions-shadow"):
        continue
    pairs[i] = (b7[i]["file"], b8[i]["file"])
for s in "ABC":
    for kind in ("layer", "shadow"):
        pairs[f"cushions-{s} {kind}"] = (m7["slot_cushions"]["sets"][s][kind], m8["slot_cushions"]["sets"][s][kind])
assert set(V7) == set(V8), (set(V7) ^ set(V8))
for vid in V8:
    pairs[f"{vid} layer"] = (V7[vid]["file"], V8[vid]["file"])
    pairs[f"{vid} shadow"] = (V7[vid]["shadow"], V8[vid]["shadow"])
files = {}
for k, (f7, f8) in pairs.items():
    p7, p8 = os.path.join(LD, f7), os.path.join(LD, f8)
    rec = dict(r7=f7, r8=f8, same_path=f7 == f8, same_bytes=sha(p7) == sha(p8))
    if not rec["same_bytes"]:
        A7, A8 = u8(p7), u8(p8)
        if A7.ndim == 2:
            A7, A8 = A7[..., None], A8[..., None]
        if A7.shape[-1] == 4:
            a7, a8 = A7[..., 3].astype(int), A8[..., 3].astype(int)
            d = np.abs(A7[..., :3].astype(int) - A8[..., :3].astype(int)).max(2)
            under = (a7 > 0) | (a8 > 0)
            rec.update(kind="RGBA", alpha_changed_px=int((a7 != a8).sum()), alpha_changed_box=box(a7 != a8),
                       rgb_changed_under_alpha_px=int(((d > 0) & under).sum()), rgb_changed_box=box((d > 0) & under),
                       rgb_max_change=int(d[under].max()) if under.any() else 0,
                       rgb_changed_at_alpha255_px=int(((d > 0) & (a7 == 255) & (a8 == 255)).sum()),
                       rgb_max_change_at_alpha255=int(d[(a7 == 255) & (a8 == 255)].max()),
                       rgb_changed_where_alpha0_both_px=int(((d > 0) & ~under).sum()))
        else:
            s7, s8 = A7[..., :3].astype(int).min(2), A8[..., :3].astype(int).min(2)
            ch = s7 != s8
            rec.update(kind="shadow", changed_px=int(ch.sum()), changed_box=box(ch), darker_px=int((s8 < s7).sum()),
                       lighter_px=int((s8 > s7).sum()), max_lighter=int((s8 - s7).max()), max_darker=int((s7 - s8).max()))
    files[k] = rec
res["files"] = files
res["changed"] = sorted(k for k, v in files.items() if not v["same_bytes"])
res["unchanged_count"] = sum(v["same_bytes"] for v in files.values())
res["unchanged_new_path_but_same_bytes"] = sorted(k for k, v in files.items() if v["same_bytes"] and not v["same_path"])
print("changed:", res["changed"], "| unchanged", res["unchanged_count"], "of", len(files), flush=True)

# ------------------------------------------------------------------ 2. the ungraded sources
W7, W8 = os.path.join(P2, "work-r7"), os.path.join(P2, "work-r8")
src = {}
for kind in ("layers", "shadows"):
    for f in sorted(os.listdir(os.path.join(W8, kind))):
        p8, p7 = os.path.join(W8, kind, f), os.path.join(W7, kind, f)
        rec = dict(r7_exists=os.path.exists(p7))
        if rec["r7_exists"]:
            rec["same_bytes"] = sha(p7) == sha(p8)
            if not rec["same_bytes"]:
                A7, A8 = u8(p7).astype(int), u8(p8).astype(int)
                if A7.ndim == 2:
                    A7, A8 = A7[..., None], A8[..., None]
                if A7.shape[-1] == 4:
                    d = np.abs(A7[..., :3] - A8[..., :3]).max(2)
                    under = (A7[..., 3] > 0) | (A8[..., 3] > 0)
                    rec.update(alpha_changed_px=int((A7[..., 3] != A8[..., 3]).sum()), rgb_changed_under_alpha_px=int(((d > 0) & under).sum()),
                               rgb_changed_box=box((d > 0) & under), rgb_max=int(d[under].max()), under_alpha_px=int(under.sum()))
                else:
                    s7, s8 = A7[..., :3].min(2), A8[..., :3].min(2)
                    rec.update(changed_px=int((s7 != s8).sum()), changed_box=box(s7 != s8), darker_px=int((s8 < s7).sum()),
                               max_lighter=int((s8 - s7).max()))
        src[f"{kind}/{f}"] = rec
res["ungraded_sources"] = src
print("ungraded:", {k: (v.get("same_bytes"), v.get("changed_px", v.get("rgb_changed_under_alpha_px"))) for k, v in src.items()}, flush=True)


# ------------------------------------------------------------------ 3. the composites
def region(lf, sf):
    L = u8(os.path.join(LD, lf))
    S = u8(os.path.join(LD, sf))
    S = S[..., :3].min(2) if S.ndim == 3 else S
    return (L[..., 3] > 0) | (S < 255)


def reg_pair(i7, i8):
    return region(*i7) | region(*i8)


R = {}
R["curtains"] = reg_pair((b7["curtains"]["file"], b7["curtains-shadow"]["file"]), (b8["curtains"]["file"], b8["curtains-shadow"]["file"]))
R["candle-holders"] = reg_pair((b7["candle-holders"]["file"], b7["candle-holders-shadow"]["file"]),
                               (b8["candle-holders"]["file"], b8["candle-holders-shadow"]["file"]))
for vid in ("curtains-v2", "curtains-v3", "candle-holders-v2"):
    R[vid] = reg_pair((V7[vid]["file"], V7[vid]["shadow"]), (V8[vid]["file"], V8[vid]["shadow"]))
comp = {}


def cmp(t7, t8, zones):
    G7 = u8(os.path.join(P2, "graded", t7))[..., :3].astype(int)
    G8 = u8(os.path.join(P2, "graded", t8))[..., :3].astype(int)
    d = np.abs(G7 - G8).max(2)
    ch = d > 0
    z = np.zeros(ch.shape, bool)
    for k in zones:
        z |= R[k]
    per = {k: int((ch & R[k]).sum()) for k in zones}
    return dict(changed_px=int(ch.sum()), changed_outside_changed_products=int((ch & ~z).sum()), max_change=int(d.max()),
                per_product=per, zones=zones, changed_box=box(ch))


for s in "ABC":
    comp[f"default set {s}"] = cmp(f"default-scene-r7-set-{s}-graded-v3c.png", f"default-scene-r8-set-{s}-graded-v3c.png", ["curtains", "candle-holders"])
for vid in V8:
    zones = [vid if vid.startswith("curtains") else "curtains", "candle-holders-v2" if vid == "candle-holders-v2" else "candle-holders"]
    comp[f"variant {vid} set B"] = cmp(f"variant-r7-{vid}-set-B-graded-v3c.png", f"variant-r8-{vid}-set-B-graded-v3c.png", zones)
res["composites"] = comp
res["composites_outside_total"] = int(sum(v["changed_outside_changed_products"] for v in comp.values()))
for k, v in comp.items():
    print(k, v["changed_px"], v["changed_outside_changed_products"], v["per_product"], flush=True)

# ------------------------------------------------------------------ 4. where (the named zones)
MARK_BOX_R8 = (1704, 1240, 1752, 1292)       # fix_r8.py MARK_BOX (x0, y0, x1, y1), exclusive ends
DESIGNER_BOX = (1711, 1251, 1747, 1266)      # the designer's 3.3.1 "about x 1711-1746, y 1251-1265"
BENCH_ZONE = (100, 1150, 260, 1240)          # the cut over the bench: the break and the stone contact (QA's lines, canvas px)


def inside(b, Z):
    return b is None or (b[0] >= Z[0] and b[1] >= Z[1] and b[2] < Z[2] and b[3] < Z[3])


wh = {}
for k in ("candle-holders", "candle-holders-shadow"):
    r = files[k]
    b = r.get("rgb_changed_box") or r.get("changed_box")
    ab = r.get("alpha_changed_box")
    wh[k] = dict(box=b, alpha_box=ab, inside_r8_mark_box=inside(b, MARK_BOX_R8) and inside(ab, MARK_BOX_R8),
                 inside_designer_box=inside(b, DESIGNER_BOX) and inside(ab, DESIGNER_BOX))
for k in ("curtains", "curtains-shadow", "curtains-v2 layer", "curtains-v2 shadow"):
    r = files[k]
    b = r.get("rgb_changed_box") or r.get("changed_box")
    wh[k] = dict(box=b, alpha_box=r.get("alpha_changed_box"), inside_bench_zone=inside(b, BENCH_ZONE))
res["where"] = dict(mark_box_r8=MARK_BOX_R8, designer_box=DESIGNER_BOX, bench_zone=BENCH_ZONE, layers=wh)
print(json.dumps(wh, indent=1), flush=True)
json.dump(res, open(os.path.join(OUT, "data/scope.json"), "w"), indent=1)
