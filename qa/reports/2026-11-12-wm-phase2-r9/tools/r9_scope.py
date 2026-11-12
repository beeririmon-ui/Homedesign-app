#!/usr/bin/env python3
"""
qa-agent 2026-11-12 (R9): the scope. QA's own code; from render-agent only the manifests' file names, compose order and variant lists.
  1. Git: every path under the phase-2 folder that changed since QA's R8 commit (365321f9): added / modified / deleted.
  2. Bytes: every file of QA's R8 sha256 list (qa/reports/2026-11-12-wm-phase2-r8/data/manifest.json: the manifest-r8 rows and the
     assets rows) against the file on disk today.
  3. manifest-r8 -> manifest-r9, slot by slot (12 defaults + shadows, 3 cushion sets, 10 variants + shadows): same path, same bytes;
     for every file whose bytes differ, the per-pixel change (alpha, RGB under alpha, RGB at alpha 255 in both, shadow).
  4. The scenes: the 3 default scenes and the 10 set-B variant scenes, composed by QA's own compositor (the manifest formula, one
     rounding per product) from manifest-r8 and from manifest-r9; changed pixels, and changed pixels outside the union of the two
     changed products' regions (alpha > 0 or shadow < 255, in R8 or R9). The same on the stored truths (graded/*r8* vs the truth each
     variant names in manifest-r9).
Writes data/scope.json.     ~/.venvs/motion/bin/python3.12 -I r9_scope.py
"""
import hashlib
import json
import os
import subprocess

import numpy as np
from PIL import Image

REPO = "/home/user/homedesign-app"
P2 = os.path.join(REPO, "assets/renders/living-room/warm-modern/phase2-2026-11-10")
LD = os.path.join(P2, "layers")
OUT = os.path.join(REPO, "qa/reports/2026-11-12-wm-phase2-r9")
R8QA = os.path.join(REPO, "qa/reports/2026-11-12-wm-phase2-r8")
R8_COMMIT = "365321f9"


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def u8(p):
    return np.asarray(Image.open(p))


def box(m):
    if not m.any():
        return None
    ys, xs = np.nonzero(m)
    return [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]


res = {}
# ------------------------------------------------------------------ 1. git
g = subprocess.run(["git", "-C", REPO, "diff", "--name-status", R8_COMMIT, "HEAD", "--", os.path.relpath(P2, REPO)],
                   capture_output=True, text=True, check=True).stdout.split("\n")
st = subprocess.run(["git", "-C", REPO, "status", "--porcelain", "--", os.path.relpath(P2, REPO)], capture_output=True, text=True, check=True).stdout
rows = [ln.split("\t") for ln in g if ln.strip()]
res["git_since_r8_qa_commit"] = dict(commit=R8_COMMIT, added=[r[1] for r in rows if r[0] == "A"],
                                     modified=[r[1] for r in rows if r[0] == "M"], deleted=[r[1] for r in rows if r[0] == "D"],
                                     other=[r for r in rows if r[0] not in "AMD"], working_tree_dirty=st.strip().splitlines())
print("git:", len(res["git_since_r8_qa_commit"]["added"]), "added;", res["git_since_r8_qa_commit"]["modified"], res["git_since_r8_qa_commit"]["deleted"],
      "dirty", res["git_since_r8_qa_commit"]["working_tree_dirty"], flush=True)

# ------------------------------------------------------------------ 2. QA's R8 sha256 list
base8 = json.load(open(os.path.join(R8QA, "data/manifest.json")))
lst = {}
for r in base8["manifest_r8"]["rows"]:
    if r.get("sha256_qa"):
        lst[r["path"]] = r["sha256_qa"]
for r in base8["assets_manifest_r8"]["rows"]:
    if r.get("sha256_qa"):
        p = next((x["path"] for x in json.load(open(os.path.join(LD, "asset-manifest-entries-r8.json")))["assets"] if x["id"] == r["id"]), None)
        lst[p] = r["sha256_qa"]
chk = {p: dict(r8=s, now=sha(os.path.join(REPO, p)) if os.path.exists(os.path.join(REPO, p)) else None) for p, s in lst.items()}
res["r8_sha256_list"] = dict(files=len(chk), identical=sum(v["r8"] == v["now"] for v in chk.values()),
                             differ=[p for p, v in chk.items() if v["r8"] != v["now"]])
