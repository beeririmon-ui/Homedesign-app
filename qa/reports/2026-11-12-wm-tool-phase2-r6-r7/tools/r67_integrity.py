#!/usr/bin/env python3
"""
qa-agent 2026-11-12, QA of R6 (0-token code fixes) and R7 (planter k, true curtain lengths, table group move, passes 6'/7')
of the warm-modern living-room tool, phase 2. QA's own code; from render-agent only the manifests' file names, compose order and
variant lists. Extends qa/reports/2026-11-11-wm-tool-phase2-r5/tools/r5_integrity.py.

Usage:  python3 r67_integrity.py r6     (prev r5)
        python3 r67_integrity.py r7     (prev r6)

  1. Files prev -> tag (sha256) for every default layer / shadow, every variant, the cushion sets; base.png against the approved base.
  2. Recomposite base + 12 defaults + set X against graded/default-scene-<tag>-set-X (A, B, C), three paths:
       P1 manifest formula (one rounding per product); P2 two 8-bit passes; P4 browser premultiplied.
     gate: p99.9 <= 2 and max <= 6 (worst channel, 8-bit), over the union of the regions.
  3. Swap-diff of the defaults: each product off (sets A, B, C), and the 3 set swaps (full frame).
     + region tightness: region pixels farther than 60 px from the layer's alpha bbox (stray shadow / alpha).
  4. tag vs prev scenes: changed pixels outside the union of the changed products' regions (prev u tag).
  5. Every layer whose bytes changed although the manifest says nothing was asked of it (e.g. the basket): what changed and where.
  6. Disjointness of every variant slot's region union against every other slot and cushion set.
  7. Each variant alone (sets A, B, C; P1, P2, P4) against its truth; swap default<->variant and variant<->empty locality.
  8. The FULL CROSS of the variant slots x sets A, B, C x paths P1 and P4, computed on the union of the variant slots' regions
     (outside it every option is the identity, proved per pixel by the formula), against (a) the truth built by pasting each
     chosen variant's truth on its slot's two-region union and (b) independence (the single-variant composites pasted).
Writes data/integrity-<tag>.json.
"""
import hashlib
import itertools
import json
import os
import sys
import time

import cv2
import numpy as np
from PIL import Image

TAG = sys.argv[1]
PREV = {"r6": "r5", "r7": "r6"}[TAG]
REPO = "/home/user/homedesign-app"
P2 = os.path.join(REPO, "assets/renders/living-room/warm-modern/phase2-2026-11-10")
P1 = os.path.join(REPO, "assets/renders/living-room/warm-modern/pilot-phase1-2026-11-07")
OUT = os.path.join(REPO, "qa/reports/2026-11-12-wm-tool-phase2-r6-r7")
LD = os.path.join(P2, "layers")
t0 = time.time()


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def u8(p):
    return np.asarray(Image.open(p))


mp = json.load(open(os.path.join(LD, f"manifest-{PREV}.json")))
mt = json.load(open(os.path.join(LD, f"manifest-{TAG}.json")))
order = mt["compose"]["order"]
assert order == mp["compose"]["order"]
bp = {l_["id"]: l_ for l_ in mp["layers"]}
bt = {l_["id"]: l_ for l_ in mt["layers"]}
products = [i for i in order if i != "base" and not i.endswith("-shadow")]
res = dict(tag=TAG, prev=PREV)

# ---------------------------------------------------------------- 1. files
files = {}
for i in order:
    if i in ("base", "cushions", "cushions-shadow"):
        continue
    fp, ft = bp[i]["file"], bt[i]["file"]
    files[i] = dict(prev=fp, tag=ft, same_bytes=sha(os.path.join(LD, fp)) == sha(os.path.join(LD, ft)))
for s in "ABC":
    for kind in ("layer", "shadow"):
        fp, ft = mp["slot_cushions"]["sets"][s][kind], mt["slot_cushions"]["sets"][s][kind]
        files[f"cushions {s} {kind}"] = dict(prev=fp, tag=ft, same_bytes=sha(os.path.join(LD, fp)) == sha(os.path.join(LD, ft)))
pv = {v["id"]: v for vs in mp["variants"].values() for v in vs}
for slot, vs in mt["variants"].items():
    for v in vs:
        for kind, key in (("layer", "file"), ("shadow", "shadow")):
            if v["id"] in pv:
                fp = pv[v["id"]][key]
                files[f"{v['id']} {kind}"] = dict(prev=fp, tag=v[key], same_bytes=sha(os.path.join(LD, fp)) == sha(os.path.join(LD, v[key])),
                                                 product_prev=pv[v["id"]]["product"]["card_id"], product_tag=v["product"]["card_id"])
            else:
                files[f"{v['id']} {kind}"] = dict(prev=None, tag=v[key], same_bytes=False, new_variant=True)
