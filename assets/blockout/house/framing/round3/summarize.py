#!/usr/bin/env python3
"""Compact table of the round-3 selfcheck for the README / the manager. 0 tokens.  python3 summarize.py"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
s = json.load(open(os.path.join(HERE, "selfcheck.json")))
ORDER = ["D1", "D2", "H0", "C0", "MB0", "K-boy", "K-girl", "B1", "B2", "W0", "M0"]
print("| frame | room | L (r2) | placeholders | generic | lamps on | est > 0.02 | edge tangents | obj. tangents | designer rules failing | runtime |")
print("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
for f in ORDER:
    R = s.get("frames", {}).get(f)
    if not R:
        print(f"| {f} | | not rendered | | | | | | | | |")
        continue
    t = R.get("F3_tangents", {})
    edges = "; ".join(f"{e['item'].split('/')[-1]} {e['side']} {e['margin']}" for e in t.get("edge_tangents", [])) or "none"
    objs = "; ".join(f"{o['a'].split('/')[-1]}/{o['b'].split('/')[-1]} {o['kind']} {o.get('gap', o.get('overlap_thickness'))}" for o in t.get("object_object_tangents", [])) or "none"
    rules = "; ".join(r["rule"][:40] for r in R.get("rules_designer", []) if not r["ok"]) or "none"
    print(f"| {f} | {R['room']} | {R['mean_L']} ({R.get('mean_L_round2')}) | {len(R['placeholders_shown'])} | {', '.join(x.split('/')[-1] for x in R['built_generic']) or '-'} | "
          f"{', '.join(x.split('/')[-1] for x in R['lamps_on']) or 'none'} | {', '.join(R['est_flags']) or 'none'} | {edges} | {objs} | {rules} | {R['runtime_s']} s |")
print()
for f in ORDER:
    R = s.get("frames", {}).get(f)
    if not R:
        continue
    lb = R.get("light_balance", {})
    if "living_minus_hall_stops" in lb:
        print(f"{f}: living - hall = {lb['living_minus_hall_stops']} stops (pass {lb['pass_2_3_stop']}); QA point (0.35,0.40) - facing wall = {lb.get('qa_point_minus_front_wall_L')} L")
    wp = {k: v.get("L_hsl") for k, v in R.get("wall_patches", {}).items() if "L_hsl" in v}
    print(f"{f} wall patches L: {wp}")
    if "F8_mirror" in R:
        print(f"{f} mirror F8: {R['F8_mirror'].get('result')} non-wall {R['F8_mirror'].get('non_wall_objects')}")
print()
print("cameras identical to round 2:", {f: v["identical"] for f, v in s.get("cameras", {}).items()})
