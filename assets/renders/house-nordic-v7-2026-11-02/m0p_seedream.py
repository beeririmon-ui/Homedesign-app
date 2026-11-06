#!/usr/bin/env python3
"""
m0p_seedream.py: M0p 1.2 on the seedream route (the job paid on 2026-11-05, briefs/render-m0-model-test-2026-11-05.md step 2; fetched
2026-11-06 after var2 was re-authorised). render-agent, 0 tokens today. New files only, in assets/renders/living-room/nordic/v9/:
  fetch   the raw -> raw/pose-m0p-shell-seedream.png, normalised to the 2736 x 1539 canvas -> pose-m0p-shell-seedream.png, lock_v2 (the M0p
          clay of round 5b) -> -lock-v2.json / .jpg, the shell check (the M0p clay's level lines and corners) -> -shell.json / .jpg,
          the job row in jobs-m0-model-test-2026-11-05.json
  build   one global affine to the clay (if lock_v2 asks for it) + the wall round onto its 38 cm circle -> pose-m0p-1-2-shell-seedream-fix-base
  art     the triptych (art_m0_12.py with the M0p camera) -> pose-m0p-1-2-shell-seedream-fix.png (+ lock_v2, grading v5 as a record)
"""
import json
import os
import subprocess
import sys

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fix_m0_12 as M  # noqa: E402
import fix_v7 as F  # noqa: E402
import shell_lock_m0 as SL  # noqa: E402
import m0_model_test as T  # noqa: E402

REPO = M.REPO
DATE = "2026-11-06"
SRC_ID = "pose-m0p-shell-seedream"
JID = "pose-m0p-1-2-shell-seedream"
OD_REL, OD = T.OD_REL, T.OD
CLAY = os.path.join(REPO, "assets/blockout/house/framing/round5b/poses/M0p.png")
URL = ("https://cqfxzynnlzsxugtwrsex.supabase.co/storage/v1/object/public/generated-images/09acbcfd-5936-4b44-9775-f842f767bcef/"
       "seedream5p-4ef16ef9bcc9e5449413c845cfcf2a34-0-1793869607552-e82df088.png")
DL = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/dl-m0p/"
# the M0p clay's shell (canvas uv, read on the clay): level lines (y, the x where they are clear of furniture) and the two corners
H_LINES = {"back wall floor line (y 0.789)": (0.789, [0.08, 0.12, 0.60, 0.66]), "back wall skirting top (y 0.752)": (0.752, [0.08, 0.12, 0.60, 0.66]),
           "back wall cornice (y 0.095)": (0.095, [0.12, 0.22, 0.45, 0.60])}
V_LINES = {"left corner (x 0.047)": (0.047, [0.20, 0.30, 0.40, 0.55]), "back-right corner (x 0.698)": (0.698, [0.20, 0.30, 0.40, 0.55, 0.65])}
ROUND_XZ, ROUND_D = (-1.20, 1.20), 0.38


def register(PL, jid):
    PL.VF.RETAKES[jid] = PL.JOBS["pose-m0p-v8b"]
    J = T.jr()
    if not any(j["id"] == jid for j in J["jobs"]):
        J["jobs"].append(dict(id=jid, out_dir=OD_REL, model="code" if jid != SRC_ID else "seedream-5-pro", tokens=0, status="stub"))
        T.save_jr(J)
    PL.VF.RETAKES_JOBS = T.JR


def to16(u, v):
    """canvas uv -> the 16:9 frame at 1920 x 1080"""
    return (u * 4072 - 116) / 3840 * 1920, (v * 2290 - 65) / 2160 * 1080


