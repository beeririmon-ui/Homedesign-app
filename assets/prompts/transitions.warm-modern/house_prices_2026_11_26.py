import json, math
CRUISE = 1.5
SEED, NANO, KS = 650, 400, 324          # live, var2_estimate_cost 2026-11-26 (fromLiveLookup)
M_STILL, M_CLIP, CAP = 1.71, 1.25, 2.0  # stills: the 1.71 history margin; clips: 1 retake in 4; cap: every job twice

def walk_s(L, bends90=0.0, enter_cruise=False):
    return L / CRUISE + (0.4 if enter_cruise else 0.7) + 0.5 * bends90
def turn_s(deg):
    return deg / 90.0 + 0.4

# stills: id -> (model price, role)
S = {
 "M0x-W": (SEED, "M0-W point, yaw -47, 24 mm: the kitchen exit (clip start)"),
 "M0s-W": (NANO, "M0-W point, yaw -98: turn only"),
 "M0b-W": (SEED, "M0-W point, yaw -150: the hall exit (clip start); the spine to the bedroom door"),
 "M0m-W": (NANO, "M0-W point, yaw 70: turn only"),
 "M0i-W": (SEED, "M0-W point, yaw 130: arrival from the kitchen (clip end)"),
 "PD-155": (NANO, "PD, yaw -155: turn only"),
 "PDx": (SEED, "PD, yaw 133: the kitchen exit toward M0-W (clip start)"),
 "HW": (SEED, "HX, yaw 95: toward the work-room door (clip start)"),
 "KBi": (SEED, "K-boy point, yaw 90 (clip end)"), "KBm": (NANO, "K-boy point, yaw -30: turn only"), "KBx": (SEED, "K-boy point, yaw -90, the door (clip start)"),
 "KGi": (SEED, "K-girl point, yaw 90 (clip end)"), "KGm": (NANO, "K-girl point, yaw -30: turn only"), "KGx": (SEED, "K-girl point, yaw -90 (clip start)"),
 "CBm": (NANO, "CB, yaw 20: turn only"), "CBx": (SEED, "CB, yaw 63, the door (clip start)"),
 "MBf": (SEED, "(1.6, 21.05, 1.10), yaw 90: past the bed's foot (clip end / start)"), "MBx": (SEED, "MB0 point, yaw -42, the door (clip start)"),
 "W0i": (SEED, "W0 point, yaw 130 (clip end)"), "W0m": (NANO, "W0 point, yaw 65: turn only"), "W0x": (SEED, "W0 point, yaw -50, the door (clip start)"),
}
# transitions in route order. kind: reuse / K (kling, first+last still) / CT (code turn) / C25 (code 2.5D on depth)
T = [
 # id, from, to, metres, site seconds, method, kling seconds, new stills, wave, note
 ("door", "D0", "D0o", 0, 0.8, "reuse: code", 0, [], 0, "exists"),
 ("1a", "D0o", "HT", 3.8, 2.8, "reuse: K (QA passed)", 0, [], 0, "the living room through the opening: code re-feed from H-W (as HT2); retake 1,296 only in the cap"),
 ("1b", "HT", "HD", 1.14, 0.7, "reuse: code", 0, [], 0, "rebuilt from HT2 after its re-feed"),
 ("look", "HD", "HC, then HDx2", 0, 4.4, "reuse: CT (HD2, HC130, HC, HDx2)", 0, [], 0, "90 deg left, rest 0.8 s on HC, 155 deg right"),
 ("T-E0-W", "HDx2", "M0-W", 3.01, round(walk_s(3.01, enter_cruise=True), 1), "K", 3, [], 1, "replaces clip 2; lens 24 -> 35 mm and 1.20 -> 1.05 m inside the walk"),
 ("T-LD-W", "M0-W", "D1", 2.55, round(turn_s(61) * 0.8 + walk_s(2.55), 1), "CT + K", 3, ["M0x-W"], 2, "61 deg right in place, the walk starts in the last 20 deg; 9 deg more with the stop"),
 ("P-D", "D1", "D2", 0, 1.2, "CT", 0, [], 0, "30 deg, both frames exist"),
 ("T-DL-W", "D1", "M0-W", 2.55, round(turn_s(171) + walk_s(2.55) + turn_s(119) * 0.7, 1), "CT + K + CT", 3, ["PD-155", "PDx", "M0i-W", "M0m-W"], 4, "171 deg right at PD via D2; 119 deg right at M0-W with the stop"),
 ("T-MH-W", "M0-W", "HC", 3.01, round(turn_s(164) + walk_s(3.01, 0.33), 1), "CT + K", 3, ["M0s-W", "M0b-W"], 2, "164 deg right in place (through M0x-W, shared with T-LD-W); 30 deg bend at HX; rest on HC or flow on"),
 ("T-HBoy", "HC", "K-boy", 5.88, round(walk_s(5.88, 1) + turn_s(57) * 0.6, 1), "K + CT", 6, ["KBi"], 3, "90 deg right through the door at 0.8 m/s; 57 deg head turn with the stop"),
 ("T-BoyH", "K-boy", "HDx2", 5.88, round(turn_s(123) + walk_s(5.88, 1.28), 1), "CT + K", 6, ["KBm", "KBx"], 4, "123 deg right in place; 90 deg bend out of the door, 25 deg at HX; then T-E0-W or the turn to HC"),
 ("T-HGirl", "HC", "K-girl", 9.51, round(walk_s(9.51, 1) + turn_s(57) * 0.6, 1), "K + CT", 9, ["KGi"], 3, "as the boy, 3.63 m further"),
 ("T-GirlH", "K-girl", "HDx2", 9.51, round(turn_s(123) + walk_s(9.51, 1.28), 1), "CT + K", 9, ["KGm", "KGx"], 4, "as the boy"),
 ("T-HBath", "HC", "B2", 5.74, round(walk_s(5.74, 1), 1), "K", 6, [], 3, "90 deg left through the door; the head leads 28 deg; ends on B2 (no arrival still)"),
 ("P-B", "B2", "B1", 0, 1.2, "CT", 0, [], 0, "35 deg, both frames exist"),
 ("T-BathH", "B2", "HDx2", 5.74, round(turn_s(120) + walk_s(5.74, 1.28), 1), "CT + K", 6, ["CBm", "CBx"], 4, "120 deg left in place via B1"),
 ("T-HM", "HC", "MBf", 13.31, round(walk_s(13.31, 1), 1), "K", 10, ["MBf"], 3, "the corridor 9.43 m, the door at X 2.45, the arc round the bed's foot"),
 ("MBa", "MBf", "MB0", 2.30, round(walk_s(2.30) + 0.4, 1), "K", 3, [], 3, "slows to a stop, the head turns 90 deg to the bed wall"),
 ("T-MbH", "MB0", "HDx2", 14.12, round(turn_s(42) + walk_s(14.12, 0.75), 1), "CT + K", 10, ["MBx"], 4, "42 deg right in place, 42 deg bend at the door, 25 deg at HX; split at C0 only if QA fails (C0-W 650 + about 300, in the cap)"),
 ("T-HW", "HDx2", "W0", 3.90, round(turn_s(70) + walk_s(3.90, 0.5) + turn_s(130) * 0.6, 1), "CT + K + CT", 4, ["HW", "W0i", "W0m"], 3, "70 deg left at HX; through the hidden leaf; 130 deg right with the stop"),
 ("T-WH", "W0", "HDx2", 4.0, round(turn_s(50) + walk_s(4.0, 0.5), 1), "CT + K", 4, ["W0x"], 4, "50 deg right in place, out to the junction"),
]
rows, tot = [], dict(list=0, exp=0, cap=0)
seen = set()
for t in T:
    tid, fr, to, L, sec, how, ks, st, wave, note = t
    clip = KS * ks
    st_new = [s for s in st if s not in seen]; seen |= set(st_new)
    st_list = sum(S[s][0] for s in st_new)
    lst = clip + st_list
    exp = round(clip * M_CLIP + st_list * M_STILL)
    cap = round(lst * CAP)
    tot["list"] += lst; tot["exp"] += exp; tot["cap"] += cap
    rows.append(dict(id=tid, frm=fr, to=to, m=L, s=sec, how=how, kling_s=ks, clip=clip, stills=st_new, stills_list=st_list, list=lst, expected=exp, cap=cap, wave=wave, note=note))
