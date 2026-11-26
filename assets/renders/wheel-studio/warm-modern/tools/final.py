#!/usr/bin/env python3
"""Run the studio post over the chosen raws (0 tokens): -> out/<variant>.png (1024) + meta.json. Specials:
caramel towel = the linen towel's 3/4 render recoloured (Lab mean/std transfer, product only) to the caramel render's own colour
(its two flux returns were top-down flat lays); work = the portrait frame return re-proportioned to landscape in code (rows cut,
columns stretched through the blank canvas), then the three 386242 prints set into the blank canvas, lit by the canvas's own light."""
import json, os, sys
import cv2
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from common import *  # noqa
from post import process, stats

CFG = {
 'set-B': ('raw/set-B-r2.jpg', 'flat', None), 'set-A': ('raw/set-A-r1.jpg', 'flat', None), 'set-C': ('raw/set-C-r1.jpg', 'flat', None),
 'hand-towel-aliexpress-pure-linen-towel-38x55-linen': ('raw/towel-linen-r1.jpg', 'flat', None),
 'tea-towel-cj-waffle-cotton-beige-45x65-pair-khaki': ('raw/teatowel-khaki-r2.jpg', 'flat', None),
 'pendant-cj-silk-ribbed-pumpkin-40-50cm-warm-light': ('raw/pend-pumpkin-r1.jpg', 'pendant', [0.12, 0.45, 0.88, 0.82]),
 'pendant-cj-scalloped-pleated-bell-45': ('raw/pend-bell-r1.jpg', 'pendant', [0.24, 0.2, 0.74, 0.6]),
 'bedspread-cj-waffle-gauze-fringe-150x200-deep-chestnut-brown': ('raw/bs-chestnut-r2.jpg', 'flat', None),
 'bedspread-cj-waffle-gauze-fringe-150x200-coffee': ('raw/bs-coffee-r1.jpg', 'flat', None),
 'bedspread-cj-waffle-gauze-fringe-150x200-green': ('raw/bs-green-r1.jpg', 'flat', None),
 'bedspread-cj-waffle-gauze-fringe-150x200-linen-brown': ('raw/bs-linenbrown-r1.jpg', 'flat', None),
 'bedspread-cj-waffle-gauze-fringe-150x200-pink': ('raw/bs-pink-r1.jpg', 'flat', [0.1, 0.3, 0.98, 0.88]),
 'sofa-cover-cj-cotton-muslin-fringe-pecan-150x200': ('raw/throw-pecan-r2.jpg', 'flat', None),
 'sofa-cover-cj-cotton-muslin-fringe-flax-brown-150x200': ('raw/throw-flax-r1.jpg', 'flat', None),
 'sofa-cover-cj-cotton-muslin-fringe-clay-150x200': ('raw/throw-clay-r1.jpg', 'flat', None),
}
FILL = {'pendant-cj-scalloped-pleated-bell-45': 0.55}
OPTS = {'bedspread-cj-waffle-gauze-fringe-150x200-pink': dict(sig_px=30, edge_px=110),
        'set-C': dict(t_px=(6, 30)),   # the return's wall carries a large cast shadow: keep only the contact shadow
        'pendant-cj-silk-ribbed-pumpkin-40-50cm-warm-light': dict(t_px=(4, 28), keep_px=(6, 14)),
        'pendant-cj-scalloped-pleated-bell-45': dict(t_px=(4, 28), keep_px=(6, 14))}   # its cast shadow ends in a hard edge in the return
os.makedirs('out', exist_ok=True); os.makedirs('out/mask', exist_ok=True)
META = {}
only = sys.argv[1:]
for k, (raw, kind, box) in CFG.items():
    if only and k not in only: continue
    o, mo, rec, *_ = process(raw, kind, shade_box=box, restrict=(kind == 'pendant' or box is not None), fill=FILL.get(k, 0.72), **OPTS.get(k, {}))
    save_png(f'out/{k}.png', o); cv2.imwrite(f'out/mask/{k}.png', mo.astype(np.uint8) * 255)
    rec.update(stats(o, mo)); META[k] = rec; print(k, rec['scale'], rec['fill'], rec['backdrop_lab'])

