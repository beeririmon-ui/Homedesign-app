#!/usr/bin/env python3
"""
qa-agent 2026-11-11, QA of R5 (warm-modern living-room tool, phase 2: the 0-token colour fixes and the variant passes 4' / 5').
QA's own code: nothing imported from render-agent; from the manifests only the file names, the compose order and the variants list.

  1. Files: r4 -> r5 (sha256) for every default layer / shadow and the cushion sets; base.png against the approved phase-1 v3c base.
  2. Recomposite base + 12 defaults + set X against graded/default-scene-r5-set-X (A, B, C), three paths:
       P1  manifest formula, one rounding per product: round(below*sh/255*(1-a) + rgb*a)
       P2  two 8-bit passes: m = round(below*sh/255); out = round(m*(1-a) + rgb*a)
       P4  browser / gl.ts: premultiplied, multiply = round(src*dst/255), normal = round(src_pm + dst*(1-a/255))
     gate: p99.9 <= 2 and max <= 6 (worst channel, 8-bit levels), over the union of the regions.
  3. Swap-diff of the defaults: every product off with all others on (sets A, B, C), and the three set swaps.
  4. r5 against r4 scenes: changed pixels outside the union of the changed products' regions (r4 u r5).
  5. The basket (changed bytes, 'the stack under it changed'): alpha / RGB-under-alpha / shadow changes against r4, and where.
  6. Regions of every slot (default u all variants) against every other slot and every cushion set: pairwise overlap in px.
  7. Each variant alone (sets A, B, C; P1, P2, P4): against its truth (set B: graded/variant-r5-<id>-set-B; A and C: the set's default
     scene with the variant truth pasted on the union of the two regions); swap default <-> variant changes nothing outside the union of
     the two regions; variant <-> empty slot changes nothing outside the variant's region.
  8. The FULL CROSS of the slots with variants (curtains 2 x framed-art 2 x accent-sconces 3 x vase 2 x pendant 2 = 48) x sets A, B, C,
     paths P1 and P4 (288 composites): each against (a) the truth built by pasting each chosen variant's truth on its slot's region union
     (a recomposite gate) and (b) the 'independence' expectation built by pasting the single-variant composites of the same path (exact 0
     if the slots do not interact).
Writes data/integrity.json.   python3 r5_integrity.py
"""
import hashlib
import itertools
import json
import os
import time

import numpy as np
from PIL import Image

REPO = "/home/user/homedesign-app"
P2 = os.path.join(REPO, "assets/renders/living-room/warm-modern/phase2-2026-11-10")
P1 = os.path.join(REPO, "assets/renders/living-room/warm-modern/pilot-phase1-2026-11-07")
OUT = os.path.join(REPO, "qa/reports/2026-11-11-wm-tool-phase2-r5")
LD = os.path.join(P2, "layers")


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def u8(p):
    return np.asarray(Image.open(p))


m4 = json.load(open(os.path.join(LD, "manifest-r4.json")))
m5 = json.load(open(os.path.join(LD, "manifest-r5.json")))
order = m5["compose"]["order"]
assert order == m4["compose"]["order"]
b4 = {l_["id"]: l_ for l_ in m4["layers"]}
b5 = {l_["id"]: l_ for l_ in m5["layers"]}
products = [i for i in order if i != "base" and not i.endswith("-shadow")]
res = dict(manifest_r4="layers/manifest-r4.json", manifest_r5="layers/manifest-r5.json")
t0 = time.time()

# ---------------------------------------------------------------- 1. files
files = {}
for i in order:
    if i in ("base", "cushions", "cushions-shadow"):
        continue
    f4, f5 = b4[i]["file"], b5[i]["file"]
    files[i] = dict(r4=f4, r5=f5, same_name=f4 == f5, same_bytes=sha(os.path.join(LD, f4)) == sha(os.path.join(LD, f5)))
for s in "ABC":
    for kind in ("layer", "shadow"):
        f4, f5 = m4["slot_cushions"]["sets"][s][kind], m5["slot_cushions"]["sets"][s][kind]
        files[f"cushions {s} {kind}"] = dict(r4=f4, r5=f5, same_bytes=sha(os.path.join(LD, f4)) == sha(os.path.join(LD, f5)))
res["files"] = files
res["files_changed"] = sorted(k for k, v in files.items() if not v["same_bytes"])
res["files_same_bytes_new_name"] = sorted(k for k, v in files.items() if v["same_bytes"] and not v.get("same_name", True))
res["base_same_bytes_as_approved"] = sha(os.path.join(LD, "base.png")) == sha(os.path.join(P1, "layers-v3c/base.png"))
print("changed:", res["files_changed"], "| same bytes, new name:", res["files_same_bytes_new_name"], "| base ok:", res["base_same_bytes_as_approved"])