waves = {}
for r in rows:
    w = waves.setdefault(r["wave"], dict(list=0, expected=0, cap=0, clips=0, stills=0, kling_s=0))
    w["list"] += r["list"]; w["expected"] += r["expected"]; w["cap"] += r["cap"]; w["clips"] += 1 if r["kling_s"] else 0
    w["stills"] += len(r["stills"]); w["kling_s"] += r["kling_s"]
out = dict(date="2026-11-26", author="motion-agent", brief="briefs/wm-transitions-house-plan-2026-11-26.md",
           source="var2_estimate_cost, live (fromLiveLookup), 2026-11-26; nothing sent",
           unit_prices={"kling-3-omni image-to-video 1080p, no audio, a second": KS, "seedream-5-pro image-to-image 2K": SEED, "nano-banana-2 image-to-image 2K": NANO},
           margins={"stills_expected": M_STILL, "clips_expected": M_CLIP, "cap_every_job": CAP,
                    "why": "stills: the 1.71 history margin of route-prices-2026-11-17.json; clips: 1a and clip 2 passed on take 1 with code repairs, but doorways and bends are new, so one retake in four; cap: every job run twice"},
           pace={"cruise_m_s": CRUISE, "turn_peak_deg_s": 90, "rule": "FB8: forward only; every return is a turn in place and a walk forward; products go down before a move and come back in the reveal, so every clip and still is the empty room"},
           stills={k: dict(price=v[0], role=v[1]) for k, v in S.items()},
           transitions=rows, waves=waves, total=tot,
           not_counted=["M0-W hero and P-W / H-W (FB13)", "the HT2 / HDx2 re-feed through the opening and its 2 x 400 fallback (FB16)", "the house light pass L0 on every plate (FB16)"])
json.dump(out, open("/home/user/homedesign-app/assets/prompts/transitions.warm-modern/house-prices-2026-11-26.json", "w"), indent=1, ensure_ascii=False)
for r in rows: print(r["id"], r["m"], r["s"], r["how"], r["kling_s"], r["stills"], r["list"], r["expected"], r["cap"], "w", r["wave"])
print("waves", json.dumps(waves)); print("total", tot)
print("kling seconds", sum(r["kling_s"] for r in rows), "stills", len(seen), "clips", sum(1 for r in rows if r["kling_s"]))