def shell(path, label):
    c, r = SL.frame16(CLAY), SL.frame16(path)
    gxc, gyc = SL.grads(c)
    gxr, gyr = SL.grads(r)
    rows, src, dst = [], [], []
    floor_r = {}
    for ln, (v, us) in H_LINES.items():
        for u in us:
            x, y = to16(u, v)
            x, y = int(round(x)), int(round(y))
            pc, pr = gyc[:, x - 15:x + 16].mean(1), gyr[:, x - 15:x + 16].mean(1)
            yc, yr, rel = SL.find(pc, pr, y)
            if ln.startswith("back wall floor"):
                floor_r[x] = (yc, yr)
            elif ln.startswith("back wall skirting") and x in floor_r and floor_r[x][1] is not None:
                # as a pair with the floor line (the gap 0.6-1.6x the clay's): the skirting's own edge above the render's floor line
                fc, fr_ = floor_r[x]
                gap = fc - yc
                a_, b_ = int(fr_ - 1.6 * gap), int(fr_ - 0.6 * gap)
                seg = pr[a_:b_ + 1]
                sign = np.sign(pc[int(round(yc))])
                cand = [i for i in SL.peaks(seg) if np.sign(seg[i]) == sign]
                if cand:
                    j = a_ + max(cand, key=lambda i: abs(seg[i]))
                    yr = j + SL.subpix(pr, j)
                    rel = float(abs(pr[j]) / max(abs(pc[int(round(yc))]), 1e-3))
            rows.append(dict(line=ln, at_x=x, clay=round(float(yc), 2), render=(round(float(yr), 2) if yr is not None else None),
                             d=(round(float(yr - yc), 2) if yr is not None else None), rel_strength=round(rel, 2)))
            if yr is not None:
                src.append((x, yc))
                dst.append((x, yr))
    for ln, (u, vs) in V_LINES.items():
        for v in vs:
            x, y = to16(u, v)
            x, y = int(round(x)), int(round(y))
            pc, pr = gxc[y - 20:y + 21].mean(0), gxr[y - 20:y + 21].mean(0)
            xc, xr, rel = SL.find(pc, pr, x)
            rows.append(dict(line=ln, at_y=y, clay=round(float(xc), 2), render=(round(float(xr), 2) if xr is not None else None),
                             d=(round(float(xr - xc), 2) if xr is not None else None), rel_strength=round(rel, 2)))
            if xr is not None:
                src.append((xc, y))
                dst.append((xr, y))
    src, dst = np.array(src, float), np.array(dst, float)
    raw = np.hypot(*(dst - src).T)
    A, _ = cv2.estimateAffine2D(src, dst, method=cv2.LMEDS)
    ra = np.hypot(*(cv2.transform(src.reshape(-1, 1, 2), A).reshape(-1, 2) - dst).T)
    per = {}
    for r_ in rows:
        if r_["d"] is not None:
            per.setdefault(r_["line"], []).append(abs(r_["d"]))
    rep = dict(still=os.path.relpath(path, REPO), label=label, clay=os.path.relpath(CLAY, REPO), frame_px=[1920, 1080], limit_px=SL.LIMIT, lines=rows,
               per_line={k: round(max(v), 2) for k, v in per.items()}, raw_max_px=round(float(raw.max()), 2),
               global_affine=dict(scale=[round(float(np.hypot(A[0, 0], A[1, 0])), 4), round(float(np.hypot(A[0, 1], A[1, 1])), 4)],
                                  shift_px=[round(float(A[0, 2]), 2), round(float(A[1, 2]), 2)], residual_max_px=round(float(ra.max()), 2)),
               verdict=dict(raw_pass=bool(raw.max() <= SL.LIMIT), after_global_affine_pass=bool(ra.max() <= SL.LIMIT),
                            rule="G1.4 master: every shell line within 9.6 px (0.5 % of 1920), raw or after one global affine (code)"),
               how="shell_lock_m0.find on the M0p clay's own level lines and corners (the M0 named points do not exist in this pose)")
    return rep


