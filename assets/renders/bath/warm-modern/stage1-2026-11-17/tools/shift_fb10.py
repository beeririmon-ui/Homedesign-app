#!/usr/bin/env python3
"""
shift_fb10.py: after QA of FB10 (qa/reports/2026-11-18-bath-fb10), render-agent 2026-11-18. 0 tokens.
Runs after compose_fb10.py:
  1. the designer's ruling on the right gap (0.005 not accepted): the rope basket and the waffle stack move left together by
     40 px, 0.0156 of the frame's width (QA: 0.0155-0.016 balances the two ends; 41 px would leave the left end at 0.0199 by
     QA's reading), their shadows with them, by whole pixels (no resampling). The stack slides along the shelf (6.5 cm, so
     40 px left and 10 px up, the shelf's own line): it keeps its depth, 5 cm behind the board's front edge (a level move
     would have brought it to 1.5 cm from it). The basket moves level (4.4 cm along and 3.4 cm forward): its foot is below
     the canvas, and a rise would cut it flat in the overscan.
     What the move uncovers shows the plate (the bare shelf), as every pixel outside the layers does.
  2. B2F-L1: the basket's lower-left corner (canvas x 1745-1772, rows 1472-1494 before the move): a light wedge of shelf and a
     thin dark arc inside the alpha; the alpha there keeps only the rope (L* over 55), soft-edged, its edge pixels coloured
     from the rope just inside, so the corner closes on a clean curve against the walnut.
Then the composites (defaults, linen, khaki) are recomposed from the files (RND2: outside every alpha, shadow and light,
plate.png byte for byte).

  python3 shift_fb10.py
"""
import json
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ST = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import compose_defaults as C  # noqa: E402
import compose_fb10 as F  # noqa: E402
import grade_plate as G  # noqa: E402

FW = 2642.51 - 77.49           # the frame box's width on the canvas
SHIFT_PX = 40                  # 0.0156 of the frame
SHIFT = {"bath-towels": (-40, -10), "storage-basket": (-40, 0)}   # (dx, dy) px
SLOTS = ("bath-towels", "storage-basket")
CORNER = (1745, 1472, 1773, 1495)   # x0, y0, x1, y1 of B2F-L1, before the move


def shift(a, dx, dy, fill):
    """move by whole pixels (dx, dy <= 0: left and up)"""
    out = np.full_like(a, fill)
    H, W = a.shape[:2]
    out[:H + dy, :W + dx] = a[-dy:, -dx:]
    return out


def heal_corner(rgba):
    x0, y0, x1, y1 = CORNER
    rgb = rgba[..., :3].astype(np.float64) / 255
    a = rgba[..., 3].astype(np.float64) / 255
    L = G.to_lab(rgb[y0 - 6:y1 + 6, x0 - 6:x1 + 6])[..., 0]
    rope = np.zeros(a.shape, bool)
    rope[y0 - 6:y1 + 6, x0 - 6:x1 + 6] = (L > 55) & (a[y0 - 6:y1 + 6, x0 - 6:x1 + 6] > 0)
    reg = np.zeros(a.shape, bool)
    reg[y0:y1, x0:x1] = True
    body = ((a >= 0.5) & ~reg) | (rope & reg)               # the rope only, inside the corner; the rest as it was
    na = np.where(reg, np.minimum(C.soft(body), a), a)      # the corner's alpha can only shrink
    nrgb = np.where(reg[..., None], C.defringe(rgb, body), rgb)
    out = rgba.copy()
    out[..., :3] = C.q(nrgb)
    out[..., 3] = C.q(na)
    out[..., :3][out[..., 3] == 0] = 0
    changed = int((out[..., 3] != rgba[..., 3]).sum() + (np.abs(out[..., :3].astype(int) - rgba[..., :3]).max(2) > 0).sum())
    return out, dict(region=list(CORNER), alpha_px_before=int((rgba[..., 3][reg] > 0).sum()), alpha_px_after=int((out[..., 3][reg] > 0).sum()),
                     px_changed=changed)


