#!/usr/bin/env python3
"""
m0_1_2_pipeline.py: the M0 1.2.1 jobs of briefs/render-m0-new-camera-2026-11-03.md (render-agent, 2026-11-03) on the v8 tools of this
folder, without changing them. What it patches at import, in memory only:
  - v7_frames: the three new ids in the RETAKES table (m0-v8, pose-m0p-v8, pose-m0x-v8), the clay folder = framing/round5 (the 1.2.1
    clays, framing_r5.py), the jobs file = jobs-m0-1-2-2026-11-03.json, and the 1.1 M0 furniture boxes dropped: the round-5 clay carries
    sofa, coffee table and armchair as 'furniture' boxes, so lock_v2 reads its fixed edges from the clay of the new camera;
  - process_v8: the M0 grade points are the Bible 1.8 (B1) points of the 1.2 clay (canvas uv from round5/selfcheck.json: the back wall by
    the corner (-1.75, 0, 1.60) [L 90-94, regrade-v3 target 93 (92-95) kept as the brief asks] and the window wall (-2.30, 0.30, 1.60)
    [L 80-88]) and the 1.2 window box; M0p reads the same wall in its own clay; M0x (no wall in frame) inherits M0's stops.
lock_v2.py and process_v8.py run unchanged (G1.4: M0 is a video endpoint, 0.5 % = 9.6 px per strip; M0p / M0x are pan endpoints, 2 px).

  python3 m0_1_2_pipeline.py put <local> <upload_url> <public_url> <key> [--clay]     # record a PUT upload (sha256 verified)
  python3 m0_1_2_pipeline.py prep <id>                                                 # job-<id>.json + the jobs row ("prepared")
  python3 m0_1_2_pipeline.py fetch <id> <result_url>                                   # raw, normalise, lock_v2, grade v3, boxes, jobs row
  python3 m0_1_2_pipeline.py sheet                                                     # old M0 r2 | new M0 | lock -> assets/renders/house-nordic-m0-1-2-sheet-2026-11-03.jpg

--r5b (render-agent, 2026-11-04; the brief resumed after house plan 1.2.2): the same steps on the round-5b clays (framing/round5b: pouf,
armchair and rug at 1.2.2), the v8b prompts (gen_m0_v8_prompts.py --round5b), new ids m0-v8b / pose-m0p-v8b / pose-m0x-v8b (new files
only; the jobs file jobs-m0-1-2-2-2026-11-04.json), grading v4 (process_v8 --grade v4: the M0 1.2 Bible points from the round-5b
selfcheck, the back wall by the corner (0.427, 0.416) [90-94, target 93] and the window wall (0.352, 0.415) [80-88], the wall hue
correction when H > 40, C* <= 7; M0x inherits M0's stops and correction), lock_v2 edges v3, and a `cutouts` step that cuts M0p's /
M0x's references from the new M0 (graded v4) by the frame uv boxes their prompts name. Without --r5b everything is as on 2026-11-03.
--dry (with --r5b): every output into the scratchpad (dry-m0-1-2-2/), no var2 call anywhere (the clay and the cut-outs are marked "not
uploaded"), fetch takes a local file; used to run the chain end to end on the clay itself.

  python3 m0_1_2_pipeline.py --r5b put <local> <upload_url> <public_url> <key> [--clay]   # clay keys M0 / M0p / M0x; cut-out keys m0p-* / m0x-*
  python3 m0_1_2_pipeline.py --r5b prep m0-v8b                                           # job-m0-v8b.json: the var2 create_image args, ready
  python3 m0_1_2_pipeline.py --r5b fetch m0-v8b <result_url>                             # raw, normalise, lock_v2 (v3), grade v4, boxes, jobs row
  python3 m0_1_2_pipeline.py --r5b cutouts                                               # M0p / M0x references from m0-v8b graded v4
  python3 m0_1_2_pipeline.py --r5b sheet                                                 # -> assets/renders/house-nordic-m0-1-2-2-sheet-2026-11-04.jpg
  python3 m0_1_2_pipeline.py --r5b --dry dryrun                                          # the whole chain on the clay, no var2
"""
import hashlib
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, HERE)
import v7_frames as VF  # noqa: E402

R5 = os.path.join(REPO, "assets", "blockout", "house", "framing", "round5")
JR_PATH = os.path.join(HERE, "jobs-m0-1-2-2026-11-03.json")
IDX_PATH = os.path.join(HERE, "refs", "index-m0-1-2-2026-11-03.json")
IDX7 = json.load(open(os.path.join(HERE, "refs", "index-v7.json")))
DL = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/dl-results"
DATE = "2026-11-03"

# id -> (frame, kind, clay, pan endpoint (2 px) / video endpoint (9.6 px), overscan canvas, room)
JOBS = {"m0-v8": ("M0", "master", "M0.png", False, True, "living-room"),
        "pose-m0p-v8": ("M0p", "pose", "poses/M0p.png", True, True, "living-room"),
        "pose-m0x-v8": ("M0x", "pose", "poses/M0x.png", True, True, "living-room")}
