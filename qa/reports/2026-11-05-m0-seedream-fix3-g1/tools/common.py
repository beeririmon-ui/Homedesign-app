"""
qa-agent, 2026-11-05: G1 on M0 1.2 from the three-model test (seedream-5-pro raw + code composite) and on the fix3 round.
Builds on the 11-04 (second round) registry, imported (not edited). Writes under qa/reports/2026-11-05-m0-seedream-fix3-g1/.
"""
import importlib.util
import os

REPO = "/home/user/homedesign-app"
OUT = os.path.join(REPO, "qa/reports/2026-11-05-m0-seedream-fix3-g1")
_s = importlib.util.spec_from_file_location("qa1104b_common", os.path.join(REPO, "qa/reports/2026-11-04-m0-fix2-cb0-g1/tools/common.py"))
C5 = importlib.util.module_from_spec(_s)
_s.loader.exec_module(C5)
C3 = C5.C3
pr = C3.pr
P = "assets/renders"
V9 = f"{P}/living-room/nordic/v9"
# (frame key, kind, graded, raw (geometry), clay relative to round4/, selfcheck tag, cam, overscan, room, base)
NEW = {
    "M0 seedream raw":  ("M0 1.2", "m0s", f"{V9}/m0-shell-seedream-graded-v5.png", f"{V9}/m0-shell-seedream.png", "../round5b/M0.png", "r5b:M0", (25, .47, .50), True, "living", "M0 1.2"),
    "M0 seedream fix":  ("M0 1.2", "m0s", f"{V9}/m0-1-2-shell-seedream-graded-fix-v5.png", f"{V9}/m0-1-2-shell-seedream-fix.png", "../round5b/M0.png", "r5b:M0", (25, .47, .50), True, "living", "M0 1.2"),
    "M0p 1.2 fix3":     ("M0p 1.2", "fix3", f"{P}/poses/nordic/v8/pose-m0p-v8b-graded-fix3-v5.png", f"{P}/poses/nordic/v8/pose-m0p-v8b-fix3.png", "../round5b/poses/M0p.png", "r5b:M0p", (0, .47, .50), True, "living", "M0 1.2"),
    "B1 r3 fix3":       ("B1", "fix3", f"{P}/bath/nordic/v7/b1-v7-r3-graded-fix3-v5.png", f"{P}/bath/nordic/v7/b1-v7-r3-fix3.png", "r3-2026-11-03/B1.png", "r3", (-22, .52, .46), True, "bath", "B1"),
    "CB-0 b1r3f3":      ("CB-0", "cb0", f"{P}/poses/nordic/v7/pose-cb-0-v7-graded-b1r3f3-v5.png", f"{P}/poses/nordic/v7/pose-cb-0-v7-b1r3f3.png", "poses/CB-0.png", "r4", (0, .50, .46), True, "bath", "B1"),
    "W0-in r2 fix3":    ("W0-in", "fix3", f"{P}/poses/nordic/v7/pose-w0-in-v7-r2-graded-fix3-v5.png", f"{P}/poses/nordic/v7/pose-w0-in-v7-r2-fix3.png", "poses/W0-in.png", "r4", (0, .50, .46), False, "work", "W0"),
    "K-girl-0 r2 fix3": ("K-girl-0", "fix3", f"{P}/poses/nordic/v7/pose-k-girl-0-v7-r2-graded-fix3-v5.png", f"{P}/poses/nordic/v7/pose-k-girl-0-v7-r2-fix3.png", "poses/K-girl-0.png", "r4", (0, .50, .46), True, "girl", "K-girl"),
}
C3.STILLS.update(NEW)
load, at, boxes, fn, rgb, crop_canvas = C3.load, C3.at, C3.boxes, C3.fn, C3.rgb, C3.crop_canvas
FIX3 = ["B1 r3 fix3", "CB-0 b1r3f3", "W0-in r2 fix3", "M0p 1.2 fix3", "K-girl-0 r2 fix3"]
M0S = ["M0 seedream raw", "M0 seedream fix"]
for _d in ("data", "overlays"):
    os.makedirs(os.path.join(OUT, _d), exist_ok=True)
