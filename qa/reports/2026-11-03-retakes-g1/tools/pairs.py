"""
G1.14 / G3.4 on the retakes: pan_reproject.check between every pair of stills that share a centre of projection (the pan
participants of the brief), on the graded-v3 files and on the clays (the tool's floor); identity checks of each retake against
its v7 predecessor (same camera: how far the retake moved); endpoint sheets for the video pairs that do not share a point
(W0 -> W0-in is a dolly: `check` is not valid there and is reported as informational only); and the 3 % overscan requirement
of docs/transitions-render-plan-2026-11-02.md section 3 / 6.4 (every still in a pan of 21 deg or more).
Writes data/pairs.json, data/overscan.json, overlays/pair-<a>-<b>.jpg, overlays/endpoints-<a>-<b>.jpg.
"""
import json
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402

W, H = 1920, 1080
# (A, B, label, degrees, valid: same centre of projection)
PAIRS = [("K-girl fix", "K-girl-0 r2", "T-CGirl pan (K-girl -> K-girl-0)", 33, True),
         ("B1 r3", "B2 r3", "P-B pan", 35, True),
         ("B1 r3", "CB-0", "T-CBath pan (CB-0 -> B1)", 22, True),
         ("CB-0", "B2 r3", "(CB-0 -> B2, 57 deg, informational)", 57, True),
         ("B1", "B1 r3", "identity: B1 v7 vs B1 r3 (same camera)", 0, True),
         ("B2", "B2 r3", "identity: B2 v7 vs B2 r3 (same camera)", 0, True),
         ("K-girl-0", "K-girl-0 r2", "identity: K-girl-0 v7 vs r2 (same camera)", 0, True),
         ("W0-in", "W0-in r2", "identity: W0-in v7 vs r2 (same camera)", 0, True),
         ("W0 fix", "W0-in r2", "V4 pull-back / T-HW slide: a dolly, NOT a pan: check is not valid (parallax); informational", 0, False)]
ENDPOINTS = [("W0 fix", "W0-in r2", "V4 pull-back (W0 <-> W0-in)"), ("K-girl fix", "K-girl-0 r2", "T-CGirl pan"), ("B1 r3", "B2 r3", "P-B pan"),
             ("CB-0", "B1 r3", "T-CBath pan"), ("B1", "B1 r3", "B1 v7 -> r3"), ("B2", "B2 r3", "B2 v7 -> r3"),
             ("K-girl-0", "K-girl-0 r2", "K-girl-0 v7 -> r2"), ("W0-in", "W0-in r2", "W0-in v7 -> r2")]
OVS_REQUIRED = {"W0-in r2": (False, "no pan: end of the V4 pull-back / T-HW slide"), "K-girl-0 r2": (True, "T-CGirl pan 33 deg"),
                "B1 r3": (True, "T-CBath 22 deg, P-B 35 deg"), "B2 r3": (True, "P-B 35 deg")}


def pair(a, b, label, deg, valid, imgs):
    A, B = imgs[a], imgs[b]
    out = dict(a=a, b=b, pan=label, degrees=deg, same_centre=valid)
    for what in ("render", "clay"):
        try:
            r = C.pr.overlap_check(A[what], A["cam"], B[what], B["cam"], W, H,
                                   os.path.join(C.OUT, "overlays", f"pair-{C.fn(a)}-{C.fn(b)}.jpg") if what == "render" else None)
            bands = [max(abs(x["dx_px"]), abs(x["dy_px"])) for x in r["bands"]]
            bands_rel = [max(abs(x["dx_px"]), abs(x["dy_px"])) for x in r["bands"] if x["response"] >= 0.05]
            r["worst_band_px"] = round(max(bands), 2)
            r["worst_band_px_reliable"] = round(max(bands_rel), 2) if bands_rel else None
            r["bands_reliable"] = len(bands_rel)
            r["bands_pass_2px"] = bool(max(bands) <= 2.0)
            r["dL_mean"] = round(abs(r["L_mean"]["a"] - r["L_mean"]["b"]), 2)
            out[what] = r
        except Exception as e:  # noqa: BLE001
            out[what] = dict(error=str(e)[:200])
    rr, rc = out.get("render", {}), out.get("clay", {})
    print(f"{a:12s} -> {b:12s} {deg:3d} deg | render shift {rr.get('shift_px')} worst band {rr.get('worst_band_px')} (reliable {rr.get('worst_band_px_reliable')}, {rr.get('bands_reliable')}) "
          f"dE {rr.get('deltaE', {}).get('mean')} dL {rr.get('dL_mean')} | clay worst band {rc.get('worst_band_px')} | {label}")
    return out


def endpoint_sheet(a, b, label, imgs):
    A = C.pr.to8(C.pr.fit(imgs[a]["render"], 960, 540))
    B = C.pr.to8(C.pr.fit(imgs[b]["render"], 960, 540))
    sheet = cv2.cvtColor(np.concatenate([A, B], axis=1), cv2.COLOR_RGB2BGR)
    cv2.putText(sheet, f"{a}  ->  {b}   {label}", (12, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
    cv2.imwrite(os.path.join(C.OUT, "overlays", f"endpoints-{C.fn(a)}-{C.fn(b)}.jpg"), sheet, [cv2.IMWRITE_JPEG_QUALITY, 80])


if __name__ == "__main__":
    need = sorted({x for p in PAIRS for x in p[:2]} | {x for e in ENDPOINTS for x in e[:2]})
    imgs = {}
    for f in need:
        d = C.load(f, raw=False)
        imgs[f] = dict(render=d["graded"], clay=d["clay"], cam=d["cam"], ovs=d["ovs"], frame_ok=d.get("frame_file_matches_crop"),
                       frame_diff=d.get("frame_file_max_diff"), size=d["graded_size"])
    res = [pair(a, b, l, deg, v, imgs) for a, b, l, deg, v in PAIRS]
    json.dump(res, open(os.path.join(C.OUT, "data", "pairs.json"), "w"), indent=1)
    for a, b, l in ENDPOINTS:
        endpoint_sheet(a, b, l, imgs)
    ovs = {}
    for f in C.RETAKES:
        req, why = OVS_REQUIRED[f]
        applied = imgs[f]["ovs"]
        ovs[f] = dict(required=req, why=why, applied=applied, canvas_px=imgs[f]["size"], in_plan_overscan_list=C.STILLS[f][0] in set(C.PLAN["overscan"]["frames"]),
                      frame_file_matches_centre_crop=imgs[f]["frame_ok"], frame_file_max_diff_8bit=imgs[f]["frame_diff"], passed=bool(applied or not req))
        print(f"{f:12s} overscan required {req!s:5} applied {applied!s:5} canvas {imgs[f]['size']} frame-file = centre crop: {imgs[f]['frame_ok']} (max diff {imgs[f]['frame_diff']}) -> {'pass' if ovs[f]['passed'] else 'FAIL'}")
    json.dump(ovs, open(os.path.join(C.OUT, "data", "overscan.json"), "w"), indent=1)
