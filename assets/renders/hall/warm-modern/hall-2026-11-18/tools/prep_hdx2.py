#!/usr/bin/env python3
"""
prep_hdx2.py: the model input and the masks of HDx2 (route 12.2: hdx.png + the walnut console), render-agent 2026-11-18. 0 tokens.
As prep_ht2.py, for the console (id 101 of wm-hall-2026-11-18/HDx):
  the mask  = the clay's console and its soft shadow on the plaster (the clay with / without it, under 0.95 against its own median
              400-800 px away, fading out 0.20 m from the console's box and 8 cm above its top), dilated 12 px. The bottom-left corner
              (the bench) is not in it: it comes from code (bench_code.py corner).
  the input = hdx.png outside the mask, byte for byte; inside: the plaster times the clay's shading ratio; the console = the clay's,
              scaled by (HDx's left walnut lining, u 0.291-0.319 / the clay's), the lining's chroma, its front face (normal +Y) held
              0 to -2/3 stop under the lining (route 12.2)
  python3 prep_hdx2.py <work_dir>  ->  hdx2-input.png, hdx2-mask.png, hdx2-core.png, prep-hdx2.json
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit as K  # noqa: E402
from prep_ht2 import lining_mask, masks, normals  # noqa: E402

N = "HDx"
LIN_U = (0.291, 0.319)


def main(work):
    hdx8 = K.rgb8(os.path.join(K.PREV, "hdx.png"))
    hdx = hdx8.astype(np.float64) / 255
    cls, obj, sh, core, mask, R, mrep = masks(N, (K.CONSOLE_ID,), thr=0.95, top_z=0.80, box=((2.55, 6.35, 0.0), (3.35, 6.70, 0.80)), reach=0.20)
    lin = K.to_lin(hdx)
    clay = K.to_lin(K.rgb(K.clay_png(N)))
    nrm = normals(N)
    res = lin.copy()
    inside = mask & ~obj
    res[inside] = lin[inside] * R[inside][:, None]
    lm = lining_mask(cls, N, LIN_U)
    Ys, Yc = lin @ K.W709, clay @ K.W709
    g = float(np.median(Ys[lm]) / np.median(Yc[lm]))
    b = clay * g
    front = obj & (nrm[..., 1] > 0.7)
    endf = obj & (nrm[..., 0] < -0.7)
    top = obj & (nrm[..., 2] > 0.7)
    rep = dict(lining_px=int(lm.sum()), lining_still_Y=round(float(np.median(Ys[lm])), 4), lining_clay_Y=round(float(np.median(Yc[lm])), 4), gain=round(g, 4))
    fs = float(np.log2(np.median((b @ K.W709)[front]) / np.median(Ys[lm])))
    rep["front_vs_lining_from_clay"] = round(fs, 3)
    tgt = min(max(fs, -2 / 3 + 0.05), -0.05)
    b = b * 2 ** (tgt - fs)
    rep["front_vs_lining_in_input"] = round(tgt, 3)
    for nm, m in (("end_face", endf), ("top", top)):
        if m.any():
            rep[nm + "_vs_front_in_input"] = round(float(np.log2(np.median((b @ K.W709)[m]) / np.median((b @ K.W709)[front]))), 3)
    lab = K.lab_from_lin(b)
    ls = K.lab_from_lin(lin)
    a0, b0 = float(np.median(ls[lm][:, 1])), float(np.median(ls[lm][:, 2]))
    lab[obj, 1] = a0 + (lab[obj, 1] - lab[obj, 1].mean()) * 0.3
    lab[obj, 2] = b0 + (lab[obj, 2] - lab[obj, 2].mean()) * 0.3
    b[obj] = K.lin_from_lab(lab[obj])
    res[obj] = b[obj]
    out8 = np.clip(np.rint(np.where(mask[..., None], K.to_srgb(res), hdx) * 255), 0, 255).astype(np.uint8)
    out8[~mask] = hdx8[~mask]
    K.save(os.path.join(work, "hdx2-input.png"), out8)
    K.save(os.path.join(work, "hdx2-mask.png"), np.where(mask, 255, 0).astype(np.uint8))
    K.save(os.path.join(work, "hdx2-core.png"), np.where(core, 255, 0).astype(np.uint8))
    ys, xs = np.nonzero(obj)
    U, V = K.canvas(N).uv()
    rep.update(lining_ab=[round(a0, 2), round(b0, 2)], shading=mrep, mask_px=int(mask.sum()), console_px=int(obj.sum()), shadow_px=int(sh.sum()),
               console_bbox_uv=[round(v, 4) for v in (*K.uv_of_px(N, xs.min(), ys.min()), *K.uv_of_px(N, xs.max() + 1, ys.max() + 1))],
               mask_touches_opening_u_0291_0651=int((mask & (U >= 0.291) & (U <= 0.651)).sum()),
               mask_in_bottom_left=int((mask & (U < 0.40) & (V > 0.85)).sum()),
               outside_mask_max_diff_levels=int(np.abs(out8.astype(int) - hdx8.astype(int))[~mask].max()))
    K.dump(os.path.join(work, "prep-hdx2.json"), rep)
    print(rep)


if __name__ == "__main__":
    main(sys.argv[1])