OUT_DIR = {"m0-v8": "assets/renders/living-room/nordic/v8/", "pose-m0p-v8": "assets/renders/poses/nordic/v8/", "pose-m0x-v8": "assets/renders/poses/nordic/v8/"}
PROMPT = {"m0-v8": "assets/prompts/recipe-v5.nordic/m0-v8.txt", "pose-m0p-v8": "assets/prompts/poses-v7.nordic/pose-m0p-v8.txt",
          "pose-m0x-v8": "assets/prompts/poses-v7.nordic/pose-m0x-v8.txt"}
INHERIT = {"pose-m0x-v8": ("m0-v8", "-v3")}
R5B = "--r5b" in sys.argv
DRY = R5B and "--dry" in sys.argv
GRADE = "v3"
IDX_NEW = None
SHEET_OUT = os.path.join(REPO, "assets", "renders", "house-nordic-m0-1-2-sheet-2026-11-03.jpg")
if R5B:
    R5 = os.path.join(REPO, "assets", "blockout", "house", "framing", "round5b")
    JR_PATH = os.path.join(HERE, "jobs-m0-1-2-2-2026-11-04.json")
    IDX_NEW = os.path.join(HERE, "refs", "index-m0-1-2-2-2026-11-04.json")
    DATE = "2026-11-04"
    GRADE = "v4"
    JOBS = {"m0-v8b": ("M0", "master", "M0.png", False, True, "living-room"),
            "pose-m0p-v8b": ("M0p", "pose", "poses/M0p.png", True, True, "living-room"),
            "pose-m0x-v8b": ("M0x", "pose", "poses/M0x.png", True, True, "living-room")}
    OUT_DIR = {"m0-v8b": "assets/renders/living-room/nordic/v8/", "pose-m0p-v8b": "assets/renders/poses/nordic/v8/", "pose-m0x-v8b": "assets/renders/poses/nordic/v8/"}
    PROMPT = {"m0-v8b": "assets/prompts/recipe-v5.nordic/m0-v8b.txt", "pose-m0p-v8b": "assets/prompts/poses-v7.nordic/pose-m0p-v8b.txt",
              "pose-m0x-v8b": "assets/prompts/poses-v7.nordic/pose-m0x-v8b.txt"}
    INHERIT = {"pose-m0x-v8b": ("m0-v8b", "-v4")}
    SHEET_OUT = os.path.join(REPO, "assets", "renders", "house-nordic-m0-1-2-2-sheet-2026-11-04.jpg")
    if DRY:
        DRYD = os.path.join(os.path.dirname(DL), "dry-m0-1-2-2")
        os.makedirs(DRYD, exist_ok=True)
        JR_PATH = os.path.join(DRYD, "jobs-dry.json")
        IDX_NEW = os.path.join(DRYD, "refs-dry.json")
        OUT_DIR = {k: os.path.join(DRYD, "out") + "/" for k in OUT_DIR}
        SHEET_OUT = os.path.join(DRYD, "sheet-dry.jpg")
# the M0p / M0x references cut from the new M0 (frame uv boxes as their prompts name them; 2026-11-04)
CUTS = {"m0p-1-sofa-wall": (0.45, 0.92, 0.25, 0.95), "m0p-2-table": (0.44, 0.81, 0.70, 1.00), "m0p-3-floor-right": (0.85, 1.00, 0.55, 1.00),
        "m0x-1-sofa-right-end": (0.75, 0.93, 0.55, 0.95), "m0x-2-floor-rug": (0.55, 0.85, 0.85, 1.00)}
# the 1.2 window opening (plan projection, frame fractions): u 0.034-0.292, v -0.077..0.673 -> the overscan canvas
_W = (0.034, 0.292, -0.077, 0.673)
M0_WIN_12 = (round((_W[0] * 3840 + 116) / 4072, 4), round((_W[1] * 3840 + 116) / 4072, 4), max(0.0, round((_W[2] * 2160 + 65) / 2290, 4)), round((_W[3] * 2160 + 65) / 2290, 4))

VF.R4 = R5
VF.RETAKES.update(JOBS)
VF.RETAKES_JOBS = JR_PATH
VF.M0_FURNITURE = {}

import lock_v2 as LK  # noqa: E402
import process_v8 as P  # noqa: E402
import fetch_retakes as FR  # noqa: E402

P.M0_PTS = {}
P.M0_WIN = M0_WIN_12
P.BIBLE_TARGET["M0"] = (93.0, 92.0, 95.0, "Bible 1.8 B1: the back wall by the corner (-1.75, 0, 1.60) L 90-94; the regrade-v3 target 93 [92-95] kept (briefs/render-m0-new-camera-2026-11-03.md 5)")
_choose0 = P.choose_points


