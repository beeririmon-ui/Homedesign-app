"""
qa-agent 2026-11-07: shell_lock.py's measure (render vs clay r4 shell layer, QA's own projection, nearest-peak pairing, raw, no affine)
run on the v3 shell and its furniture base, ungraded and graded. Writes data/shell-lock-v3.json and overlays/shell-v3-named-lines.jpg.
Usage: ~/.venvs/motion/bin/python -I shell_lock_v3.py
"""
import importlib.util
import json
import os

import cv2
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("sl", os.path.join(HERE, "shell_lock.py"))
sl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sl)
clay = Image.open(sl.CLAY).convert("RGB").resize((1920, 1080), Image.LANCZOS)
gc = sl.gray(clay)
out = {"method": "as data/shell-lock.json (shell_lock.py), on the v3 files"}
for name in ("shell-v3.png", "shell-v3-graded.png", "shell-furniture-v3.png"):
    gr = sl.gray(Image.open(os.path.join(sl.P, name)).convert("RGB").resize((1920, 1080), Image.LANCZOS))
    out[name] = {ln: sl.nearest_peak_line(gc, gr, A, B) for ln, (A, B) in sl.LINES.items()}
sv = Image.open(os.path.join(sl.P, "shell-v3.png")).convert("RGB")
im = cv2.cvtColor(np.asarray(sv), cv2.COLOR_RGB2BGR)
W, H = sv.size
for ln, (A, B) in sl.LINES.items():
    pts = []
    for k in range(60):
        t = k / 59
        Pt = [A[i] + (B[i] - A[i]) * t for i in range(3)]
        u, v, d = sl.r1.project(sl.CAM, *Pt)
        u, v = sl.canvas_uv(u, v)
        if d > 0.1:
            pts.append((int(u * W), int(v * H)))
    for p, q in zip(pts[:-1], pts[1:]):
        cv2.line(im, p, q, (0, 0, 255), 2)
cv2.imwrite(os.path.join(sl.OUT, "overlays", "shell-v3-named-lines.jpg"), cv2.resize(im, (1920, 1080)), [cv2.IMWRITE_JPEG_QUALITY, 85])
json.dump(out, open(os.path.join(sl.OUT, "data", "shell-lock-v3.json"), "w"), indent=1)
for name in ("shell-v3.png", "shell-v3-graded.png", "shell-furniture-v3.png"):
    print("==", name)
    for ln, m in out[name].items():
        print("  ", ln, {k: (round(v, 2) if isinstance(v, float) else v) for k, v in m.items()})
