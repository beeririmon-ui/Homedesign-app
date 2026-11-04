"""
qa-agent, G1 on the four zero-token code fixes of 2026-11-04 and the grading v4 (30 rows): registry and loaders.
Re-uses the loaders of qa/reports/2026-11-03-retakes-g1/tools/common.py (imported, not edited); everything written goes under
qa/reports/2026-11-04-retakes-fixes-g1/. Run with ~/.venvs/motion/bin/python. No network, no installs, no var2.
"""
import importlib.util
import os
import sys

REPO = "/home/user/homedesign-app"
OUT = os.path.join(REPO, "qa/reports/2026-11-04-retakes-fixes-g1")
_prev = os.path.join(REPO, "qa/reports/2026-11-03-retakes-g1/tools/common.py")
_spec = importlib.util.spec_from_file_location("qa1103_common", _prev)
C3 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(C3)
pr = C3.pr

P = "assets/renders"
# the four fixes: (frame key, kind, graded-fix-v4, raw -fix (geometry), clay, selfcheck, cam, overscan, room, base, raw retake before the fix, job id)
FIXES = {
    "B1 r3 fix":       ("B1",       "fix8", f"{P}/bath/nordic/v7/b1-v7-r3-graded-fix-v4.png",             f"{P}/bath/nordic/v7/b1-v7-r3-fix.png",             "r3-2026-11-03/B1.png", "r3", (-22, .52, .46), True,  "bath", "B1",     "B1 r3",       "b1-v7-r3"),
    "B2 r3 fix":       ("B2",       "fix8", f"{P}/bath/nordic/v7/b2-v7-r3-graded-fix-v4.png",             f"{P}/bath/nordic/v7/b2-v7-r3-fix.png",             "r3-2026-11-03/B2.png", "r3", (-57, .52, .46), True,  "bath", "B1",     "B2 r3",       "b2-v7-r3"),
    "K-girl-0 r2 fix": ("K-girl-0", "fix8", f"{P}/poses/nordic/v7/pose-k-girl-0-v7-r2-graded-fix-v4.png", f"{P}/poses/nordic/v7/pose-k-girl-0-v7-r2-fix.png", "poses/K-girl-0.png",   "r4", (0, .50, .46),   True,  "girl", "K-girl", "K-girl-0 r2", "pose-k-girl-0-v7-r2"),
    "W0-in r2 fix":    ("W0-in",    "fix8", f"{P}/poses/nordic/v7/pose-w0-in-v7-r2-graded-fix-v4.png",    f"{P}/poses/nordic/v7/pose-w0-in-v7-r2-fix.png",    "poses/W0-in.png",      "r4", (0, .50, .46),   False, "work", "W0",     "W0-in r2",    "pose-w0-in-v7-r2"),
}
FIX_IDS = list(FIXES)

# grading v4: the 26 rows of 11-03 with -v4 / -fix-v4 files, plus the four new fixes = 30 (regrade-v4-summary.json)
V4 = {}
for sid, t in C3.STILLS.items():
    if t[1] in ("master", "pose"):
        V4[sid] = (t[0], t[1], t[2].replace("-graded-v3.png", "-graded-v4.png"), t[3], t[4], t[5], t[6], t[7], t[8], t[9])
    elif t[1] == "fix":
        V4[sid] = (t[0], t[1], t[2].replace("-graded-fix-v3.png", "-graded-fix-v4.png"), None, t[4], t[5], t[6], t[7], t[8], t[9])
for sid, t in FIXES.items():
    V4[sid] = t[:10]
# the raw retakes before the fix keep their 11-03 registry entry (graded-v3), for before / after comparisons
V4_ROWS = [s for s in V4 if V4[s][1] in ("master", "fix", "pose")] + FIX_IDS
AGENT_ID = dict(C3.AGENT_ID, **{s: FIXES[s][11] for s in FIXES})

# make C3's loaders see the v4 registry (a module attribute swap, in this process only)
C3.STILLS = dict(C3.STILLS, **{s: V4[s] for s in V4})
C3.OUT = OUT
load, at, boxes, fn, rgb, crop_canvas, canvas_uv_to_frame, box_to_frame, selfcheck = (C3.load, C3.at, C3.boxes, C3.fn, C3.rgb, C3.crop_canvas,
                                                                                     C3.canvas_uv_to_frame, C3.box_to_frame, C3.selfcheck)
SC3, SC4, PLAN, PLAN3 = C3.SC3, C3.SC4, C3.PLAN, C3.PLAN3


def agent_measurements_v4(sid):
    import json
    g = C3.STILLS[sid][2]
    p = os.path.join(REPO, g.replace("-graded-fix-v4.png", "-measurements-fix-v4.json").replace("-graded-v4.png", "-measurements-v4.json"))
    return json.load(open(p)) if os.path.exists(p) else None


def agent_lock_fix(sid):
    import json
    p = os.path.join(REPO, FIXES[sid][3].replace("-fix.png", "-lock-fix.json"))
    return json.load(open(p)) if os.path.exists(p) else None


for _d in ("data", "overlays"):
    os.makedirs(os.path.join(OUT, _d), exist_ok=True)
