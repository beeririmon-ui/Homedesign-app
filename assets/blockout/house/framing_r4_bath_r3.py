#!/usr/bin/env python3
"""
Round-4 bath clays for the r3 retakes (render-agent, 2026-11-03; 0 var2 tokens). framing_r4.py is imported, not changed; the
round-4 folder is read only: everything goes to framing/round4/r3-2026-11-03/ (own plan.json, selfcheck-render-A.json, overlays,
B1.png, B2.png before tone). Brief: briefs/render-v7-retakes-2026-11-03.md task 2 (B1 r3, B2 r3); the clay lines of
assets/prompts/recipe-v5.nordic/b1-v7-r3.txt and b2-v7-r3.txt (master-designer, 2026-11-02; V7Q3 = yes, 2026-11-03).

What changes against round 4, and nothing else:
  B1: + bath/floor-planter and bath/toilet-brush among the placeholders;  B2: + bath/floor-planter.
  bath/floor-planter: pot D30 x H30 (the card: 30 x 30 x 30) at (5.05, 10.20): the slot centre (4.95, 10.20) moved +0.10 X by the
                      designer (house plan 12, <= 10 cm) so the pot clears the brush; a soft fern volume (ellipsoid r 0.26) to Z 1.20
                      (bath.json: plant_top_max 120; the fern is the registered filler).
  bath/toilet-brush:  D8 x H38 (the card) at its slot (4.70, 10.30) (round 3 moved it there; the round-2 proxy was D9 x H36).
Same camera CB, same light, same render exposure (+1.35), overscan 3 % (canvas 4072x2290), 16 samples, OIDN. The post (tone_r4
exposure 0.885, WB gains of group CB, shoulder) is applied by tone_r4_fixed.py with the recorded round-4 values, so the new clays
match the round-4 B1 / B2 everywhere except the two placeholders.

  python3 framing_r4_bath_r3.py --res 3840 --samples 16        (about 10 min per frame on 4 cores; EXRs in the scratchpad)
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import framing_r4 as r4  # noqa: E402

r3, r2, M = r4.r3, r4.r2, r4.M
OUT = os.path.join(HERE, "framing", "round4", "r3-2026-11-03")
EXR = os.path.join(r4.SCRATCH, "r4-exr-r3")
PLANTER_C = (5.05, 10.20)
BRUSH_C = (4.70, 10.30)

_v7 = r4.v7_fixes


def v7_fixes_r3(R):
    notes = _v7(R)
    # the existing proxies carry the slot materials (pass index colours); reuse them, then rebuild at the card sizes
    pot_mat = R["bath/floor-planter"]["objs"][0].data.materials[0]
    brush_mat = R["bath/toilet-brush"]["objs"][0].data.materials[0]
    r3.kill_group(R, "bath/floor-planter")
    r3.reg(R, "bath/floor-planter",
           [r3.cyl("fplant_pot_r3", PLANTER_C, 0.15, 0.0, 0.30, pot_mat), r3.ell("fplant_crown_r3", PLANTER_C, 0.26, 0.26, 1.20, M["crown"])],
           "bath", src="b1-v7-r3.txt h: floor-planter-aliexpress-seagrass-straight-planter-basket-30 (D30 x H30) + fern to Z 1.20, centre (5.05, 10.20) "
                       "(slot (4.95, 10.20) +0.10 X, designer move <= 10 cm, house plan 12)")
    r3.kill_group(R, "bath/toilet-brush")
    r3.reg(R, "bath/toilet-brush", [r3.cyl("tbrush_r3", BRUSH_C, 0.04, 0.0, 0.38, brush_mat)], "bath",
           src="b1-v7-r3.txt i: toilet-brush-aliexpress-matte-black-steel-cylinder-245996 (D8 x H38) at the slot (4.70, 10.30)")
    notes.append("bath/floor-planter: D30 x H30 pot + fern ellipsoid r 0.26 to Z 1.20 at (5.05, 10.20) (b1-v7-r3.txt h)")
    notes.append("bath/toilet-brush: D8 x H38 at (4.70, 10.30) (b1-v7-r3.txt i)")
    return notes


r4.v7_fixes = v7_fixes_r3


def plan_r3():
    src = os.path.join(HERE, "framing", "round4", "plan.json")
    p = json.load(open(src))
    f1, f2 = p["frames"]["B1"], p["frames"]["B2"]
    for s in ("floor-planter", "toilet-brush"):
        if s not in f1["placeholders"]:
            f1["placeholders"].append(s)
        if s in f1.get("empty_per_designer", []):
            f1["empty_per_designer"].remove(s)
    if "floor-planter" not in f2["placeholders"]:
        f2["placeholders"].append("floor-planter")
    if "floor-planter" in f2.get("empty_per_designer", []):
        f2["empty_per_designer"].remove("floor-planter")
    f1["prompt_file"], f2["prompt_file"] = "b1-v7-r3-v8.txt", "b2-v7-r3-v8.txt"
    f1["notes"] += "; r3 (2026-11-03, V7Q3): + floor planter D30 x H30 + fern at (5.05, 10.20), + toilet brush D8 x H38 at (4.70, 10.30)"
    f2["notes"] += "; r3 (2026-11-03, V7Q3): + the floor planter of B1 r3 at (5.05, 10.20), cut by the left edge"
    p["version"] = p.get("version", "1.1") + " + bath r3 (2026-11-03)"
    p["source_r3"] = "assets/blockout/house/framing_r4_bath_r3.py; briefs/render-v7-retakes-2026-11-03.md task 2; b1-v7-r3.txt / b2-v7-r3.txt clay lines"
    os.makedirs(OUT, exist_ok=True)
    dst = os.path.join(OUT, "plan.json")
    json.dump(p, open(dst, "w"), indent=2, ensure_ascii=False)
    return dst


if __name__ == "__main__":
    plan = plan_r3()
    argv = ["--plan", plan, "--group", "A", "--frames", "B1,B2", "--out", OUT, "--exr", EXR] + sys.argv[1:]
    r4.main(argv)