res["files"] = files
res["files_changed"] = sorted(k for k, v in files.items() if not v["same_bytes"])
res["base_same_bytes_as_approved"] = sha(os.path.join(LD, "base.png")) == sha(os.path.join(P1, "layers-v3c/base.png"))
print("changed:", res["files_changed"], "| base ok:", res["base_same_bytes_as_approved"], flush=True)

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


lay, shd = load_man(mt, bt)
VAR = {}
for slot, vs in mt["variants"].items():
    for v in vs:
        VAR[v["id"]] = dict(slot=slot, L=u8(os.path.join(LD, v["file"])), S=u8(os.path.join(LD, v["shadow"]))[..., :3])
        assert VAR[v["id"]]["L"].shape == (H, W, 4) and VAR[v["id"]]["S"].shape == (H, W, 3), v["id"]


def region_of(L, S):
    return (L[..., 3] > 0) | (S.min(2) < 255)


reg = {k: region_of(lay[k], shd[k]) for k in lay}
vreg = {k: region_of(v["L"], v["S"]) for k, v in VAR.items()}


def tight(L, R):
    a = L[..., 3] > 0
    if not a.any():
        return None
    ys, xs = np.nonzero(a)
    bx = [xs.min() - 60, ys.min() - 60, xs.max() + 60, ys.max() + 60]
    m = np.ones(R.shape, bool)
    m[max(0, bx[1]):bx[3] + 1, max(0, bx[0]):bx[2] + 1] = False
    return int((R & m).sum())


res["region_px_beyond_60px_of_alpha_box"] = {k: tight(lay[k], reg[k]) for k in lay}
res["region_px_beyond_60px_of_alpha_box"].update({k: tight(VAR[k]["L"], vreg[k]) for k in VAR})


def apply(out, rgb, a, sh, path):
    if path == "P1":
        out = np.floor(out * sh / 255.0 * (1 - a) + rgb * a + 0.5)
    elif path == "P2":
        m = np.floor(out * sh / 255.0 + 0.5)
        out = np.floor(m * (1 - a) + rgb * a + 0.5)
    else:
        pm = np.floor(rgb * a + 0.5)
        m = np.floor(sh * out / 255.0 + 0.5)
        out = np.floor(pm + m * (1 - a) + 0.5)
    return np.clip(out, 0, 255)


def stack(s, path="P1", skip=(), repl=None):
    repl = repl or {}
    out = base.copy()
    for pid in products:
        k = "set-" + s if pid == "cushions" else pid
        if pid in skip:
            continue
        L, S = (VAR[repl[pid]]["L"], VAR[repl[pid]]["S"]) if pid in repl else (lay[k], shd[k])
        out = apply(out, L[..., :3].astype(np.float32), L[..., 3:4].astype(np.float32) / 255.0, S.astype(np.float32), path)
    return out


def gate(c, T, region):
    d = np.abs(c - T).max(-1)
    return dict(p999_region=float(np.percentile(d[region], 99.9)), max=float(d.max()),
                px_gt2=int((d > 2).sum()), px_gt6=int((d > 6).sum()), outside_region_gt0=int(((d > 0) & ~region).sum()))


def ok(r):
    return r["p999_region"] <= 2 and r["max"] <= 6


# ---------------------------------------------------------------- 2. recomposite defaults
union_def, truth, rec, comps = {}, {}, {}, {}
for s in "ABC":
    truth[s] = u8(os.path.join(P2, f"graded/default-scene-{TAG}-set-{s}-graded-v3c.png"))[..., :3].astype(np.float32)
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
        r["gt2_by_layer"] = {k: int(((d > 2) & reg[k]).sum()) for k in lay
                             if (not k.startswith("set-") or k == "set-" + s) and ((d > 2) & reg[k]).any()}
        rec[s][path] = r
    print("recomposite", s, {p: (rec[s][p]["p999_region"], rec[s][p]["max"], rec[s][p]["px_gt2"]) for p in rec[s]}, round(time.time() - t0), flush=True)
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
print("swap defaults: toggles", len(sw), "outside", res["swap_diff_defaults_outside_total"], round(time.time() - t0), flush=True)

# ---------------------------------------------------------------- 4. tag vs prev scenes
layp, shdp = load_man(mp, bp)
regp = {k: region_of(layp[k], shdp[k]) for k in layp}
changed_products = sorted({k.split(" ")[0].replace("-shadow", "") for k in res["files_changed"] if not k.startswith("cushions") and "-v" not in k.split(" ")[0]})
cu = np.zeros((H, W), bool)
for k in changed_products:
    cu |= reg[k] | regp[k]
