"""add the FB16 files to assets/manifest.json (append only; an id already there is replaced)"""
import sys, os, json, hashlib, glob
REPO = "/home/user/homedesign-app"; R = REPO + "/assets/renders"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, R + "/tools/finish"); import finish as F  # noqa
from rooms16 import ROOMS16
ST = "FB16 house light pass, in code over the fb15 stack: not QA'd, HD_PUBLIC=0 only"
def ent(id_, path, kind, room, tokens=0, model="code (L0 light pass)", prompts=None):
    p = os.path.join(REPO, path)
    return dict(id=id_, path=path, kind=kind, room=room, style="warm-modern", created="2026-11-26", model=model,
                recipe="assets/renders/tools/fb16/ (run16.py)", tokens=tokens, status=ST, prompts=prompts,
                sha256=hashlib.sha256(open(p, "rb").read()).hexdigest(), bytes=os.path.getsize(p))
E = []
for k in ("west", "north"):
    E.append(ent(f"wm-fb16-outside-{k}", f"assets/renders/outside/warm-modern/fb16-2026-11-26/outside-{k}-fb16.jpg", f"outside plate ({k}), no products", "outside",
                 400, "var2 nano-banana-2 2K text-to-image", f"assets/prompts/wm-fb16-2026-11-26/outside-{k}-fb16.json"))
for key, cfg in ROOMS16.items():
    fc = F.ROOMS[key]; cp = os.path.join(R, fc["out_dir"], fc["out_name"] + "-fb16-checks.json")
    if not os.path.exists(cp):
        continue
    c = json.load(open(cp)); room = fc["room"]; tag = key.lower()
    for f in c["files"] + [os.path.relpath(cp, REPO)]:
        b = os.path.basename(f)
        if b.endswith("-fb16-finish.png"): kind = f"{key} frame, canvas, L0 over the finished fb15 stack"
        elif b.endswith("-fb16-frame.png"): kind = f"{key} frame 1920x1080"
        elif b.endswith("-fb16-checks.json"): kind = f"{key} checks (RND2, black point, targets, pasted test)"
        elif b.startswith("window-glow"): kind = f"{key} window glow (screen over the whole graded composite)"
        elif b.endswith(".json"): kind = f"{key} manifest fb16 (base, grade, glows)"
        elif "plate" in b or b in ("ht2-fb16.png", "hdx2-fb16.png"): kind = f"{key} base with the new outside" + (" and the living room re-fed from M0-W" if key == "HDx2" else "")
        else: kind = f"{key} lamp glow (screen): " + b.replace("-fb16.png", "")
        E.append(ent(f"wm-fb16-{tag}-{b.replace('.png', '').replace('.json', '')}", f, kind, room))
E.append(ent("wm-fb16-house-light-sheet", "assets/renders/house-light-fb16.jpg", "house sheet: every frame at x1, M0-W and its hero", "house"))
m = json.load(open(REPO + "/assets/manifest.json"))
ids = {e["id"] for e in E}
m["assets"] = [a for a in m["assets"] if a.get("id") not in ids] + E
json.dump(m, open(REPO + "/assets/manifest.json", "w"), ensure_ascii=False, indent=1)
print(len(E), "entries")