print("R8 list:", res["r8_sha256_list"], flush=True)

# ------------------------------------------------------------------ 3. manifest-r8 -> manifest-r9
m8 = json.load(open(os.path.join(LD, "manifest-r8.json")))
m9 = json.load(open(os.path.join(LD, "manifest-r9.json")))
assert m8["compose"]["order"] == m9["compose"]["order"]
order = m9["compose"]["order"]
b8 = {l_["id"]: l_ for l_ in m8["layers"]}
b9 = {l_["id"]: l_ for l_ in m9["layers"]}
V8 = {v["id"]: v for vs in m8["variants"].values() for v in vs}
V9 = {v["id"]: v for vs in m9["variants"].values() for v in vs}
assert set(V8) == set(V9) and set(b8) == set(b9)
pairs = {}
for i in order:
    if i in ("cushions", "cushions-shadow"):
        continue
    pairs[i] = (b8[i]["file"], b9[i]["file"])
for s in "ABC":
    for kind in ("layer", "shadow"):
        pairs[f"cushions-{s} {kind}"] = (m8["slot_cushions"]["sets"][s][kind], m9["slot_cushions"]["sets"][s][kind])
for vid in V9:
    pairs[f"{vid} layer"] = (V8[vid]["file"], V9[vid]["file"])
    pairs[f"{vid} shadow"] = (V8[vid]["shadow"], V9[vid]["shadow"])
files = {}
for k, (f8, f9) in pairs.items():
    p8, p9 = os.path.join(LD, f8), os.path.join(LD, f9)
    rec = dict(r8=f8, r9=f9, same_path=f8 == f9, same_bytes=sha(p8) == sha(p9))
    if not rec["same_bytes"]:
        A8, A9 = u8(p8).astype(int), u8(p9).astype(int)
        if A8.ndim == 3 and A8.shape[-1] == 4:
            a8, a9 = A8[..., 3], A9[..., 3]
            d = np.abs(A8[..., :3] - A9[..., :3]).max(2)
            under = (a8 > 0) | (a9 > 0)
            rec.update(kind="RGBA", alpha_changed_px=int((a8 != a9).sum()), alpha_raised_px=int((a9 > a8).sum()), alpha_lowered_px=int((a9 < a8).sum()),
                       alpha_changed_box=box(a8 != a9), alpha_max_change=int(np.abs(a9 - a8).max()),
                       rgb_changed_px_anywhere=int((d > 0).sum()), rgb_changed_under_alpha_px=int(((d > 0) & under).sum()),
                       rgb_changed_box=box(d > 0), rgb_max_change=int(d.max()),
                       rgb_changed_at_alpha255_both_px=int(((d > 0) & (a8 == 255) & (a9 == 255)).sum()),
                       rgb_changed_where_alpha_not_raised_px=int(((d > 0) & ~(a9 > a8)).sum()),
                       rgb_changed_where_alpha_rose_from_0_px=int(((d > 0) & (a8 == 0) & (a9 > 0)).sum()),
                       rgb_changed_where_alpha_rose_from_gt0_px=int(((d > 0) & (a8 > 0) & (a9 > a8)).sum()),
                       rgb_changed_where_alpha0_both_px=int(((d > 0) & ~under).sum()))
        else:
            rec.update(kind="other")
    files[k] = rec
res["files"] = files
res["changed"] = sorted(k for k, v in files.items() if not v["same_bytes"])
res["unchanged_count"] = sum(v["same_bytes"] for v in files.values())
res["new_path_same_bytes"] = sorted(k for k, v in files.items() if v["same_bytes"] and not v["same_path"])
print("changed:", res["changed"], "| unchanged", res["unchanged_count"], "of", len(files), flush=True)
for k in res["changed"]:
    print("  ", k, {x: y for x, y in files[k].items() if x not in ("r8", "r9")}, flush=True)

# ------------------------------------------------------------------ 4. the scenes
base = u8(os.path.join(LD, "base.png"))[..., :3].astype(np.float32)
products = [i for i in order if i != "base" and not i.endswith("-shadow")]


def region(lf, sf):
    L = u8(os.path.join(LD, lf))
    S = u8(os.path.join(LD, sf))
    S = S[..., :3].min(2) if S.ndim == 3 else S
    return (L[..., 3] > 0) | (S < 255)


