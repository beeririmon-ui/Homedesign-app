#!/usr/bin/env python3
"""
bench_code.py: the bench carried in code from HT2 (its only source, route 12.1) into HD's bottom strip and into HDx2's bottom-left corner,
render-agent 2026-11-18. 0 tokens.
  strip  HD2 = hd.png with the bench in the canvas strip under the 16:9 frame (route 2.7, 12.0). The bench's pixels: HT2 carried to HD
         through the clay depth of both (the bench is planes: exact), where HT really sees the point; the few it does not, filled from
         their neighbours. Around the bench, the stone and floor take the clay's shading ratio (with / without the bench), only below the
         frame. The 16:9 frame of HD is not touched: 0 levels.
  corner the bench in HDx2's canvas: HD2's strip turned by the pure 65 degree rotation (route 12.0) where HD's canvas has the ray, and HT2
         through the depth where it does not; the clay's shading ratio around it. Applied over the composed console edit.
  python3 bench_code.py strip  <ht2.png> <out_hd2.png> <report.json>
  python3 bench_code.py corner <ht2.png> <hd2.png> <hdx2_console.png> <out.png> <report.json>
"""
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit as K  # noqa: E402


def fill(img, valid, sigma=3.0):
    """Normalised convolution: values for pixels outside `valid` from their valid neighbours."""
    v = valid.astype(np.float32)
    num = cv2.GaussianBlur(img.astype(np.float32) * v[..., None], (0, 0), sigma)
    den = cv2.GaussianBlur(v, (0, 0), sigma)[..., None]
    f = num / np.maximum(den, 1e-6)
    return np.where(valid[..., None], img, f), den[..., 0]


def shading_ratio(name, obj):
    """The clay's shading ratio around the bench (with / without it), as prep_ht2.masks: against its own baseline 400-800 px away, fading
    8 cm above the seat and 0.20 m from the bench's box; 1 elsewhere."""
    from prep_ht2 import masks
    _, _, _, _, mask, R, _ = masks(name, (K.BENCH_ID,), thr=0.95, top_z=0.45, box=((0.81, 6.70, 0.0), (1.21, 7.50, 0.45)), reach=0.20)
    return np.where(mask | obj, R, 1.0).astype(np.float32)


def alpha_of(obj):
    a = cv2.GaussianBlur(obj.astype(np.float32), (0, 0), 0.6)
    return np.where(obj, 1.0, np.clip(a * 2, 0, 1))


def put_bench(dst_name, base_lin, src_lin, src_name, frame_lock=True, extra=None):
    """The bench of `src` (a still on its canvas, linear) put into `base_lin` (the destination still, linear)."""
    cls = K.clay_id(dst_name)
    obj = cls == K.BENCH_ID
    img, vis = K.reproject(src_lin, src_name, dst_name, dst_ids=(K.BENCH_ID,))
    rep = dict(bench_px=int(obj.sum()), from_src_px=int(vis.sum()))
    if extra is not None:
        e_img, e_vis = extra
        use = e_vis & obj
        img = np.where(use[..., None], e_img, img)
        vis = vis | use
        rep["from_rotation_px"] = int(use.sum())
    filled, den = fill(img, vis & obj)
    rep["filled_px"] = int((obj & ~vis).sum())
    R = shading_ratio(dst_name, obj)
    if frame_lock:                                   # the frame is not touched: the shading fades in over 40 px below its bottom edge
        cv = K.canvas(dst_name)
        yy = np.arange(R.shape[0], dtype=np.float32)[:, None] - (cv.box[3] - 0.5)
        t = np.clip(yy / 40.0, 0, 1)
        R = 1 - (1 - R) * (t * t * (3 - 2 * t))
        rep["shading_fade_below_frame_px"] = 40
    out = base_lin * R[..., None]
    al = alpha_of(obj)[..., None]
    out = out * (1 - al) + filled * al
    if frame_lock:
        cv = K.canvas(dst_name)
        U, V = cv.uv()
        inframe = (U >= 0) & (U <= 1) & (V >= 0) & (V <= 1)
        out[inframe] = base_lin[inframe]
        rep["bench_px_inside_16_9_frame"] = int((obj & inframe).sum())
    changed = (np.abs(R - 1) > 0.002) | (al[..., 0] > 0)
    rep["shading_ratio_min_around"] = round(float(R[~obj & changed].min()), 3) if (~obj & changed).any() else 1.0
    return out, obj, changed, rep


