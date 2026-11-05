#!/usr/bin/env python3
"""
m0_model_test.py: the three-model test for the M0 1.2 shell (briefs/render-m0-model-test-2026-11-05.md, owner decision M0S1; render-agent,
2026-11-05). New files only, under assets/renders/living-room/nordic/v9/:
  fetch <id> <url>   raw download -> <id>.png (normalised to the 2736 x 1539 overscan canvas), the shell lock (shell_lock_m0.py: QA's named
                     shell lines) -> <id>-shell.json / -shell.jpg, lock_v2 (edges v3, round-5b clay) -> <id>-lock-v2.json / .jpg, grading v5,
                     a row in jobs-m0-model-test-2026-11-05.json
  sheet              assets/renders/house-nordic-m0-model-test-sheet-2026-11-05.jpg: clay | each model | shell overlays
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
import shell_lock_m0 as SL  # noqa: E402

REPO = M.REPO
DATE = "2026-11-05"
OD_REL = "assets/renders/living-room/nordic/v9/"
OD = os.path.join(REPO, OD_REL)
JR = os.path.join(HERE, "jobs-m0-model-test-2026-11-05.json")
DL = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/dl-results"
SHEET = os.path.join(REPO, "assets/renders/house-nordic-m0-model-test-sheet-2026-11-05.jpg")


def jr():
    return json.load(open(JR)) if os.path.exists(JR) else dict(date=DATE, brief="briefs/render-m0-model-test-2026-11-05.md", decision="M0S1",
                                                                cap_tokens=1600, jobs=[])


def save_jr(J):
    J["tokens_spent"] = sum(j.get("tokens", 0) for j in J["jobs"])
    json.dump(J, open(JR, "w"), indent=1, ensure_ascii=False)


def overlay(still_png, rep, out_jpg):
    """the clay's shell points (red) and the render's (green) on the 16:9 frame at 1920, with the clay's edges faint"""
    r = SL.frame16(still_png)
    c = SL.frame16(SL.CLAY)
    e = cv2.Canny(cv2.cvtColor(np.clip(c, 0, 255).astype(np.uint8), cv2.COLOR_RGB2GRAY), 40, 110)
    im = np.clip(r, 0, 255).astype(np.uint8).copy()
    im[e > 0] = (im[e > 0] * 0.4 + np.array([255, 60, 60]) * 0.6).astype(np.uint8)
    for row in rep["lines"]:
        if "at_x" in row:
            pc = (int(row["at_x"]), int(round(row["clay"])))
            pr = (int(row["at_x"]), int(round(row["render"]))) if row["render"] is not None else None
        else:
            pc = (int(round(row["clay"])), int(row["at_y"]))
            pr = (int(round(row["render"])), int(row["at_y"])) if row["render"] is not None else None
        cv2.circle(im, pc, 6, (255, 0, 0), 2)
        if pr:
            cv2.circle(im, pr, 6, (0, 220, 0), 2)
            cv2.line(im, pc, pr, (255, 220, 0), 1)
            cv2.putText(im, f"{row['d']:+.0f}", (pr[0] + 8, pr[1] - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 120, 255), 2)
    v = rep["verdict"]
    cv2.putText(im, f"{rep['label']}: raw max {rep['raw_max_px']} px, after 1 affine {rep['global_affine']['residual_max_px']} px (limit 9.6) "
                    f"{'PASS' if v['after_global_affine_pass'] else 'FAIL'}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 0, 0), 2)
    cv2.imwrite(out_jpg, cv2.cvtColor(im, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 85])


def fetch(jid, url, model, tokens, extra=None):
    from PIL import Image
    os.makedirs(os.path.join(OD, "raw"), exist_ok=True)
    os.makedirs(DL, exist_ok=True)
    ext = os.path.splitext(url.split("?")[0])[1].lower() or ".png"
    dl = os.path.join(DL, jid + ext)
    rr = subprocess.run(["curl", "-sS", "-L", "--max-time", "240", "-o", dl, "-w", "%{http_code}", url], capture_output=True, text=True)
    raw = os.path.join(OD, "raw", jid + ext)
    open(raw, "wb").write(open(dl, "rb").read())
    im0 = Image.open(dl).convert("RGB")
    W0, H0 = im0.size
    im = im0.resize((2736, 1539), Image.LANCZOS)
    norm = os.path.join(OD, jid + ".png")
    im.save(norm)
    rep = SL.measure(norm, f"{jid} ({model})")
    json.dump(rep, open(os.path.join(OD, jid + "-shell.json"), "w"), indent=1, ensure_ascii=False)
    overlay(norm, rep, os.path.join(OD, jid + "-shell.jpg"))
    PL = M._pipeline()
    PL.VF.RETAKES[jid] = PL.JOBS["m0-v8b"]
    J0 = jr()
    if not any(j["id"] == jid for j in J0["jobs"]):
        J0["jobs"].append(dict(id=jid, out_dir=OD_REL, model=model, tokens=tokens, status="measuring"))
        save_jr(J0)
    PL.VF.RETAKES_JOBS = JR
    lock = PL.LK.run_frame(jid, render_path=norm, out_path=os.path.join(OD, jid + "-lock-v2.json"), overlay_path=os.path.join(OD, jid + "-lock-v2.jpg"), date=DATE)
    res = PL.P.process(jid, norm, "-v5", "v2", "auto", "none", OD, f"{jid}: M0 1.2 shell test ({model}), grading v5", exposure="bible", grade_mode="v5")
    s, v = lock["summary"], lock["verdict"]
    J = jr()
    J["jobs"] = [j for j in J["jobs"] if j["id"] != jid]
    row = dict(id=jid, out_dir=OD_REL, model=model, tokens=tokens, url=url, http=rr.stdout.strip(), returned_px=[W0, H0], raw=os.path.relpath(raw, REPO),
               normalised=OD_REL + jid + ".png",
               shell=dict(raw_max_px=rep["raw_max_px"], after_global_affine_max_px=rep["global_affine"]["residual_max_px"],
                          affine_scale=rep["global_affine"]["scale"], affine_shift_px=rep["global_affine"]["shift_px"],
                          homography_all_planes_max_px=rep["homography_all_planes_residual_max_px"],
                          back_wall_H_on_window_wall_max_px=rep["back_wall_homography_on_window_wall_max_px"],
                          vanishing_point=rep["back_wall_vanishing_point"], per_line=rep["per_line"], verdict=rep["verdict"],
                          record=OD_REL + jid + "-shell.json", overlay=OD_REL + jid + "-shell.jpg"),
               lock_v2=dict(shift_px=s["register_shift_px"], scale_pct=s["register_scale_pct"], band_after=s["worst_band_px_after_register"],
                            tile_after=s["worst_tile_ecc_px_after_register"], fixed_edges_worst_px=s["fixed_edges_worst_px"], fixed_ratios=s["fixed_ratios"],
                            verdict={k: v[k] for k in ("global_pass", "residual_pass", "edges_pass", "pass")}),
               furniture_edges=lock["fixed_edges"],
               grade_v5=dict(measured=res["bible_v3"]["measured_L"], range=res["bible_v3"]["range"], meets_bible=res["bible_v3"]["meets_bible"],
                             fails=[k for k, x in res["checks"].items() if k.startswith("bible_") and x is False], outputs=res["outputs"]),
               **(extra or {}))
    J["jobs"].append(row)
    save_jr(J)
    print(json.dumps({k: row[k] for k in ("id", "returned_px", "shell", "lock_v2", "grade_v5")}, indent=1)[:4000])
    return row


def sheet():
    from PIL import Image, ImageDraw
    J = jr()
    tiles = [(SL.CLAY, "CLAY round 5b (M0 1.2.3 camera)")]
    for j in J["jobs"]:
        if "shell" not in j or "normalised" not in j:          # stub / composite / not-run rows have no render of their own
            continue
        lk = j["lock_v2"]
        tiles.append((os.path.join(REPO, j["normalised"]), f"{j['model']} ({j['tokens']} tok): shell raw {j['shell']['raw_max_px']} / affine {j['shell']['after_global_affine_max_px']} px, "
                                                           f"VP {j['shell']['vanishing_point']['render'][0]:.0f} (clay {j['shell']['vanishing_point']['clay'][0]:.0f})"))
        tiles.append((os.path.join(REPO, j["shell"]["overlay"]), f"{j['id']} shell lock overlay: red = clay points, green = render"))
        lv = os.path.join(REPO, j["out_dir"], j["id"] + "-lock-v2.jpg")
        if os.path.exists(lv):
            tiles.append((lv, f"{j['id']} lock_v2: shift {lk['shift_px']} px, scale {lk['scale_pct']} %, edges {lk['fixed_edges_worst_px']} px, pass {lk['verdict']['pass']}"))
    for j in J["jobs"]:
        if j.get("status") != "composite":
            continue
        fx = os.path.join(REPO, j["out_dir"], j["id"] + "-frame-fix-v5.png")
        if not os.path.exists(fx):
            continue
        n = json.load(open(os.path.join(REPO, j["out_dir"], j["id"] + "-fix.json")))
        lk = n.get("checks", {}).get("lock_v2", {})
        sh = n.get("shell_lock", {})
        tiles.append((fx, f"{j['id']}-fix (code, 0 tok), grading v5: lock_v2 pass {lk.get('verdict', {}).get('pass')}, shift {lk.get('shift_px')} px, "
                          f"edges {lk.get('fixed_edges_worst_px')} px; shell raw {sh.get('raw_max_px')} px"))
        for suf, t in (("-fix-shell.jpg", "shell lock overlay"), ("-fix-lock-v2.jpg", "lock_v2 overlay")):
            p = os.path.join(REPO, j["out_dir"], j["id"] + suf)
            if os.path.exists(p):
                tiles.append((p, f"{j['id']}-fix {t}"))
    w = 960
    rows = []
    for p, t in tiles:
        im = Image.open(p).convert("RGB")
        im = im.resize((w, int(round(w * im.size[1] / im.size[0]))), Image.LANCZOS)
        if im.size[1] != 540:
            im = im.resize((w, 540), Image.LANCZOS)
        canvas = Image.new("RGB", (w, 540 + 34), (250, 250, 250))
        canvas.paste(im, (0, 34))
        ImageDraw.Draw(canvas).text((8, 10), t, fill=(20, 20, 20))
        rows.append(canvas)
    cols = 2
    n = len(rows)
    H = ((n + cols - 1) // cols) * 574
    out = Image.new("RGB", (cols * w, H + 40), (255, 255, 255))
    skipped = "; ".join(f"{j['model']}: {j['status']}" for j in J["jobs"] if j.get("status") in ("not run", "not needed"))
    ImageDraw.Draw(out).text((10, 12), f"M0 1.2 shell, three-model test ({DATE}, decision M0S1): tokens {J.get('tokens_spent')} of {J['cap_tokens']} "
                                       f"(incl. the M0p job, not fetched). {skipped}. Not QA'd.", fill=(0, 0, 0))
    for i, t in enumerate(rows):
        out.paste(t, ((i % cols) * w, 40 + (i // cols) * 574))
    out.save(SHEET, quality=85)
    print(SHEET)


if __name__ == "__main__":
    if sys.argv[1] == "fetch":
        fetch(sys.argv[2], sys.argv[3], sys.argv[4], int(sys.argv[5]), json.loads(sys.argv[6]) if len(sys.argv) > 6 else None)
    elif sys.argv[1] == "sheet":
        sheet()
