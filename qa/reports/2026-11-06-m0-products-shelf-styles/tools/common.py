"""
qa-agent, 2026-11-06: G1 on the products pass of the Nordic M0 1.2 (M0S2), the M0p warp, the shelf A/B and a reading of the five
style previews. Builds on the 11-05 registry, imported (not edited). Writes under qa/reports/2026-11-06-m0-products-shelf-styles/.
"""
import importlib.util
import os

REPO = "/home/user/homedesign-app"
OUT = os.path.join(REPO, "qa/reports/2026-11-06-m0-products-shelf-styles")
_s = importlib.util.spec_from_file_location("qa1105_common", os.path.join(REPO, "qa/reports/2026-11-05-m0-seedream-fix3-g1/tools/common.py"))
C6 = importlib.util.module_from_spec(_s)
_s.loader.exec_module(C6)
C3 = C6.C3
pr = C3.pr
V9 = "assets/renders/living-room/nordic/v9"
NEW = {
    "M0 products fix": ("M0 1.2", "m0s", f"{V9}/m0-1-2-products-graded-fix-v6.png", f"{V9}/m0-1-2-products-fix.png", "../round5b/M0.png", "r5b:M0", (25, .47, .50), True, "living", "M0 1.2"),
    "M0p seedream fix": ("M0p 1.2", "m0s", f"{V9}/pose-m0p-1-2-shell-seedream-graded-fix-v6.png", f"{V9}/pose-m0p-1-2-shell-seedream-fix.png", "../round5b/poses/M0p.png", "r5b:M0p", (0, .47, .50), True, "living", "M0 1.2"),
    "M0p seedream warp": ("M0p 1.2", "m0s", f"{V9}/pose-m0p-1-2-shell-seedream-graded-fix-v6.png", f"{V9}/pose-m0p-1-2-shell-seedream-fix-warp.png", "../round5b/poses/M0p.png", "r5b:M0p", (0, .47, .50), True, "living", "M0 1.2"),
}
C3.STILLS.update(NEW)
load, at, boxes, fn, rgb, crop_canvas = C3.load, C3.at, C3.boxes, C3.fn, C3.rgb, C3.crop_canvas
for _d in ("data", "overlays"):
    os.makedirs(os.path.join(OUT, _d), exist_ok=True)
