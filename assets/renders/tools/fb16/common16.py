import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import os, sys, json
import numpy as np, cv2
from PIL import Image
sys.path.insert(0, "/home/user/homedesign-app/assets/renders/tools/finish")
import finish as F  # noqa
from rooms16 import ROOMS16, R, BLACK  # noqa

def lab(rgb8):
    return cv2.cvtColor(rgb8.astype(np.float32) / 255.0, cv2.COLOR_RGB2LAB)

def legend(cfg):
    if not cfg.get("legend"):
        return {}
    s = json.load(open(cfg["legend"]))
    return {int(k): v for k, v in (s.get("ids") or {}).items()}

def load(key):
    cfg = ROOMS16[key]
    F.ROOMS[key] = dict(F.ROOMS[key], manifest=cfg["manifest"])
    st = F.load_room(key)
    return cfg, st

def idmap(cfg):
    p = cfg["clay"] + "-id.png"
    if not os.path.exists(p):
        return None
    return np.asarray(Image.open(p))

def region_of(layers, lights, shape):
    reg = np.zeros(shape, bool)
    for L, S in layers:
        reg |= L[..., 3] > 0
        if S is not None:
            reg |= S.min(2) < 255
    for Lt in lights:
        reg |= Lt.max(2) > 0
    return reg

def plaster_mask(ids, leg, reg, erode=8, ids_override=None):
    pl = ids_override or [k for k, v in leg.items() if v.lower().startswith("plaster")]
    m = np.isin(ids, pl) & ~reg
    m = cv2.erode(m.astype(np.uint8), np.ones((2 * erode + 1, 2 * erode + 1), np.uint8)) > 0
    return m

def measure(img8, pm, fmask=None):
    Lb = lab(img8)
    v = Lb[pm]
    Lall = Lb[..., 0] if fmask is None else Lb[..., 0][fmask]
    return dict(plaster=[round(float(np.median(v[:, i])), 2) for i in range(3)], plaster_px=int(pm.sum()),
                black_p05=round(float(np.percentile(Lall, 0.5)), 2))
