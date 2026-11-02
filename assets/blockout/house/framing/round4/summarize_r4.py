#!/usr/bin/env python3
"""Table of the round-4 clays from selfcheck.json into README.md (between the TABLE markers). 0 tokens.  python3 summarize_r4.py"""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
sc = json.load(open(os.path.join(HERE, 'selfcheck.json')))['frames']
order = ['M0', 'D1', 'D2', 'H0', 'C0', 'MB0', 'K-boy', 'K-girl', 'B1', 'B2', 'W0',
         'H0x', 'H0e', 'M0p', 'M0x', 'PD-35', 'W0-in', 'S1prime', 'R2m', 'K-boy-0', 'K-girl-0', 'CB-0', 'MB-in']
rows = ['| still | file | camera (x, y, z), yaw, u0/v0 | canvas | samples | exposure (round 3 = +0.35) | reference patch: target -> L | glass p99 | lamps lit |',
        '| --- | --- | --- | --- | --- | --- | --- | --- | --- |']
for f in order:
    d = sc.get(f)
    if not d:
        rows.append(f'| {f} | not rendered | | | | | | | |')
        continue
    p = d.get('post', {})
    c = d.get('camera', {})
    ov = d.get('overscan', {})
    canvas = (f"{ov['canvas_px'][0]}x{ov['canvas_px'][1]}" if ov.get('canvas_px') else '3840x2160 (no overscan: sent before the request)') + (' (overscan 3 %)' if ov.get('on') else '')
    ref = p.get('reference_L_final')
    refs = f"{p.get('target_L')} -> {ref}" if ref is not None else f"group {p.get('group')} (set by {p.get('exposure_group_ref')})"
    wins = ', '.join(f"{v['p99']}" for v in (p.get('window_p99') or {}).values()) or f"frame {p.get('p99_L_frame')}"
    rows.append(f"| {f} | {d.get('image', '')} | ({', '.join(str(x) for x in c.get('loc', []))}), {c.get('yaw')}, {c.get('u0')}/{c.get('v0')} | {canvas} | "
                f"{d.get('samples', '')} | +{p.get('exposure')} ({p.get('exposure_vs_round3_stops'):+} stop) | {refs} | {wins} | {', '.join(d.get('lamps_on', [])) or 'none'} |")
bal = sc.get('H0', {}).get('post', {}).get('light_balance_final', {})
extra = (f"\nH0 balance (display-referred, as round 3 measured it): living back wall through the door L {bal.get('living_back_wall_through_door', {}).get('L_final')}, "
         f"hall wall above the console L {bal.get('hall_front_wall_above_console', {}).get('L_final')}, living - hall = {bal.get('living_minus_hall_stops_display')} stop "
         f"(round 3: 0.4; target 0.5-0.9: {'pass' if bal.get('pass_2_3_stop') else 'FAIL'}).\n")
txt = open(os.path.join(HERE, 'README.md')).read()
a, b = txt.split('<!-- TABLE -->')[0], txt.split('<!-- /TABLE -->')[1]
open(os.path.join(HERE, 'README.md'), 'w').write(a + '<!-- TABLE -->\n' + '\n'.join(rows) + '\n' + extra + '<!-- /TABLE -->' + b)
print('\n'.join(rows)); print(extra)
