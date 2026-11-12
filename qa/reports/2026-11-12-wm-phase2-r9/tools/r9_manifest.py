#!/usr/bin/env python3
"""
qa-agent 2026-11-12 (R9): the records (F2, F8) and the supplier-image check.
  1. layers/asset-manifest-entries-r9.json: every entry's path exists, its sha256 and its 'bytes' match the file; every sha256 in
     'scripts_sha256' and 'tool_set_sha256' matches; tool_set_sha256 covers every file manifest-r9 names for the tool (default layers and
     shadows, cushion sets, variant layers and shadows, default and variant truths).
  2. assets/manifest.json: the R9 entries present and identical to the entries file; every entry anywhere in it that records a sha256
     matches the file; how many entries record one (R8: 0 of 1,233); against QA's R8 commit (365321f9): entries added, removed, changed.
  3. Every sha256 written in manifest-r9.json and in work-r9/fix-r9.json matches the file it names.
  4. No supplier image in the repo: every image under the phase-2 folder (all rounds) and under this QA folder, 16 x 16 dHash against
     every supplier image QA can reach offline (site/.cache/supplier-images and the session's downloaded references in the scratchpad;
     read only, -I), as in r8_manifest.py (near-blank pairs not counted); and file names that look like supplier references.
Writes data/manifest.json.     ~/.venvs/motion/bin/python3.12 -I r9_manifest.py
"""
import glob
import hashlib
import json
import os
import subprocess

import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = 80_000_000
REPO = "/home/user/homedesign-app"
P2 = os.path.join(REPO, "assets/renders/living-room/warm-modern/phase2-2026-11-10")
LD = os.path.join(P2, "layers")
OUT = os.path.join(REPO, "qa/reports/2026-11-12-wm-phase2-r9")
SC = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad"
IMG = (".png", ".jpg", ".jpeg", ".webp", ".avif", ".gif")
_cache = {}


def sha(p):
    if p not in _cache:
        _cache[p] = hashlib.sha256(open(p, "rb").read()).hexdigest()
    return _cache[p]


res = {}
# ------------------------------------------------------------------ 1. the entries file
E = json.load(open(os.path.join(LD, "asset-manifest-entries-r9.json")))
rows = []
for e in E["assets"]:
    p = os.path.join(REPO, e["path"])
    r = dict(id=e["id"], exists=os.path.isfile(p))
    if r["exists"]:
        r.update(sha_match=sha(p) == e.get("sha256"), bytes_match=os.path.getsize(p) == e.get("bytes"))
    rows.append(r)
scr = {k: (os.path.isfile(os.path.join(REPO, k)) and sha(os.path.join(REPO, k)) == v) for k, v in E["scripts_sha256"].items()}
tss = {k: (os.path.isfile(os.path.join(REPO, k)) and sha(os.path.join(REPO, k)) == v) for k, v in E["tool_set_sha256"].items()}
m9 = json.load(open(os.path.join(LD, "manifest-r9.json")))
named = set()
for l_ in m9["layers"]:
    if "file" in l_:
        named.add(os.path.relpath(os.path.join(LD, l_["file"]), REPO))
for s, st in m9["slot_cushions"]["sets"].items():
    named.add(os.path.relpath(os.path.join(LD, st["layer"]), REPO))
    named.add(os.path.relpath(os.path.join(LD, st["shadow"]), REPO))
for vs in m9["variants"].values():
    for v in vs:
        for k in ("file", "shadow"):
            named.add(os.path.relpath(os.path.join(LD, v[k]), REPO))
        named.add(os.path.relpath(os.path.normpath(os.path.join(LD, v["truth"])), REPO))
for s in "ABC":
    named.add(os.path.relpath(os.path.normpath(os.path.join(LD, m9["truths"]["default"][s])), REPO))
