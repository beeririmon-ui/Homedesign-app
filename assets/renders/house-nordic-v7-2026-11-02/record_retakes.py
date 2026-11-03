#!/usr/bin/env python3
"""
Prompt records and manifest entries for the v8 retakes of 2026-11-03 (render-agent, 0 tokens), in the shape of
assets/prompts/recipe-v5.nordic/record-template.json (as record_v7.py): one record per finished job,
  masters -> assets/prompts/recipe-v5.nordic/<id>.json, poses -> assets/prompts/poses-v7.nordic/<id>.json,
and assets/manifest.json entries for the normalised raw, the graded-v3 still, the 16:9 frame / os6 crops (overscan), the lock
overlay, the box overlay, the two r3 clays and the contact sheet. Idempotent: existing manifest ids are kept.
  python3 record_retakes.py [--dry]
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
DRY = "--dry" in sys.argv
JR = json.load(open(os.path.join(HERE, "jobs-retakes-2026-11-03.json")))
tpl = json.load(open(os.path.join(REPO, "assets", "prompts", "recipe-v5.nordic", "record-template.json")))
man_path = os.path.join(REPO, "assets", "manifest.json")
man = json.load(open(man_path))
have = {a["id"] for a in man["assets"]}
DATE = "2026-11-03"


def add(aid, path, room, kind, frame, status, extra=None):
    if aid in have or not os.path.exists(os.path.join(REPO, path)):
        return
    man["assets"].append({"id": aid, "path": path, "room": room, "style": "nordic", "kind": kind, "frame": frame, "recipe": "B v8 (retake)", "model": "gpt-image-2-5",
                          "status": status, "created": DATE, **(extra or {})})
    have.add(aid)


for j in JR["jobs"]:
    if j.get("status") != "done":
        continue
    od = j["out_dir"]
    jid = j["id"]
    meas = json.load(open(os.path.join(REPO, od, jid + "-measurements-v3.json")))
    lock = json.load(open(os.path.join(REPO, od, jid + "-lock-v2.json")))
    prep = json.load(open(os.path.join(HERE, f"job-{jid}.json")))
    a = prep["args"]
    pose = j["kind"] == "pose"
    rec = dict(tpl)
    rec.update({
        "asset_id": jid, "room": j["room"], "style": "nordic", "frame": j["frame"],
        "recipe": "B (gpt-image-2-5 sunburst), recipe v8 retake (docs/render-recipe-nordic-v8-2026-11-03.md: cut-outs with sizes and u/v, SCALE paragraph, lock_v2 acceptance, grading v3)" + (" - transition pose, route R" if pose else ""),
        "stage": "Nordic walk-through test, v8 retakes after the decisions meeting of 2026-11-03 (briefs/render-v7-retakes-2026-11-03.md); 2K, not a site asset",
        "date": DATE, "tool": "var2 MCP var2_create_image", "model": a["model"], "type": a["type"], "resolution": a["resolution"], "quality": a["quality"], "aspect_ratio": a["aspect_ratio"],
        "returned_size_px": j.get("returned_size_px"), "seed": None, "seed_note": "model exposes no seed; a regenerate is a new sample",
        "input_image": {"local": j["clay"], "sha256": prep["clay_sha256"], "var2_url": a["image_url"], "upload": "var2_request_upload + PUT (curl); downloaded back, sha256 identical"},
        "image_refs": [{"n": i + 1, "var2_url": u} for i, u in enumerate(a["image_refs"])], "image_refs_source": "assets/renders/house-nordic-v7-2026-11-02/refs/index-retakes-2026-11-03.json (cut-outs, product images) + refs/index-v7.json and poses.json (product close-ups); " + j["refs_note"],
        "negative_prompt": None, "negative_note": "no negative field; the prohibitions are the last paragraph of the prompt",
        "prompt": a["prompt"], "prompt_source": j["prompt_file"], "prompt_chars": len(a["prompt"]), "prompt_deviation": prep.get("prompt_deviation"),
        "idempotency_key": a["idempotency_key"],
        "var2": {"placeholder_id": j.get("placeholder_id"), "task_id": j.get("task_id"), "result_url": j.get("result_url"), "share_url": j.get("share_url")},
        "credits_estimated": j.get("credits_estimated"), "credits": j.get("credits"), "attempt": j["attempt"], "attempt_note": j.get("attempt_note", "first and only attempt (one attempt per prompt, recipe v8 2.3)"),
        "normalised_16_9": f"non-uniform resize {j.get('returned_size_px')} -> {j.get('normalised_px')}, no crop", "overscan": j.get("overscan"),
        "lock_v2": {"method": lock["method"], "summary": lock["summary"], "verdict": lock["verdict"], "record": od + jid + "-lock-v2.json", "overlay": od + jid + "-lock-v2.jpg",
                    "note": "acceptance check of recipe v8 2.4 at the G1.4 thresholds (every retake counted as a pan participant per the brief)"},
        "product_check": {"rule": meas["product_box_rule"], "overlay": od + jid + "-boxes-v3.png", "boxes_clay": meas["product_boxes_clay"]},
        "grade": {"applied": True, "script": "assets/renders/house-nordic-v7-2026-11-02/process_v8.py --exposure bible", "params": meas["grade"], "bible_v3": meas["bible_v3"],
                  "output": od + jid + "-graded-v3.png",
                  "rule": "grading v3 (V7Q4 yes, BIB1 all six, test page only): WB on the wall point, exposure to the Bible target of the reference wall, chroma -10 %, S curve 0.12, black point 12-15 both ways, B4 near-white chroma guard, roll-off last (ceiling L 97), no grain, no vignette"},
        "measurements": od + jid + "-measurements-v3.json", "self_check_verdict": j.get("verdict", ""), "output": od + jid + ".png", "output_raw": od + "raw/" + jid + "." + j.get("raw_ext", "png"),
        "on_sheet": True, "sheet": "assets/renders/house-nordic-retakes-sheet-2026-11-03.jpg"})
    rdir = os.path.join(REPO, "assets", "prompts", "poses-v7.nordic" if pose else "recipe-v5.nordic")
    if not DRY:
        json.dump(rec, open(os.path.join(rdir, jid + ".json"), "w"), indent=1, ensure_ascii=False)
    status = ("v8 retake still (2026-11-03), self-checked by the render-agent (lock_v2 " + ("PASS" if lock["verdict"]["pass"] else "FAIL, see the record") +
              "), awaiting qa-agent / master-designer / user; not for site")
    room, frame = j["room"], j["frame"]
    ex = {"attempt": j["attempt"], "clay": j["clay"], "prompt_record": os.path.relpath(os.path.join(rdir, jid + ".json"), REPO)}
    pref = "v8-pose-" if pose else "v8-"
    add(pref + jid, od + jid + ".png", room, ("v8-pose-" if pose else "v8-frame-") + "raw-normalised", frame, status, ex)
    add(pref + jid + "-graded-v3", od + jid + "-graded-v3.png", room, ("v8-pose-" if pose else "v8-frame-") + "graded-v3", frame, status, ex)
    if (j.get("overscan") or {}).get("on"):
        add(pref + jid + "-frame-v3", od + jid + "-frame-v3.png", room, ("v8-pose-" if pose else "v8-frame-") + "graded-v3 16:9 frame (centre crop of the overscan canvas)", frame, status, ex)
        add(pref + jid + "-os6-v3", od + jid + "-graded-os6-v3.png", room, ("v8-pose-" if pose else "v8-frame-") + "graded-v3, frame width + 3% height top and bottom (motion-agent)", frame, status, ex)
    add(pref + jid + "-lock-v2", od + jid + "-lock-v2.jpg", room, "v8-lock-v2-overlay", frame, status, ex)
    add(pref + jid + "-boxes-v3", od + jid + "-boxes-v3.png", room, "v8-product-boxes-overlay", frame, status, ex)
    print("record", jid, "| prompt", rec["prompt_chars"], "| refs", len(a["image_refs"]), "| lock", "PASS" if lock["verdict"]["pass"] else "FAIL")
for fid, nm in (("B1", "b1"), ("B2", "b2")):
    add(f"clay-r4-r3-{nm}", f"assets/blockout/house/framing/round4/r3-2026-11-03/{fid}.png", "bath", "clay-round4-r3 (bath placeholders of V7Q3)", fid,
        "clay for the r3 retakes (framing_r4_bath_r3.py + tone_r4_fixed.py, 0 tokens); the round-4 post applied as recorded", {"source": "assets/blockout/house/framing_r4_bath_r3.py"})
add("v8-retakes-sheet-2026-11-03", "assets/renders/house-nordic-retakes-sheet-2026-11-03.jpg", "house", "contact-sheet", "all", "the four v8 retakes next to their v7 predecessors, graded v3, with the lock overlays")
if not DRY:
    json.dump(man, open(man_path, "w"), indent=1, ensure_ascii=False)
print("manifest assets:", len(man["assets"]))