def strip(ht2p, outp, repp):
    hd8 = K.rgb8(os.path.join(K.PREV, "hd.png"))
    ht2 = K.to_lin(K.rgb(ht2p))
    out, obj, changed, rep = put_bench("HD", K.to_lin(hd8 / 255.0), ht2, "HT", frame_lock=True)
    o8 = np.clip(np.rint(K.to_srgb(out) * 255), 0, 255).astype(np.uint8)
    cv = K.canvas("HD")
    U, V = cv.uv()
    inframe = (U >= 0) & (U <= 1) & (V >= 0) & (V <= 1)
    o8[inframe] = hd8[inframe]
    o8[~changed] = hd8[~changed]
    K.save(outp, o8)
    d = np.abs(o8.astype(int) - hd8.astype(int)).max(-1)
    ys, xs = np.nonzero(obj)
    u0, v0 = K.uv_of_px("HD", xs.min(), ys.min())
    u1, v1 = K.uv_of_px("HD", xs.max() + 1, ys.max() + 1)
    rep.update(frame_16_9_max_diff_levels=int(d[inframe].max()), px_changed=int((d > 0).sum()), bench_bbox_uv=[round(u0, 4), round(v0, 4), round(u1, 4), round(v1, 4)])
    # the seam HT2 -> HD's strip: the bench's top, sampled back, against HT2 (a check of the carry, not of the light)
    K.dump(repp, rep)
    print(rep)


def corner(ht2p, hd2p, consp, outp, repp):
    c8 = K.rgb8(consp)
    hdx8 = K.rgb8(os.path.join(K.PREV, "hdx.png"))
    ht2 = K.to_lin(K.rgb(ht2p))
    hd2 = K.to_lin(K.rgb(hd2p))
    hd_obj = K.clay_id("HD") == K.BENCH_ID
    rimg, rins = K.rot(hd2, "HD", "HDx")
    robj, _ = K.rot(hd_obj.astype(np.float32), "HD", "HDx")
    rvalid = rins & (robj > 0.999)
    out, obj, changed, rep = put_bench("HDx", K.to_lin(c8 / 255.0), ht2, "HT", frame_lock=False, extra=(rimg, rvalid))
    o8 = np.clip(np.rint(K.to_srgb(out) * 255), 0, 255).astype(np.uint8)
    o8[~changed] = c8[~changed]
    K.save(outp, o8)
    cv = K.canvas("HDx")
    U, V = cv.uv()
    inframe = (U >= 0) & (U <= 1) & (V >= 0) & (V <= 1)
    d = np.abs(o8.astype(int) - c8.astype(int)).max(-1)
    ys, xs = np.nonzero(obj)
    rep.update(px_changed=int((d > 0).sum()), px_changed_in_frame=int(((d > 0) & inframe).sum()),
               bench_px_in_frame=int((obj & inframe).sum()),
               bench_bbox_uv=[round(v, 4) for v in (*K.uv_of_px("HDx", xs.min(), ys.min()), *K.uv_of_px("HDx", xs.max() + 1, ys.max() + 1))],
               opening_u_0291_0651_changed_px=int(((d > 0) & (U >= 0.291) & (U <= 0.651)).sum()))
    # where both sources have the bench: rotation vs depth carry (the same HT2 pixels, resampled twice)
    img2, vis2 = K.reproject(ht2, "HT", "HDx", dst_ids=(K.BENCH_ID,))
    both = rvalid & vis2 & obj
    if both.any():
        a = K.to_srgb(rimg[both]) * 255
        b = K.to_srgb(img2[both]) * 255
        rep["rotation_vs_depth_carry_levels"] = dict(px=int(both.sum()), median=round(float(np.median(np.abs(a - b))), 2),
                                                     p95=round(float(np.percentile(np.abs(a - b), 95)), 2))
    rep["hdx_untouched_outside_console_and_bench"] = int(np.abs(o8.astype(int) - hdx8.astype(int)).max(-1)[~changed & (np.abs(c8.astype(int) - hdx8.astype(int)).max(-1) == 0)].max())
    K.dump(repp, rep)
    print(rep)


if __name__ == "__main__":
    if sys.argv[1] == "strip":
        strip(*sys.argv[2:5])
    else:
        corner(*sys.argv[2:7])