res["entries_r9"] = dict(entries=len(rows), all_exist=all(r["exists"] for r in rows), sha_mismatch=[r["id"] for r in rows if not r.get("sha_match")],
                         bytes_mismatch=[r["id"] for r in rows if not r.get("bytes_match")],
                         scripts=dict(n=len(scr), mismatch=[k for k, v in scr.items() if not v]),
                         tool_set=dict(n=len(tss), mismatch=[k for k, v in tss.items() if not v], tool_files_named_by_manifest_r9=len(named),
                                       named_but_not_in_tool_set=sorted(named - set(tss)), in_tool_set_but_not_named=sorted(set(tss) - named)),
                         rows=rows)
print("entries:", {k: v for k, v in res["entries_r9"].items() if k != "rows"}, flush=True)

# ------------------------------------------------------------------ 2. assets/manifest.json
AM = json.load(open(os.path.join(REPO, "assets/manifest.json")))["assets"]
am = {a["id"]: a for a in AM}
ids = [a["id"] for a in AM]
present = {e["id"]: (am.get(e["id"]) == e) for e in E["assets"]}
withsha = [a for a in AM if a.get("sha256")]
bad = []
for a in withsha:
    p = os.path.join(REPO, a["path"])
    if not os.path.isfile(p) or sha(p) != a["sha256"]:
        bad.append(a["id"])
old = json.loads(subprocess.run(["git", "-C", REPO, "show", "365321f9:assets/manifest.json"], capture_output=True, text=True, check=True).stdout)["assets"]
om = {a["id"]: a for a in old}
res["assets_manifest"] = dict(entries=len(AM), duplicate_ids=sorted({i for i in ids if ids.count(i) > 1}),
                              r9_entries_present_and_identical=all(present.values()), r9_missing_or_different=[k for k, v in present.items() if not v],
                              entries_with_sha256=len(withsha), sha256_mismatch=bad,
                              vs_r8_qa_commit=dict(entries_then=len(old), added=sorted(set(am) - set(om)), removed=sorted(set(om) - set(am)),
                                                   changed=sorted(k for k in set(am) & set(om) if am[k] != om[k])))
print("assets/manifest:", {k: v for k, v in res["assets_manifest"].items()}, flush=True)

# ------------------------------------------------------------------ 3. sha256s written in manifest-r9.json and fix-r9.json
found = []


def walk(o, path, base):
    if isinstance(o, dict):
        f = o.get("file") or o.get("path") or o.get("layer")
        for k, v in o.items():
            if isinstance(v, str) and len(v) == 64 and all(c in "0123456789abcdef" for c in v) and ("sha" in k):
                # the file it belongs to: a sibling 'file' / 'path' / 'layer', or the key's own prefix (layer_sha256 -> layer)
                tgt = o.get(k.replace("_sha256", "")) if k.endswith("_sha256") else f
                found.append((path + "/" + k, v, tgt, base))
            walk(v, path + "/" + k, base)
    elif isinstance(o, list):
        for i, v in enumerate(o):
            walk(v, f"{path}[{i}]", base)


walk(m9, "manifest-r9", LD)
walk(json.load(open(os.path.join(P2, "work-r9/fix-r9.json"))), "fix-r9", REPO)
chk = []
for where, s_, tgt, base in found:
    if not tgt:
        chk.append(dict(where=where, file=None, match=None))
        continue
    p = tgt if os.path.isabs(tgt) else os.path.normpath(os.path.join(base, tgt))
    if not os.path.isfile(p):
        p2 = os.path.normpath(os.path.join(REPO, tgt))
        p = p2 if os.path.isfile(p2) else p
    chk.append(dict(where=where, file=os.path.relpath(p, REPO), match=os.path.isfile(p) and sha(p) == s_))
res["written_sha256"] = dict(n=len(chk), matched=sum(1 for c in chk if c["match"]), mismatched=[c for c in chk if c["match"] is False],
                             unresolved=[c for c in chk if c["match"] is None], rows=chk)
