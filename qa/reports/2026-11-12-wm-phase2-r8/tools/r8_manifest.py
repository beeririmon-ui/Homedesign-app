#!/usr/bin/env python3
"""
qa-agent 2026-11-12 (R8): manifest integrity and the supplier-image check.
  1. manifest-r8.json: every path it names (layers, shadows, cushion sets, variants, and every 'files' / build path that is a file or a
     folder) exists; every sha256 it records matches; QA's own sha256 of every image file it names (recorded for the next round).
  2. assets/manifest.json: the R8 entries (ids from layers/asset-manifest-entries-r8.json) are present and identical to the entries file;
     each path exists; any sha256 an entry records matches.
  3. No supplier image in the repo: every image under the phase-2 folder (all rounds) and under this QA folder, as a 16 x 16 dHash
     (256 bits) against every supplier image QA can reach offline (site/.cache/supplier-images and the session's downloaded references in
     the scratchpad; read only, -I), min Hamming distance; and file names that look like supplier references.
Writes data/manifest.json.     ~/.venvs/motion/bin/python3.12 -I r8_manifest.py
"""
import glob
import hashlib
import json
import os

import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = 80_000_000
REPO = "/home/user/homedesign-app"
P2 = os.path.join(REPO, "assets/renders/living-room/warm-modern/phase2-2026-11-10")
LD = os.path.join(P2, "layers")
OUT = os.path.join(REPO, "qa/reports/2026-11-12-wm-phase2-r8")
SC = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad"
IMG = (".png", ".jpg", ".jpeg", ".webp", ".avif", ".gif")


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


m = json.load(open(os.path.join(LD, "manifest-r8.json")))
res = {}
# ------------------------------------------------------------------ 1. manifest-r8
named = []
for l_ in m["layers"]:
    if "file" in l_:
        named.append(("layer " + l_["id"], os.path.join(LD, l_["file"]), l_.get("sha256")))
for s, st in m["slot_cushions"]["sets"].items():
    named.append((f"cushions {s} layer", os.path.join(LD, st["layer"]), None))
    named.append((f"cushions {s} shadow", os.path.join(LD, st["shadow"]), None))
for vs in m["variants"].values():
    for v in vs:
        named.append((v["id"] + " layer", os.path.join(LD, v["file"]), v.get("sha256")))
        named.append((v["id"] + " shadow", os.path.join(LD, v["shadow"]), None))
for k, v in m.get("files", {}).items():
    if not isinstance(v, str):
        continue
    prev_dir = LD
    for part in v.replace("->", ";").replace(",", ";").replace("(", ";").split(";"):
        t = part.strip().split(" ")[0].rstrip(")")
        if t.startswith("../") or t.endswith((".py", ".json", ".jpg", ".png")) or t.endswith("/"):
            # a bare name resolves against the layers folder, then the phase-2 folder, then the folder of the path before it
            cands = [os.path.normpath(os.path.join(d, t)) for d in (LD, P2, prev_dir)]
            hit = next((c for c in cands if os.path.exists(c)), cands[0])
            prev_dir = os.path.dirname(hit)
            named.append((f"files.{k}", hit, None))
# any other recorded sha256 anywhere in the manifest
recorded = []


def walk(o, path=""):
    if isinstance(o, dict):
        for k, v in o.items():
            if k == "sha256" and isinstance(v, str):
                recorded.append((path, v, o.get("file") or o.get("path") or o.get("source")))
            walk(v, path + "/" + k)
    elif isinstance(o, list):
        for i, v in enumerate(o):
            walk(v, f"{path}[{i}]")


walk(m)
rows = []
for name, p, sh in named:
    ex = os.path.exists(p)
    r = dict(name=name, path=os.path.relpath(p, REPO), exists=ex)
    if ex and os.path.isfile(p):
        r["sha256_qa"] = sha(p)
        if sh:
            r["sha256_recorded"] = sh
            r["sha256_match"] = r["sha256_qa"] == sh
    rows.append(r)
res["manifest_r8"] = dict(paths=len(rows), missing=[r["path"] for r in rows if not r["exists"]],
                          recorded_sha256=[dict(where=w, sha=s[:16]) for w, s, _ in recorded],
                          recorded_sha256_mismatch=[r["name"] for r in rows if r.get("sha256_match") is False],
                          recorded_sha256_count=len(recorded), rows=rows)
