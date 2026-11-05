"""
qa-agent 2026-11-04 (second round): G1.14 on the pairs this round is meant to unblock (graded v5 files), pan_reproject.check in
the overlap on the renders and on the clays (the tool's floor), plus endpoint sheets:
  P0       M0 1.2 fix -> M0p 1.2 fix (25 deg)          P1   M0p 1.2 fix -> M0x 1.2 fix (35 deg)
  P-B      B1 r3 fix2 -> B2 r3 fix2 (35 deg)            T-CGirl  K-girl fix -> K-girl-0 r2 fix2 (33 deg)
  T-CBath  B1 r3 fix2 -> CB-0 b1r3 (22 deg; CB-0 is reprojected from B1 r3 fix2, so this is a consistency check of the build)
  V4/T-HW  W0 fix -> W0-in r2 fix2: a dolly (parallax): the sheet only
Writes data/pairs.json, overlays/pair-*.jpg, overlays/endpoints-*.jpg. Usage: ~/.venvs/motion/bin/python -I pairs.py
"""
import json
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402

W, H = 1920, 1080
PAIRS = [("M0 1.2 fix", "M0p 1.2 fix", "P0 pan", 25), ("M0p 1.2 fix", "M0x 1.2 fix", "P1 pan", 35),
         ("B1 r3 fix2", "B2 r3 fix2", "P-B pan", 35), ("K-girl fix", "K-girl-0 r2 fix2", "T-CGirl pan (K-girl -> K-girl-0)", 33),
         ("B1 r3 fix2", "CB-0 b1r3", "T-CBath pan (CB-0 -> B1)", 22)]


def check(A, B, label, deg, imgs):
    out = dict(a=A, b=B, pan=label, degrees=deg)
    for what in ("render", "clay"):
        a, b = imgs[A][what], imgs[B][what]
        r = C.pr.overlap_check(a, imgs[A]["cam"], b, imgs[B]["cam"], W, H,
                               os.path.join(C.OUT, "overlays", f"pair-{C.fn(A)}-{C.fn(B)}.jpg") if what == "render" else None)
        bands = [max(abs(x["dx_px"]), abs(x["dy_px"])) for x in r["bands"]]
        rel = [max(abs(x["dx_px"]), abs(x["dy_px"])) for x in r["bands"] if x["response"] >= 0.05]
        r.update(worst_band_px=round(max(bands), 2), worst_band_px_reliable=round(max(rel), 2) if rel else None, bands_reliable=len(rel),
                 dL_mean=round(abs(r["L_mean"]["a"] - r["L_mean"]["b"]), 2))
        out[what] = r
    rr, rc = out["render"], out["clay"]
    print(f"{A:12s} -> {B:16s} {deg:3d} | render bands {[(round(x['dx_px'], 1), round(x['dy_px'], 1), x['response']) for x in rr['bands']]} reliable worst {rr['worst_band_px_reliable']} ({rr['bands_reliable']}) "
          f"dL {rr['dL_mean']} dE {rr['deltaE']['mean']} | clay worst {rc['worst_band_px']} reliable {rc['worst_band_px_reliable']} | {label}")
    return out


def sheet(a, b, label, imgs):
    A = C.pr.to8(C.pr.fit(imgs[a]["render"], 960, 540))
    B = C.pr.to8(C.pr.fit(imgs[b]["render"], 960, 540))
    s = cv2.cvtColor(np.concatenate([A, B], axis=1), cv2.COLOR_RGB2BGR)
    cv2.putText(s, f"{a}  ->  {b}   {label}", (12, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
    cv2.imwrite(os.path.join(C.OUT, "overlays", f"endpoints-{C.fn(a)}-{C.fn(b)}.jpg"), s, [cv2.IMWRITE_JPEG_QUALITY, 82])


if __name__ == "__main__":
    need = sorted({x for p in PAIRS for x in p[:2]} | {"W0 fix", "W0-in r2 fix2"})
    imgs = {}
    for f in need:
        d = C.load(f, raw=False)
        imgs[f] = dict(render=d["graded"], clay=d["clay"], cam=d["cam"])
    res = [check(a, b, l, deg, imgs) for a, b, l, deg in PAIRS]
    res[4]["clay_note"] = "no r3 clay of CB-0 (round4/r3-2026-11-03/poses/ is empty): the floor is the B1 r3 clay against the round-4 CB-0 clay (no planter / brush proxies)"
    json.dump(res, open(os.path.join(C.OUT, "data", "pairs.json"), "w"), indent=1)
    for a, b, l in [("M0 1.2 fix", "M0p 1.2 fix", "P0"), ("M0p 1.2 fix", "M0x 1.2 fix", "P1"), ("B1 r3 fix2", "B2 r3 fix2", "P-B"),
                    ("K-girl fix", "K-girl-0 r2 fix2", "T-CGirl"), ("CB-0 b1r3", "B1 r3 fix2", "T-CBath"), ("W0 fix", "W0-in r2 fix2", "V4 / T-HW (dolly)")]:
        sheet(a, b, l, imgs)