def choose_points_12(frame, kind, sc_frame, sc_all, wb_mode, exposure="cap", v4=False):
    pts, wb_pt, src, win_box, warn = _choose0(frame, kind, sc_frame, sc_all, wb_mode, exposure, v4)
    if frame in ("M0", "M0p", "M0x"):
        wp = sc_frame.get("wall_patches") or {}
        bw, ww = wp.get("bible18_back_wall_by_corner_L90_94"), wp.get("bible18_window_wall_L80_88")
        if bw and "L_hsl" in bw and frame != "M0x":
            wb_pt = (bw["u"], bw["v"])
            src = f"Bible 1.8 B1 point: back wall by the corner (-1.75, 0, 1.60) at canvas ({bw['u']:.3f}, {bw['v']:.3f}); clay L {bw['L_hsl']} (target 93, 92-95 as regrade-v3)"
            warn = None
            pts[f"back wall by the corner ({bw['u']:.3f},{bw['v']:.3f}) [B1: 90-94; regrade-v3 target 93]"] = wb_pt
        if ww and "L_hsl" in ww:
            pts[f"window wall ({ww['u']:.3f},{ww['v']:.3f}) [B1: 80-88]"] = (ww["u"], ww["v"])
        for k, lab in (("back_wall_behind_art_centre", "back wall behind the art centre [88-91]"), ("back_wall_right_end_L82_86", "back wall right end [82-86]"),
                       ("hero_wall_mid", "hero wall mid (above the art)"), ("ceiling", "ceiling"), ("floor_centre", "floor centre")):
            q = wp.get(k)
            if q and "L_hsl" in q:
                pts[f"{lab} ({q['u']:.3f},{q['v']:.3f})"] = (q["u"], q["v"])
        if frame == "M0":
            win_box = M0_WIN_12
        if frame == "M0x":
            warn = (f"no wall of the living room in frame: stops inherited from {'m0-v8b' if R5B else 'm0-v8'} (one exposure per camera point, P1 pan); "
                    "the default point is a reading only")
    return pts, wb_pt, src, win_box, warn


P.choose_points = choose_points_12


def _jr():
    return json.load(open(JR_PATH)) if os.path.exists(JR_PATH) else {"clay": {}, "jobs": []}


def _save_jr(J):
    J["stage"] = ("M0 at the 1.2.1 camera, house plan 1.2.2 positions (briefs/render-m0-new-camera-2026-11-03.md, resumed 2026-11-04): m0-v8b, then "
                  "pose-m0p-v8b and pose-m0x-v8b with M0's cut-outs" + (" [DRY RUN on the clay: no var2]" if DRY else "")) if R5B else \
        "M0 at the 1.2.1 camera (briefs/render-m0-new-camera-2026-11-03.md): m0-v8, then pose-m0p-v8 and pose-m0x-v8 with M0's cut-outs"
    J["model"] = "gpt-image-2-5, quality sunburst, 2K, 16:9, image-to-image from the round-5" + ("b" if R5B else "") + " clay; recipe v8"
    J["cap_tokens"] = 2400
    J["budget_note"] = "1,800 for the three jobs (600 each, one attempt) + 600 reserve: a second attempt only for M0 and only on a lock_v2 scale failure"
    J["spent_tokens"] = sum(j.get("credits") or 0 for j in J["jobs"])
    json.dump(J, open(JR_PATH, "w"), indent=1, ensure_ascii=False)


def put(local, up, pub, key, clay=False):
    ct = "image/png" if local.lower().endswith(".png") else "image/jpeg"
    sha = hashlib.sha256(open(local, "rb").read()).hexdigest()
    r = subprocess.run(["curl", "-sS", "-X", "PUT", "--data-binary", "@" + local, "-H", "Content-Type: " + ct, "-o", "/dev/null", "-w", "%{http_code}", up], capture_output=True, text=True)
    tmp = os.path.join(os.path.dirname(DL), "put-back-m012.bin")
    os.makedirs(os.path.dirname(tmp), exist_ok=True)
    r2 = subprocess.run(["curl", "-sS", "-L", "--max-time", "180", "-o", tmp, "-w", "%{http_code}", pub], capture_output=True, text=True)
    sha2 = hashlib.sha256(open(tmp, "rb").read()).hexdigest() if os.path.exists(tmp) else None
    ok = (r.stdout.strip() == "200" and sha == sha2)
    rec = dict(var2_url=pub, put=r.stdout.strip(), get=r2.stdout.strip(), verified=ok, size=os.path.getsize(local), sha256=sha)
    if clay:
        J = _jr()
        J.setdefault("clay", {})[key] = dict(local=os.path.relpath(local, REPO), **rec)
        _save_jr(J)
    else:
        ip = IDX_NEW if (IDX_NEW and key in CUTS) else IDX_PATH
        idx = json.load(open(ip))
        idx["refs"][key].update(rec)
        json.dump(idx, open(ip, "w"), indent=1, ensure_ascii=False)
    print(key, os.path.basename(local), "PUT", r.stdout.strip(), "GET", r2.stdout.strip(), "verified", ok)
    return ok


def v7ref(note_part):
    for x in IDX7["frames"]["M0"]:
        if note_part in x["note"]:
            return x["var2_url"]
    raise KeyError(note_part)


def myref(key):
    if key in CUTS and IDX_NEW:
        r = (json.load(open(IDX_NEW)) if os.path.exists(IDX_NEW) else {"refs": {}})["refs"].get(key, {})
    else:
        r = json.load(open(IDX_PATH))["refs"][key]
    u = r.get("var2_url")
    if DRY and not u:
        return f"DRY-RUN:not-uploaded:{key}"
    assert u, f"reference {key} not uploaded"
    return u


# the product close-ups of m0-v7 (wow pass order b, c, e, h, i, j, l, m, n, o), already on var2
PRODUCTS_M0 = [("cube", "travertine cube"), ("pendant", "pumpkin pendant"), ("jar", "jar"), ("nyoko", "NYOKO"), ("boucle", "boucle cushion"),
               ("sage", "sage knit"), ("throw", "muslin throw"), ("runner", "sage runner"), ("holders", "travertine holders"), ("bowl", "bowl")]