# caramel: the linen 3/4 geometry, recoloured to the caramel return's colour
CAR = 'hand-towel-aliexpress-pure-linen-towel-38x55-caramel'
if not only or CAR in only:
    lin_o = load('out/hand-towel-aliexpress-pure-linen-towel-38x55-linen.png')
    # the towel itself (grok segment-map of the linen return, located by template match: error 0), moved like the post moved the raw
    LM = json.load(open('out/meta.json'))['hand-towel-aliexpress-pure-linen-towel-38x55-linen'] if 'hand-towel-aliexpress-pure-linen-towel-38x55-linen' not in META else META['hand-towel-aliexpress-pure-linen-towel-38x55-linen']
    sc = LM['scale']; bx = LM['bbox_raw']; cxr, cyr = (bx[0] + bx[2]) / 2, (bx[1] + bx[3]) / 2
    Mt = np.float32([[sc, 0, 512 - sc * cxr], [0, sc, 512 - sc * cyr]])
    lin_m = cv2.warpAffine(cv2.imread('seg/linen-towel-mask-raw.png', 0), Mt, (1024, 1024), flags=cv2.INTER_LINEAR) > 127
    _, _, rc, cm, crgb, c_corr = process('raw/towel-caramel-r2.jpg', 'flat')
    Ls, Lt = lab(lin_o), lab(c_corr)
    ps, pt = Ls[lin_m], Lt[cm]
    mu_s, sd_s = ps.mean(0), ps.std(0); mu_t, sd_t = pt.mean(0), pt.std(0)
    r = np.clip(sd_t / sd_s, 0.5, 2.0)
    new = (Ls - mu_s) * r + mu_t
    lin_m = cv2.dilate(lin_m.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)      # 2 px out: no light rim of the linen
    inner = cv2.distanceTransform(lin_m.astype(np.uint8), cv2.DIST_L2, 5)
    a = np.clip(inner / 2.0, 0, 1)[..., None]
    o = lab2rgb(new) * a + lin_o * (1 - a)
    save_png(f'out/{CAR}.png', o); cv2.imwrite(f'out/mask/{CAR}.png', lin_m.astype(np.uint8) * 255)
    rec = dict(raw='raw/towel-linen-r1.jpg (geometry) + raw/towel-caramel-r2.jpg (colour)', method='Lab mean/std transfer on the product pixels',
               src_lab_mean=[round(float(v), 2) for v in mu_s], target_lab_mean=[round(float(v), 2) for v in mu_t], std_ratio=[round(float(v), 3) for v in r])
    rec.update(stats(o, lin_m)); META[CAR] = rec; print(CAR, rec['target_lab_mean'])