R = {vid: region(V8[vid]["file"], V8[vid]["shadow"]) | region(V9[vid]["file"], V9[vid]["shadow"]) for vid in ("pendant-v2", "curtains-v3")}
ZONE = R["pendant-v2"] | R["curtains-v3"]
res["regions_px"] = {k: int(v.sum()) for k, v in R.items()}
res["regions_overlap_px"] = int((R["pendant-v2"] & R["curtains-v3"]).sum())


def compose(man, s, repl):
    by = {l_["id"]: l_ for l_ in man["layers"]}
    VV = {v["id"]: v for vs in man["variants"].values() for v in vs}
    out = base.copy()
    for pid in products:
        if pid == "cushions":
            lf, sf = man["slot_cushions"]["sets"][s]["layer"], man["slot_cushions"]["sets"][s]["shadow"]
        elif pid in repl:
            lf, sf = VV[repl[pid]]["file"], VV[repl[pid]]["shadow"]
        else:
            lf, sf = by[pid]["file"], by[pid + "-shadow"]["file"]
        L = u8(os.path.join(LD, lf))
        S = u8(os.path.join(LD, sf))[..., :3].astype(np.float32)
        a = L[..., 3:4].astype(np.float32) / 255
        out = np.floor(out * S / 255 * (1 - a) + L[..., :3].astype(np.float32) * a + 0.5)
    return np.clip(out, 0, 255)


scenes = [("default A", "A", {}), ("default B", "B", {}), ("default C", "C", {})] + [(f"variant {vid} B", "B", {V9[vid]["slot"]: vid}) for vid in V9]
sc = {}
for name, s, repl in scenes:
    c8, c9 = compose(m8, s, repl), compose(m9, s, repl)
    d = np.abs(c8 - c9).max(2)
    ch = d > 0
    sc[name] = dict(changed_px=int(ch.sum()), changed_outside_two_products=int((ch & ~ZONE).sum()), max_change=int(d.max()),
                    in_pendant_v2_region=int((ch & R["pendant-v2"]).sum()), in_curtains_v3_region=int((ch & R["curtains-v3"]).sum()))
    print("scene", name, sc[name], flush=True)
res["scenes_composed_by_qa"] = sc
res["scenes_composed_outside_total"] = int(sum(v["changed_outside_two_products"] for v in sc.values()))

# the stored truths
tr = {}
for s in "ABC":
    f8 = f"graded/default-scene-r8-set-{s}-graded-v3c.png"
    f9 = os.path.normpath(os.path.join("layers", m9["truths"]["default"][s]))
    tr[f"default {s}"] = dict(r8=f8, r9=f9, same_path=f8 == f9, same_bytes=sha(os.path.join(P2, f8)) == sha(os.path.join(P2, f9)))
for vid in V9:
    f8 = os.path.normpath(os.path.join("layers", V8[vid]["truth"]))
    f9 = os.path.normpath(os.path.join("layers", V9[vid]["truth"]))
    rec = dict(r8=f8, r9=f9, same_path=f8 == f9, same_bytes=sha(os.path.join(P2, f8)) == sha(os.path.join(P2, f9)))
    if not rec["same_bytes"]:
        T8 = u8(os.path.join(P2, f8))[..., :3].astype(int)
        T9 = u8(os.path.join(P2, f9))[..., :3].astype(int)
        d = np.abs(T8 - T9).max(2)
        ch = d > 0
        rec.update(changed_px=int(ch.sum()), changed_outside_own_region=int((ch & ~R[vid]).sum()) if vid in R else None,
                   changed_outside_two_products=int((ch & ~ZONE).sum()), max_change=int(d.max()), changed_box=box(ch))
        # the stored truth against QA's own composite of the R9 scene
        c9 = compose(m9, "B", {V9[vid]["slot"]: vid})
        dq = np.abs(c9 - T9).max(2)
        rec["qa_compose_vs_truth_r9"] = dict(max=int(dq.max()), px_gt0=int((dq > 0).sum()), p999_in_region=float(np.percentile(dq[R[vid]], 99.9)))
    tr[f"variant {vid}"] = rec
    print("truth", vid, {k: v for k, v in rec.items() if k not in ("r8", "r9")}, flush=True)
res["stored_truths"] = tr
json.dump(res, open(os.path.join(OUT, "data/scope.json"), "w"), indent=1)
print("written", flush=True)