vs_ = {}
for s in "ABC":
    Gp = u8(os.path.join(P2, f"graded/default-scene-{PREV}-set-{s}-graded-v3c.png"))[..., :3].astype(np.int16)
    d = np.abs(truth[s].astype(np.int16) - Gp).max(2)
    ch = d > 0
    vs_[s] = dict(changed_px=int(ch.sum()), changed_outside_changed_products=int((ch & ~cu).sum()),
                  per_product={k: int((ch & (reg[k] | regp[k])).sum()) for k in changed_products})
res["scenes_vs_prev"] = dict(changed_products=changed_products, sets=vs_)
print("scenes vs prev", changed_products, {s: (vs_[s]["changed_px"], vs_[s]["changed_outside_changed_products"]) for s in vs_}, flush=True)


# ---------------------------------------------------------------- 5. per-layer change detail (prev -> tag) for every changed default
def box(m):
    if not m.any():
        return None
    ys, xs = np.nonzero(m)
    return [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1]


det = {}
for k in changed_products:
    Ap, At = layp[k][..., 3].astype(np.int16), lay[k][..., 3].astype(np.int16)
    Cp, Ct = layp[k][..., :3].astype(np.int16), lay[k][..., :3].astype(np.int16)
    da = At != Ap
    dc = np.abs(Ct - Cp).max(2)
    drgb = (dc > 0) & ((At > 0) | (Ap > 0))
    dsh = np.abs(shd[k].astype(np.int16) - shdp[k].astype(np.int16)).max(2) > 0
    both255 = (At == 255) & (Ap == 255)
    det[k] = dict(alpha_changed_px=int(da.sum()), alpha_changed_box=box(da), alpha_max_change=int(np.abs(At - Ap).max()),
                  rgb_changed_under_alpha_px=int(drgb.sum()), rgb_changed_at_alpha255_both=int((drgb & both255).sum()),
                  rgb_max_change_alpha255=int(dc[both255 & drgb].max()) if (both255 & drgb).any() else 0,
                  shadow_changed_px=int(dsh.sum()), shadow_changed_box=box(dsh), rgb_changed_box=box(drgb))
res["layer_change_detail"] = det
print("detail", json.dumps(det)[:2000], flush=True)

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
near = {}
for a_ in vslots:
    dt = cv2.distanceTransform((~slot_union[a_]).astype(np.uint8), cv2.DIST_L2, 5)
    nd = {b_: round(float(dt[slot_union[b_]].min()), 1) for b_ in slot_union if b_ != a_ and slot_union[b_].any()}
    near[a_] = dict(sorted(nd.items(), key=lambda kv: kv[1])[:4])
res["disjoint"] = dict(variant_slot_overlaps=ov, nearest_other_regions_px=near,
                       non_variant_pairs_overlap={f"{a_} x {b_}": int((slot_union[a_] & slot_union[b_]).sum())
                                                  for a_, b_ in itertools.combinations([k for k in slots if k not in vslots], 2)
                                                  if (slot_union[a_] & slot_union[b_]).any()})
print("disjoint", ov, near, flush=True)

# ---------------------------------------------------------------- 7. each variant alone
vtruthB = {vid: u8(os.path.join(P2, f"graded/variant-{TAG}-{vid}-set-B-graded-v3c.png"))[..., :3].astype(np.float32) for vid in VAR}
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
    # the B truth outside the two regions must be the default B truth (the truth itself is local)
    dB = np.abs(vtruthB[vid] - truth["B"]).max(2) > 0
    vr[vid]["truth_B_differs_from_default_outside_two_regions"] = int((dB & ~two).sum())
    print("variant", vid, {k: (r["p999_region"], r["max"]) for k, r in vr[vid].items() if isinstance(r, dict)},
          vr[vid]["B P1"]["swap_vs_default_outside_two_regions"], vr[vid]["B P1"]["variant_vs_empty_outside_variant_region"],
          vr[vid]["truth_B_differs_from_default_outside_two_regions"], round(time.time() - t0), flush=True)
res["variants_alone"] = vr
res["variants_alone_pass"] = all(ok(r) for v in vr.values() for r in v.values() if isinstance(r, dict)) and all(
    v[f"{s} P1"]["swap_vs_default_outside_two_regions"] == 0 and v[f"{s} P1"]["variant_vs_empty_outside_variant_region"] == 0
    for v in vr.values() for s in "ABC")
json.dump(res, open(os.path.join(OUT, f"data/integrity-{TAG}.json"), "w"), indent=1)

# ---------------------------------------------------------------- 8. the full cross on the variant-slot pixel union
U = np.zeros((H, W), bool)
for sl_ in vslots:
    U |= slot_union[sl_]
idx = np.flatnonzero(U)
print("full cross: union px", idx.size, flush=True)