# ---------------------------------------------------------------- load
base = u8(os.path.join(LD, "base.png"))[..., :3].astype(np.float32)
H, W = base.shape[:2]


def load_man(man, byid):
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


lay, shd = load_man(m5, b5)
VAR = {}
for slot, vs in m5["variants"].items():
    for v in vs:
        VAR[v["id"]] = dict(slot=slot, L=u8(os.path.join(LD, v["file"])), S=u8(os.path.join(LD, v["shadow"]))[..., :3])
        assert VAR[v["id"]]["L"].shape == (H, W, 4) and VAR[v["id"]]["S"].shape == (H, W, 3), v["id"]


def region_of(L, S):
    return (L[..., 3] > 0) | (S.min(2) < 255)


reg = {k: region_of(lay[k], shd[k]) for k in lay}
vreg = {k: region_of(v["L"], v["S"]) for k, v in VAR.items()}


def stack(s, path="P1", skip=(), repl=None):
    """repl = {slot: variant id}"""
    repl = repl or {}
    out = base.copy()
    for pid in products:
        k = "set-" + s if pid == "cushions" else pid
        if pid in skip:
            continue
        if pid in repl:
            L, S = VAR[repl[pid]]["L"], VAR[repl[pid]]["S"]
        else:
            L, S = lay[k], shd[k]
        rgb = L[..., :3].astype(np.float32)
        a = L[..., 3:4].astype(np.float32) / 255.0
        sh = S.astype(np.float32)
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


def gate(c, T, region):
    d = np.abs(c - T).max(2)
    return dict(p999_region=float(np.percentile(d[region], 99.9)), max=float(d.max()), max_at=[int(v) for v in np.unravel_index(int(d.argmax()), d.shape)[::-1]],
                px_gt0=int((d > 0).sum()), px_gt2=int((d > 2).sum()), px_gt6=int((d > 6).sum()), outside_region_gt0=int(((d > 0) & ~region).sum()))


def ok(r):
    return r["p999_region"] <= 2 and r["max"] <= 6


# ---------------------------------------------------------------- 2. recomposite defaults
union_def = {}
truth = {}
rec, comps = {}, {}
for s in "ABC":
    truth[s] = u8(os.path.join(P2, f"graded/default-scene-r5-set-{s}-graded-v3c.png"))[..., :3].astype(np.float32)
    u = np.zeros((H, W), bool)
    for k in lay:
        if k.startswith("set-") and k != "set-" + s:
            continue
        u |= reg[k]
    union_def[s] = u
    rec[s] = {}
    for path in ("P1", "P2", "P4"):
        c = stack(s, path)
        comps[(s, path)] = c
        r = gate(c, truth[s], u)
        d = np.abs(c - truth[s]).max(2)
        r["gt2_by_layer"] = {k: int(((d > 2) & reg[k]).sum()) for k in lay if (not k.startswith("set-") or k == "set-" + s) and ((d > 2) & reg[k]).any()}
        rec[s][path] = r
    print("recomposite", s, {p: (rec[s][p]["p999_region"], rec[s][p]["max"], rec[s][p]["px_gt2"]) for p in rec[s]}, round(time.time() - t0))
res["recomposite_defaults"] = rec
res["recomposite_defaults_pass"] = all(ok(rec[s][p]) for s in "ABC" for p in rec[s])

# ---------------------------------------------------------------- 3. swap-diff defaults
sw = {}
for s in "ABC":
    full = comps[(s, "P1")]
    for pid in products:
        k = "set-" + s if pid == "cushions" else pid
        c = stack(s, skip=(pid,))
        ch = np.abs(c - full).max(2) > 0
        sw[f"{pid} [set {s}]"] = dict(changed=int(ch.sum()), changed_outside_region=int((ch & ~reg[k]).sum()))
for x, y in (("A", "B"), ("A", "C"), ("B", "C")):
    ch = np.abs(comps[(x, "P1")] - comps[(y, "P1")]).max(2) > 0
    sw[f"cushions {x}<->{y}"] = dict(changed=int(ch.sum()), changed_outside_union=int((ch & ~(reg["set-" + x] | reg["set-" + y])).sum()))
res["swap_diff_defaults"] = sw
res["swap_diff_defaults_outside_total"] = int(sum(v.get("changed_outside_region", v.get("changed_outside_union", 0)) for v in sw.values()))
print("swap defaults: toggles", len(sw), "outside", res["swap_diff_defaults_outside_total"], round(time.time() - t0))

