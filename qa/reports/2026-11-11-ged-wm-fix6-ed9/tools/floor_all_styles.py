"""
qa-agent 2026-11-11: G-ED.11's shadow floor (L* at the 1st percentile on a quarter-size copy, the gate's guardrails.py) on every
current story frame in register r12 (frames not superseded, and the master section's current frames), plus the two new ones, and
whether a written, owner-approved Bible with an L* floor covers the style (docs/design-bible/: nordic.md 1.9 and warm-modern.md 1.0.1
are Bibles; the other four are "brief-draft" files, not binding).
Usage: ~/.venvs/motion/bin/python -I floor_all_styles.py. Writes data/floor-all-styles.json.
"""
import importlib.util
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import OUT, REPO  # noqa: E402

reg = json.load(open(os.path.join(REPO, "qa/reports/ged-register-2026-11-10-r12.json")))
spec = importlib.util.spec_from_file_location("guardrails", os.path.join(REPO, "qa/reports/2026-11-07-gate-g-ed/tools/guardrails.py"))
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)
BIBLE = {"nordic": "docs/design-bible/nordic.md 1.9, 'מעקות': L* 8 at least (binding)",
         "warm-modern": "docs/design-bible/warm-modern.md 1.0.1, 'מעקות גריידינג': L* 8 at least (binding; Q-ED7 closed 2026-11-11)",
         "boho": None, "japandi": None, "mediterranean": None, "modern-country": None}
cur = []
sup = set(reg["superseded_by"]) | set(reg["master_superseded_by"])
for part in ("frames", "master"):
    for k, f in reg[part].items():
        if k not in sup:
            cur.append((part, k, f["file"], f["state"]))
cur += [("frames", "warm-modern-A-ed9 (new)", "assets/renders/editorial-phase-b-2026-11-06/warm-modern-A-ed9.png", "this round"),
        ("master", "warm-modern-MB-A-fix6 (new)", "assets/renders/master/editorial-2026-11-07/warm-modern/warm-modern-MB-A-fix6.png", "this round")]
rows = []
for part, k, f, st in cur:
    style = next(s for s in ("warm-modern", "modern-country", "mediterranean", "japandi", "boho", "nordic") if k.startswith(s))
    m = g.measure(os.path.join(REPO, f), [])
    rows.append(dict(part=part, key=k, file=f, state_r12=st, style=style, p0_5=m["shadow_floor_L_p0_5"], p1=m["shadow_floor_L_p1"],
                     bible_floor=BIBLE[style], meets_8=m["shadow_floor_L_p1"] >= 8))
json.dump(rows, open(os.path.join(OUT, "data", "floor-all-styles.json"), "w"), indent=1, ensure_ascii=False)
for x in rows:
    print(f'{x["part"]:7} {x["key"]:32} {x["state_r12"]:11} p1 {x["p1"]:5} bible {"yes" if x["bible_floor"] else "no"} meets8 {x["meets_8"]}')
