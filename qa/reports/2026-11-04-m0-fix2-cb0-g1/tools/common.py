"""
qa-agent, 2026-11-04 (second round): G1 on the M0 1.2 composites, the four fix2 frames, CB-0 recomposed from B1 r3, grading v5.
Builds on the 11-03 loaders (imported through the 11-04 registry, not edited). Writes under qa/reports/2026-11-04-m0-fix2-cb0-g1/.
"""
import importlib.util
import json
import os

REPO = "/home/user/homedesign-app"
OUT = os.path.join(REPO, "qa/reports/2026-11-04-m0-fix2-cb0-g1")
_s = importlib.util.spec_from_file_location("qa1104_common", os.path.join(REPO, "qa/reports/2026-11-04-retakes-fixes-g1/tools/common.py"))
C4 = importlib.util.module_from_spec(_s)
_s.loader.exec_module(C4)
C3 = C4.C3
pr = C3.pr
R5B = os.path.join(REPO, "assets/blockout/house/framing/round5b")
SC5B = json.load(open(os.path.join(R5B, "selfcheck.json")))["frames"]
P = "assets/renders"
# (frame key, kind, graded, raw (geometry), clay relative to round4/, selfcheck tag, cam, overscan, room, base)
NEW = {
    "M0 1.2 fix":   ("M0 1.2",   "m0fix", f"{P}/living-room/nordic/v8/m0-v8b-r2-graded-fix-v5.png", f"{P}/living-room/nordic/v8/m0-v8b-r2-fix.png", "../round5b/M0.png",        "r5b:M0",  (25, .47, .50),  True, "living", "M0 1.2"),
    "M0 1.2 r2":    ("M0 1.2",   "m0raw", f"{P}/living-room/nordic/v8/m0-v8b-r2-graded-v4.png",     f"{P}/living-room/nordic/v8/m0-v8b-r2.png",     "../round5b/M0.png",        "r5b:M0",  (25, .47, .50),  True, "living", "M0 1.2"),
    "M0p 1.2 fix":  ("M0p 1.2",  "m0fix", f"{P}/poses/nordic/v8/pose-m0p-v8b-graded-fix-v5.png",   f"{P}/poses/nordic/v8/pose-m0p-v8b-fix.png",    "../round5b/poses/M0p.png", "r5b:M0p", (0, .47, .50),   True, "living", "M0 1.2"),
    "M0x 1.2 fix":  ("M0x 1.2",  "m0fix", f"{P}/poses/nordic/v8/pose-m0x-v8b-graded-fix-v5.png",   f"{P}/poses/nordic/v8/pose-m0x-v8b-fix.png",    "../round5b/poses/M0x.png", "r5b:M0x", (-35, .47, .50), True, "living", "M0 1.2"),
    "B1 r3 fix2":       ("B1",       "fix2", f"{P}/bath/nordic/v7/b1-v7-r3-graded-fix2-v5.png",             f"{P}/bath/nordic/v7/b1-v7-r3-fix2.png",             "r3-2026-11-03/B1.png", "r3", (-22, .52, .46), True,  "bath", "B1"),
    "B2 r3 fix2":       ("B2",       "fix2", f"{P}/bath/nordic/v7/b2-v7-r3-graded-fix2-v5.png",             f"{P}/bath/nordic/v7/b2-v7-r3-fix2.png",             "r3-2026-11-03/B2.png", "r3", (-57, .52, .46), True,  "bath", "B1"),
    "K-girl-0 r2 fix2": ("K-girl-0", "fix2", f"{P}/poses/nordic/v7/pose-k-girl-0-v7-r2-graded-fix2-v5.png", f"{P}/poses/nordic/v7/pose-k-girl-0-v7-r2-fix2.png", "poses/K-girl-0.png",   "r4", (0, .50, .46),   True,  "girl", "K-girl"),
    "W0-in r2 fix2":    ("W0-in",    "fix2", f"{P}/poses/nordic/v7/pose-w0-in-v7-r2-graded-fix2-v5.png",    f"{P}/poses/nordic/v7/pose-w0-in-v7-r2-fix2.png",    "poses/W0-in.png",      "r4", (0, .50, .46),   False, "work", "W0"),
    "CB-0 b1r3":        ("CB-0",     "cb0",  f"{P}/poses/nordic/v7/pose-cb-0-v7-graded-b1r3-v5.png",        f"{P}/poses/nordic/v7/pose-cb-0-v7-b1r3.png",        "poses/CB-0.png",       "r4", (0, .50, .46),   True,  "bath", "B1"),
}
PREV = {"B1 r3 fix2": "B1 r3 fix", "B2 r3 fix2": "B2 r3 fix", "K-girl-0 r2 fix2": "K-girl-0 r2 fix", "W0-in r2 fix2": "W0-in r2 fix", "M0 1.2 fix": "M0 1.2 r2", "CB-0 b1r3": "CB-0"}
JOB = {"B1 r3 fix2": "b1-v7-r3", "B2 r3 fix2": "b2-v7-r3", "K-girl-0 r2 fix2": "pose-k-girl-0-v7-r2", "W0-in r2 fix2": "pose-w0-in-v7-r2",
       "M0 1.2 fix": "m0-v8b-r2", "M0p 1.2 fix": "pose-m0p-v8b", "M0x 1.2 fix": "pose-m0x-v8b", "CB-0 b1r3": "pose-cb-0-v7"}
C3.STILLS.update(NEW)

_orig_selfcheck = C3.selfcheck


def _selfcheck(sid):
    t = C3.STILLS[sid]
    if t[5].startswith("r5b:"):
        return SC5B[t[5].split(":")[1]]
    return _orig_selfcheck(sid)


C3.selfcheck = _selfcheck
load, at, boxes, fn, rgb, crop_canvas = C3.load, C3.at, C3.boxes, C3.fn, C3.rgb, C3.crop_canvas
FIX2 = ["B1 r3 fix2", "B2 r3 fix2", "K-girl-0 r2 fix2", "W0-in r2 fix2"]
M012 = ["M0 1.2 fix", "M0p 1.2 fix", "M0x 1.2 fix"]
for _d in ("data", "overlays"):
    os.makedirs(os.path.join(OUT, _d), exist_ok=True)
