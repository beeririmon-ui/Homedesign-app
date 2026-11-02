"""
G1.7-G1.11, G1.13 and G1.17 on every v7 frame and pose, measured independently on the kept graded render (16:9 frame).
Values in HSL (Bible: H degrees, S and L in percent), L = (max+min)/2, as the Bible and process_v7.py define them.
Writes data/light-<id>.json.
"""
import colorsys
import glob
import json
import os
import sys

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402

JOBS = {j["id"]: j for j in json.load(open(os.path.join(C.REPO, "assets/renders/house-nordic-v7-2026-11-02/jobs.json")))["jobs"]}
AGENT_TARGET_L = {"M0": 93.0, "H0": 82.0, "C0": 82.0, "B1": 86.0, "B2": 86.0}
POSE_BASE = {"H0x": "H0", "H0e": "H0", "M0p": "M0", "M0x": "M0", "PD-35": "D1", "W0-in": "W0", "S1'": "C0",
             "K-boy-0": "K-boy", "K-girl-0": "K-girl", "CB-0": "B1", "MB-in": "MB0"}
LAMP_WORDS = ("sconce", "pendant", "lights", "lantern", "downlight", "ceiling-light")


def Lmap(a):
    return (a.max(2) + a.min(2)) / 2 * 100


def hsl(rgb):
    h, l, s = colorsys.rgb_to_hls(*[float(x) for x in rgb])
    return [round(h * 360, 1), round(s * 100, 1), round(l * 100, 1)]


def patch(a, u, v, w=0.01):
    H, W = a.shape[:2]
    hw = max(2, int(w * W / 2))
    x, y = int(u * W), int(v * H)
    return a[max(0, y - hw):y + hw + 1, max(0, x - hw):x + hw + 1].reshape(-1, 3).mean(0)


def box_px(a, b):
    H, W = a.shape[:2]
    u0, u1, v0, v1 = b
    return a[max(0, int(v0 * H)):min(H, int(v1 * H)), max(0, int(u0 * W)):min(W, int(u1 * W))]


def stops_to(rgb, target_L):
    """Exposure (stops) that brings a patch's luminance to the sRGB grey of target_L (HSL L of a neutral = sRGB value)."""
    def s2l(x):
        x = np.asarray(x, float)
        return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)
    Y = np.array([0.2126, 0.7152, 0.0722])
    y = float(s2l(rgb).dot(Y))
    t = float(s2l(target_L / 100))
    return round(float(np.log2(t / max(y, 1e-6))), 3)