print("written sha:", res["written_sha256"]["n"], res["written_sha256"]["matched"], res["written_sha256"]["mismatched"], res["written_sha256"]["unresolved"], flush=True)


# ------------------------------------------------------------------ 4. supplier images (as r8_manifest.py)
def dhash(p, n=16):
    im = Image.open(p)
    im.draft("RGBA", (n * 8, n * 8))
    im = im.convert("RGBA")
    bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
    g8 = Image.alpha_composite(bg, im).convert("L")
    g = np.asarray(g8.resize((n + 1, n), Image.BILINEAR), np.int16)
    ink = float(np.asarray(g8.resize((64, 64), Image.BILINEAR), np.float32).std())
    return (g[:, 1:] > g[:, :-1]).flatten(), ink


sup = []
for pat in (os.path.join(REPO, "site/.cache/supplier-images/**/*"), os.path.join(SC, "r7/refs-dl/**/*"), os.path.join(SC, "r5/refs-dl/**/*"),
            os.path.join(SC, "dl-cards/**/*"), os.path.join(SC, "dl-products/**/*"), os.path.join(SC, "supplier/**/*"), os.path.join(SC, "dl-r3/**/*"),
            os.path.join(SC, "dl-cushion-skus/**/*"), os.path.join(SC, "qa-img1/**/*")):
    for p in glob.glob(pat, recursive=True):
        if os.path.isfile(p):
            try:
                h, ink = dhash(p)
                sup.append((p, h, ink))
            except Exception:       # noqa: BLE001
                pass
S = np.array([h for _, h, _ in sup])
SINK = np.array([k for _, _, k in sup])
ours = [p for p in glob.glob(os.path.join(P2, "**/*"), recursive=True) + glob.glob(os.path.join(OUT, "**/*"), recursive=True)
        if os.path.isfile(p) and p.lower().endswith(IMG)]
near, mins, new_r9 = [], [], []
for p in ours:
    try:
        h, ink = dhash(p)
    except Exception as e:          # noqa: BLE001
        near.append(dict(path=os.path.relpath(p, REPO), error=repr(e)))
        continue
    d = (S != h[None, :]).sum(1).astype(float)
    d[(SINK < 8) | (ink < 8)] = 999
    i = int(d.argmin())
    if d[i] < 999:
        mins.append(int(d[i]))
    rel = os.path.relpath(p, REPO)
    if d[i] <= 40:
        near.append(dict(path=rel, min_hamming_256=int(d[i]), nearest=os.path.basename(sup[i][0]), ink=round(ink, 1)))
    if "-r9" in rel or "crops-r9" in rel or "2026-11-12-wm-phase2-r9" in rel:
        new_r9.append(dict(path=rel, min_hamming_256=int(d[i]) if d[i] < 999 else None))
names = [os.path.relpath(p, REPO) for p in glob.glob(os.path.join(P2, "**/*"), recursive=True) + glob.glob(os.path.join(OUT, "**/*"), recursive=True)
         if any(t in os.path.basename(p).lower() for t in ("sku", "refs-dl", "supplier", "aliexpress-photo", "cj-photo"))]
res["supplier_images"] = dict(supplier_images_compared=len(sup), repo_images_checked=len(ours), min_hamming_256_overall=int(min(mins)) if mins else None,
                              near_matches_le_40_of_256=near, suspicious_names=names, r9_images=new_r9,
                              r9_images_min=min([q["min_hamming_256"] for q in new_r9 if q["min_hamming_256"] is not None], default=None),
                              rule="a copy (resized / re-encoded) reads <= ~20 of 256; unrelated pictures read ~100-140")
print("supplier:", {k: v for k, v in res["supplier_images"].items() if k not in ("near_matches_le_40_of_256", "r9_images")},
      "near:", len(near), flush=True)
json.dump(res, open(os.path.join(OUT, "data/manifest.json"), "w"), indent=1)
