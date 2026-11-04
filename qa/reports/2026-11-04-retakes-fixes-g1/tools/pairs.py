"""
G1.14 / G3.4 on the pairs the fixes are meant to unblock (graded-v4 / graded-fix-v4 files): pan_reproject.check in the overlap,
on the renders and on the clays (the tool's floor), plus the endpoint sheets by eye:
  P-B      B1 r3 fix -> B2 r3 fix (35 deg)
  T-CGirl  K-girl fix (graded-fix-v4) -> K-girl-0 r2 fix (33 deg)
  T-CBath  B1 r3 fix -> CB-0 (22 deg): today's CB-0 is still the v7 composite (no r3 clay of CB-0 exists)
  T-HW/V4  W0 fix -> W0-in r2 fix: a dolly (parallax): no check, the sheet only
Writes data/pairs.json and overlays/pair-*.jpg, overlays/endpoints-*.jpg.
"""
import json
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402

W, H = 1920, 1080
PAIRS = [("B1 r3 fix", "B2 r3 fix", "P-B pan", 35), ("K-girl fix", "K-girl-0 r2 fix", "T-CGirl pan (K-girl -> K-girl-0)", 33),
         ("B1 r3 fix", "CB-0", "T-CBath pan (CB-0 -> B1), today's CB-0 (v7 composite)", 22),
         ("B1 r3", "B2 r3", "P-B on 11-03 (raw retakes, graded v3)", 35), ("K-girl fix", "K-girl-0 r2", "T-CGirl on 11-03", 33)]


def check(A, B, label, deg, imgs, clayA=None, clayB=None):
    out = dict(a=A, b=B, pan=label, degrees=deg)
    for what in ("render", "clay"):
        a = imgs[A][what] if what == "render" else (clayA if clayA is not None else imgs[A]["clay"])
        b = imgs[B][what] if what == "render" else (clayB if clayB is not None else imgs[B]["clay"])
        r = C.pr.overlap_check(a, imgs[A]["cam"], b, imgs[B]["cam"], W, H,
                               os.path.join(C.OUT, "overlays", f"pair-{C.fn(A)}-{C.fn(B)}.jpg") if what == "render" else None)
        bands = [max(abs(x["dx_px"]), abs(x["dy_px"])) for x in r["bands"]]
        rel = [max(abs(x["dx_px"]), abs(x["dy_px"])) for x in r["bands"] if x["response"] >= 0.05]
        r.update(worst_band_px=round(max(bands), 2), worst_band_px_reliable=round(max(rel), 2) if rel else None, bands_reliable=len(rel),
                 dL_mean=round(abs(r["L_mean"]["a"] - r["L_mean"]["b"]), 2))
        out[what] = r
    rr, rc = out["render"], out["clay"]
    print(f"{A:12s} -> {B:16s} {deg:3d} | render bands {[ (round(x['dx_px'],1), round(x['dy_px'],1), x['response']) for x in rr['bands']]} reliable worst {rr['worst_band_px_reliable']} ({rr['bands_reliable']}) "
          f"dL {rr['dL_mean']} dE {rr['deltaE']['mean']} | clay worst {rc['worst_band_px']} | {label}")
    return out


def sheet(a, b, label, imgs):
    A = C.pr.to8(C.pr.fit(imgs[a]["render"], 960, 540))
    B = C.pr.to8(C.pr.fit(imgs[b]["render"], 960, 540))
    s = cv2.cvtColor(np.concatenate([A, B], axis=1), cv2.COLOR_RGB2BGR)
    cv2.putText(s, f"{a}  ->  {b}   {label}", (12, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
    cv2.imwrite(os.path.join(C.OUT, "overlays", f"endpoints-{C.fn(a)}-{C.fn(b)}.jpg"), s, [cv2.IMWRITE_JPEG_QUALITY, 82])


if __name__ == "__main__":
    need = sorted({x for p in PAIRS for x in p[:2]} | {"W0 fix", "W0-in r2 fix"})
    imgs = {}
    for f in need:
        d = C.load(f, raw=False)
        imgs[f] = dict(render=d["graded"], clay=d["clay"], cam=d["cam"])
    res = []
    for a, b, l, deg in PAIRS:
        res.append(check(a, b, l, deg, imgs))
    res[2]["clay_note"] = ("no r3 clay of CB-0 exists (round4/r3-2026-11-03/poses/ is empty): the floor here is the B1 r3 clay against the round-4 CB-0 "
                           "clay, which has no planter / brush placeholders, so it is not a pure tool floor")
    json.dump(res, open(os.path.join(C.OUT, "data", "pairs.json"), "w"), indent=1)
    for a, b, l in [("B1 r3 fix", "B2 r3 fix", "P-B"), ("K-girl fix", "K-girl-0 r2 fix", "T-CGirl"), ("CB-0", "B1 r3 fix", "T-CBath"), ("W0 fix", "W0-in r2 fix", "V4 / T-HW (dolly)")]:
        sheet(a, b, l, imgs)