def main():
    man_p = os.path.join(ST, "layers", "manifest.json")
    man = json.load(open(man_p))
    if not man.get("fb10"):
        sys.exit("run compose_fb10.py first")
    if man.get("fb10_shift"):
        sys.exit("the shelf shift is already applied: re-run the chain (compose_defaults, --recolour, post_b2, compose_fb10) first")
    n = SHIFT_PX
    plate = np.asarray(Image.open(os.path.join(ST, "plate.png")).convert("RGB"))
    rec = dict(date="2026-11-18", tool="tools/shift_fb10.py", source="qa/reports/2026-11-18-bath-fb10 (3b, B2F-L1); the designer's ruling on the right gap",
               shift_u=round(n / FW, 5), shift_px={k: list(v) for k, v in SHIFT.items()}, slots=list(SLOTS))
    lay = {l["slot"]: l for l in man["layers"]}
    for k in SLOTS:
        l = lay[k]
        rgba = np.asarray(Image.open(os.path.join(ST, l["layer"])))
        s8 = np.asarray(Image.open(os.path.join(ST, l["shadow"])))
        if k == "storage-basket":
            rgba, rec["b2f_l1"] = heal_corner(rgba)
        dx, dy = SHIFT[k]
        rgba2 = shift(rgba, dx, dy, 0)
        s2 = shift(s8, dx, dy, 255)
        Image.fromarray(rgba2, "RGBA").save(os.path.join(ST, l["layer"]))
        Image.fromarray(s2).save(os.path.join(ST, l["shadow"]))
        ys, xs = np.nonzero((rgba2[..., 3] > 0) | (s2 < 255))
        l.update(alpha_px=int((rgba2[..., 3] > 0).sum()), shadow_px=int((s2 < 255).sum()),
                 bbox_px=[int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1], shifted_px=list(SHIFT[k]))
    F_ = F.files(man)
    L8 = np.asarray(Image.open(os.path.join(ST, man["light"]["file"])).convert("RGB"))

    def region_of(pairs):
        r = L8.max(2) > 0
        for rgba, s8 in pairs:
            r |= (rgba[..., 3] > 0) | (s8 < 255)
        return r

    out = {}
    o8 = C.q(F.stack(man, plate, F_))
    Image.fromarray(o8).save(os.path.join(ST, "b2-defaults.png"))
    C.frame_png(o8, os.path.join(ST, "b2-defaults-frame.png"))
    reg = region_of(F_.values())
    out["defaults"] = int((np.abs(o8.astype(int) - plate.astype(int)).max(2)[~reg] > 0).sum())
    for v in man["variants"]:
        sw = {v["slot"]: (np.asarray(Image.open(os.path.join(ST, v["layer"]))), np.asarray(Image.open(os.path.join(ST, v["shadow"]))))}
        ov = C.q(F.stack(man, plate, F_, swap=sw))
        name = v["composite"].rsplit(".", 1)[0]
        Image.fromarray(ov).save(os.path.join(ST, name + ".png"))
        C.frame_png(ov, os.path.join(ST, name + "-frame.png"))
        rv = region_of(list(F_.values()) + list(sw.values()))
        out[name] = int((np.abs(ov.astype(int) - plate.astype(int)).max(2)[~rv] > 0).sum())
        swap_reg = (sw[v["slot"]][0][..., 3] > 0) | (sw[v["slot"]][1] < 255) | (F_[v["slot"]][0][..., 3] > 0) | (F_[v["slot"]][1] < 255)
        d = np.abs(ov.astype(int) - o8.astype(int)).max(2) > 0
        v["outside_differing_px_vs_plate"] = out[name]
        v["differing_px_vs_defaults_outside_the_swap_region"] = int((d & ~swap_reg).sum())
    man["rnd2"] = dict(region_px=int(reg.sum()), outside_differing_px=out["defaults"], rule=man["rnd2"]["rule"])
    rec["rnd2_outside_differing_px"] = out
    man["fb10_shift"] = rec
    json.dump(man, open(man_p, "w"), indent=1, ensure_ascii=False)
    print(json.dumps(rec))


if __name__ == "__main__":
    main()
