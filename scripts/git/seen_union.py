import json, subprocess, sys
def show(stage):
    return json.loads(subprocess.check_output(["git", "show", f":{stage}:data/sources/seen.json"]))
b, o, t = show(1), show(2), show(3)
out = json.loads(json.dumps(o))
for sec in ("items", "aliases", "cards"):
    B, O, T = b.get(sec) or {}, o.get(sec) or {}, t.get(sec) or {}
    out.setdefault(sec, {})
    for k, v in T.items():
        if B.get(k) == v:
            continue
        if O.get(k) == B.get(k):
            out[sec][k] = v
        elif isinstance(v, dict) and isinstance(O.get(k), dict):
            m = dict(O[k])
            for kk, vv in v.items():
                m.setdefault(kk, vv)
            if str(v.get("last_seen", "")) > str(m.get("last_seen", "")):
                m["last_seen"] = v["last_seen"]
            out[sec][k] = m
out["updated"] = max(str(o.get("updated")), str(t.get("updated")))
open("data/sources/seen.json", "w").write(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
