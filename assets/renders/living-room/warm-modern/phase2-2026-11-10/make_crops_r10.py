#!/usr/bin/env python3
"""
make_crops_r10.py: the R10 crops of pendant 2 for the designer (render-agent, 2026-11-12; 0 tokens). R10 STOPPED on the stop rule of
docs/proposals/wm-pendant2-r9-eye-2026-11-12.md section 4.4 (rule 2: steps in 35 of the 48 sectors, work-r10/fix-r10.json), so there is no
'after': every crop is R9 (graded/variant-r9-pendant-v2-set-B-graded-v3c.png, the truth; at alpha 255 it is the layer's own RGB), with
the measure of step 1 drawn on a twin panel. Every x 2 crop shows the whole lantern, both flanks (the designer's crop rule). Nearest
neighbour: the pixels as they are.
  crops-r10/pendant-2-x1.png             the pendant at x 1 in its frame (the canopy, the cord, the lantern and the wall round it)
  crops-r10/pendant-2-x2.png             the whole lantern at x 2: R9 | R9 with the measured steps (a tick at the sector's centre and the row
                                         boundary; red = darker below, blue = lighter below; long ticks = the three band edges)
  crops-r10/pendant-2-x2-measure.png     the same at x 2 on L* stretched to the paper's 1-99.5 % (the measure's view: the bands made legible)
  crops-r10/pendant-2-left-x4.png        the left flank at x 4, where the bands end at the outline: R9 | R9 with the steps
  crops-r10/pendant-2-sector-map.png     the residual over the 48 sectors (x) and the rows (y), with the steps; the line after sector 24 is
                                         the stop rule's limit
  python3.12 -I -B make_crops_r10.py            the crops
  python3.12 -I -B make_crops_r10.py entries    layers/asset-manifest-entries-r10.json (a sha256 for every new R10 file; R9's tool set
                                                re-hashed against layers/asset-manifest-entries-r9.json)
"""
import glob
import hashlib
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join
GRD, LAY, WR10 = D(HERE, "graded"), D(HERE, "layers"), D(HERE, "work-r10")
OUT = D(HERE, "crops-r10")
REPO = os.path.abspath(D(HERE, *[".."] * 5))
BASE = "assets/renders/living-room/warm-modern/phase2-2026-11-10/"
FONT = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 15)
LANTERN = (1540, 190, 1810, 365)      # the whole lantern (R9's crop box: alpha x 1551-1797, y 190-360)
LEFT = (1548, 236, 1652, 346)          # the left flank, where the bands end at the outline


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def _new(p):
    assert not os.path.exists(p) or os.environ.get("REDO"), f"would overwrite {p}"
    os.makedirs(os.path.dirname(p), exist_ok=True)
    return p


def labelled(tiles, scale):
    """make_crops_r9.labelled(), copied: the tiles side by side, each with its label bar"""
    ims = []
    for lab, im in tiles:
        t = im.resize((im.width * scale, im.height * scale), Image.NEAREST) if scale != 1 else im
        bar = Image.new("RGB", (t.width, 24), (25, 25, 25))
        ImageDraw.Draw(bar).text((6, 3), lab, fill=(255, 255, 255), font=FONT)
        c = Image.new("RGB", (t.width, t.height + 24), (25, 25, 25))
        c.paste(bar, (0, 0))
        c.paste(t, (0, 24))
        ims.append(c)
    W = sum(i.width for i in ims) + 6 * (len(ims) - 1)
    out = Image.new("RGB", (W, max(i.height for i in ims)), (255, 255, 255))
    x = 0
    for i in ims:
        out.paste(i, (x, 0))
        x += i.width + 6
    return out


def up(im, box, scale):
    return im.crop(box).resize(((box[2] - box[0]) * scale, (box[3] - box[1]) * scale), Image.NEAREST)


