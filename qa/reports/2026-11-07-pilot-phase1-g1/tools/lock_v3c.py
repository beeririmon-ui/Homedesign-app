"""
qa-agent 2026-11-07: F3 check: shell_lock.py's measure (QA's, raw, nearest-peak, clay r4) on the v3c display shell and base, against
render-agent's lock_F3 in shell-fix-v3.json. Usage: ~/.venvs/motion/bin/python -I lock_v3c.py. Writes data/lock-v3c.json.
"""
import importlib.util
import json
import os

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("sl", os.path.join(HERE, "shell_lock.py"))
sl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sl)
gc = sl.gray(Image.open(sl.CLAY).convert("RGB").resize((1920, 1080), Image.LANCZOS))
out = {}
for name in ("shell-v3-graded-v3c.png",):
    gr = sl.gray(Image.open(os.path.join(sl.P, name)).convert("RGB").resize((1920, 1080), Image.LANCZOS))
    out[name] = {ln: sl.nearest_peak_line(gc, gr, A, B) for ln, (A, B) in sl.LINES.items()}
ra = json.load(open(os.path.join(sl.P, "shell-fix-v3.json")))["lock_F3"]["results"]
out["render_agent_lock_F3"] = {k: {ln: v.get("p90_abs_px") for ln, v in r["lines"].items()} | {"verdict": r.get("verdict")} for k, r in ra.items()}
out["qa_worst_p90"] = max(v["p90_abs_px"] for v in out["shell-v3-graded-v3c.png"].values())
out["qa_min_paired"] = min(v["paired"] for v in out["shell-v3-graded-v3c.png"].values())
json.dump(out, open(os.path.join(sl.OUT, "data", "lock-v3c.json"), "w"), indent=1)
print(json.dumps({k: v for k, v in out.items() if k != "shell-v3-graded-v3c.png"}, indent=1)[:2500])
print({ln: v["p90_abs_px"] for ln, v in out["shell-v3-graded-v3c.png"].items()})