SPEC = {
    "m0-v8": dict(cutouts=["m012-1-sofa", "m012-2-table", "m012-3-armchair"], products=PRODUCTS_M0, clay_key="M0",
                  refs_note="1-3 cut-outs of the old M0 r2 graded v3 (sofa, coffee table, armchair: look only); 4-13 = m0-v7 product close-ups: cube, pendant, jar, NYOKO, boucle, sage knit, throw, runner, holders, bowl"),
    "pose-m0p-v8": dict(cutouts=["m0p-1-sofa-wall", "m0p-2-table", "m0p-3-floor-right"], products=[p for p in PRODUCTS_M0 if p[0] != "jar"], clay_key="M0p",
                        refs_note="1-3 cut-outs of the new M0 (m0-v8 graded v3): sofa with the wall and the cubes, table group, floor and rug on the right; 4-12 = m0-v7 product close-ups (no jar: the sill is out of this pose)"),
    "pose-m0x-v8": dict(cutouts=["m0x-1-sofa-right-end", "m0x-2-floor-rug", "d1-3-dining-through-opening"], products=[p for p in PRODUCTS_M0 if p[0] in ("cube", "nyoko", "throw")], clay_key="M0x",
                        refs_note="1-2 cut-outs of the new M0 (sofa right end with throw and lumbar; floor and rug); 3 = cut-out of the D1 v7 master (the dining table under the lantern, the bench, the kitchen run: the view through the opening only); 4-6 = cube, NYOKO, throw"),
}


if R5B:
    SPEC = {"m0-v8b": dict(SPEC["m0-v8"], refs_note=SPEC["m0-v8"]["refs_note"] + " (round-5b clay, house plan 1.2.2)"),
            "pose-m0p-v8b": dict(SPEC["pose-m0p-v8"], refs_note=SPEC["pose-m0p-v8"]["refs_note"].replace("m0-v8 graded v3", "m0-v8b graded v4")),
            "pose-m0x-v8b": dict(SPEC["pose-m0x-v8"], refs_note=SPEC["pose-m0x-v8"]["refs_note"])}


def prep(jid, attempt=1, attempt_note=None):
    S = SPEC[jid]
    frame, kind, clay_file, pan, overscan, room = JOBS[jid]
    txt = open(os.path.join(REPO, PROMPT[jid]), encoding="utf-8").read()
    body = [l for l in txt.split("\n") if not l.startswith("#")]
    while body and body[0].strip() == "":
        body.pop(0)
    while body and body[-1].strip() == "":
        body.pop()
    prompt = "\n".join(body)
    assert len(prompt) <= 4000, f"prompt {len(prompt)} > 4000"
    refs = [myref(k) for k in S["cutouts"]] + [v7ref(n) for _, n in S["products"]]
    assert all(refs) and len(refs) <= 15
    J = _jr()
    clay = J.get("clay", {}).get(S["clay_key"])
    if DRY and not clay:
        loc = os.path.join(R5, JOBS[jid][2])
        clay = dict(local=os.path.relpath(loc, REPO), var2_url=f"DRY-RUN:not-uploaded:clay-{S['clay_key']}", verified=False,
                    sha256=hashlib.sha256(open(loc, "rb").read()).hexdigest())
    assert clay and (clay.get("verified") or DRY), "clay upload not verified"
    key = f"v8-m0-1-2-{jid}-{DATE.replace('-', '')}-a{attempt}"
    args = dict(model="gpt-image-2-5", type="image-to-image", quality="sunburst", resolution="2K", aspect_ratio="16:9",
                image_url=clay["var2_url"], image_refs=refs, prompt=prompt, idempotency_key=key)
    out = dict(id=jid, frame=frame, recipe="v8", prompt_deviation="lines starting with # stripped; positions already in canvas fractions (no conversion)",
               prompt_chars=len(prompt), ascii=prompt.isascii(), refs=len(refs), refs_note=S["refs_note"], clay=clay["local"], clay_sha256=clay["sha256"], args=args)
    out["dry_run"] = DRY
    json.dump(out, open(os.path.join(os.path.dirname(JR_PATH) if DRY else HERE, f"job-{jid}.json"), "w"), indent=1, ensure_ascii=False)
    row = dict(id=jid, frame=frame, kind=kind, room=room, recipe="v8 (docs/render-recipe-nordic-v8-2026-11-03.md)", prompt_file=PROMPT[jid], out_dir=OUT_DIR[jid],
               model="gpt-image-2-5", quality="sunburst", resolution="2K", aspect_ratio="16:9", idempotency_key=key, attempt=attempt,
               attempt_note=attempt_note or "first and only attempt (one attempt per prompt; the reserve is for M0 on a scale failure only)", status="prepared",
               credits_estimated=None, credits=None, date=DATE, pan_participant=pan, lock_threshold_px=(2.0 if pan else 9.6),
               overscan=(dict(on=True, canvas_px=[4072, 2290], frame_px=[3840, 2160], crop_box_px=[116, 65, 3956, 2225], per_side_fraction_x=0.0302, per_side_fraction_y=0.0301) if overscan else dict(on=False)),
               clay=clay["local"], clay_var2_url=clay["var2_url"], refs=len(refs), refs_note=S["refs_note"], prompt_chars=len(prompt))
    prev = next((j for j in J["jobs"] if j["id"] == jid), None)
    if prev and prev.get("attempts"):
        row["attempts"] = prev["attempts"]
    J["jobs"] = [j for j in J["jobs"] if j["id"] != jid] + [row]
    _save_jr(J)
    print(json.dumps({k: v for k, v in out.items() if k != "args"}, ensure_ascii=False))
    return out