def run(fid):
    d = C.load(fid)
    a = d["graded"]
    raw = d["norm"]
    H, W = a.shape[:2]
    sc = d["sc"]
    bx = C.boxes(d)
    L = Lmap(a)
    rep = dict(frame=fid, kind=d["kind"], room=d["room"], size=[W, H])
    base = POSE_BASE.get(fid, fid)

    # --- reference wall patches (clay selfcheck points, in canvas uv -> frame uv) ---------------------------------
    pts = {}
    for k, v in sc.get("wall_patches", {}).items():
        if "u" in v and "v" in v and "L_hsl" in v:
            u, vv = (C.canvas_uv_to_frame(v["u"], v["v"]) if d["ovs"] else (v["u"], v["v"]))
            if 0 <= u <= 1 and 0 <= vv <= 1:
                pts[k] = dict(uv=[round(u, 4), round(vv, 4)], clay_L=v["L_hsl"], graded_HSL=hsl(patch(a, u, vv)), raw_HSL=hsl(patch(raw, u, vv)))
    if base == "M0":
        for k, (u, v, t) in {"bible_corner (0.467,0.385) [92-95; 1.4: 90-94]": (0.467, 0.385, "92-95"),
                             "bible_behind_sofa (0.69,0.22) [88-91]": (0.69, 0.22, "88-91"),
                             "bible_right_edge (0.97,0.31) [82-86]": (0.97, 0.31, "82-86")}.items():
            if fid == "M0":
                pts[k] = dict(uv=[u, v], target=t, graded_HSL=hsl(patch(a, u, v)), raw_HSL=hsl(patch(raw, u, v)))
    rep["wall_patches"] = pts
    # the frame's reference point and the exposure needed, measured by QA
    ref_uv = sc.get("post", {}).get("reference_uv")
    if fid == "M0":
        ref_uv = [0.467, 0.385]
    if ref_uv:
        u, v = (C.canvas_uv_to_frame(*ref_uv) if d["ovs"] else ref_uv)
        p = patch(a, u, v)
        praw = patch(raw, u, v)
        bible_lo = 92.0 if base == "M0" else 90.0           # G1.7 (M0, binding) / G1.8 (proposal, BIB1 open)
        rep["reference"] = dict(uv=[round(u, 4), round(v, 4)], graded_HSL=hsl(p), raw_HSL=hsl(praw),
                                target_bible_lo=bible_lo, target_agent=AGENT_TARGET_L.get(base, 90.0),
                                stops_needed_to_bible_from_raw=stops_to(praw, bible_lo),
                                stops_needed_to_bible_from_graded=stops_to(p, bible_lo),
                                stops_needed_to_agent_target_from_raw=stops_to(praw, AGENT_TARGET_L.get(base, 90.0)),
                                white_H_ok_32_40=bool(32 <= hsl(p)[0] <= 40), white_S_ok_15_28=bool(15 <= hsl(p)[1] <= 28),
                                white_H_under_25=bool(hsl(p)[0] < 25))
    # the agent's own grade record
    aid = os.path.basename(C.FRAMES[fid][1])
    mfile = os.path.join(C.REPO, C.FRAMES[fid][1] + "-measurements.json")
    if os.path.exists(mfile):
        m = json.load(open(mfile))
        g = m.get("grade", {}).get("exposure", {})
        rep["agent_grade"] = dict(target_L=g.get("target_L"), needed_stops=g.get("needed_stops"), applied_stops=g.get("applied_stops"), flag=g.get("flag"),
                                  wb_H_before=m.get("grade", {}).get("white_balance", {}).get("H_before"),
                                  black_point=m.get("grade", {}).get("black_point"), returned_size_px=m.get("returned_size_px"),
                                  resize_16_9=m.get("resize_16_9"), strong_peak_lock=m.get("clay_lock_worst_abs_shift_strong_peaks"))

    # --- window / brightest area (G1.13, G1.7) --------------------------------------------------------------------
    win = None
    wname = None
    for nm, (kind, b, area, vis) in bx.items():
        if kind == "window":
            win, wname = b, nm
            break
    if fid == "M0":
        win, wname = (0.19, 0.375, 0.025, 0.553), "window (pilot box, no window box in the round-4 M0 selfcheck)"
    if win is None:
        for nm, (kind, b, area, vis) in bx.items():
            if kind == "door" or "portal" in nm:
                win, wname = b, nm + " (vista through the opening: the brightest area by design)"
                break
    if fid == "H0":
        win, wname = (0.26, 0.44, 0.05, 0.95), "living vista through the door (process_v7 box)"
    sat = (a.max(2) >= 254.5 / 255)
    rep["saturated_px_total"] = int(sat.sum())
    if win is not None:
        wl = box_px(L, win)
        inside = int(box_px(sat, win).sum())
        mask = np.zeros_like(L, bool)
        u0, u1, v0, v1 = win
        mask[max(0, int(v0 * H)):min(H, int(v1 * H)), max(0, int(u0 * W)):min(W, int(u1 * W))] = True
        outside_L = L[~mask]
        rep["window"] = dict(box=wname, box_uv=[round(x, 4) for x in win], width_frac=round(win[1] - win[0], 3),
                             L_p50=round(float(np.median(wl)), 1), L_p99=round(float(np.percentile(wl, 99)), 1), L_max=round(float(wl.max()), 1),
                             saturated_inside=inside, saturated_outside=int(sat.sum()) - inside,
                             outside_L_p99=round(float(np.percentile(outside_L, 99)), 1), outside_L_p999=round(float(np.percentile(outside_L, 99.9)), 1),
                             brightest=bool(np.percentile(wl, 99) >= np.percentile(outside_L, 99.9)),
                             p99_le_97=bool(np.percentile(wl, 99) <= 97.0), no_255=bool(sat.sum() == 0),
                             margins=dict(left=round(win[0], 3), right=round(1 - win[1], 3), top=round(win[2], 3), bottom=round(1 - win[3], 3)))
    else:
        rep["window"] = dict(box=None, note="no window and no opening box in this frame (Bible 1.6 allows it in the second frame of a room)",
                             frame_L_p99=round(float(np.percentile(L, 99)), 1), no_255=bool(sat.sum() == 0))

    # --- black point, frame mean, white hue over the walls (G1.9) ------------------------------------------------
    k = max(4, int(0.005 * W))
    pm = sliding_window_view(L, (k, k))[::4, ::4].mean((2, 3))
    rep["black_point_L"] = round(float(pm.min()), 1)
    rep["frame_mean_L"] = round(float(L.mean()), 1)
    # white / beige surfaces: L > 70 and S < 30 -> hue distribution (pink / lilac = H < 25)
    sub = a[::6, ::6].reshape(-1, 3)
    hls = np.array([colorsys.rgb_to_hls(*c) for c in sub])
    white = (hls[:, 1] * 100 > 70) & (hls[:, 2] * 100 < 30)
    hw = hls[white, 0] * 360
    rep["whites"] = dict(share_of_frame=round(float(white.mean()), 3), H_median=round(float(np.median(hw)), 1) if len(hw) else None,
                         S_median=round(float(np.median(hls[white, 2]) * 100), 1) if len(hw) else None,
                         share_H_under_25=round(float((hw < 25).mean()), 4) if len(hw) else None,
                         share_H_over_50=round(float((hw > 50).mean()), 4) if len(hw) else None)
    # floor band (bottom 10 %, middle 60 %): parquet H 30-40 S 30-45 L 68-78 (G1.11 proposal; bath is limestone, no target)
    fl = a[int(0.90 * H):int(0.99 * H), int(0.20 * W):int(0.80 * W)].reshape(-1, 3)[::31]
    fh = np.array([colorsys.rgb_to_hls(*c) for c in fl])
    rep["floor_median_HSL"] = [round(float(np.median(fh[:, 0])) * 360, 1), round(float(np.median(fh[:, 2])) * 100, 1), round(float(np.median(fh[:, 1])) * 100, 1)]
    rep["floor_note"] = "bottom 10 % of the frame, middle 60 %: parquet in every room but the bath (limestone) and the hall / corridor (parquet, but the runner / rug may sit there)"
    if fid == "M0":
        r = L[int(0.76 * H):int(0.83 * H), int(0.52 * W):int(0.84 * W)]
        rep["contact_shadow_under_sofa_minL_p1"] = [round(float(r.min()), 1), round(float(np.percentile(r, 1)), 1)]

    # --- lamps (G1.10): shade glow and hue inside each lamp proxy box ----------------------------------------------
    lamps = {}
    lit = set(sc.get("lamps_on", []))
    for nm, (kind, b, area, vis) in bx.items():
        if kind != "proxy" or not any(w in nm for w in LAMP_WORDS):
            continue
        if (b[1] - b[0]) * (b[3] - b[2]) <= 0:
            continue
        pb = box_px(a, b)
        if pb.size == 0:
            continue
        lb = Lmap(pb)
        top = pb.reshape(-1, 3)[lb.reshape(-1) >= np.percentile(lb, 90)]
        hh = np.array([colorsys.rgb_to_hls(*c) for c in top[::max(1, len(top) // 400)]])
        lamps[nm] = dict(box_uv=[round(x, 4) for x in b], in_clay_lamps_on=nm in lit, L_p95=round(float(np.percentile(lb, 95)), 1),
                         L_max=round(float(lb.max()), 1), glow_H_median=round(float(np.median(hh[:, 0]) * 360), 1),
                         glow_S_median=round(float(np.median(hh[:, 2]) * 100), 1),
                         shade_L_93_97=bool(93 <= np.percentile(lb, 95) <= 97.5), shade_H_35_45=bool(35 <= np.median(hh[:, 0]) * 360 <= 45),
                         shade_S_25_45=bool(25 <= np.median(hh[:, 2]) * 100 <= 45))
        if rep["window"].get("L_p99") is not None:
            lamps[nm]["not_brighter_than_window"] = bool(np.percentile(lb, 99) <= rep["window"]["L_p99"] + 0.5)
    rep["lamps"] = lamps
    rep["lamps_on_in_clay"] = sorted(lit)

    # --- technical (G1.17) -------------------------------------------------------------------------------------------
    job = JOBS.get(aid)
    pf = job.get("prompt_file") if job else None
    rep["technical"] = dict(job_id=aid, prompt_file=pf, prompt_file_exists=bool(pf and os.path.exists(os.path.join(C.REPO, pf))),
                            prompt_record_json=bool(glob.glob(os.path.join(C.REPO, "assets/prompts/**/" + aid + ".json"), recursive=True)),
                            graded_size=[W, H], is_2k=bool(W >= 1920), ratio_16_9=bool(abs(W / H - 16 / 9) < 0.002),
                            overscan_canvas=bool(d["ovs"]), frame_file_matches_crop=d.get("frame_file_matches_crop"),
                            model=job.get("model") if job else None, quality=job.get("quality") if job else None, credits=job.get("credits") if job else None)
    json.dump(rep, open(os.path.join(C.OUT, "data", f"light-{fid.replace(chr(39), 'prime')}.json"), "w"), indent=1, ensure_ascii=False)
    r = rep.get("reference", {})
    w = rep["window"]
    print(f"{fid:9s} ref L {r.get('graded_HSL')} raw {r.get('raw_HSL')} need(bible,raw) {r.get('stops_needed_to_bible_from_raw')} | agent {rep.get('agent_grade', {}).get('needed_stops')} {rep.get('agent_grade', {}).get('flag', '')[:5]} "
          f"| win p99 {w.get('L_p99')} brightest {w.get('brightest')} 255 {rep['saturated_px_total']} | black {rep['black_point_L']} | whites H {rep['whites']['H_median']} S {rep['whites']['S_median']} <25 {rep['whites']['share_H_under_25']} | floor {rep['floor_median_HSL']} | lamps {[(k.split('/')[-1], v['L_p95'], v['glow_H_median'], v['glow_S_median']) for k, v in lamps.items()]}")


if __name__ == "__main__":
    for f in (sys.argv[1:] or C.MASTERS + C.POSES):
        run(f)
