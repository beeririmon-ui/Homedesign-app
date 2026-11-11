#!/usr/bin/env python3
"""
codefix_ed9.py: Q-ED7 (a), the toe lift on the warm-modern living-room story frame; render-agent, 2026-11-11. 0 tokens, code only.
Source: docs/master-bedroom-comparison-2026-11-07.md §6 (master-designer, 2026-11-10: keep the Bible's L* 8 floor for the
warm-modern story frames, lift the toe in code in both frames); QA qa/reports/2026-11-10-ged-master-wm-fix5.json (G-ED.11:
ed8 p1 3.7). Base: warm-modern-A-ed8.png ("final test", already shown to the owner; not changed). Out: warm-modern-A-ed9.png.

The toe ONLY, nothing else: ../master/editorial-2026-11-07/q_ed7_toe.py, the same curve as the master bedroom's fix6
(mb1_fix8.py): L* only, lift below 12, soft blend to the identity at 20, nothing at L* >= 20 moves (copied byte for byte), hue
and saturation kept; s0 solved so that the gate's p1 (quarter-size bilinear copy, guardrails.py) is 9.0 (target 8.5-9.5).
The light and the brightness do not move: DL1 is measured on the plaster and the frame median, both far above L* 20.

Record: codefix-ed9.json. Crops: codefix-ed9-before-after/ (the black bowl, the walnut coffee table; 100 % and x4).
Usage: ~/.venvs/motion/bin/python -I codefix_ed9.py
"""
import json
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "master", "editorial-2026-11-07"))
import q_ed7_toe as T  # noqa: E402

BASE = "warm-modern-A-ed8.png"
OUT = "warm-modern-A-ed9.png"
REC = os.path.join(HERE, "codefix-ed9.json")
CROPS = os.path.join(HERE, "codefix-ed9-before-after")
PATCHES = {   # frame px (x0, y0, x1, y1); the product reads, for G-ED.3 spot checks
    "black bowl (body, L* < 25)": (1380, 1000, 1630, 1110),
    "walnut coffee table, left drum base (L* < 25)": (1110, 1250, 1410, 1440),
    "walnut coffee table, right drum base (L* < 25)": (1870, 1250, 2170, 1450),
    "walnut coffee table, top edge (L* < 40)": (900, 1160, 2380, 1240),
}


def reads(before, after):
    out = {}
    for name, box in PATCHES.items():
        lmax = 25.0 if "L* < 25" in name else 40.0
        x0, y0, x1, y1 = box
        lb0 = T.lab(before[y0:y1, x0:x1]).reshape(-1, 3)
        lb1 = T.lab(after[y0:y1, x0:x1]).reshape(-1, 3)
        m = lb0[:, 0] < lmax                                   # the same pixels before and after
        r = {}
        for k, lb in (("ed8", lb0), ("ed9", lb1)):
            a, b = np.median(lb[m, 1]), np.median(lb[m, 2])
            r[k] = dict(L=round(float(np.median(lb[m, 0])), 1), C=round(float(np.hypot(a, b)), 1),
                        h=round(float(np.degrees(np.arctan2(b, a))), 1), p5_L=round(float(np.percentile(lb[m, 0], 5)), 1))
        r["px"] = int(m.sum())
        r["box"] = list(box)
        out[name] = r
    return out


def main():
    fr = np.asarray(Image.open(os.path.join(HERE, BASE)).convert("RGB"))
    s0 = T.solve_s0(fr)
    fin, info = T.apply(fr, s0)
    Image.fromarray(fin).save(os.path.join(HERE, OUT))
    Lfr, Lfin = T.L_of(fr), T.L_of(fin)
    chk = T.checks(fr, fin)
    gb, gf = T.gate_percentiles(fr), T.gate_percentiles(fin)
    rec = dict(
        date="2026-11-11", by="render-agent", pass_id="codefix-ed9 (Q-ED7 (a), 0 tokens, code only)", tokens=0,
        base=BASE, out=OUT, script="codefix_ed9.py",
        toe_module="../master/editorial-2026-11-07/q_ed7_toe.py (the same curve as the master bedroom's fix6, mb1_fix8.py)",
        source="docs/master-bedroom-comparison-2026-11-07.md §6 (Q-ED7 ruling (a)); qa/reports/2026-11-10-ged-master-wm-fix5.json (G-ED.11)",
        note="TEST, not for the site; new files only; ed8 and every approved file untouched; no var2. The toe only: the light and the "
             "brightness do not move (DL1 is measured on the plaster and the frame median). ed8 was shown to the owner; the manager "
             "notes the change when ed9 is shown. Awaiting qa-agent: G-ED.11 (p1, p5, split flag), G-ED.8 for the toe, G-ED.3 spot reads",
        toe=dict(
            curve="q_ed7_toe.curve: slope s0 below L* 12, smoothstep blend of the slope to 1 at 20, identity from 20; lift (1 - s0)(16 - L) below 12",
            s0=round(float(s0), 4), lift_by_L=T.lift_table(s0), chromaticity_own_from_L=T.REL_HI, chromaticity_local_below_L=T.REL_LO,
            local_sigma_px=T.SIGMA_LOC, local_source_L=list(T.REL_SRC), local_cover_k=T.COVER_K, fallback_srgb="#2E2824 (Bible espresso)", info=info,
            p1_target=[8.5, 9.5], p5_rise_max=3,
        ),
        gate_percentiles={"ed8": gb, "ed9": gf},
        p1_rise=round(gf["p1"] - gb["p1"], 2), p5_rise=round(gf["p5"] - gb["p5"], 2),
        full_res_percentiles={"ed8": T.full_percentiles(fr), "ed9": T.full_percentiles(fin)},
        checks=chk,
        frame_median_L={"ed8": round(float(np.median(Lfr)), 2), "ed9": round(float(np.median(Lfin)), 2)},
        frame_p90_L={"ed8": round(float(np.percentile(Lfr, 90)), 2), "ed9": round(float(np.percentile(Lfin, 90)), 2)},
        product_reads=reads(fr, fin),
        gate_guardrails_py=T.gate_guardrails([os.path.join(HERE, BASE), os.path.join(HERE, OUT)]),
    )
    os.makedirs(CROPS, exist_ok=True)
    spec = [
        ("black-bowl-100.jpg", (1330, 950, 1690, 1150), 1, "black bowl", 1.0),
        ("black-bowl-x4.jpg", (1460, 1030, 1580, 1100), 4, "black bowl, body and inner rim", 1.0),
        ("walnut-table-100.jpg", (1060, 1120, 1520, 1460), 1, "walnut coffee table, left drum base and top edge", 1.0),
        ("walnut-table-x4.jpg", (1300, 1250, 1420, 1320), 4, "walnut coffee table, drum base in shadow", 1.0),
        ("under-table-100.jpg", (1700, 1180, 2200, 1460), 1, "walnut coffee table, right drum base and the rug under the table", 1.0),
    ]
    crops = []
    for name, box, sc, title, st in spec:
        T.crop_pair(fr, fin, box, sc, "warm-modern-A ed8 | ed9 · " + title, os.path.join(CROPS, name), stretch=st)
        crops.append("codefix-ed9-before-after/" + name)
    rec["crops"] = crops
    json.dump(rec, open(REC, "w"), indent=1, ensure_ascii=False)
    print(json.dumps(rec, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