def fetch(jid, url):
    from PIL import Image
    frame, kind, clay_file, pan, overscan, room = JOBS[jid]
    J = _jr()
    job = next(j for j in J["jobs"] if j["id"] == jid)
    out_dir = os.path.join(REPO, OUT_DIR[jid])
    os.makedirs(os.path.join(out_dir, "raw"), exist_ok=True)
    os.makedirs(DL, exist_ok=True)
    ext = os.path.splitext(url.split("?")[0])[1].lower() or ".png"
    dl = os.path.join(DL, jid + ext)
    if os.path.exists(url):                       # a local file (the dry run on the clay)
        open(dl, "wb").write(open(url, "rb").read())
        print("local", url, os.path.getsize(dl))
    else:
        r = subprocess.run(["curl", "-sS", "-L", "--max-time", "240", "-o", dl, "-w", "%{http_code}", url], capture_output=True, text=True)
        print("GET", r.stdout.strip(), os.path.getsize(dl))
    raw_copy = os.path.join(out_dir, "raw", jid + ext)
    open(raw_copy, "wb").write(open(dl, "rb").read())
    im0 = Image.open(dl).convert("RGB")
    W0, H0 = im0.size
    W, H = W0, int(round(W0 * 9 / 16))
    im = im0.resize((W, H), Image.LANCZOS) if H != H0 else im0
    norm = os.path.join(out_dir, jid + ".png")
    im.save(norm)
    print("normalised", (W0, H0), "->", (W, H))
    lock = LK.run_frame(jid, render_path=norm, out_path=os.path.join(out_dir, jid + "-lock-v2.json"), overlay_path=os.path.join(out_dir, jid + "-lock-v2.jpg"))
    stops = hue_force = None
    if jid in INHERIT:
        stops = FR.stops_of(*INHERIT[jid])
        if GRADE == "v4":
            bm = json.load(open(os.path.join(VF.out_dir(INHERIT[jid][0]), INHERIT[jid][0] + "-measurements" + INHERIT[jid][1] + ".json")))
            hue_force = True if bm["grade"].get("wall_hue_v4", {}).get("applied") else None
    gs = "-" + GRADE
    if GRADE == "v4":
        res = P.process(jid, norm, gs, "v2", "auto", "none", out_dir, f"{jid}: M0 1.2.1 at 1.2.2 positions, grading v4 (Bible 1.8 + QA §11.2)",
                        exposure="bible", stops=stops, grade_mode="v4", hue_force=hue_force)
    else:
        res = P.process(jid, norm, "-v3", "v2", "auto", "none", out_dir, f"{jid}: M0 1.2.1, grading v3 (Bible targets)", exposure="bible", stops=stops)
    FR.boxes_overlay(os.path.join(out_dir, jid + "-graded" + gs + ".png"), os.path.join(out_dir, jid + "-boxes" + gs + ".png"), frame, jid, overscan)
    # QA 2026-11-03 §4: wall H / C* absolute and the window wall, + the hue correction when H > 40 (-graded-v3h.png; the -v3 still is kept)
    wp = (VF.selfcheck_for(jid, frame).get("wall_patches") or {})
    wall = wp.get("bible18_back_wall_by_corner_L90_94") if frame != "M0x" else None
    winw = wp.get("bible18_window_wall_L80_88")
    qa = None
    if wall and "u" in wall and GRADE == "v3":
        qa = qa_wall(os.path.join(out_dir, jid + "-graded-v3.png"), (wall["u"], wall["v"]), (winw["u"], winw["v"]) if winw and "u" in winw else None,
                     os.path.join(out_dir, jid + "-graded-v3h.png"))
        if qa.get("output") and overscan:
            from PIL import Image as _I
            g = _I.open(qa["output"])
            g.crop(VF.frame_box_px(*g.size)).save(os.path.join(out_dir, jid + "-frame-v3h.png"))
        json.dump(qa, open(os.path.join(out_dir, jid + "-qa-wall-v3.json"), "w"), indent=1)
    s, v = lock["summary"], lock["verdict"]
    job.update(status="done", result_url=url, raw_ext=ext.lstrip("."), returned_size_px=[W0, H0], normalised_px=[W, H],
               lock_v2=dict(shift_px=s["register_shift_px"], scale_pct=s["register_scale_pct"], band_after=s["worst_band_px_after_register"],
                            tile_after=s["worst_tile_ecc_px_after_register"], edges_worst_px=s["fixed_edges_worst_px"], ratios=s["fixed_ratios"],
                            residual_limit=v["thresholds"]["residual_px"], global_pass=v["global_pass"], residual_pass=v["residual_pass"], edges_pass=v["edges_pass"],
                            **{"pass": v["pass"]}, record=OUT_DIR[jid] + jid + "-lock-v2.json", overlay=OUT_DIR[jid] + jid + "-lock-v2.jpg"),
               **{"grade_" + GRADE: dict(stops=res["grade"]["exposure"]["applied_stops"], inherited=stops is not None, target=res["bible_v3"]["target_L"], measured=res["bible_v3"]["measured_L"],
                                         window_wall=res["bible_v3"].get("window_wall"), window_p99=res["measure_after"]["brightest area (window / door): L p50 / p99 / max"][1],
                                         black=res["measure_after"]["darkest 0.5% patch L [12-15]"], meets_bible=res["bible_v3"]["meets_bible"], checks=res["checks"],
                                         wall_v4=res["bible_v3"].get("wall_v4"), hue_correction=res["grade"].get("wall_hue_v4"),
                                         files=res["outputs"], measurements=OUT_DIR[jid] + jid + "-measurements" + gs + ".json")},
               boxes_overlay=OUT_DIR[jid] + jid + "-boxes" + gs + ".png", qa_wall=qa)
    if overscan:
        fx0, fy0, fx1, fy1 = VF.frame_box_px(W, H)
        job["overscan"].update(output_canvas_px=[W, H], output_frame_box_px=[fx0, fy0, fx1, fy1], output_frame_px=[fx1 - fx0, fy1 - fy0],
                               files=dict(canvas=OUT_DIR[jid] + jid + "-graded" + gs + ".png", frame=OUT_DIR[jid] + jid + "-frame" + gs + ".png",
                                          os6=OUT_DIR[jid] + jid + "-graded-os6" + gs + ".png"))
    _save_jr(J)
    print("lock_v2", json.dumps(job["lock_v2"]))
    print("grade_" + GRADE, json.dumps({k: v for k, v in job["grade_" + GRADE].items() if k not in ("checks", "files", "wall_v4", "hue_correction")}))
    return job