# work: landscape frame from the portrait return, then the prints
if not only or 'work' in only:
    fr = load('raw/work-frame-r2.jpg')
    CUT = (400, 550); ST = (400, 700, 415)          # rows cut through the canvas; columns 400-700 stretched to 415
    ov = 24                                          # the cut cross-faded over 24 rows: no step in the wall shadow
    wv = np.linspace(0, 1, ov, dtype=np.float32)[:, None, None]
    fr = np.concatenate([fr[:CUT[0] - ov], fr[CUT[0] - ov:CUT[0]] * (1 - wv) + fr[CUT[1]:CUT[1] + ov] * wv, fr[CUT[1] + ov:]], 0)
    mid = cv2.resize(fr[:, ST[0]:ST[1]], (ST[2], fr.shape[0]), interpolation=cv2.INTER_CUBIC)
    fr = np.concatenate([fr[:, :ST[0]], mid, fr[:, ST[1]:]], 1)
    h, w = fr.shape[:2]
    box = [200 / w, 140 / h, (880 + ST[2] - (ST[1] - ST[0])) / w, (900 - (CUT[1] - CUT[0]) - 24) / h]
    o, mo, rec, *_ = process('raw/work-frame-r2.jpg (re-proportioned)', 'flat', shade_box=box, pre=fr, restrict=True)
    save_png('out/work-frame.png', o); cv2.imwrite('out/mask/work-frame.png', mo.astype(np.uint8) * 255)
    rec.update(dict(reproportion=dict(rows_cut=list(CUT), cols_stretched=[ST[0], ST[1]], to=ST[2], size=[w, h])))
    META['work-frame'] = rec
    # the blank canvas: the large uniform sand region inside the mat
    L = lab(o)
    ys, xs = np.nonzero(mo); cy, cx = int(np.median(ys)), int(np.median(xs))
    seed = np.median(L[cy - 20:cy + 20, cx - 20:cx + 20].reshape(-1, 3), 0)
    cv = (np.linalg.norm(L - seed, axis=-1) < 6).astype(np.uint8)
    cv = cv2.morphologyEx(cv, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    n, lb, st, _ = cv2.connectedComponentsWithStats(cv, 8); cv = (lb == lb[cy, cx]).astype(np.uint8)
    cv = cv2.morphologyEx(cv, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    ys_, xs_ = np.nonzero(cv); T_, B_ = ys_.min(), ys_.max(); hh = B_ - T_
    def edges(r0, r1):
        L_, R_ = [], []
        for y in range(int(r0), int(r1)):
            xr = np.nonzero(cv[y])[0]
            if len(xr): L_.append(xr.min()); R_.append(xr.max())
        return np.median(L_), np.median(R_)
    lt, rt = edges(T_ + 0.05 * hh, T_ + 0.2 * hh); lb_, rb_ = edges(B_ - 0.2 * hh, B_ - 0.05 * hh)
    rb_ = rt + (lt - lb_)     # the lean: a symmetric trapezoid; the left side and the top band are clean, the canvas's lower right is shaded
    # the side edges as straight lines through the two bands, extended to the top and bottom rows
    yt, yb = T_ + 0.125 * hh, B_ - 0.125 * hh
    fx = lambda a0, a1, y: a0 + (a1 - a0) * (y - yt) / (yb - yt)
    quad = np.array([[fx(lt, lb_, T_), T_], [fx(rt, rb_, T_), T_], [fx(rt, rb_, B_), B_], [fx(lt, lb_, B_), B_]], np.float32)
    quad += np.array([[-1, -1], [1, -1], [1, 1], [-1, 1]], np.float32)   # 1 px out, under the mat's edge
    canvas_lin = to_lin(o); alb = np.median(canvas_lin[cv > 0], 0)
    light = cv2.GaussianBlur(canvas_lin, (0, 0), 1.5) / alb
    LAND = (38, 125, 766, 668)
    FILES = {'08': 'ref/' + [f for f in os.listdir('ref') if f][0]}
    import hashlib
    URL = {'08': 'https://ae01.alicdn.com/kf/Sabff5188ff2c40d0a5e0885cf7cda14a8.jpg', '01': 'https://ae01.alicdn.com/kf/S0c6d91355e12444388ff139962b388021.jpg',
           '02': 'https://ae01.alicdn.com/kf/S31ea5f0037c44870a4ca50c90fe2d0fbN.jpg'}
    qw = (np.linalg.norm(quad[1] - quad[0]) + np.linalg.norm(quad[2] - quad[3])) / 2
    qh = (np.linalg.norm(quad[3] - quad[0]) + np.linalg.norm(quad[2] - quad[1])) / 2
    for key, u in URL.items():
        f = 'ref/' + hashlib.md5(u.encode()).hexdigest()[:8] + '.jpg'
        pr = load(f)[LAND[1]:LAND[3], LAND[0]:LAND[2]]
        ph, pw = pr.shape[:2]; kk = max(qw / pw, qh / ph); sw, sh = qw / kk, qh / kk
        ox, oy = (pw - sw) / 2, (ph - sh) / 2
        src = np.float32([[ox, oy], [ox + sw, oy], [ox + sw, oy + sh], [ox, oy + sh]])
        Hm = cv2.getPerspectiveTransform(src, quad)
        warped = cv2.warpPerspective(to_lin(pr), Hm, (1024, 1024), flags=cv2.INTER_AREA)
        cover = cv2.warpPerspective(np.ones((ph, pw), np.float32), Hm, (1024, 1024), flags=cv2.INTER_LINEAR)
        res = to_srgb(canvas_lin * (1 - cover[..., None]) + warped * light * cover[..., None])
        vk = f'framed-art-aliexpress-misty-landscape-386242-work-{key}-30x40'
        save_png(f'out/{vk}.png', res); cv2.imwrite(f'out/mask/{vk}.png', mo.astype(np.uint8) * 255)
        META[vk] = dict(raw='raw/work-frame-r2.jpg (blank frame, re-proportioned)', print=f, print_box=list(LAND), quad=quad.round(1).tolist(),
                        canvas_px=int(cv.sum()), **stats(res, mo))
        print(vk, quad.round(1).tolist())
old = json.load(open('out/meta.json')) if os.path.exists('out/meta.json') else {}
old.update(META); json.dump(old, open('out/meta.json', 'w'), indent=1)
