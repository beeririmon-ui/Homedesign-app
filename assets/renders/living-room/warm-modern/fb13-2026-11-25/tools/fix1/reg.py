"""reg.py: register a nano return onto its input crop (prep.py's SIFT affine + tone fit), save the registered crop and the diff"""
import json, os, sys
import cv2, numpy as np
from PIL import Image
import types
_src = open("/home/user/homedesign-app/assets/renders/living-room/warm-modern/fb13-2026-11-25/tools/prep.py").read().split("\n")
P = types.SimpleNamespace()
_ns = dict(np=np, cv2=cv2)
exec("\n".join(_src[30:67]), _ns)   # prep.py's sift_affine and tone_fit, unchanged
P.sift_affine, P.tone_fit = _ns["sift_affine"], _ns["tone_fit"]
S = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/fix1/"
rd = lambda p: np.asarray(Image.open(p).convert("RGB")).astype(np.float32) / 255.0
def reg(name, ret):
    inp = rd(S + f"send/{name}-crop.png")
    ch, cw = inp.shape[:2]
    res = rd(S + f"ret/{ret}")
    inp2 = cv2.resize(inp, (cw * 2, ch * 2), interpolation=cv2.INTER_LANCZOS4)
    A, rec = P.sift_affine(res, inp2)
    w2 = cv2.warpAffine(res, A, (cw * 2, ch * 2), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REPLICATE)
    w1 = cv2.resize(w2, (cw, ch), interpolation=cv2.INTER_AREA)
    d = np.abs(cv2.GaussianBlur(w1, (0, 0), 2.0) - cv2.GaussianBlur(inp, (0, 0), 2.0)).max(2)
    w1, tone = P.tone_fit(w1, inp, d < 0.05)
    d = np.abs(cv2.GaussianBlur(w1, (0, 0), 2.0) - cv2.GaussianBlur(inp, (0, 0), 2.0)).max(2)
    rec.update(tone_gain_offset=tone, unchanged_share=round(float((d < 0.04).mean()), 3), returned_px=list(res.shape[1::-1]),
               mean_abs_diff_unchanged=round(float(np.abs(w1 - inp)[d < 0.04].mean() * 255), 2))
    np.save(S + f"ret/{name}-reg.npy", w1.astype(np.float16))
    np.save(S + f"ret/{name}-d.npy", d.astype(np.float16))
    return w1, d, rec
if __name__ == "__main__":
    out = {}
    for name, ret in [("e1-olive", "e1-olive-nano.jpg"), ("e2-curtain", "e2-curtain-nano.jpg"), ("e3-holder", "e3-holder-nano.jpg")]:
        w1, d, rec = reg(name, ret)
        out[name] = rec
        print(name, json.dumps({k: v for k, v in rec.items() if k != "A"}))
        Image.fromarray((np.clip(d * 4, 0, 1) * 255).astype(np.uint8)).resize((w1.shape[1] // 2, w1.shape[0] // 2)).save(S + f"v-{name}-d.png")
    json.dump(out, open(S + "ret/reg.json", "w"), indent=1)