print("manifest-r8:", len(rows), "paths; missing", res["manifest_r8"]["missing"], "; recorded sha256", len(recorded), flush=True)

# ------------------------------------------------------------------ 2. assets/manifest.json
ent = json.load(open(os.path.join(LD, "asset-manifest-entries-r8.json")))["assets"]
am = {a["id"]: a for a in json.load(open(os.path.join(REPO, "assets/manifest.json")))["assets"]}
ar = []
for e in ent:
    a = am.get(e["id"])
    p = os.path.join(REPO, e["path"])
    r = dict(id=e["id"], present=a is not None, identical=a == e, exists=os.path.exists(p), is_dir=os.path.isdir(p))
    if os.path.isfile(p):
        r["sha256_qa"] = sha(p)
        if a and a.get("sha256"):
            r["sha256_match"] = a["sha256"] == r["sha256_qa"]
    r["records_sha256"] = bool(a and a.get("sha256"))
    ar.append(r)
dups = [i for i in [e["id"] for e in ent] if sum(1 for x in json.load(open(os.path.join(REPO, "assets/manifest.json")))["assets"] if x["id"] == i) > 1]
res["assets_manifest_r8"] = dict(entries=len(ent), all_present=all(r["present"] for r in ar), all_identical=all(r["identical"] for r in ar),
                                 all_exist=all(r["exists"] for r in ar), with_sha256=sum(r["records_sha256"] for r in ar), duplicate_ids=dups, rows=ar)
print("assets/manifest R8:", {k: v for k, v in res["assets_manifest_r8"].items() if k != "rows"}, flush=True)


# ------------------------------------------------------------------ 3. supplier images
def dhash(p, n=16):
    """the 16 x 16 dHash and the 'ink' (std of the 64 x 64 grey thumbnail over a white matte): a near-blank picture (an alpha mask, a
    shadow file, a white supplier image) carries no content and matches any other near-blank one, so pairs where either side has
    ink < 8 are not counted as matches (as the site's rights scanner guards it, site/tools/lib/rights-content.ts)"""
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
            except Exception:       # noqa: BLE001  (a cache file that is not an image)
                pass
S = np.array([h for _, h, _ in sup])
SINK = np.array([k for _, _, k in sup])
ours = [p for p in glob.glob(os.path.join(P2, "**/*"), recursive=True) + glob.glob(os.path.join(OUT, "**/*"), recursive=True)
        if os.path.isfile(p) and p.lower().endswith(IMG)]
near = []
mins = []
blank_hits = []
for p in ours:
    try:
        h, ink = dhash(p)
    except Exception as e:          # noqa: BLE001
        near.append(dict(path=os.path.relpath(p, REPO), error=repr(e)))
        continue
    d = (S != h[None, :]).sum(1).astype(float)
    d_all = d.copy()
    d[(SINK < 8) | (ink < 8)] = 999          # near-blank on either side: no content to match
    i = int(d.argmin())
    if d[i] < 999:
        mins.append(int(d[i]))
    if d[i] <= 40:
        near.append(dict(path=os.path.relpath(p, REPO), min_hamming_256=int(d[i]), nearest=os.path.basename(sup[i][0]), ink=round(ink, 1)))
    blank_hits.append(int(((d_all <= 40) & ((SINK < 8) | (ink < 8))).any()))
names = [os.path.relpath(p, REPO) for p in glob.glob(os.path.join(P2, "**/*"), recursive=True) + glob.glob(os.path.join(OUT, "**/*"), recursive=True)
         if any(t in os.path.basename(p).lower() for t in ("sku", "refs-dl", "supplier", "aliexpress-photo", "cj-photo"))]
res["supplier_images"] = dict(supplier_images_compared=len(sup), repo_images_checked=len(ours), min_hamming_256_overall=int(min(mins)) if mins else None,
                              near_blank_pairs_le_40_not_counted=int(sum(blank_hits)),
                              near_matches_le_40_of_256=near, suspicious_names=names,
                              rule="a copy (resized / re-encoded) reads <= ~20 of 256; unrelated pictures read ~100-140")
print("supplier:", {k: v for k, v in res["supplier_images"].items()}, flush=True)
json.dump(res, open(os.path.join(OUT, "data/manifest.json"), "w"), indent=1)