def sheet():
    from PIL import Image, ImageDraw, ImageFont
    w = 900
    th = int(w * 9 / 16)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
        font_h = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
    except Exception:
        font = font_h = ImageFont.load_default()
    J = _jr()
    m = "m0-v8b" if R5B else "m0-v8"
    job = next(j for j in J["jobs"] if j["id"] == m)
    lk, gr = job["lock_v2"], job["grade_" + GRADE]
    old_m0 = "m0-v7-r2-graded-v4.png" if R5B else "m0-v7-r2-graded-v3.png"
    ww = (gr.get("window_wall") or {}).get("L")
    tiles = [(os.path.join(REPO, "assets/renders/living-room/nordic/v7", old_m0), f"OLD  M0 r2 (house plan 1.1 camera, graded {GRADE}): history since V7Q1 b",
              "sofa 1.20x the clay, lock_v2 FAIL (edges 90 px)"),
             (os.path.join(REPO, OUT_DIR[m], f"{m}-frame-{GRADE}.png"), f"NEW  M0 1.2.1 (0.83, 4.64, 1.20), yaw 25, 24 mm, u0 0.47 v0 0.50{', 1.2.2 positions' if R5B else ''}: {m} graded {GRADE}",
              f"grade {GRADE}: corner wall L {gr['measured']} (target {gr['target']}), window wall {ww}, p99 {gr['window_p99']}, black {gr['black']}, meets Bible {gr['meets_bible']}"),
             (os.path.join(REPO, OUT_DIR[m], f"{m}-lock-v2.jpg"), f"LOCK  {m} vs the round-5{'b' if R5B else ''} clay: clay edges in red over the still (lock_v2, G1.4)",
              f"shift {lk['shift_px']} px, scale {lk['scale_pct']} %, resid band {lk['band_after']} / tile {lk['tile_after']} px (limit {lk['residual_limit']}), edges {lk['edges_worst_px']} px, ratios {lk['ratios']}: {'PASS' if lk['pass'] else 'FAIL'}")]
    pad, head, cap = 12, 70, 56
    im = Image.new("RGB", (3 * (w + pad) + pad, head + th + cap + 2 * pad), (246, 245, 242))
    d = ImageDraw.Draw(im)
    title = (f"M0 at the new camera (house plan 1.2.1, positions 1.2.2), {DATE}: old M0 r2 | new M0 (m0-v8b) | lock_v2. 2K test, grading v4 (test page only). Not QA'd."
             + (" DRY RUN ON THE CLAY." if DRY else "")) if R5B else \
        "M0 at the new camera (house plan 1.2.1, V7Q1 b), 2026-11-03: old M0 r2 | new M0 (m0-v8) | lock_v2. 2K test, grading v3 (Bible targets, test page only). Not QA'd."
    d.text((pad, 14), title, fill=(15, 15, 15), font=font_h)
    for k, (p, t1, t2) in enumerate(tiles):
        x = pad + k * (w + pad)
        t = Image.open(p).convert("RGB")
        t = t.resize((w, int(round(w * t.size[1] / t.size[0]))), Image.LANCZOS)
        im.paste(t.crop((0, 0, w, min(th, t.size[1]))), (x, head))
        d.text((x, head + th + 6), t1[:120], fill=(15, 15, 15), font=font)
        d.text((x, head + th + 30), t2[:150], fill=(80, 80, 80), font=font)
    outp = SHEET_OUT
    im.save(outp, quality=88)
    print("sheet", outp)
    return outp


