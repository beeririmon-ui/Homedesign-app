#!/usr/bin/env python3
"""
git_check.py: qa-agent, 2026-11-10. Read-only. The approved v3c files and their sources against git:
working tree vs the commit of 2026-11-07 that last wrote them, vs HEAD, commits since 2026-11-08 touching them,
and base.png vs shell-furniture-v3-graded-v3c.png byte for byte.
Usage: python3 git_check.py <out_json>
"""
import filecmp
import hashlib
import json
import subprocess
import sys

REPO = "/home/user/homedesign-app"
P = "assets/renders/living-room/warm-modern/pilot-phase1-2026-11-07"
FILES = ["shell-furniture-v3-graded-v3c.png", "composite-set-A-v3-graded-v3c.png", "composite-set-B-v3-graded-v3c.png",
         "composite-set-C-v3-graded-v3c.png", "shell-v3-graded-v3c.png", "layers/cushions/set-A.png", "layers/cushions/set-B.png",
         "layers/cushions/set-C.png", "shadows/cushions/set-A.png", "shadows/cushions/set-B.png", "shadows/cushions/set-C.png",
         "cushion-polys.json"]


def git(*a):
    return subprocess.run(["git", "-C", REPO, *a], capture_output=True, text=True).stdout.strip()


out = {"files": {}}
for f in FILES:
    path = f"{P}/{f}"
    last = git("log", "-1", "--format=%h %ad", "--date=iso", "--", path)
    commit = last.split()[0]
    wt = git("hash-object", path)
    out["files"][f] = dict(last_commit=last, worktree_blob=wt, blob_at_last_commit=git("rev-parse", f"{commit}:{path}"),
                           blob_at_head=git("rev-parse", f"HEAD:{path}"),
                           sha256=hashlib.sha256(open(f"{REPO}/{path}", "rb").read()).hexdigest(),
                           worktree_status=git("status", "--porcelain", "--", path) or "clean")
    out["files"][f]["unchanged"] = (wt == out["files"][f]["blob_at_last_commit"] == out["files"][f]["blob_at_head"]
                                    and out["files"][f]["worktree_status"] == "clean" and last.split()[1] < "2026-11-10")
out["commits_since_2026_11_08_touching_them"] = git("log", "--since=2026-11-08", "--format=%h %s", "--", *[f"{P}/{f}" for f in FILES]) or []
out["base_png_byte_identical_to_shell_furniture_v3_graded_v3c"] = filecmp.cmp(f"{REPO}/{P}/layers-v3c/base.png",
                                                                             f"{REPO}/{P}/shell-furniture-v3-graded-v3c.png", shallow=False)
out["all_unchanged"] = all(v["unchanged"] for v in out["files"].values()) and not out["commits_since_2026_11_08_touching_them"]
json.dump(out, open(sys.argv[1], "w"), indent=1)
print(json.dumps({k: v["unchanged"] for k, v in out["files"].items()}), out["base_png_byte_identical_to_shell_furniture_v3_graded_v3c"], out["all_unchanged"])