def g(arr):
    return arr.reshape(-1, arr.shape[-1])[idx].astype(np.float32)


baseU = g(base)
layU = {}
for k in lay:
    L, S = lay[k], shd[k]
    act = (L.reshape(-1, 4)[idx, 3] > 0) | (S.reshape(-1, 3)[idx].min(1) < 255)
    layU[k] = None if not act.any() else (g(L[..., :3]), g(L[..., 3:4]) / 255.0, g(S))
varU = {vid: (g(v["L"][..., :3]), g(v["L"][..., 3:4]) / 255.0, g(v["S"])) for vid, v in VAR.items()}
truthU = {s: g(truth[s]) for s in "ABC"}
vtruthU = {vid: g(vtruthB[vid]) for vid in VAR}
twoU = {vid: (vreg[vid] | reg[VAR[vid]["slot"]]).reshape(-1)[idx] for vid in VAR}
unionU = {s: union_def[s].reshape(-1)[idx] for s in "ABC"}
vregU = {vid: vreg[vid].reshape(-1)[idx] for vid in VAR}
skipped_layers = sorted(k for k, v in layU.items() if v is None)


def stackU(s, path, repl):
    out = baseU.copy()
    for pid in products:
        k = "set-" + s if pid == "cushions" else pid
        if pid in repl:
            rgb, a, sh = varU[repl[pid]]
        else:
            if layU[k] is None:
                continue
            rgb, a, sh = layU[k]
        out = apply(out, rgb, a, sh, path)
    return out


singleU = {}
for vid, v in VAR.items():
    for s in "ABC":
        for path in ("P1", "P4"):
            singleU[(vid, s, path)] = stackU(s, path, {v["slot"]: vid})
defU = {(s, p): stackU(s, p, {}) for s in "ABC" for p in ("P1", "P4")}
# consistency: the 1-D default composites equal the full-frame ones on U
res["full_cross_1d_consistency_max"] = float(max(np.abs(defU[(s, p)] - comps[(s, p)].reshape(-1, 3)[idx]).max() for s in "ABC" for p in ("P1", "P4")))
choices = {sl_: [None] + [vid for vid, v in VAR.items() if v["slot"] == sl_] for sl_ in vslots}
combos = list(itertools.product(*[choices[s_] for s_ in vslots]))
n_out_const = H * W - idx.size
worst = dict(p999=0.0, max=0.0, indep_max=0.0)
rows = []
fails = []
for ci, combo in enumerate(combos):
    repl = {sl_: vid for sl_, vid in zip(vslots, combo) if vid}
    for s in "ABC":
        T = truthU[s].copy()
        regu = unionU[s].copy()
        for sl_, vid in repl.items():
            T[twoU[vid]] = vtruthU[vid][twoU[vid]]
            regu |= vregU[vid]
        for path in ("P1", "P4"):
            c = stackU(s, path, repl)
            d = np.abs(c - T).max(1)
            # outside U the composite equals the default one (identity); its error there is the default recomposite's error
            dout = np.abs(comps[(s, path)] - truth[s]).max(2)
            dout_reg = dout[union_def[s] & ~U]
            allreg = np.concatenate([d[regu], dout_reg])
            p999 = float(np.percentile(allreg, 99.9))
            mx = float(max(d.max(), dout[~U].max()))
            E = defU[(s, path)].copy()
            for sl_, vid in repl.items():
                E[twoU[vid]] = singleU[(vid, s, path)][twoU[vid]]
            di = float(np.abs(c - E).max())
            r = dict(combo={k: (v or "default") for k, v in zip(vslots, combo)}, set=s, path=path, p999=p999, max=mx, gt2=int((d > 2).sum()), indep_max=di)
            rows.append(r)
            worst["p999"] = max(worst["p999"], p999)
            worst["max"] = max(worst["max"], mx)
            worst["indep_max"] = max(worst["indep_max"], di)
            if p999 > 2 or mx > 6 or di > 0:
                fails.append(r)
    if ci % 24 == 0:
        print("combo", ci, "/", len(combos), round(time.time() - t0), worst, flush=True)
res["full_cross"] = dict(slots=vslots, choices={k: [(x or "default") for x in v] for k, v in choices.items()}, n_combos=len(combos),
                         n_composites=len(rows), union_px=int(idx.size), layers_identity_on_union=skipped_layers, worst=worst,
                         all_pass=all(r["p999"] <= 2 and r["max"] <= 6 for r in rows),
                         independence_all_zero=all(r["indep_max"] == 0 for r in rows), fails=fails[:20])
res["full_cross_rows"] = rows
json.dump(res, open(os.path.join(OUT, f"data/integrity-{TAG}.json"), "w"), indent=1)
print("written", round(time.time() - t0), "s; full cross", len(rows), "composites; worst", worst, flush=True)