def cutouts():
    """--r5b: M0p's and M0x's references cut from the new M0 (m0-v8b graded v4, 16:9 frame) by the frame uv boxes their prompts name;
    written to refs/m0-1-2-2-2026-11-04/ (dry: the scratchpad) and listed in the new index as not uploaded (put uploads them)."""
    from PIL import Image
    assert R5B, "cutouts: --r5b only"
    src = os.path.join(REPO, OUT_DIR["m0-v8b"], "m0-v8b-frame-v4.png")
    im = Image.open(src).convert("RGB")
    W, H = im.size
    d = os.path.join(os.path.dirname(IDX_NEW), "cutouts") if DRY else os.path.join(HERE, "refs", "m0-1-2-2-2026-11-04")
    os.makedirs(d, exist_ok=True)
    idx = json.load(open(IDX_NEW)) if os.path.exists(IDX_NEW) else {"note": "M0p / M0x references cut from m0-v8b graded v4 (m0_1_2_pipeline.py --r5b cutouts)", "refs": {}}
    for k, (u0, u1, v0, v1) in CUTS.items():
        c = im.crop((int(u0 * W), int(v0 * H), int(u1 * W), int(v1 * H)))
        p = os.path.join(d, k + ".jpg")
        c.save(p, quality=92)
        idx["refs"].setdefault(k, {}).update(local=os.path.relpath(p, REPO) if not DRY else p, source=os.path.relpath(src, REPO) if not DRY else src,
                                             frame_uv=[u0, u1, v0, v1], size_px=list(c.size), sha256=hashlib.sha256(open(p, "rb").read()).hexdigest(),
                                             var2_url=idx["refs"].get(k, {}).get("var2_url"), verified=idx["refs"].get(k, {}).get("verified", False))
        print("cut-out", k, c.size)
    json.dump(idx, open(IDX_NEW, "w"), indent=1, ensure_ascii=False)
    return idx


def dryrun():
    """--r5b --dry: the whole chain on the clay, no var2: prep m0-v8b (args with the clay marked not uploaded) -> fetch the round-5b M0
    clay itself as the 'result' (normalise, lock_v2 v3, grade v4, boxes) -> cutouts -> prep / fetch M0p and M0x on their clays (M0x
    inheriting M0's stops and correction) -> sheet. Every file goes to the scratchpad."""
    assert DRY, "dryrun needs --r5b --dry"
    rep = {}
    for jid in ("m0-v8b", "pose-m0p-v8b", "pose-m0x-v8b"):
        out = prep(jid)
        assert len(out["args"]["image_refs"]) == out["refs"] and out["args"]["model"] == "gpt-image-2-5" and out["prompt_chars"] <= 4000
        job = fetch(jid, os.path.join(R5, JOBS[jid][2]))
        rep[jid] = dict(prompt_chars=out["prompt_chars"], refs=out["refs"], lock_v2=job["lock_v2"],
                        grade_v4={k: v for k, v in job["grade_v4"].items() if k not in ("checks", "files")}, boxes=job["boxes_overlay"])
        if jid == "m0-v8b":
            cutouts()
    rep["sheet"] = sheet()
    json.dump(rep, open(os.path.join(DRYD, "dryrun-report.json"), "w"), indent=1, ensure_ascii=False)
    print("DRY RUN OK:", os.path.join(DRYD, "dryrun-report.json"))
    return rep


if __name__ == "__main__":
    av = [x for x in sys.argv[1:] if x not in ("--r5b", "--dry", "--clay")]
    cmd = av[0]
    if cmd == "put":
        put(av[1], av[2], av[3], av[4], clay="--clay" in sys.argv)
    elif cmd == "prep":
        att = int(av[2]) if len(av) > 2 else 1
        prep(av[1], att, av[3] if len(av) > 3 else None)
    elif cmd == "fetch":
        fetch(av[1], av[2])
    elif cmd == "sheet":
        sheet()
    elif cmd == "cutouts":
        cutouts()
    elif cmd == "dryrun":
        dryrun()
    elif cmd == "winbox":
        print("M0 1.2 window box, canvas uv:", M0_WIN_12)


# ---------------------------------------------------------------------------------------------------------------
# QA 2026-11-03 (qa/reports/2026-11-03-retakes-g1.md §4, §11.2), applied after grading v3 of m0-v8 / pose-m0p-v8 / pose-m0x-v8:
#   wall hue H (HSL) 32-40 and C* (CIELAB) <= 7 on the wall patch as absolute values, the window wall L 80-88 where the frame has one;
#   when H > 40 a hue-selective correction on the near-white walls: pixels with L* 82-97.5 and C* < 16 whose hue is yellower than the
#   target are turned back to the target hue (the hue of HSL H 36, S 20, L 93) and their chroma capped at 6.5, with soft weights, so
#   the oatmeal sofa (h ~80), the oak (C* > 20), the lamp glows (C* > 12) and the window glass (L* > 96, faded out) keep their colour.
# ---------------------------------------------------------------------------------------------------------------
def _lab(sr):
    import numpy as np
    lin = np.where(sr <= 0.04045, sr / 12.92, ((sr + 0.055) / 1.055) ** 2.4)
    M = np.array([[0.4124564, 0.3575761, 0.1804375], [0.2126729, 0.7151522, 0.0721750], [0.0193339, 0.1191920, 0.9503041]])
    xyz = lin @ M.T / np.array([0.95047, 1.0, 1.08883])
    fx = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * fx[..., 1] - 16, 500 * (fx[..., 0] - fx[..., 1]), 200 * (fx[..., 1] - fx[..., 2])], -1)


