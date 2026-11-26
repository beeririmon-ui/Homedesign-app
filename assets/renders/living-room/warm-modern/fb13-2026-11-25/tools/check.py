#!/usr/bin/env python3
"""check.py: the stack composed by the manifests' formula (finish.compose) against the hero; previews of states."""
import json, os, sys
import cv2, numpy as np
from PIL import Image
import hwlib as L
sys.path.insert(0, os.path.join(L.REPO, "assets/renders/tools/finish"))
import finish as F
from extract import ORDER, LAMPS
D = sys.argv[1] if len(sys.argv) > 1 else os.path.join(L.OUT, "stack")
names = [k for k, _ in ORDER]
rd = lambda p, m: np.asarray(Image.open(p).convert(m))
base = rd(os.path.join(D, "base.png"), "RGB")
lay = {k: (rd(os.path.join(D, f"layer-{k}.png"), "RGBA"), rd(os.path.join(D, f"shadow-{k}.png"), "RGB")) for k in names}
lights = {l: rd(os.path.join(D, f"light-{l}.png"), "RGB") for l in LAMPS}
hero = rd(os.path.join(L.OUT, "prep", "hero.png"), "RGB")
full = F.compose(base, [lay[k] for k in names], [lights[l] for l in LAMPS])
d = np.abs(full.astype(int) - hero.astype(int)).max(2)
fm = L.frame_mask()
rep = dict(max=int(d.max()), mean=round(float(d.mean()), 4), px_over_2=int((d > 2).sum()), px_over_8=int((d > 8).sum()), px_over_8_in_frame=int(((d > 8) & fm).sum()),
           p99_9=float(np.percentile(d, 99.9)))
print(json.dumps(rep))
json.dump(rep, open(os.path.join(D, "check-default.json"), "w"))
sm = lambda a, p: Image.fromarray(a).resize((1360, 765), Image.LANCZOS).save(p, quality=88)
sm(full, os.path.join(D, "v-full.jpg"))
sm(base, os.path.join(D, "v-base.jpg"))
sm(F.compose(base, [lay[k] for k in names], []), os.path.join(D, "v-lamps-off.jpg"))
sm(F.compose(base, [lay[k] for k in names if k not in ("coffee-table", "bowl", "candle-holders")], [lights[l] for l in LAMPS]), os.path.join(D, "v-no-table.jpg"))
sm(F.compose(base, [lay[k] for k in names if k not in ("cushions", "magazine-holder", "planter")], [lights[l] for l in LAMPS]), os.path.join(D, "v-no-cushions-holder-planter.jpg"))
dd = np.clip(d * 12, 0, 255).astype(np.uint8)
sm(np.dstack([dd] * 3), os.path.join(D, "v-diff-x12.jpg"))
