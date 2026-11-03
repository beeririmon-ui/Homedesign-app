#!/usr/bin/env python3
"""
Prepare one v8 retake job (render-agent, 2026-11-03; 0 tokens): the prompt body of the *-v8.txt file (# header stripped, no
coordinate conversion: the v8 prompts carry canvas fractions already), the references in the header's order as var2 URLs (the
cut-outs and product images of refs/index-retakes-2026-11-03.json; the product close-ups of refs/index-v7.json and poses.json),
the clay URL (round-4 uploads in jobs.json for the poses; the r3 clays in jobs-retakes-2026-11-03.json), and the exact
var2_create_image arguments -> job-<id>.json, plus the job row in jobs-retakes-2026-11-03.json (status "prepared").
  python3 prep_retakes_job.py <pose-w0-in-v7-r2 | pose-k-girl-0-v7-r2 | b1-v7-r3 | b2-v7-r3>
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, HERE)
import v7_frames as VF  # noqa: E402

J7 = json.load(open(os.path.join(HERE, "jobs.json")))
IDX7 = json.load(open(os.path.join(HERE, "refs", "index-v7.json")))
POSES = json.load(open(os.path.join(HERE, "poses.json")))
IDXR = json.load(open(os.path.join(HERE, "refs", "index-retakes-2026-11-03.json")))["refs"]
JR_PATH = os.path.join(HERE, "jobs-retakes-2026-11-03.json")
JR = json.load(open(JR_PATH)) if os.path.exists(JR_PATH) else {"clay": {}, "jobs": []}


def r(key):
    u = IDXR[key].get("var2_url")
    assert u, f"reference {key} not uploaded"
    return u


SPEC = {
    "pose-w0-in-v7-r2": dict(prompt="assets/prompts/poses-v7.nordic/pose-w0-in-v7-r2-v8.txt", out_dir="assets/renders/poses/nordic/v7/", clay_key=("v7", "W0-in"),
                             refs=[r("w0in-1-desk-top"), r("w0in-2-shelf"), r("w0in-3-plant"), r("w0in-4-under-desk"), r("w0in-5-chair"), r("w0in-6-right-corner")] + POSES["W0-in"]["product_refs"],
                             refs_note="1-6 cut-outs of w0-v7-graded-fix-v3; 7-11 = W0-in.txt product refs (rope basket, kraft bin, seagrass belly, felt bins, pen cup) = w0-v7.txt refs 2-6"),
    "pose-k-girl-0-v7-r2": dict(prompt="assets/prompts/poses-v7.nordic/pose-k-girl-0-v7-r2-v8.txt", out_dir="assets/renders/poses/nordic/v7/", clay_key=("v7", "K-girl-0"),
                                refs=[r("kgirl0-1-desk-doll-band"), r("kgirl0-2-prints"), r("kgirl0-3-ledges"), r("kgirl0-4-bed-foot"), r("kgirl0-5-wall-band-line")] + POSES["K-girl-0"]["product_refs"],
                                refs_note="1-5 cut-outs of k-girl-v7-graded-fix-v3; 6-9 = K-girl-0.txt product refs (prints, ledges, muslin, bunny doll)"),
    "b1-v7-r3": dict(prompt="assets/prompts/recipe-v5.nordic/b1-v7-r3-v8.txt", out_dir="assets/renders/bath/nordic/v7/", clay_key=("r3", "B1-r3"),
                     refs=[r("b1r3-1-wc-ledge"), r("b1r3-2-shower-corner")] + [x["var2_url"] for x in IDX7["frames"]["B1"]] + [r("planter-seagrass-30"), r("toilet-brush-black")],
                     refs_note="1-2 cut-outs of b1-v7-graded-v3; 3-9 = b1-v7.txt refs 1-7; 10 planter card; 11 brush card"),
    "b2-v7-r3": dict(prompt="assets/prompts/recipe-v5.nordic/b2-v7-r3-v8.txt", out_dir="assets/renders/bath/nordic/v7/", clay_key=("r3", "B2-r3"),
                     refs=lambda: [r("b2r3-1-b1r3-shower-planter"), r("b2r3-2-b1r3-planter")] + [IDX7["frames"]["B2"][i]["var2_url"] for i in (1, 4, 5, 6, 7, 8, 9)] + [r("planter-seagrass-30")],
                     refs_note="attempt 2 (10 refs): 1-2 cut-outs of b1-v7-r3-graded-v3; 3-9 = b2-v7.txt refs 2, 5-10 (lamp, soap, cup, vase, rope basket, towel ring, hand towel); 10 planter card. Attempt 1 (13 refs: + b2-v7 vanity crop, curtain, pump bottle) timed out at the provider",
                     attempt=2, attempt_note="attempt 2 after the provider timeout of attempt 1 (13 refs, 600 not refunded at the time); 10 refs; the one reserve of the brief"),
}

SPEC["pose-k-girl-0-v7-r3"] = dict(SPEC["pose-k-girl-0-v7-r2"], attempt=2, attempt_note="second attempt (the brief's one reserve, 600): the r2 sample failed lock_v2 on scale "
                                   "(desk width ratio 0.936, right edge -34 px); same v8 prompt and references, new sample")
jid = sys.argv[1]
S = SPEC[jid]
frame, kind, clay_file, pan, overscan, room = VF.RETAKES[jid]
txt = open(os.path.join(REPO, S["prompt"]), encoding="utf-8").read()
body = [l for l in txt.split("\n") if not l.startswith("#")]
while body and body[0].strip() == "":
    body.pop(0)
while body and body[-1].strip() == "":
    body.pop()
prompt = "\n".join(body)
assert "PLANTER_BOX" not in prompt, "fill the planter box first"
assert len(prompt) <= 4000, f"prompt {len(prompt)} > 4000"
refs = S["refs"]() if callable(S["refs"]) else S["refs"]
assert all(refs) and len(refs) <= 15
if S["clay_key"][0] == "v7":
    clay = J7["clay"][S["clay_key"][1]]
else:
    clay = JR["clay"][S["clay_key"][1]]
key = f"v8-{jid}-20261103-a{S.get('attempt', 1)}"
args = dict(model="gpt-image-2-5", type="image-to-image", quality="sunburst", resolution="2K", aspect_ratio="16:9",
            image_url=clay["var2_url"], image_refs=refs, prompt=prompt, idempotency_key=key)
out = dict(id=jid, frame=frame, recipe="v8", prompt_deviation="lines starting with # stripped; positions already in canvas fractions (no conversion)",
           prompt_chars=len(prompt), ascii=prompt.isascii(), refs=len(refs), refs_note=S["refs_note"], clay=clay["local"], clay_sha256=clay["sha256"], args=args)
json.dump(out, open(os.path.join(HERE, f"job-{jid}.json"), "w"), indent=1, ensure_ascii=False)
row = dict(id=jid, frame=frame, kind=kind, room=room, recipe="v8 (docs/render-recipe-nordic-v8-2026-11-03.md; logged as v8 per the brief)", prompt_file=S["prompt"],
           out_dir=S["out_dir"], model="gpt-image-2-5", quality="sunburst", resolution="2K", aspect_ratio="16:9", idempotency_key=key, attempt=S.get("attempt", 1),
           attempt_note=S.get("attempt_note", "first and only attempt (one attempt per prompt, recipe v8 2.3)"), status="prepared",
           credits_estimated=None, credits=None, date="2026-11-03", pan_participant=pan,
           overscan=(dict(on=True, canvas_px=[4072, 2290], frame_px=[3840, 2160], crop_box_px=[116, 65, 3956, 2225], per_side_fraction_x=0.0302, per_side_fraction_y=0.0301) if overscan else dict(on=False)),
           clay=clay["local"], clay_var2_url=clay["var2_url"], refs=len(refs), refs_note=S["refs_note"], prompt_chars=len(prompt))
JR["stage"] = "v8 retakes after the decisions meeting of 2026-11-03 (briefs/render-v7-retakes-2026-11-03.md): W0-in r2, K-girl-0 r2, B1 r3, B2 r3"
JR["model"] = "gpt-image-2-5, quality sunburst, 2K, 16:9, image-to-image from the clay; recipe v8"
JR["cap_tokens"] = 3000
JR.setdefault("budget_note", "2,400 for the four jobs + 600 reserve (one second attempt at most, only on a lock_v2 scale / position failure)")
prev = next((j for j in JR.get("jobs", []) if j["id"] == jid), None)
if prev and prev.get("attempts"):
    row["attempts"] = prev["attempts"]
    row["attempt_note"] = prev.get("attempt_note", row["attempt_note"])
JR["jobs"] = [j for j in JR.get("jobs", []) if j["id"] != jid] + [row]
JR["spent_tokens"] = sum(j.get("credits") or 0 for j in JR["jobs"])
json.dump(JR, open(JR_PATH, "w"), indent=1, ensure_ascii=False)
print(json.dumps({k: v for k, v in out.items() if k != "args"}, ensure_ascii=False))