def marked(im, box, scale, steps, three):
    """the crop at scale, a tick per step at (its sector's centre x, its row boundary)"""
    x0, y0, x1, y1 = box
    t = im.crop(box).resize(((x1 - x0) * scale, (y1 - y0) * scale), Image.NEAREST)
    d = ImageDraw.Draw(t)
    for s in steps:
        X, Y = (s["x"] - x0) * scale, (s["row_boundary"] - y0) * scale
        if not (0 <= X < t.width and 0 <= Y < t.height):
            continue
        half = (2.6 if s["chain"] in three else 1.6) * scale
        col = (230, 30, 30) if s["change_L_r8_lab"] < 0 else (30, 110, 255)
        d.line([(X - half, Y), (X + half, Y)], fill=col, width=max(1, scale // 2 + (1 if s["chain"] in three else 0)))
    return t


def crops():
    rec = json.load(open(D(WR10, "fix-r10.json")))
    steps = [s for sec in rec["step1"]["sectors"] for s in sec["steps"]]
    three = set(rec["step1"]["the_three_bands"]["curves"])
    T9 = Image.open(D(GRD, "variant-r9-pendant-v2-set-B-graded-v3c.png")).convert("RGB")
    n = rec["stop_rule"]["rule_2_more_than_24_sectors"]["sectors_r8_lab"]
    os.makedirs(OUT, exist_ok=True)
    # x 1 in the frame
    labelled([("R9, x 1 in the frame (R10 stopped: no after)", T9.crop((1430, 0, 1920, 430)))], 1).save(_new(D(OUT, "pendant-2-x1.png")))
    # x 2, the whole lantern
    labelled([("R9 (x 2, whole lantern)", up(T9, LANTERN, 2)), (f"R9 + steps > 1 L*: {n} of 48 sectors", marked(T9, LANTERN, 2, steps, three))],
             1).save(_new(D(OUT, "pendant-2-x2.png")))
    # x 2 on stretched L*
    a = np.asarray(T9).astype(np.float32) / 255
    L = cv2.cvtColor(a, cv2.COLOR_RGB2LAB)[..., 0]
    A = np.asarray(Image.open(D(LAY, "pendant", "pendant-cj-pleated-pumpkin-lantern-40-r9.png")))[..., 3]
    x0, y0, x1, y1 = LANTERN
    m = A[y0:y1, x0:x1] == 255
    lo, hi = np.percentile(L[y0:y1, x0:x1][m], 1), np.percentile(L[y0:y1, x0:x1][m], 99.5)
    g = np.clip((L - lo) / (hi - lo), 0, 1)
    g = np.where(A > 0, g, 0.12)
    S = Image.fromarray((np.stack([g] * 3, -1) * 255).astype(np.uint8))
    labelled([("L* stretched (measure view)", up(S, LANTERN, 2)), ("+ steps: red darker below, blue lighter", marked(S, LANTERN, 2, steps, three))],
             1).save(_new(D(OUT, "pendant-2-x2-measure.png")))
    # x 4, the left flank
    labelled([("R9 left flank (x 4)", up(T9, LEFT, 4)), ("R9 + steps", marked(T9, LEFT, 4, steps, three))], 1).save(_new(D(OUT, "pendant-2-left-x4.png")))
    # the sector map
    z = np.load(D(WR10, "pendant2-sectors-r10.npz"))
    R, rows = z["R_r8_lab_opencv"], z["rows"]
    sx, sy = 12, 3
    img = np.clip(0.5 + np.nan_to_num(R) / 5.0, 0, 1)
    img = np.where(np.isfinite(R), img, 0.1)
    im = Image.fromarray((img.T * 255).astype(np.uint8)).convert("RGB").resize((R.shape[0] * sx, R.shape[1] * sy), Image.NEAREST)
    d = ImageDraw.Draw(im)
    for s in steps:
        t = int(next(sec["sector"] for sec in rec["step1"]["sectors"] if s in sec["steps"]))
        k = int(np.nonzero(rows == s["row_boundary"])[0][0])
        col = (230, 30, 30) if s["change_L_r8_lab"] < 0 else (30, 110, 255)
        d.rectangle([t * sx + 1, k * sy - 1, t * sx + sx - 2, k * sy + 1], fill=col)
    d.line([(24 * sx, 0), (24 * sx, im.height)], fill=(255, 200, 0), width=2)
    labelled([(f"residual, sectors 0-47 (left to right) x rows {rows.min()}-{rows.max()}; steps in {n} sectors", im)], 1).save(_new(D(OUT, "pendant-2-sector-map.png")))
    print(sorted(os.listdir(OUT)))


def entries():
    rec = json.load(open(D(WR10, "fix-r10.json")))
    status = ("warm-modern tool, phase 2 R10 (code, 0 tokens, 2026-11-12): P2-2 STOPPED at step 1 on the designer's stop rule (rule 2: steps "
              "> 1 L* in %d of 48 sectors); no layer written, nothing recomposed; for master-designer (section 4.4) and the owner"
              % rec["stop_rule"]["rule_2_more_than_24_sectors"]["sectors_r8_lab"])
    out = []

    def add(eid, rel_, kind):
        p = D(HERE, rel_)
        out.append(dict(id=eid, path=BASE + rel_, kind=kind, model="code (R10, 0 tokens)", status=status, style="warm-modern", room="living-room",
                        created="2026-11-12", recipe=BASE + "fix_r10.py, make_crops_r10.py", sha256=sha(p), bytes=os.path.getsize(p)))
    add("wm-tool-ph2-r10-fix-record", "work-r10/fix-r10.json", "R10 record: P2-2 step 1 (the measure in 48 sectors), the stop rule, R9 baselines")
    add("wm-tool-ph2-r10-pendant2-sectors", "work-r10/pendant2-sectors-r10.npz", "R10: pendant 2's sector profiles, residuals and steps (numpy)")
    for p in sorted(glob.glob(D(OUT, "*.png"))):
        add("wm-tool-ph2-r10-crop-" + os.path.splitext(os.path.basename(p))[0], os.path.relpath(p, HERE), "R10 crop (R9 + the measure; no after)")
    scripts = {BASE + s: sha(D(HERE, s)) for s in ("fix_r10.py", "make_crops_r10.py")}
    e9 = json.load(open(D(LAY, "asset-manifest-entries-r9.json")))["tool_set_sha256"]
    now = {k: sha(D(REPO, k)) for k in e9}
    bad = sorted(k for k in e9 if now[k] != e9[k])
    res = dict(note="to merge into assets/manifest.json 'assets' (render-agent 2026-11-12; R10: new files only, the entries in a separate JSON for "
                    "the manager). R10 stopped on the stop rule: no layer, manifest, verification or truth was written; the tool's set is "
                    "R9's, re-hashed here",
               assets=out, scripts_sha256=scripts,
               not_written=dict(layer="layers/pendant/pendant-cj-pleated-pumpkin-lantern-40-r10.png", manifest="layers/manifest-r10.json",
                                verification="layers/verify-layers-r10.json", truths="graded/*r10*", reason="the stop rule (fix-r10.json stop_rule)"),
               tool_set_unchanged_since_r9=dict(files=len(e9), same_sha256_as_r9_entries=len(e9) - len(bad), mismatches=bad,
                                                against="layers/asset-manifest-entries-r9.json tool_set_sha256"))
    json.dump(res, open(_new(D(LAY, "asset-manifest-entries-r10.json")), "w"), indent=1, ensure_ascii=False)
    print("entries", len(out), "tool files", len(e9), "mismatches", bad)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "entries":
        entries()
    else:
        crops()