def overlay(path, rep, out):
    r = SL.frame16(path)
    c = SL.frame16(CLAY)
    e = cv2.Canny(cv2.cvtColor(np.clip(c, 0, 255).astype(np.uint8), cv2.COLOR_RGB2GRAY), 40, 110)
    im = np.clip(r, 0, 255).astype(np.uint8).copy()
    im[e > 0] = (im[e > 0] * 0.4 + np.array([255, 60, 60]) * 0.6).astype(np.uint8)
    for row in rep["lines"]:
        if row["render"] is None:
            continue
        if "at_x" in row:
            pc, pr = (row["at_x"], int(round(row["clay"]))), (row["at_x"], int(round(row["render"])))
        else:
            pc, pr = (int(round(row["clay"])), row["at_y"]), (int(round(row["render"])), row["at_y"])
        cv2.circle(im, pc, 6, (255, 0, 0), 2)
        cv2.circle(im, pr, 6, (0, 220, 0), 2)
        cv2.putText(im, f"{row['d']:+.0f}", (pr[0] + 8, pr[1] - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 120, 255), 2)
    v = rep["verdict"]
    cv2.putText(im, f"{rep['label']}: raw max {rep['raw_max_px']} px, after 1 affine {rep['global_affine']['residual_max_px']} px "
                    f"{'PASS' if v['after_global_affine_pass'] else 'FAIL'}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 0, 0), 2)
    cv2.imwrite(out, cv2.cvtColor(im, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 85])


def lock(PL, jid, path, suf):
    lk = PL.LK.run_frame(jid, render_path=path, out_path=os.path.join(OD, jid + suf + "-lock-v2.json"),
                         overlay_path=os.path.join(OD, jid + suf + "-lock-v2.jpg"), date=DATE)
    s, v = lk["summary"], lk["verdict"]
    return dict(shift_px=s["register_shift_px"], scale_pct=s["register_scale_pct"], band_after=s["worst_band_px_after_register"],
                tile_after=s["worst_tile_ecc_px_after_register"], fixed_edges_worst_px=s["fixed_edges_worst_px"], fixed_ratios=s["fixed_ratios"],
                verdict={k: v[k] for k in ("global_pass", "residual_pass", "edges_pass", "pass")})


def fetch():
    from PIL import Image
    os.makedirs(os.path.join(OD, "raw"), exist_ok=True)
    dl = os.path.join(DL, SRC_ID + ".png")
    if not os.path.exists(dl):
        subprocess.run(["curl", "-sS", "-L", "--max-time", "240", "-o", dl, URL], check=True)
    raw = os.path.join(OD, "raw", SRC_ID + ".png")
    open(raw, "wb").write(open(dl, "rb").read())
    im0 = Image.open(dl).convert("RGB")
    norm = os.path.join(OD, SRC_ID + ".png")
    im0.resize((2736, 1539), Image.LANCZOS).save(norm)
    PL = M._pipeline()
    register(PL, SRC_ID)
    lk = lock(PL, SRC_ID, norm, "")
    rep = shell(norm, f"{SRC_ID} (seedream-5-pro)")
    json.dump(rep, open(os.path.join(OD, SRC_ID + "-shell.json"), "w"), indent=1, ensure_ascii=False)
    overlay(norm, rep, os.path.join(OD, SRC_ID + "-shell.jpg"))
    J = T.jr()
    old = next((j for j in J["jobs"] if j["id"] == SRC_ID), {})
    J["jobs"] = [j for j in J["jobs"] if j["id"] != SRC_ID]
    row = dict(old, id=SRC_ID, out_dir=OD_REL, model="seedream-5-pro", tokens=650, status="fetched 2026-11-06 (var2 re-authorised)", url=URL,
               returned_px=list(im0.size), raw=os.path.relpath(raw, REPO), normalised=OD_REL + SRC_ID + ".png",
               shell=dict(raw_max_px=rep["raw_max_px"], after_global_affine_max_px=rep["global_affine"]["residual_max_px"], per_line=rep["per_line"],
                          affine_scale=rep["global_affine"]["scale"], affine_shift_px=rep["global_affine"]["shift_px"], verdict=rep["verdict"],
                          record=OD_REL + SRC_ID + "-shell.json", overlay=OD_REL + SRC_ID + "-shell.jpg"),
               lock_v2=lk)
    J["jobs"].append(row)
    T.save_jr(J)
    print(json.dumps(dict(lock=lk, shell={k: rep[k] for k in ("raw_max_px", "per_line", "global_affine", "verdict")}), indent=1))


def round_fix(a, cam):
    """the wall round (as m0_shell_fix.round_fix, for any camera): its rendered size against the projected 38 cm circle; scaled about its centre"""
    import art_m0_12 as A
    H, W = a.shape[:2]
    Hn = A.C_canvas(W, H) @ A.H_wall(cam)
    th = np.linspace(0, 2 * np.pi, 72, endpoint=False)
    circ = A.apply_h(Hn, np.stack([ROUND_XZ[0] + ROUND_D / 2 * np.cos(th), ROUND_XZ[1] + ROUND_D / 2 * np.sin(th)], 1))
    (tcx, tcy), (tw, thh), _ = cv2.fitEllipse(circ.astype(np.float32))
    Hh, L, S = M.hls(a)
    box = (int(tcx - 1.3 * tw), int(tcx + 1.3 * tw), int(tcy - 1.3 * thh), int(tcy + 1.3 * thh))
    rope = ((Hh >= 15) & (Hh <= 50) & (S >= 22) & (L < 85)).astype(np.uint8)
    rm = np.zeros_like(rope)
    rm[max(0, box[2]):box[3], max(0, box[0]):box[1]] = 1
    rope = cv2.morphologyEx(rope * rm, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(rope)
    k = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
    cnts, _ = cv2.findContours((lab == k).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    (ecx, ecy), (ew, eh), ang = cv2.fitEllipse(max(cnts, key=len).astype(np.float32))
    return dict(rendered=dict(centre_px=[round(ecx, 1), round(ecy, 1)], axes_px=[round(ew, 1), round(eh, 1)]),
                target=dict(centre_px=[round(tcx, 1), round(tcy, 1)], axes_px=[round(tw, 1), round(thh, 1)], wall_point=[ROUND_XZ[0], 0.02, ROUND_XZ[1]], diameter_cm=38),
                size_over_target=round(float(np.sqrt(ew * eh / (tw * thh))), 3), centre_offset_px=[round(ecx - tcx, 1), round(ecy - tcy, 1)])


def build():
    import fix_v8 as F8
    PL = M._pipeline()
    register(PL, SRC_ID)
    F8.VF = PL.VF
    a = F.load(os.path.join(OD, SRC_ID + ".png"))
    warped, aff = F8.global_affine_to_clay(SRC_ID, a)
    p = os.path.join(OD, JID + "-fix-base.png")
    F.save(warped, p)
    import art_m0_12 as A
    rr = round_fix(warped, A.CAMS["pose-m0p-v8b"])
    note = dict(asset_id=JID + "-fix-base", date=DATE, tokens=0, script="assets/renders/house-nordic-v7-2026-11-02/m0p_seedream.py",
                source=OD_REL + SRC_ID + ".png", clay="assets/blockout/house/framing/round5b/poses/M0p.png",
                global_affine=dict(aff, why="G1.4: lock_v2's register of the raw read -0.91 % vertical (limit 0.5 %); the M0p shell lines pass raw (6.6 px)"),
                wall_round=dict(rr, action="none: within 2 % of the projected 38 cm circle and 8 px of its centre (M0's seedream round was 1.86x and was scaled)"),
                furniture="kept as rendered (lock_v2 edges and ratios), the M0 rule",
                output=OD_REL + JID + "-fix-base.png")
    json.dump(note, open(p.replace(".png", ".json"), "w"), indent=1, ensure_ascii=False)
    print(json.dumps(dict(affine=aff["register_after"], round=rr)))


def art():
    import art_m0_12 as A
    PL = M._pipeline()
    register(PL, JID)
    M.OUT[JID] = OD_REL
    A.CAMS[JID] = A.CAMS["pose-m0p-v8b"]
    A.BASE_SUF, A.ART_SUF, A.DATE = "-fix-base", "-fix", DATE
    note = A.run(JID, do_lock=True)
    rep = shell(os.path.join(OD, JID + "-fix.png"), JID + "-fix")
    json.dump(rep, open(os.path.join(OD, JID + "-fix-shell.json"), "w"), indent=1, ensure_ascii=False)
    overlay(os.path.join(OD, JID + "-fix.png"), rep, os.path.join(OD, JID + "-fix-shell.jpg"))
    n = json.load(open(os.path.join(OD, JID + "-fix.json")))
    n["shell_lock"] = dict(raw_max_px=rep["raw_max_px"], per_line=rep["per_line"], verdict=rep["verdict"], record=OD_REL + JID + "-fix-shell.json")
    json.dump(n, open(os.path.join(OD, JID + "-fix.json"), "w"), indent=1, ensure_ascii=False)
    print(json.dumps(dict(shell=n["shell_lock"], lock=n["checks"]["lock_v2"], placed=n.get("placed_measured")), indent=0)[:2500])


if __name__ == "__main__":
    w = sys.argv[1]
    if w == "build":
        build()
    if w == "art":
        art()
    if w == "fetch":
        fetch()
    if w == "round":
        import art_m0_12 as A
        print(json.dumps(round_fix(F.load(os.path.join(OD, SRC_ID + ".png")), A.CAMS["pose-m0p-v8b"])))
