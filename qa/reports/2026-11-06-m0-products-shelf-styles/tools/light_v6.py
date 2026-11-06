"""
qa-agent 2026-11-06: grading v6 of the products composite (and the M0 seedream v5 for reference) at the Bible points: back wall by
the corner 90-94, centre 88-91 (above the triptych and between it and the sofa), the right edge 82-86, window wall 80-88; black,
max, 255; the tonal shape (share over L* 90, local contrast, mean C*). Writes data/light-v6.json. Usage: ~/.venvs/motion/bin/python -I light_v6.py
"""
import importlib.util
import json
import os

REPO = "/home/user/homedesign-app"
OUT = os.path.join(REPO, "qa/reports/2026-11-06-m0-products-shelf-styles")
_s = importlib.util.spec_from_file_location("lm0s", os.path.join(REPO, "qa/reports/2026-11-05-m0-seedream-fix3-g1/tools/light_m0s.py"))
LM = importlib.util.module_from_spec(_s)
_s.loader.exec_module(LM)
LV = LM.LV
R = "assets/renders/living-room/nordic/v9/"
FILES = {"M0 products v6": R + "m0-1-2-products-graded-fix-v6.png", "M0 products + shelf v6 (B)": R + "m0-1-2-products-shelf-graded-fix-v6.png",
         "M0 seedream v5 (11-05)": R + "m0-1-2-shell-seedream-graded-fix-v5.png"}
if __name__ == "__main__":
    out = {}
    for k, f in FILES.items():
        a = LV.rgb(f)
        fall = {n: dict(LV.read(a, u, v), range=[lo, hi], ok=bool(lo <= LV.read(a, u, v)["L"] <= hi)) for n, (u, v, lo, hi) in LM.FALL.items()}
        out[k] = dict(file=f, window_wall=LV.read(a, 0.352, 0.415), fall_off=fall, black=LV.black_point(a), max_L=round(float(LV.Lmap(a).max()), 1),
                      px255=int((a.max(2) >= 254.5 / 255).sum()), shape=LM.shape(a))
        print(k, {n: (v["L"], v["C"], v["ok"]) for n, v in fall.items()}, "ww", out[k]["window_wall"]["L"], "black", out[k]["black"], "max", out[k]["max_L"], out[k]["px255"],
              "share>90", out[k]["shape"]["share_Lstar_over_90"], "lc", out[k]["shape"]["local_contrast_median"], "C", out[k]["shape"]["mean_C"])
    json.dump(out, open(os.path.join(OUT, "data", "light-v6.json"), "w"), indent=1)