def _srgb_from_lab(lab):
    import numpy as np
    fy = (lab[..., 0] + 16) / 116
    fx, fz = fy + lab[..., 1] / 500, fy - lab[..., 2] / 200
    inv = lambda t: np.where(t ** 3 > 0.008856, t ** 3, (t - 16 / 116) / 7.787)  # noqa: E731
    xyz = np.stack([inv(fx) * 0.95047, inv(fy), inv(fz) * 1.08883], -1)
    Mi = np.array([[3.2404542, -1.5371385, -0.4985314], [-0.9692660, 1.8760108, 0.0415560], [0.0556434, -0.2040259, 1.0572252]])
    lin = np.clip(xyz @ Mi.T, 0, 1)
    return np.where(lin <= 0.0031308, lin * 12.92, 1.055 * np.power(lin, 1 / 2.4) - 0.055)


def _hsl_patch(a, u, v, w=0.012):
    import colorsys
    H, W = a.shape[:2]
    p = a[max(0, int((v - w * 16 / 9) * H)):int((v + w * 16 / 9) * H), max(0, int((u - w) * W)):int((u + w) * W)].reshape(-1, 3).mean(0)
    h, l, s = colorsys.rgb_to_hls(*p)
    lab = _lab(p[None, :])[0]
    return dict(H=round(h * 360, 1), S=round(s * 100, 1), L=round(l * 100, 1), C=round(float((lab[1] ** 2 + lab[2] ** 2) ** 0.5), 1),
                h_ab=round(float(__import__("math").degrees(__import__("math").atan2(lab[2], lab[1]))), 1))


def qa_wall(graded_png, wall_uv, window_wall_uv=None, out_png=None, fix=True):
    """QA's wall checks on a graded still (+ the hue correction when H > 40); returns the record."""
    import colorsys
    import math
    import numpy as np
    from PIL import Image
    a = np.asarray(Image.open(graded_png).convert("RGB"), float) / 255.0
    rec = dict(rule="QA 2026-11-03 §4: wall H 32-40, C* <= 7 (absolute), window wall L 80-88", wall_uv=list(wall_uv), before=_hsl_patch(a, *wall_uv))
    if window_wall_uv:
        rec["window_wall_uv"] = list(window_wall_uv)
        rec["window_wall_before"] = _hsl_patch(a, *window_wall_uv)
    need = rec["before"]["H"] > 40 or rec["before"]["C"] > 7
    rec["correction_needed"] = bool(need)
    if need and fix:
        ht = colorsys.hls_to_rgb(36 / 360, 0.93, 0.20)
        lt = _lab(np.array(ht)[None, :])[0]
        h_t = math.atan2(lt[2], lt[1])
        lab = _lab(a)
        C = np.hypot(lab[..., 1], lab[..., 2])
        h = np.arctan2(lab[..., 2], lab[..., 1])
        ss = lambda x, e0, e1: np.clip((x - e0) / (e1 - e0), 0, 1) ** 2 * (3 - 2 * np.clip((x - e0) / (e1 - e0), 0, 1))  # noqa: E731
        w = ss(lab[..., 0], 80, 84) * (1 - ss(lab[..., 0], 97.3, 98.5)) * (1 - ss(C, 14, 18))   # walls L* 84-97 (HSL 93 ~ L* 96); glass L* > 98; lamp glows C* > 18
        dh = np.angle(np.exp(1j * (h - h_t)))
        w = w * ss(dh, 0.0, math.radians(6))                      # only hues yellower than the target
        h_new = h - dh * w
        C_new = C - (C - np.minimum(C, 6.5)) * w
        out = lab.copy()
        out[..., 1], out[..., 2] = C_new * np.cos(h_new), C_new * np.sin(h_new)
        b = _srgb_from_lab(out)
        b = np.where(w[..., None] > 0, b, a)
        rec["after"] = _hsl_patch(b, *wall_uv)
        if window_wall_uv:
            rec["window_wall_after"] = _hsl_patch(b, *window_wall_uv)
        rec["pixels_touched_pct"] = round(float((w > 0.05).mean() * 100), 1)
        rec["target"] = dict(hsl=[36, 20, 93], h_ab=round(math.degrees(h_t), 1), C_cap=6.5)
        if out_png:
            Image.fromarray((np.clip(b, 0, 1) * 255 + 0.5).astype(np.uint8)).save(out_png)
            rec["output"] = out_png
    rec["pass"] = dict(H_32_40=bool(32 <= rec.get("after", rec["before"])["H"] <= 40), C_le_7=bool(rec.get("after", rec["before"])["C"] <= 7),
                       window_wall_80_88=(None if not window_wall_uv else bool(80 <= rec.get("window_wall_after", rec["window_wall_before"])["L"] <= 88)))
    return rec


if __name__ == "__main__" and sys.argv[1] == "qa-wall":   # (2026-11-03 v3 only)
    print(json.dumps(qa_wall(sys.argv[2], (float(sys.argv[3]), float(sys.argv[4])), (float(sys.argv[5]), float(sys.argv[6])) if len(sys.argv) > 6 else None,
                             sys.argv[7] if len(sys.argv) > 7 else None), indent=1))
