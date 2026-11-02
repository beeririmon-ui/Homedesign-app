"""
G1.14 / G3.4: agreement between stills that share a point (pan_reproject.check on the kept renders, and on the clays as
the tool's floor), and the 3 % overscan requirement of docs/transitions-render-plan-2026-11-02.md section 3 / 6.4.
Also side-by-side sheets for the video endpoints that do not share a point (eye check of "same objects").
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
PLAN_OVS = set(C.PLAN["overscan"]["frames"])
# every still in a pan of 21 deg or more, from the transitions plan (route R): P0 M0->M0p 25, P1 M0p->M0x 35, P2 PD-35->D1 21,
# P-D D1->D2 35, T-CBoy K-boy-0->K-boy 33, T-CGirl K-girl-0->K-girl 33, T-CBath CB-0->B1 22, P-B B1->B2 35
REQUIRED = {"M0": "P0 25 deg", "M0p": "P0 25 / P1 35 deg", "M0x": "P1 35 deg", "PD-35": "P2 21 deg", "D1": "P2 21 deg, P-D 35 deg",
            "D2": "P-D 35 deg", "K-boy-0": "33 deg", "K-boy": "33 deg", "K-girl-0": "33 deg", "K-girl": "33 deg",
            "CB-0": "22 deg", "B1": "22 deg, P-B 35 deg", "B2": "P-B 35 deg"}
NOT_REQUIRED = {"H0": "PH 12 / 13 deg", "H0x": "13 deg", "H0e": "12 deg", "C0": "no pan", "S1'": "no pan", "W0": "no pan",
                "W0-in": "no pan", "MB0": "no pan", "MB-in": "no pan"}
# pairs sharing a centre of projection: (A, B, pan id, degrees)
PAIRS = [("H0", "H0x", "T-E0 pan", 13), ("H0", "H0e", "PH", 12), ("H0e", "H0x", "(H0e-H0x, 25)", 25),
         ("M0", "M0p", "P0", 25), ("M0p", "M0x", "P1", 35), ("M0", "M0x", "(M0-M0x, 60)", 60),
         ("D1", "PD-35", "P2", 21), ("D1", "D2", "P-D", 35), ("PD-35", "D2", "(PD-35-D2, 56)", 56),
         ("K-boy", "K-boy-0", "T-CBoy pan", 33), ("K-girl", "K-girl-0", "T-CGirl pan", 33),
         ("B1", "CB-0", "T-CBath pan", 22), ("B1", "B2", "P-B", 35), ("CB-0", "B2", "(CB-0-B2, 57)", 57)]
# video endpoints: different positions, the same objects must appear (eye check on a sheet)
ENDPOINTS = [("H0x", "M0", "V1 dolly"), ("M0x", "PD-35", "V2 dolly"), ("H0e", "W0-in", "V3 slide"), ("W0", "W0-in", "V4 pull-back"),
             ("S1'", "H0e", "V5 rail"), ("C0", "S1'", "V6 rail"), ("S1'", "K-boy-0", "V7 slide"), ("C0", "K-girl-0", "V8 slide"),
             ("S1'", "CB-0", "V9 slide"), ("MB-in", "C0", "V10 pull-back"), ("MB-in", "MB0", "V11 slide")]


def fn(x):
    return x.replace("'", "prime")


def pair(a, b, label, deg, imgs):
    A, B = imgs[a], imgs[b]
    out = {}
    for what in ("render", "clay"):
        try:
            r = C.pr.overlap_check(A[what], A["cam"], B[what], B["cam"], W, H,
                                   os.path.join(C.OUT, "overlays", f"pair-{fn(a)}-{fn(b)}.jpg") if what == "render" else None)
            bands = [max(abs(x["dx_px"]), abs(x["dy_px"])) for x in r["bands"]]
            r["worst_band_px"] = round(max(bands), 2)
            r["bands_pass_2px"] = bool(max(bands) <= 2.0)
            r["dL_mean"] = round(abs(r["L_mean"]["a"] - r["L_mean"]["b"]), 2)
            out[what] = r
        except Exception as e:  # noqa: BLE001
            out[what] = dict(error=str(e)[:200])
    out.update(a=a, b=b, pan=label, degrees=deg)
    rr, rc = out.get("render", {}), out.get("clay", {})
    print(f"{a:7s} -> {b:8s} {label:14s} {deg:3d}deg | render shift {rr.get('shift_px')} worst band {rr.get('worst_band_px')} dE {rr.get('deltaE', {}).get('mean')} dL {rr.get('dL_mean')} "
          f"| clay worst band {rc.get('worst_band_px')} shift {rc.get('shift_px', {}).get('response') if rc.get('shift_px') else rc.get('error')}")
    return out


def endpoint_sheet(a, b, label, imgs):
    A = C.pr.to8(C.pr.fit(imgs[a]["render"], 960, 540))
    B = C.pr.to8(C.pr.fit(imgs[b]["render"], 960, 540))
    sheet = np.concatenate([A, B], axis=1)
    sheet = cv2.cvtColor(sheet, cv2.COLOR_RGB2BGR)
    cv2.putText(sheet, f"{a}  ->  {b}   {label}", (12, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
    cv2.imwrite(os.path.join(C.OUT, "overlays", f"endpoints-{fn(a)}-{fn(b)}.jpg"), sheet, [cv2.IMWRITE_JPEG_QUALITY, 80])


if __name__ == "__main__":
    imgs = {}
    for f in C.MASTERS + C.POSES:
        d = C.load(f)
        imgs[f] = dict(render=d["graded"], clay=d["clay"], cam=d["cam"], ovs=d["ovs"], frame_ok=d.get("frame_file_matches_crop"))
    res = [pair(a, b, l, deg, imgs) for a, b, l, deg in PAIRS]
    json.dump(res, open(os.path.join(C.OUT, "data", "pairs.json"), "w"), indent=1)
    for a, b, l in ENDPOINTS:
        endpoint_sheet(a, b, l, imgs)
    ovs = {}
    for f in C.MASTERS + C.POSES:
        req = f in REQUIRED
        applied = imgs[f]["ovs"]
        ovs[f] = dict(required=req, why=REQUIRED.get(f, NOT_REQUIRED.get(f)), applied=applied, in_plan_overscan_list=f in PLAN_OVS,
                      frame_file_matches_centre_crop=imgs[f]["frame_ok"], pass_=bool(applied or not req),
                      note=("clay and job sent at 16:9 before the request; the pan gap at this still stays for inpainting (README round 4, 6)"
                            if req and not applied else None))
    json.dump(ovs, open(os.path.join(C.OUT, "data", "overscan.json"), "w"), indent=1)
    for f, v in ovs.items():
        print(f"{f:9s} overscan required {v['required']!s:5} applied {v['applied']!s:5} crop-file ok {v['frame_file_matches_centre_crop']} -> {'pass' if v['pass_'] else 'FAIL'}")