# ---------------------------------------------------------------- 4. r5 vs r4 scenes
lay4, shd4 = load_man(m4, b4)
changed_products = sorted({k.split(" ")[0].replace("-shadow", "") for k in res["files_changed"] if not k.startswith("cushions")})
reg4 = {k: region_of(lay4[k], shd4[k]) for k in changed_products}
cu = np.zeros((H, W), bool)
for k in changed_products:
    cu |= reg[k] | reg4[k]
vs = {}
for s in "ABC":
    G4 = u8(os.path.join(P2, f"graded/default-scene-r4-set-{s}-graded-v3c.png"))[..., :3].astype(np.int16)
    G5 = truth[s].astype(np.int16)
    d = np.abs(G5 - G4).max(2)
    ch = d > 0
    vs[s] = dict(changed_px=int(ch.sum()), changed_outside_changed_products=int((ch & ~cu).sum()),
                 per_product={k: int((ch & (reg[k] | reg4[k])).sum()) for k in changed_products})
res["r5_vs_r4_scenes"] = dict(changed_products=changed_products, sets=vs)
print("r5 vs r4", {s: (vs[s]["changed_px"], vs[s]["changed_outside_changed_products"]) for s in vs})


# ---------------------------------------------------------------- 5. the basket r4 -> r5
def box(m):
    if not m.any():
        return None
    ys, xs = np.nonzero(m)
    return [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1]


bk = {}
A4, A5 = lay4["basket"][..., 3].astype(np.int16), lay["basket"][..., 3].astype(np.int16)
C4, C5 = lay4["basket"][..., :3].astype(np.int16), lay["basket"][..., :3].astype(np.int16)
S4, S5 = shd4["basket"].astype(np.int16), shd["basket"].astype(np.int16)
da = A5 != A4
dc = np.abs(C5 - C4).max(2)
drgb = (dc > 0) & ((A5 > 0) | (A4 > 0))
dsh = np.abs(S5 - S4).max(2) > 0
both255 = (A5 == 255) & (A4 == 255)
pl = lay["planter"][..., 3] > 0
pl4 = lay4["planter"][..., 3] > 0
bk = dict(alpha_changed_px=int(da.sum()), alpha_changed_box=box(da), alpha_max_change=int(np.abs(A5 - A4).max()),
          rgb_changed_under_alpha_px=int(drgb.sum()), rgb_changed_under_alpha255_both_px=int((drgb & both255).sum()),
          rgb_changed_soft_px=int((drgb & ~both255).sum()), rgb_max_change_alpha255=int(dc[both255].max()) if both255.any() else 0,
          rgb_max_change_soft=int(dc[drgb & ~both255].max()) if (drgb & ~both255).any() else 0,
          changes_over_planter_r4_or_r5_px=int(((da | drgb) & (pl | pl4)).sum()), changes_not_over_planter_px=int(((da | drgb) & ~(pl | pl4)).sum()),
          shadow_changed_px=int(dsh.sum()), shadow_changed_box=box(dsh), rgb_changed_box=box(drgb))
res["basket_r4_vs_r5"] = bk
print("basket", bk)

# ---------------------------------------------------------------- 6. disjointness
slots = [p for p in products if p != "cushions"]
slot_union = {k: reg[k].copy() for k in slots}
for vid, v in VAR.items():
    slot_union[v["slot"]] |= vreg[vid]
for s in "ABC":
    slot_union["set-" + s] = reg["set-" + s]
vslots = sorted({v["slot"] for v in VAR.values()})
ov = {}
for a_ in vslots:
    for b_ in slot_union:
        if b_ == a_ or (b_ in vslots and b_ < a_):
            continue
        n = int((slot_union[a_] & slot_union[b_]).sum())
        if n:
            ov[f"{a_} x {b_}"] = n
# the nearest distance between each variant slot's region union and every other region (px), to see how close they come
import cv2  # noqa: E402
near = {}
for a_ in vslots:
    dt = cv2.distanceTransform((~slot_union[a_]).astype(np.uint8), cv2.DIST_L2, 5)
    near[a_] = {b_: round(float(dt[slot_union[b_]].min()), 1) for b_ in slot_union if b_ != a_ and slot_union[b_].any()}
    near[a_] = dict(sorted(near[a_].items(), key=lambda kv: kv[1])[:4])
res["disjoint"] = dict(variant_slot_overlaps=ov, nearest_other_regions_px=near,
                       non_variant_pairs_overlap={f"{a_} x {b_}": int((slot_union[a_] & slot_union[b_]).sum())
                                                  for a_, b_ in itertools.combinations([k for k in slots if k not in vslots], 2)
                                                  if (slot_union[a_] & slot_union[b_]).any()})
