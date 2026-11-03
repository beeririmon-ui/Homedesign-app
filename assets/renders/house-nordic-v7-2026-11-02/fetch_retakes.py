#!/usr/bin/env python3
"""
Fetch and process one v8 retake (render-agent, 2026-11-03; 0 var2 tokens after the job): download the finished var2 image to
<out_dir>/raw/<id>.<ext>, normalise to exact 16:9 by a non-uniform resize as process_v7 did (no crop), save <out_dir>/<id>.png,
then (1) lock_v2 at the G1.4 thresholds (pan participant: 2 px per strip after register) -> <id>-lock-v2.json + overlay
<id>-lock-v2.jpg (the clay's edges in red over the still), (2) grading v3 (process_v8.py --exposure bible; the stops inherited
from the group reference where the frame has no wall of its own: K-girl-0 from K-girl's v3 grade, B2 r3 from B1 r3) -> <id>-graded-v3.png
(+ -frame-v3 / -graded-os6-v3 on the overscan canvases), <id>-measurements-v3.json, (3) the product-box overlay <id>-boxes-v3.png
(the clay's placeholder boxes, +-15 % band, on the graded still) for the +-15 % check, and (4) the job row in
jobs-retakes-2026-11-03.json (status, result url, lock summary, grade).
  python3 fetch_retakes.py <job id> <result url>
"""
import json
import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import v7_frames as VF  # noqa: E402
import lock_v2 as LK  # noqa: E402
import process_v8 as P  # noqa: E402

JR_PATH = os.path.join(HERE, "jobs-retakes-2026-11-03.json")
INHERIT = {"b2-v7-r3": ("b1-v7-r3", "-v3")}      # K-girl-0 reads its own wall since the r2 retake (process_v8 K_GIRL_0_WALL)
DL = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/dl-results"


def stops_of(fid, suffix):
    p = os.path.join(VF.out_dir(fid), fid + "-measurements" + suffix + ".json")
    return json.load(open(p))["grade"]["exposure"]["applied_stops"]


def boxes_overlay(graded_path, out_path, frame, fid, overscan):
    im = Image.open(graded_path).convert("RGB")
    W, H = im.size
    d = ImageDraw.Draw(im)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 22)
    except Exception:
        font = ImageFont.load_default()
    for nm, b in VF.product_boxes(frame, fid).items():
        u0, u1, v0, v1 = b
        x0, x1, y0, y1 = u0 * W, u1 * W, v0 * H, v1 * H
        d.rectangle((x0, y0, x1, y1), outline=(230, 40, 40), width=3)
        mx, my = 0.15 * (x1 - x0), 0.15 * (y1 - y0)
        d.rectangle((x0 - mx, y0 - my, x1 + mx, y1 + my), outline=(240, 200, 40), width=1)
        d.text((x0 + 4, max(0, y0 - 26)), nm.split("/")[-1], fill=(230, 40, 40), font=font)
    if overscan:
        fx0, fy0, fx1, fy1 = VF.frame_box_px(W, H)
        d.rectangle((fx0, fy0, fx1, fy1), outline=(40, 120, 240), width=2)
    im.save(out_path)


def main(jid, url):
    frame, kind, clay_file, pan, overscan, room = VF.frame(jid)
    J = json.load(open(JR_PATH))
    job = next(j for j in J["jobs"] if j["id"] == jid)
    out_dir = os.path.join(VF.REPO, job["out_dir"])
    os.makedirs(os.path.join(out_dir, "raw"), exist_ok=True)
    os.makedirs(DL, exist_ok=True)
    ext = os.path.splitext(url.split("?")[0])[1].lower() or ".png"
    dl = os.path.join(DL, jid + ext)
    r = subprocess.run(["curl", "-sS", "-L", "--max-time", "240", "-o", dl, "-w", "%{http_code}", url], capture_output=True, text=True)
    print("GET", r.stdout.strip(), os.path.getsize(dl))
    raw_copy = os.path.join(out_dir, "raw", jid + ext)
    Image.open(dl).save(raw_copy) if ext != ".png" else open(raw_copy, "wb").write(open(dl, "rb").read())
    im0 = Image.open(dl).convert("RGB")
    W0, H0 = im0.size
    W, H = W0, int(round(W0 * 9 / 16))
    im = im0.resize((W, H), Image.LANCZOS) if H != H0 else im0
    norm = os.path.join(out_dir, jid + ".png")
    im.save(norm)
    print("normalised", (W0, H0), "->", (W, H))
    # 1. lock_v2
    lock = LK.run_frame(jid, render_path=norm, out_path=os.path.join(out_dir, jid + "-lock-v2.json"), overlay_path=os.path.join(out_dir, jid + "-lock-v2.jpg"))
    # 2. grading v3
    stops = None
    if jid in INHERIT:
        stops = stops_of(*INHERIT[jid])
    res = P.process(jid, norm, "-v3", "v2", "auto", "none", out_dir, f"{jid}: v8 retake, grading v3 (Bible targets)", exposure="bible", stops=stops)
    # 3. boxes overlay
    boxes_overlay(os.path.join(out_dir, jid + "-graded-v3.png"), os.path.join(out_dir, jid + "-boxes-v3.png"), frame, jid, overscan)
    # 4. job row
    s, v = lock["summary"], lock["verdict"]
    job.update(status="done", result_url=url, raw_ext=ext.lstrip("."), returned_size_px=[W0, H0], normalised_px=[W, H],
               lock_v2=dict(shift_px=s["register_shift_px"], scale_pct=s["register_scale_pct"], band_after=s["worst_band_px_after_register"],
                            tile_after=s["worst_tile_ecc_px_after_register"], edges_worst_px=s["fixed_edges_worst_px"], ratios=s["fixed_ratios"],
                            residual_limit=v["thresholds"]["residual_px"], global_pass=v["global_pass"], residual_pass=v["residual_pass"], edges_pass=v["edges_pass"],
                            **{"pass": v["pass"]}, record=job["out_dir"] + jid + "-lock-v2.json", overlay=job["out_dir"] + jid + "-lock-v2.jpg"),
               grade_v3=dict(stops=res["grade"]["exposure"]["applied_stops"], inherited=stops is not None, target=res["bible_v3"]["target_L"], measured=res["bible_v3"]["measured_L"],
                             window_p99=res["measure_after"]["brightest area (window / door): L p50 / p99 / max"][1], black=res["measure_after"]["darkest 0.5% patch L [12-15]"],
                             meets_bible=res["bible_v3"]["meets_bible"], files=res["outputs"], measurements=job["out_dir"] + jid + "-measurements-v3.json"),
               boxes_overlay=job["out_dir"] + jid + "-boxes-v3.png")
    if overscan:
        fx0, fy0, fx1, fy1 = VF.frame_box_px(W, H)
        job["overscan"].update(output_canvas_px=[W, H], output_frame_box_px=[fx0, fy0, fx1, fy1], output_frame_px=[fx1 - fx0, fy1 - fy0],
                               files=dict(canvas=job["out_dir"] + jid + "-graded-v3.png", frame=job["out_dir"] + jid + "-frame-v3.png", os6=job["out_dir"] + jid + "-graded-os6-v3.png"))
    J["spent_tokens"] = sum(j.get("credits") or 0 for j in J["jobs"])
    json.dump(J, open(JR_PATH, "w"), indent=1, ensure_ascii=False)
    print("lock_v2", json.dumps(job["lock_v2"]))
    print("grade_v3", json.dumps(job["grade_v3"]))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
