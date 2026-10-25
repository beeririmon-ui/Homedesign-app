#!/usr/bin/env python3
"""
Prompt records for the Phase B drafts, in the shape of assets/prompts/recipe-v5.nordic/record-template.json (as the recipe-v5
make_records.py): one assets/prompts/recipe-v5.nordic/<asset_id>.json per job in jobs.json, plus assets/manifest.json entries for the
raw-normalised and graded outputs. Idempotent: existing manifest ids are kept.
  python3 record.py [jobs.json]
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
jobs_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "jobs.json")
J = json.load(open(jobs_path))
tpl = json.load(open(os.path.join(REPO, "assets", "prompts", "recipe-v5.nordic", "record-template.json")))
man_path = os.path.join(REPO, "assets", "manifest.json")
man = json.load(open(man_path))
have = {a["id"] for a in man["assets"]}
refs_idx = json.load(open(os.path.join(HERE, "refs", "index.json"))) if os.path.exists(os.path.join(HERE, "refs", "index.json")) else {"refs": {}}
for j in J["jobs"]:
    if j.get("status") != "done":
        continue
    out_dir = f"assets/renders/{j['room']}/nordic/recipe-v5/"
    meas = json.load(open(os.path.join(REPO, out_dir, j["id"] + "-measurements.json")))
    txt = open(os.path.join(REPO, "assets", "prompts", "recipe-v5.nordic", j["prompt_file"]), encoding="utf-8").read()
    body = [l for l in txt.split("\n") if not l.startswith("#")]
    while body and body[0].strip() == "":
        body.pop(0)
    prompt = "\n".join(body)
    stripped = len(txt) - len(prompt)
    clay = J["clay"][j["frame"]]
    refs = []
    for pid in j.get("refs", []):
        r = refs_idx["refs"].get(pid, {})
        refs.append(dict(product=pid, file=r.get("file"), var2_url=r.get("var2_url"), source_url=r.get("source_url"), sha256=r.get("sha256"),
                         usage_rights=r.get("usage_rights")))
    rec = dict(tpl)
    rec.update({
        "asset_id": j["id"], "room": j["room"], "style": "nordic", "frame": j["frame"], "recipe": "B (+ the verdict's five changes)",
        "stage": "recipe-v5 Phase B draft 2K (gate 2: the owner approves the room sheet)", "date": j.get("date", "2026-10-25"),
        "tool": "var2 MCP var2_create_image", "model": j["model"], "type": "image-to-image", "resolution": "2K", "quality": j.get("quality"),
        "aspect_ratio": "16:9", "returned_size_px": meas["returned_size_px"], "seed": None,
        "seed_note": "model exposes no seed; a regenerate is a new sample",
        "input_image": {"local": clay["local"], "sha256": clay["sha256"], "var2_url": clay["var2_url"],
                        "upload": "var2_request_upload + PUT (curl); downloaded back, sha256 identical" if clay.get("verified") else "var2_request_upload + PUT (curl)"},
        "image_refs": refs, "negative_prompt": None, "negative_note": "no negative field; the prohibitions are the last paragraph of the prompt",
        "prompt": prompt, "prompt_source": f"assets/prompts/recipe-v5.nordic/{j['prompt_file']} (master-designer, 2026-10-25)",
        "prompt_chars": len(prompt),
        "prompt_deviation": f"lines starting with # stripped as the header instructs ({stripped} chars of header removed)" if stripped else "none: sent as the file text",
        "idempotency_key": j["idempotency_key"],
        "var2": {"placeholder_id": j.get("placeholder_id"), "task_id": j.get("task_id"), "result_url": j.get("result_url"),
                 "share_url": ("https://www.var2.ai/image/" + j["placeholder_id"]) if j.get("placeholder_id") else None},
        "credits_estimated": j.get("credits_estimated"), "credits": j.get("credits"), "attempt": j["attempt"],
        "attempt_note": j.get("attempt_note", "first and only attempt" if j["attempt"] == 1 else "retake: the first broke the clay lock / invented an object"),
        "normalised_16_9": meas["resize_16_9"],
        "clay_lock": {"method": meas["clay_lock_note"], "regions": meas["clay_lock"], "auto_worst_abs_shift": meas["clay_lock_worst_abs_shift"],
                      "auto_worst_abs_shift_strong_peaks": meas["clay_lock_worst_abs_shift_strong_peaks"], "verdict": j.get("lock")},
        "product_check": {"rule": meas["product_box_rule"], "overlay": out_dir + j["id"] + "-boxes.png", "reading": j.get("products", "")},
        "grade": {"applied": True, "script": "assets/renders/house-nordic-2026-10-25/process_r5.py", "params": meas["grade"],
                  "output": out_dir + j["id"] + "-graded.png",
                  "rule": "docs/render-recipe-nordic-2026-10-24.md 2.6: WB on the hero-wall patch, exposure capped +-0.2 stop, chroma -10%, "
                          "roll-off from L 94, S curve 0.12, black point to L 12.5 only if below 12, no grain, no vignette"},
        "measurements": out_dir + j["id"] + "-measurements.json", "self_check_verdict": j.get("verdict", ""),
        "output": out_dir + j["id"] + ".png", "output_raw": out_dir + "raw/" + j["id"] + "." + j["raw_ext"]})
    json.dump(rec, open(os.path.join(REPO, "assets", "prompts", "recipe-v5.nordic", j["id"] + ".json"), "w"), indent=1, ensure_ascii=False)
    for suffix, path, kind in [("", out_dir + j["id"] + ".png", "recipe-v5-phaseB-draft"), ("-graded", out_dir + j["id"] + "-graded.png", "recipe-v5-phaseB-draft-graded")]:
        aid = "recipe-v5-" + j["id"] + suffix
        if aid in have:
            continue
        man["assets"].append({"id": aid, "path": path, "room": j["room"], "style": "nordic", "kind": kind, "frame": j["frame"], "recipe": "B",
                              "model": j["model"], "status": "Phase B draft for gate 2 (room sheet); self-checked, awaiting qa-agent / master-designer / user (not for site)",
                              "prompt_record": f"assets/prompts/recipe-v5.nordic/{j['id']}.json", "created": j.get("date", "2026-10-25")})
        have.add(aid)
    print("record", j["id"])
json.dump(man, open(man_path, "w"), indent=1, ensure_ascii=False)
print("manifest assets:", len(man["assets"]))
