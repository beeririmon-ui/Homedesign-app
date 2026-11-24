#!/usr/bin/env python3
"""
ledger.py: the var2 ledger of the kids' stage one (render-agent, 2026-11-24). One jobs.json per room, written right after every send
(the brief: "write jobs.json after every send, so a restart can't lose the ledger"), and updated with the verdict when the result is in.
  python3 ledger.py add <kid> '<json entry>'          # right after a send (placeholder_id, model, tokens, input, refs, prompt, key)
  python3 ledger.py set <kid> <id> '<json fields>'    # the result: url, raw, verdict
  python3 ledger.py sum                               # the money so far, both rooms
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kids_common import ST  # noqa: E402

CAP = dict(plan="about 5,050-9,700 for both rooms (א.6 + ב.6)", stop_above=9700)


def path(kid):
    return os.path.join(ST[kid], "jobs.json")


def load(kid):
    p = path(kid)
    if os.path.exists(p):
        return json.load(open(p))
    return dict(run=f"render-agent, 2026-11-24: K-{kid}, the warm-modern {kid}'s room, stage one (briefs/wm-kids-stage1-render-2026-11-24.md; "
                    "docs/proposals/wm-kids-rooms-render-2026-11-19.md, ch. ד over א-ג)",
                cap=CAP, estimate_before_every_send=True, var2="every send priced with var2_estimate_cost first; no code or token asked for",
                sent=[], spent=0)


def save(kid, J):
    J["spent"] = sum(int(e.get("tokens") or 0) for e in J["sent"] if e.get("charged", True))
    J["updated"] = time.strftime("%Y-%m-%d %H:%M")
    tmp = path(kid) + ".tmp"
    json.dump(J, open(tmp, "w"), indent=1, ensure_ascii=False)
    os.replace(tmp, path(kid))
    return J["spent"]


def main(a):
    if a[0] == "add":
        J = load(a[1])
        e = json.loads(a[2])
        e.setdefault("sent_at", time.strftime("%Y-%m-%d %H:%M"))
        J["sent"] = [x for x in J["sent"] if x["id"] != e["id"]] + [e]
        print(a[1], "spent", save(a[1], J))
    elif a[0] == "set":
        J = load(a[1])
        for e in J["sent"]:
            if e["id"] == a[2]:
                e.update(json.loads(a[3]))
        print(a[1], "spent", save(a[1], J))
    elif a[0] == "sum":
        tot = 0
        for k in ("boy", "girl"):
            s = load(k)["spent"] if os.path.exists(path(k)) else 0
            print(k, s)
            tot += s
        print("both", tot, "cap", CAP["stop_above"])


if __name__ == "__main__":
    main(sys.argv[1:])