print("disjoint: variant-slot overlaps", ov, "| non-variant overlaps", res["disjoint"]["non_variant_pairs_overlap"])

# ---------------------------------------------------------------- 7. each variant alone
vtruthB = {vid: u8(os.path.join(P2, f"graded/variant-r5-{vid}-set-B-graded-v3c.png"))[..., :3].astype(np.float32) for vid in VAR}
single = {}
vr = {}
for vid, v in VAR.items():
    slot = v["slot"]
    two = vreg[vid] | reg[slot]
    vr[vid] = {}
    for s in "ABC":
        T = vtruthB[vid] if s == "B" else truth[s].copy()
        if s != "B":
            T[two] = vtruthB[vid][two]
        regu = union_def[s] | vreg[vid]
        for path in ("P1", "P2", "P4"):
            c = stack(s, path, repl={slot: vid})
            single[(vid, s, path)] = c
            r = gate(c, T, regu)
            if path == "P1":
                ch = np.abs(c - comps[(s, "P1")]).max(2) > 0
                r["swap_vs_default_changed"] = int(ch.sum())
                r["swap_vs_default_outside_two_regions"] = int((ch & ~two).sum())
                e = stack(s, "P1", skip=(slot,))
                ch2 = np.abs(c - e).max(2) > 0
                r["variant_vs_empty_changed"] = int(ch2.sum())
                r["variant_vs_empty_outside_variant_region"] = int((ch2 & ~vreg[vid]).sum())
            vr[vid][f"{s} {path}"] = r
    print("variant", vid, {k: (r["p999_region"], r["max"]) for k, r in vr[vid].items()},
          vr[vid]["B P1"]["swap_vs_default_outside_two_regions"], vr[vid]["B P1"]["variant_vs_empty_outside_variant_region"], round(time.time() - t0))
res["variants_alone"] = vr
res["variants_alone_pass"] = all(ok(r) for v in vr.values() for r in v.values()) and all(
    v[f"{s} P1"]["swap_vs_default_outside_two_regions"] == 0 and v[f"{s} P1"]["variant_vs_empty_outside_variant_region"] == 0 for v in vr.values() for s in "ABC")

# ---------------------------------------------------------------- 8. the full cross
choices = {}
for slot in vslots:
    choices[slot] = [None] + [vid for vid, v in VAR.items() if v["slot"] == slot]
combos = list(itertools.product(*[choices[s_] for s_ in vslots]))
cross = []
worst = dict(p999=0.0, max=0.0, indep_max=0.0)
for combo in combos:
    repl = {slot: vid for slot, vid in zip(vslots, combo) if vid}
    for s in "ABC":
        T = truth[s].copy()
        for slot, vid in repl.items():
            two = vreg[vid] | reg[slot]
            T[two] = vtruthB[vid][two]
        regu = union_def[s].copy()
        for vid in repl.values():
            regu |= vreg[vid]
        for path in ("P1", "P4"):
            c = stack(s, path, repl=repl)
            r = gate(c, T, regu)
            E = comps[(s, path)].copy()
            for slot, vid in repl.items():
                two = vreg[vid] | reg[slot]
                E[two] = single[(vid, s, path)][two]
            di = np.abs(c - E).max(2)
            r["independence_max"] = float(di.max())
            r["independence_px_gt0"] = int((di > 0).sum())
            cross.append(dict(combo={k: (v or "default") for k, v in zip(vslots, combo)}, set=s, path=path, **r))
            worst["p999"] = max(worst["p999"], r["p999_region"])
            worst["max"] = max(worst["max"], r["max"])
            worst["indep_max"] = max(worst["indep_max"], r["independence_max"])
    print("combo", combo, "done", round(time.time() - t0), worst)
res["full_cross"] = dict(slots=vslots, choices={k: [(x or "default") for x in v] for k, v in choices.items()}, n_combos=len(combos),
                         n_composites=len(cross), worst=worst, all_pass=all(ok(r) for r in cross),
                         independence_all_zero=all(r["independence_max"] == 0 for r in cross),
                         fails=[r for r in cross if not ok(r) or r["independence_max"] > 0][:20])
res["full_cross_rows"] = [dict(combo=r["combo"], set=r["set"], path=r["path"], p999=r["p999_region"], max=r["max"], gt2=r["px_gt2"],
                               indep_max=r["independence_max"]) for r in cross]
json.dump(res, open(os.path.join(OUT, "data/integrity.json"), "w"), indent=1)
print("written", round(time.time() - t0), "s; full cross", len(cross), "composites; worst", worst)
