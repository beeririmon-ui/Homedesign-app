"""stack.py: load a M0-W manifest's stack from the repo and compose it (finish.compose), frame view as finalize.py"""
import json, os, sys
import numpy as np
from PIL import Image
REPO = "/home/user/homedesign-app"
FB13 = os.path.join(REPO, "assets/renders/living-room/warm-modern/fb13-2026-11-25")
sys.path.insert(0, os.path.join(REPO, "assets/renders/tools/finish"))
import finish as F
rd = lambda p, m: np.asarray(Image.open(p).convert(m))
def load(man_rel="layers/manifest.json", skip=()):
    man = json.load(open(os.path.join(FB13, man_rel)))
    mdir = os.path.dirname(os.path.join(FB13, man_rel))
    base = rd(os.path.normpath(os.path.join(mdir, man["base"])), "RGB")
    lays = []
    for l in man["layers"]:          # manifest order = z order
        if l["slot"] in skip:
            continue
        lays.append((l["slot"], rd(os.path.join(FB13, l["layer"]), "RGBA"), rd(os.path.join(FB13, l["shadow"]), "RGB")))
    lights = [rd(os.path.join(FB13, lt["file"]), "RGB") for lt in man["light"]]
    return man, base, lays, lights
def compose(base, lays, lights):
    return F.compose(base, [(a, s) for _, a, s in lays], lights)
def frame(canvas, man):
    st = dict(key="M0-W", frame_box=man["frame_box"], entries=[], cfg={})
    return F.frame_view(canvas, st, (1920, 1080))
if __name__ == "__main__":
    man, base, lays, lights = load()
    print([ (k, l["z"]) for k, l in zip([x[0] for x in lays], man["layers"])])
    fr = frame(compose(base, lays, lights), man)
    old = rd(os.path.join(FB13, "default-frame-m0w.png"), "RGB")
    d = np.abs(fr.astype(int) - old.astype(int))
    print("reproduce max", d.max(), "px>0", int((d.max(2) > 0).sum()))
