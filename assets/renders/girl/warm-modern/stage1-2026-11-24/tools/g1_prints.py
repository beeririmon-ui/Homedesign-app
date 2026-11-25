#!/usr/bin/env python3
"""
g1_prints.py: the girl's prints become set G1 "painted bunnies" (FB12; docs/proposals/wm-fb12-2026-11-25.md ב.10.5; the brief
briefs/wm-fb12-girl-art-g1-2026-11-25.md), render-agent, 2026-11-25; 0 tokens, no var2. Run it with python3.12 -I: it reads the supplier's
flat files in the scratchpad (kids-art-review/raw), which never enter the repo; only the warped panels inside the layer do.
  same     stage one's place() (no options) rebuilt in a scratch sandbox for both rooms: byte for byte against the repo's layers
  measure  the openings re-measured on the blank layer (instruction 3): each side fitted to the paper's edge, subpixel; A and B
           back-projected onto the wall (Y = y0 + 0.018), C onto its leaning plane; C's bottom is behind the ledge's lip, so its
           corners there are the set's own opening (A and B's mean size), along its fitted sides
  prep     the three panels: the crop recomputed where the rectified ratio is more than 3 % off the table (the table's centre kept, the
           largest rectangle of that ratio inside the art, so only blank paper comes off; the subject boxes whole, margins 3 % or more),
           resized to the panel's own size (h 400)
  place    kids_art.place with its G1 options -> layers/framed-prints/<G1 id>.png (today's Type A layer is not touched)
  compose  K-girl-defaults-g1, K-girl-V2-g1, K-girl-V3-g1 (+ -frame) through kids_cut.compose, the prints (and the throw) swapped
  checks   RND2, dE00 per ink region, the colour shares, the darkest ink, the grounds, the paper; V1-V3 -> checks.json["G1_2026_11_25"]
  sheet    qa-sheet-g1.jpg: the wall at x2 before and after, then G1 with V2, V1 and V3 at x1
  record   manifest-g1.json (today's manifest.json stays the rollback) and the root manifest's entries
  all      the above in order
"""
import colorsys
import hashlib
import importlib.util
import json
import math
import os
import shutil
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw

REPO = "/home/user/homedesign-app"
TOOLS = os.path.join(REPO, "assets/renders/boy/warm-modern/stage1-2026-11-24/tools")
sys.path.insert(0, TOOLS)
import kids_common as K  # noqa: E402
from kids_passes import PRODUCTS  # noqa: E402

C = K.C
H, W = K.H, K.W
ST = K.ST["girl"]
SCR = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/"
RAW = SCR + "kids-art-review/raw/"
WORK = SCR + "wm-kids/art/g1/"
CARD = "framed-prints-aliexpress-watercolour-bunny-nursery-prints"
G1_ID = CARD + "-g1"
TYPE_A = PRODUCTS["girl"]["framed-prints"][1]
LAYER = os.path.join(ST, "layers", "framed-prints", G1_ID + ".png")
LAYER_A = os.path.join(ST, "layers", "framed-prints", TYPE_A + ".png")
FRAMES = {"V1": ("K-girl-defaults", "K-girl-defaults-g1"), "V2": ("K-girl-V2", "K-girl-V2-g1"), "V3": ("K-girl-V3", "K-girl-V3-g1")}
BAND = 2.5                     # the unmix rim, px either side of an opening's edge
FLOOR_L = 15.0                 # WM-G1 for the ink (ב.6)
# ב.10.5's table (the boxes in the flat files' px): the frame, the design, the SKU (30 x 42, unframed), the usable art, the table's
# crop and ratio, and the subject box that must stay whole
SET = {
    "A": dict(design="B05", color="12", sku="12000048989497778", file="B05_12.webp", art=(22, 0, 1477, 2031),
              table_crop=(22, 45, 1477, 1985), table_ratio=0.75, subject=(107, 97, 1361, 1910)),
    "B": dict(design="B04", color="13", sku="12000048989497779", file="B04_13.webp", art=(22, 0, 1473, 2011),
              table_crop=(22, 108, 1473, 1922), table_ratio=0.80, subject=(241, 422, 1307, 1609)),
    "C": dict(design="B06", color="11", sku="12000048989497777", file="B06_11.webp", art=(22, 0, 1486, 2074),
              table_crop=(143, 45, 1433, 2029), table_ratio=0.65, subject=(332, 124, 1244, 1649)),
}
PAPER_REF = "A"                # B05's paper for the whole set (instruction 4)


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def kids_art():
    spec = importlib.util.spec_from_file_location("kids_art", os.path.join(TOOLS, "kids_art.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def hsl_h(rgb):
    mx, mn = rgb.max(-1), rgb.min(-1)
    d = mx - mn
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    dd = np.maximum(d, 1e-9)
    h = np.where(mx == r, ((g - b) / dd) % 6, np.where(mx == g, (b - r) / dd + 2, (r - g) / dd + 4)) * 60
    return np.where(d < 1e-9, -1.0, h)


def hsl(lab):
    rgb = np.clip(C.from_lab(np.asarray(lab, float)[None, None])[0, 0], 0, 1)
    hh, ll, ss = colorsys.rgb_to_hls(*rgb)
    return [round(hh * 360, 1), round(ss * 100, 1), round(ll * 100, 1)]


# ---------------------------------------------------------------------------------------------------------------- same
def same():
    """stage one, byte for byte: place(<kid>) with no options, in a sandbox (K.ST -> scratch, a copy of the room's manifest)"""
    out = {}
    for kid in ("boy", "girl"):
        sb = os.path.join(WORK, "sandbox", kid)
        os.makedirs(os.path.join(sb, "layers", "framed-prints"), exist_ok=True)
        shutil.copy(os.path.join(K.ST[kid], "manifest.json"), os.path.join(sb, "manifest.json"))
        keep = K.ST[kid]
        K.ST[kid] = sb
        try:
            kids_art().place(kid)
        finally:
            K.ST[kid] = keep
        pid = PRODUCTS[kid]["framed-prints"][1]
        new, old = os.path.join(sb, "layers", "framed-prints", pid + ".png"), os.path.join(keep, "layers", "framed-prints", pid + ".png")
        rn = json.load(open(os.path.join(sb, "manifest.json")))["code_fixes"]["framed-prints art"]
        ro = json.load(open(os.path.join(keep, "manifest.json")))["code_fixes"]["framed-prints art"]
        out[kid] = dict(layer=os.path.relpath(old, REPO), sha256_repo=sha(old), sha256_rebuilt=sha(new), identical=sha(old) == sha(new),
                        manifest_record_identical=rn == ro)
        shutil.rmtree(sb)
    print(json.dumps(out, indent=1))
    return out


# ------------------------------------------------------------------------------------------------------------- measure
def _blank():
    rgba = np.asarray(Image.open(K.SCR + "girl-framed-prints-blank.png")).astype(np.float64) / 255
    return rgba


def _samp(img, x, y):
    if img.ndim == 3:
        return np.stack([cv2.remap(img[..., c], x.astype(np.float32), y.astype(np.float32), cv2.INTER_LINEAR) for c in range(img.shape[2])], -1)
    return cv2.remap(img, x.astype(np.float32), y.astype(np.float32), cv2.INTER_LINEAR)


def _fit_side(lin, alpha, q, i, n=40, half=7.0, step=0.25):
    """side i of q (tl-tr, tr-br, br-bl, bl-tl): 1-D profiles across it, the paper's share between the rail's colour (the outer 3 px)
    and the paper's (the inner 3 px), its 0.5 crossing; a line by total least squares, trimmed at 2.5 MAD"""
    p0, p1 = q[i], q[(i + 1) % 4]
    d = (p1 - p0) / np.linalg.norm(p1 - p0)
    nin = np.array([-d[1], d[0]])
    if np.dot(q.mean(0) - p0, nin) < 0:
        nin = -nin
    offs = np.arange(-half, half + 1e-6, step)
    pts = []
    for t in np.linspace(0.12, 0.88, n):
        base = p0 + t * (p1 - p0)
        xy = base[None, :] + offs[:, None] * nin[None, :]
        prof = _samp(lin, xy[:, 0][None, :], xy[:, 1][None, :])[0]
        al = _samp(alpha, xy[:, 0][None, :], xy[:, 1][None, :])[0]
        if al[offs > 0].min() < 0.9:
            continue
        wood = np.median(prof[offs <= -half + 3], 0)
        pap = np.median(prof[offs >= half - 3], 0)
        v = pap - wood
        if np.dot(v, v) < 1e-3:
            continue
        s = (prof - wood) @ v / np.dot(v, v)
        k = np.nonzero((s[:-1] < 0.5) & (s[1:] >= 0.5))[0]
        if len(k) == 0:
            continue
        k = k[np.argmin(np.abs(offs[k]))]
        pts.append(base + (offs[k] + (0.5 - s[k]) / (s[k + 1] - s[k]) * step) * nin)
    pts = np.array(pts)
    for _ in range(3):
        m = pts.mean(0)
        dd = np.linalg.svd(pts - m)[2][0]
        r = (pts - m) @ np.array([-dd[1], dd[0]])
        pts = pts[np.abs(r) <= max(2.5 * 1.4826 * np.median(np.abs(r)), 0.3)]
    m = pts.mean(0)
    dd = np.linalg.svd(pts - m)[2][0]
    r = (pts - m) @ np.array([-dd[1], dd[0]])
    return (m, dd), dict(n=int(len(pts)), rms_px=round(float(np.sqrt((r ** 2).mean())), 3))


def _inter(a, b):
    (p, d), (q, e) = a, b
    t = np.linalg.solve(np.array([d, -e]).T, q - p)
    return p + t[0] * d


def _ray(x, y):
    f, r, u = K.axes()
    d = f + ((x - K.CX_) / K.F_) * r - ((y - K.HZ_) / K.F_) * u
    return d / np.linalg.norm(d)


def _hit(x, y, p0, n):
    L = np.array(K.LOC["girl"])
    d = _ray(x, y)
    return L + (np.dot(p0 - L, n) / np.dot(d, n)) * d


def measure():
    rgba = _blank()
    lin = C.lin(np.clip(rgba[..., :3], 0, 1)).astype(np.float32)
    alpha = rgba[..., 3].astype(np.float32)
    old = json.load(open(os.path.join(ST, "manifest.json")))["code_fixes"]["framed-prints art"]
    start = {fr: np.array(old[fr]["quad"], float) for fr in "AB"}
    # C: stage one's quad is the pale paper's axis-aligned box (the fallback); the frame leans, so the start is its four corners by eye
    start["C"] = np.array([(1341, 186), (1450, 164), (1444, 342), (1333, 356)], float)
    y0 = 10.25 + K.DY["girl"]                  # the east wall (framing_wm_kids.py ROOM y0 + 3.63); the art's face at y0 + 0.018
    res = {}
    for fr in "ABC":
        q = start[fr].copy()
        for _ in range(2):
            lines, sides = [], {}
            for i in range(4):
                if fr == "C" and i == 2:      # C's bottom is the ledge's lip, not the frame
                    lines.append(None)
                    continue
                ln, st_ = _fit_side(lin, alpha, q, i)
                lines.append(ln)
                sides[("top", "right", "bottom", "left")[i]] = st_
            if fr != "C":
                q = np.array([_inter(lines[3], lines[0]), _inter(lines[0], lines[1]), _inter(lines[1], lines[2]), _inter(lines[2], lines[3])])
            else:
                q = np.array([_inter(lines[3], lines[0]), _inter(lines[0], lines[1]), q[2], q[3]])
        rec = dict(stage_one_quad=old[fr]["quad"], stage_one_found_by=old[fr]["found_by"], sides_fit=sides)
        if fr in "AB":
            P = [_hit(x, y, np.array([0, y0 + 0.018, 0]), np.array([0, 1.0, 0])) for x, y in q]
            w = (np.linalg.norm(P[1] - P[0]) + np.linalg.norm(P[2] - P[3])) / 2
            h = (np.linalg.norm(P[3] - P[0]) + np.linalg.norm(P[2] - P[1])) / 2
            rec.update(opening_m=[round(w, 4), round(h, 4)], ratio_rectified=round(w / h, 4),
                       quad_px_ratio=round(float((np.linalg.norm(q[1] - q[0]) + np.linalg.norm(q[2] - q[3])) /
                                                 (np.linalg.norm(q[3] - q[0]) + np.linalg.norm(q[2] - q[1]))), 4))
        else:
            W3 = float(np.mean([res[k]["opening_m"][0] for k in "AB"]))
            H3 = float(np.mean([res[k]["opening_m"][1] for k in "AB"]))
            ll, rl = lines[3], lines[1]
            vp = np.cross(np.cross(np.r_[ll[0], 1], np.r_[ll[0] + ll[1], 1]), np.cross(np.r_[rl[0], 1], np.r_[rl[0] + rl[1], 1]))
            up = _ray(vp[0] / vp[2], vp[1] / vp[2])
            up = up if up[2] > 0 else -up      # the sides' own direction in 3-D (their vanishing point), so the corners stay on them
            ex = np.array([1.0, 0, 0]) - up[0] * up
            ex /= np.linalg.norm(ex)
            n = np.cross(ex, up)
            n /= np.linalg.norm(n)
            Lc = np.array(K.LOC["girl"])

            def width_at(s):
                p0 = Lc + s * _ray(*q[0])
                a_, b_ = _hit(*q[0], p0, n), _hit(*q[1], p0, n)
                return np.linalg.norm(b_ - a_), a_, b_
            lo, hi = 1.0, 6.0
            for _ in range(60):
                mid = (lo + hi) / 2
                lo, hi = (mid, hi) if width_at(mid)[0] < W3 else (lo, mid)
            _, TL, TR = width_at((lo + hi) / 2)
            bl, br = K.proj("girl", *(TL - H3 * up)), K.proj("girl", *(TR - H3 * up))
            q = np.array([q[0], q[1], br, bl], float)
            lip = _lip(alpha, q)
            rec.update(opening_m=[round(W3, 4), round(H3, 4)], ratio_rectified=round(W3 / H3, 4),
                       lean_deg=round(math.degrees(math.atan2(-up[1], up[2])), 2),
                       hidden_below_lip=lip,
                       note="C's bottom is behind the ledge's lip: its ratio cannot be seen, so it is the set's own opening (the same frame as "
                            "A and B, 25 x 36 cm); its bottom corners follow its fitted sides; about 4 % of the opening hides under the lip, "
                            "as in the clay (1.5 of 36.4 cm)")
        rec["quad_px"] = [[round(float(v), 2) for v in p] for p in q]
        res[fr] = rec
    for fr in "ABC":
        t = SET[fr]["table_ratio"]
        res[fr]["table_ratio"] = t
        res[fr]["off_table_pct"] = round(100 * (res[fr]["ratio_rectified"] / t - 1), 1)
        res[fr]["recompute_crop"] = bool(abs(res[fr]["ratio_rectified"] / t - 1) > 0.03)
    os.makedirs(WORK, exist_ok=True)
    json.dump(res, open(WORK + "quads.json", "w"), indent=1)
    print(json.dumps({k: {kk: v[kk] for kk in ("quad_px", "opening_m", "ratio_rectified", "table_ratio", "off_table_pct")} for k, v in res.items()}, indent=1))
    return res


def _lip(alpha, q):
    """C: the share of the opening's height hidden under the ledge's lip, at its left and right sides"""
    out = {}
    for nm, (top, bot) in (("left", (q[0], q[3])), ("right", (q[1], q[2]))):
        ts = np.linspace(0, 1, 2001)
        xy = top[None, :] + ts[:, None] * (bot - top)[None, :]
        xy = xy + np.sign(q.mean(0)[0] - top[0]) * np.array([3.0, 0])
        al = _samp(alpha, xy[:, 0][None, :], xy[:, 1][None, :])[0]
        vis = ts[al > 0.5]
        out[nm] = round(float(1 - vis.max()), 3) if len(vis) else None
    return out


# ---------------------------------------------------------------------------------------------------------------- prep
def _crop_for(fr, ratio):
    s = SET[fr]
    ax0, ay0, ax1, ay1 = s["art"]
    tx0, ty0, tx1, ty1 = s["table_crop"]
    cx, cy = (tx0 + tx1) / 2, (ty0 + ty1) / 2
    hh = min(cy - ay0, ay1 - cy)
    hw = min(cx - ax0, ax1 - cx)
    if hw / hh > ratio:
        hw = hh * ratio
    else:
        hh = hw / ratio
    box = (cx - hw, cy - hh, cx + hw, cy + hh)
    sx0, sy0, sx1, sy1 = s["subject"]
    m = dict(left=(sx0 - box[0]) / (2 * hw), right=(box[2] - sx1) / (2 * hw), top=(sy0 - box[1]) / (2 * hh), bottom=(box[3] - sy1) / (2 * hh))
    return box, {k: round(100 * v, 1) for k, v in m.items()}


def _panel(im, box, pw, ph):
    """the crop, resized to the panel by area in linear light (a print seen from further away averages its light, not its sRGB values)"""
    x0, y0, x1, y1 = box
    crop = np.asarray(im).astype(np.float64)[y0:y1, x0:x1] / 255
    return C.srgb(np.clip(cv2.resize(C.lin(crop).astype(np.float32), (pw, ph), interpolation=cv2.INTER_AREA).astype(np.float64), 0, 1))


def prep(meas=None):
    meas = meas or json.load(open(WORK + "quads.json"))
    out = {}
    os.makedirs(WORK, exist_ok=True)
    for fr in "ABC":
        r = meas[fr]["ratio_rectified"] if meas[fr]["recompute_crop"] else SET[fr]["table_ratio"]
        ph = 400
        pw = int(round(ph * r))
        box, marg = _crop_for(fr, pw / ph) if meas[fr]["recompute_crop"] else (SET[fr]["table_crop"], None)
        if marg and min(marg.values()) < 3.0:
            raise SystemExit(f"{fr}: a subject margin under 3 %: {marg}")
        box = tuple(int(round(v)) for v in box)            # whole px, so each panel px is an exact area of the file
        im = Image.open(RAW + SET[fr]["file"]).convert("RGB")
        panel = _panel(im, box, pw, ph)
        p = WORK + f"G1-{fr}.png"
        Image.fromarray(C.q(panel)).save(p)
        out[fr] = dict(design=SET[fr]["design"], file=SET[fr]["file"], file_px=list(im.size), crop=[round(float(v), 1) for v in box],
                       crop_ratio=round((box[2] - box[0]) / (box[3] - box[1]), 4), panel_px=[pw, ph], subject_margins_pct=marg,
                       table_crop=list(SET[fr]["table_crop"]), panel=p)
    json.dump(out, open(WORK + "prep.json", "w"), indent=1)
    print(json.dumps(out, indent=1))
    return out


# --------------------------------------------------------------------------------------------------------------- place
def place():
    meas = json.load(open(WORK + "quads.json"))
    pr = json.load(open(WORK + "prep.json"))
    rec = kids_art().place("girl", sizes={fr: tuple(pr[fr]["panel_px"]) for fr in "ABC"}, panels={fr: pr[fr]["panel"] for fr in "ABC"},
                           paper_ref=PAPER_REF, quads={fr: meas[fr]["quad_px"] for fr in "ABC"}, edge="unmix", floor_L=FLOOR_L,
                           out=LAYER, write_manifest=False)
    json.dump(rec, open(WORK + "place.json", "w"), indent=1)
    return rec


# ------------------------------------------------------------------------------------------------------------- compose
def _entries():
    man = json.load(open(os.path.join(ST, "manifest.json")))
    a = [l for l in man["layers"] if l["slot"] == "framed-prints"][0]
    rgba = np.asarray(Image.open(LAYER))
    ys, xs = np.nonzero(rgba[..., 3] > 0)
    g1 = dict(a, product=G1_ID, layer=os.path.relpath(LAYER, ST), alpha_px=int((rgba[..., 3] > 0).sum()),
              bbox_px=[int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1],
              sku="12000048989497778 (A, B05, colour 12) + 12000048989497779 (B, B04, 13) + 12000048989497777 (C, B06, 11); 30 x 42 unframed",
              card=CARD, set="G1", options={"A": "color 12 / 30x42-unframed", "B": "color 13 / 30x42-unframed", "C": "color 11 / 30x42-unframed"},
              usage_rights="unclear", zoom="x1 only", sale="not yet for sale",
              source="the Type A layer's frames, rails and shadow as they are; the three openings re-measured and the G1 panels warped in by code "
                     "(tools/g1_prints.py -> boy tools/kids_art.py place with its G1 options), 0 tokens",
              pass_="code-g1", passes=["from-boy", "PB4-shelf", "PB5-desk", "code-g1"])
    bs = {l.get("variant"): l for l in man["layers"] if l["slot"] == "bedspread" and not l.get("default", True)}
    return man, a, g1, bs


def compose():
    sys.path.insert(0, TOOLS)
    import kids_cut as KC
    man, a, g1, bs = _entries()
    out = {}
    # the chain first: no swap must give today's frames, byte for byte (so the G1 frames differ by the prints only)
    for v, (today, new) in FRAMES.items():
        sw = {} if v == "V1" else {"bedspread": bs[v]}
        o_today, _ = KC.compose("girl", None, swap=sw or None, write_files=False)
        same_ = bool((o_today == np.asarray(Image.open(os.path.join(ST, today + ".png")).convert("RGB"))).all())
        o8, r = KC.compose("girl", new, swap=dict(sw, **{"framed-prints": g1}))
        out[v] = dict(frame=new, today=today, chain_reproduces_today=same_, **r)
    json.dump(out, open(WORK + "compose.json", "w"), indent=1)
    print(json.dumps(out, indent=1))
    return out


# -------------------------------------------------------------------------------------------------------------- checks
def _geom():
    meas = json.load(open(WORK + "quads.json"))
    pr = json.load(open(WORK + "prep.json"))
    g = {}
    for fr in "ABC":
        pw, ph = pr[fr]["panel_px"]
        q = np.float32(meas[fr]["quad_px"])
        Hm = cv2.getPerspectiveTransform(np.float32([(0, 0), (pw, 0), (pw, ph), (0, ph)]), q)
        cover = cv2.warpPerspective(np.ones((ph, pw), np.float32), Hm, (W, H), flags=cv2.INTER_LINEAR)
        inside = (cover > 0.5).astype(np.uint8)
        d_in = cv2.distanceTransform(inside, cv2.DIST_L2, 5)
        d_out = cv2.distanceTransform(1 - inside, cv2.DIST_L2, 5)
        g[fr] = dict(Hm=Hm, pw=pw, ph=ph, q=q, inside=inside > 0, core=(inside > 0) & (d_in > BAND), grown=(inside > 0) | (d_out <= BAND))
    return g


def _lit(rgba, canvas):
    lin = C.lin(np.clip(rgba[..., :3], 0, 1))
    w = C.ero(canvas, 3).astype(np.float64)
    return np.stack([C.blur(lin[..., c] * w, 6) / np.maximum(C.blur(w, 6), 1e-4) for c in range(3)], -1)


def _regions(fr, crop_rgb):
    """the ink regions (instruction 5) on the flat file's crop, full res: B05 the fur, the flowers and the leaves; B04 the basket and the
    ink; B06 the body; and the ground (outside the subject box, pale and grey). Boolean masks at the crop's own px"""
    lab = C.to_lab(crop_rgb)
    L, Ch = lab[..., 0], np.hypot(lab[..., 1], lab[..., 2])
    hl = np.degrees(np.arctan2(lab[..., 2], lab[..., 1])) % 360
    Hh = hsl_h(crop_rgb)

    def biggest(m, close=9):
        m = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_CLOSE, C.disk(close))
        n, lb, st, _ = cv2.connectedComponentsWithStats(m)
        return lb == 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA])) if n > 1 else m.astype(bool)
    if fr == "A":
        fur = biggest((Hh >= 22) & (Hh <= 45) & (Ch >= 12) & (L > 40) & (L < 90), 9) & (Ch >= 8)
        reg = {"fur": fur, "flowers": ((Hh >= 0) & (Hh < 22) | (Hh >= 340)) & (Ch >= 12),
               "leaves": (hl >= 95) & (hl <= 170) & (Ch >= 4) & (L < 82)}
    elif fr == "B":
        basket = biggest((Hh >= 15) & (Hh <= 40) & (Ch >= 10) & (L > 20) & (L < 72), 7)
        reg = {"basket": basket, "ink": (L < 40) & (Ch >= 2)}
    else:
        reg = {"body": biggest((L < 72) & (Ch >= 6), 9)}
    return reg


def _ground(fr, box, shape):
    m = np.ones(shape, bool)
    sx0, sy0, sx1, sy1 = SET[fr]["subject"]
    x0, y0 = box[0], box[1]
    m[max(0, int(sy0 - y0)):int(sy1 - y0), max(0, int(sx0 - x0)):int(sx1 - x0)] = False
    return m


def _mean_lab(lin, w):
    w = w.astype(np.float64)
    mu = (lin * w[..., None]).reshape(-1, 3).sum(0) / max(w.sum(), 1e-9)
    return C.to_lab(C.srgb(np.clip(mu, 0, 1))[None, None])[0, 0]


def _shares(rgb, m):
    lab = C.to_lab(rgb)
    Ch = np.hypot(lab[..., 1], lab[..., 2])
    hl = np.degrees(np.arctan2(lab[..., 2], lab[..., 1])) % 360
    Hh = hsl_h(rgb)
    n = max(int(m.sum()), 1)
    cls = {"caramel": (Hh >= 20) & (Hh <= 35) & (Ch >= 15),
           "pink": (((Hh >= 0) & (Hh < 20)) | (Hh >= 330)) & (Ch >= 8),
           "green": (Hh >= 60) & (Hh <= 170) & (Ch >= 5),
           "blue": (hl >= 180) & (hl <= 300) & (Ch >= 3)}
    return {k: round(100 * float((v & m).sum()) / n, 2) for k, v in cls.items()}


def checks():
    g = _geom()
    pr = json.load(open(WORK + "prep.json"))
    meas = json.load(open(WORK + "quads.json"))
    rec_place = json.load(open(WORK + "place.json"))
    comp = json.load(open(WORK + "compose.json"))
    blank = _blank()
    new = np.asarray(Image.open(LAYER)).astype(np.float64) / 255
    olda = np.asarray(Image.open(LAYER_A)).astype(np.float64) / 255
    grown = g["A"]["grown"] | g["B"]["grown"] | g["C"]["grown"]
    inside = g["A"]["inside"] | g["B"]["inside"] | g["C"]["inside"]
    n8, o8 = np.asarray(Image.open(LAYER)), np.asarray(Image.open(LAYER_A))
    diff = (n8.astype(int) != o8.astype(int)).any(-1)
    out = {"rule": "FB12 ב.10.5: G1 (B05 / B04 / B06) in A / B / C; 0 tokens",
           "stage_one_byte_identical": json.load(open(WORK + "same.json"))}
    out["RND2_layer"] = dict(
        rule="the G1 layer against today's Type A layer: the frames, rails, shadow and alpha unchanged; change only inside the three openings "
             f"(and, on the rails' side, within {BAND} px of an opening's edge: the paper's share of the rail's edge pixels)",
        alpha_identical=bool((n8[..., 3] == o8[..., 3]).all()),
        differing_px_outside_openings_grown=int((diff & ~grown).sum()),
        differing_px_in_rim_outside_openings=int((diff & grown & ~inside).sum()),
        differing_px_inside_openings=int((diff & inside).sum()),
        type_a_layer_sha256_untouched=sha(LAYER_A))
    frames = {}
    for v, rr in comp.items():
        today = np.asarray(Image.open(os.path.join(ST, rr["today"] + ".png")).convert("RGB")).astype(int)
        f8 = np.asarray(Image.open(os.path.join(ST, rr["frame"] + ".png")).convert("RGB")).astype(int)
        d = (today != f8).any(-1)
        frames[rr["frame"]] = dict(vs_plate_outside_region_px=rr["outside_differing_px"], black_point_p05=rr["black_point_p05"],
                                   chain_reproduces_today=rr["chain_reproduces_today"],
                                   vs_today_outside_openings_grown_px=int((d & ~grown).sum()), vs_today_inside_px=int((d & grown).sum()))
    out["frames"] = frames
    # fidelity: dE00 per ink region against the flat file, in the same light scale (the scene's pixels over its own light, times the set's
    # paper, i.e. back to the file's scale); the regions warped from the file into the opening's core (not the rim, not under the lip)
    paper = np.array(rec_place["A"]["paper_lin"])
    fid, grounds, darkest = {}, {}, {}
    canvas_all = {}
    f8 = np.asarray(Image.open(os.path.join(ST, comp["V1"]["frame"] + ".png")).convert("RGB")).astype(np.float64) / 255
    for fr in "ABC":
        canvas = g[fr]["inside"] & (blank[..., 3] > 0.5)
        canvas_all[fr] = canvas
        lit = _lit(blank, canvas)
        delit = C.lin(np.clip(new[..., :3], 0, 1)) * paper / np.maximum(lit, 1e-4)
        box = pr[fr]["crop"]
        im = Image.open(RAW + SET[fr]["file"]).convert("RGB")
        x0, y0, x1, y1 = (int(round(v)) for v in box)
        crop = np.asarray(im.crop((x0, y0, x1, y1))).astype(np.float64) / 255
        crop_lin = C.lin(crop)
        panel = np.asarray(Image.open(pr[fr]["panel"]).convert("RGB")).astype(np.float64) / 255
        regs = _regions(fr, crop)
        regs_g = {"ground": _ground(fr, (x0, y0), crop.shape[:2]) & (C.to_lab(crop)[..., 0] > 70) & (np.hypot(*np.moveaxis(C.to_lab(crop)[..., 1:], -1, 0)) < 10)}
        pw, ph = g[fr]["pw"], g[fr]["ph"]
        keep = g[fr]["core"] & (new[..., 3] > 0.9)
        file_cells = cv2.resize(crop_lin.astype(np.float32), (pw, ph), interpolation=cv2.INTER_AREA).astype(np.float64)
        # the same panel warped the same way, unlit: the sampling's own share of any difference
        pan_s_lin = C.lin(np.clip(cv2.warpPerspective(panel.astype(np.float32), g[fr]["Hm"], (W, H), flags=cv2.INTER_LANCZOS4).astype(np.float64), 0, 1))
        rows = {}
        for nm, m in list(regs.items()) + list(regs_g.items()):
            # a region is the panel's cells it fills at least half of: what x1 can show of it (a 5 px ink line is under one cell)
            cov = cv2.resize(m.astype(np.float32), (pw, ph), interpolation=cv2.INTER_AREA)
            wp = (cov >= 0.5).astype(np.float32)
            ws = cv2.warpPerspective(wp, g[fr]["Hm"], (W, H), flags=cv2.INTER_LINEAR) * keep
            src = _mean_lab(file_cells, wp)
            pan = _mean_lab(C.lin(panel), wp)
            ref_s = _mean_lab(pan_s_lin, ws)
            sce = _mean_lab(delit, ws)
            row = dict(share_of_file_pct=round(100 * float(m.mean()), 2), cells=int(wp.sum()), file_Lab=[round(float(v), 1) for v in src],
                       file_px_only_Lab=[round(float(v), 1) for v in _mean_lab(crop_lin, m)],
                       placed_delit_Lab=[round(float(v), 1) for v in sce], dE00_vs_file=round(float(C.de00(tuple(src), tuple(sce))), 2),
                       dE00_vs_same_sampling=round(float(C.de00(tuple(ref_s), tuple(sce))), 2),
                       dE00_panel_8bit=round(float(C.de00(tuple(src), tuple(pan))), 2), scene_weight_px=round(float(ws.sum()), 1))
            if nm == "ground":
                scene_lab = _mean_lab(C.lin(f8), ws)
                lit_lab = _mean_lab(lit, keep)
                grounds[fr] = dict(design=SET[fr]["design"], file_L=round(float(src[0]), 1), albedo_L_in_scene=round(float(sce[0]), 1),
                                   seen_L_in_frame=round(float(scene_lab[0]), 1), lit_paper_L=round(float(lit_lab[0]), 1))
            else:
                rows[nm] = row
        fid[fr] = dict(design=SET[fr]["design"], regions=rows, max_dE00_vs_file=max(r["dE00_vs_file"] for r in rows.values()))
        Lf = C.to_lab(f8)[..., 0]
        darkest[fr] = dict(min_L=round(float(Lf[keep].min()), 2), p01_L=round(float(np.percentile(Lf[keep], 0.1)), 2),
                           file_min_L=round(float(C.to_lab(crop)[..., 0].min()), 2), file_p01_L=round(float(np.percentile(C.to_lab(crop)[..., 0], 0.1)), 2))
    out["fidelity_dE00"] = dict(rule="dE00 <= 3 per ink region against the flat file, in the same light scale (ב.6 / ב.10.5 (5)): linear means "
                                     "over the same area: the region is the panel cells it fills at least half of (what x1 can show); the file's "
                                     "light averaged over those cells, against the scene's pixels over the canvas's light, times B05's paper, the "
                                     "cells warped into each opening's core. file_px_only_Lab: the region's own pixels at full res, for reference",
                                frames=fid, max=max(v["max_dE00_vs_file"] for v in fid.values()))
    out["fidelity_dE00"]["ok"] = out["fidelity_dE00"]["max"] <= 3.0
    out["darkest_ink"] = dict(rule=f"WM-G1: the darkest ink at L* {FLOOR_L:g} or more (ב.6); the floor L' = f + L^2 / 4f below 2f",
                              frames=darkest, min=min(v["min_L"] for v in darkest.values()))
    out["darkest_ink"]["ok"] = out["darkest_ink"]["min"] >= FLOOR_L - 0.05
    gA, gB, gC = (grounds[k] for k in "ABC")
    out["grounds"] = dict(
        rule="ב.10.5 (4): one paper for the set (B05's), so B06's taupe ground is not made cream; the brief's acceptance: 'about 6-8 L* below "
             "the other two'",
        frames=grounds,
        albedo_B06_minus_B05=round(gC["albedo_L_in_scene"] - gA["albedo_L_in_scene"], 1),
        albedo_B06_minus_B04=round(gC["albedo_L_in_scene"] - gB["albedo_L_in_scene"], 1),
        file_B06_minus_B05=round(gC["file_L"] - gA["file_L"], 1), file_B06_minus_B04=round(gC["file_L"] - gB["file_L"], 1),
        seen_B06_minus_B05=round(gC["seen_L_in_frame"] - gA["seen_L_in_frame"], 1), seen_B06_minus_B04=round(gC["seen_L_in_frame"] - gB["seen_L_in_frame"], 1),
        note="the files themselves carry B06's ground 1-2 L* from the others (not 6-8), and the scene lights C (on the shelf, nearer the window) "
             "about 10-16 L* brighter than A and B (the wall beside them reads so too): with one paper and the canvas's own light, B06 keeps its "
             "file's ratio to B05; it is seen lighter than A and B, not 6-8 below them")
    out["grounds"]["ok_as_written"] = -8.5 <= out["grounds"]["seen_B06_minus_B05"] <= -5.5 and -8.5 <= out["grounds"]["seen_B06_minus_B04"] <= -5.5
    # colour shares (instruction 6): over the set as seen (the three openings' cores in the frame) and over the three flat panels
    core_all = (g["A"]["core"] | g["B"]["core"] | g["C"]["core"]) & (new[..., 3] > 0.9)
    pan_cat = np.concatenate([np.asarray(Image.open(pr[fr]["panel"]).convert("RGB")).astype(np.float64).reshape(-1, 3) / 255 for fr in "ABC"])[None]
    seen = _shares(f8, core_all)
    flat = _shares(pan_cat, np.ones(pan_cat.shape[:2], bool))
    lim = dict(caramel=(">=", 10.0), pink=("<=", 30.0), green=("<=", 10.0), blue=("<=", 3.0))
    ok = {k: (seen[k] >= t if op == ">=" else seen[k] <= t) and (flat[k] >= t if op == ">=" else flat[k] <= t) for k, (op, t) in lim.items()}
    out["colour_shares_pct"] = dict(rule="caramel >= 10 % (HSL H 20-35, C* >= 15); pink <= 30 % (HSL H 330-20, C* >= 8); green <= 10 % "
                                         "(HSL H 60-170, C* >= 5); blue <= 3 % (LCh h 180-300, C* >= 3); of the set's area",
                                    seen_in_frame=seen, flat_panels=flat, ok=ok, all_ok=all(ok.values()))
    # each of V1-V3 (instruction 6): the frame's own checks, the prints the same in all three, the plaster above the band, the V3 rule
    ids = K.ids("K-girl-plate")
    fm = K.frame_mask()
    upper = C.ero(np.isin(ids, (1,)), 4) & fm
    upper[:, :900] = False
    per_v = {}
    for v, rr in comp.items():
        f8v = np.asarray(Image.open(os.path.join(ST, rr["frame"] + ".png")).convert("RGB")).astype(np.float64) / 255
        lab = C.to_lab(f8v)
        md = np.median(lab[upper], 0)
        per_v[v] = dict(frame=rr["frame"], RND2_vs_plate_px=rr["outside_differing_px"], black_point_p05=rr["black_point_p05"],
                        same_as_today_outside_openings=frames[rr["frame"]]["vs_today_outside_openings_grown_px"] == 0,
                        prints_identical_to_V1=bool((np.abs(f8v - f8)[core_all] < 1e-9).all()),
                        shares_seen=_shares(f8v, core_all), plaster_above_band_HSL=hsl(md),
                        plaster_rule="bone, HSL H 32-40 (unchanged by the prints: the plaster is outside every opening)")
    v3 = json.load(open(os.path.join(ST, "checks.json"))).get("V3_rule")
    per_v["V3"]["V3_rule_throw"] = v3
    per_v["combinations"] = "ב.10.4: none to avoid. V2 (deep chestnut) gathers B04's basket; V3 (pink) echoes B05's flowers; V1 is the quietest"
    out["V1_V3"] = per_v
    out["paper"] = dict(rule="matte paper, no glass (ב.6): no reflection layer; the light is the blank canvas's own, blurred 6 px; nothing but "
                             "the art and that light", reflection_layer=False, paper_ref="B05 (panel A): its pixels over the 70th percentile of L*",
                        paper_lin=rec_place["A"]["paper_lin"])
    out["openings"] = {fr: dict(quad_px=meas[fr]["quad_px"], opening_m=meas[fr]["opening_m"], ratio_rectified=meas[fr]["ratio_rectified"],
                                table_ratio=meas[fr]["table_ratio"], off_table_pct=meas[fr]["off_table_pct"], panel_px=pr[fr]["panel_px"],
                                crop=pr[fr]["crop"], table_crop=pr[fr]["table_crop"], subject_margins_pct=pr[fr]["subject_margins_pct"],
                                **({"hidden_below_lip": meas[fr]["hidden_below_lip"], "lean_deg": meas[fr]["lean_deg"]} if fr == "C" else {}))
                       for fr in "ABC"}
    out["unmix"] = {fr: rec_place[fr].get("unmix") for fr in "ABC"}
    out["acceptance"] = {
        "no seam or halo at the frame edges at x2": "by eye: qa-sheet-g1.jpg (the wall at x2); the rim is unmixed (the rails' paper share only)",
        "paper reads as paper, matte, no glass": "no reflection layer; by eye on the sheet",
        "B06's taupe ground about 6-8 L* below the other two": "as written: " + ("passes" if out["grounds"]["ok_as_written"] else "FAILS") +
            f" (seen: {out['grounds']['seen_B06_minus_B05']:+.1f} vs B05, {out['grounds']['seen_B06_minus_B04']:+.1f} vs B04; albedo "
            f"{out['grounds']['albedo_B06_minus_B05']:+.1f} / {out['grounds']['albedo_B06_minus_B04']:+.1f}; the files "
            f"{out['grounds']['file_B06_minus_B05']:+.1f} / {out['grounds']['file_B06_minus_B04']:+.1f})",
        "darkest ink L* >= 15": ("passes" if out["darkest_ink"]["ok"] else "FAILS") + f" (min {out['darkest_ink']['min']})",
        "RND2 0 outside the three openings": ("passes" if out["RND2_layer"]["differing_px_outside_openings_grown"] == 0 and out["RND2_layer"]["alpha_identical"] else "FAILS"),
        "dE00 <= 3 per ink region": ("passes" if out["fidelity_dE00"]["ok"] else "FAILS") + f" (max {out['fidelity_dE00']['max']})",
        "colour shares": "passes" if out["colour_shares_pct"]["all_ok"] else "FAILS"}
    ck = json.load(open(os.path.join(ST, "checks.json")))
    ck["G1_2026_11_25"] = out
    json.dump(ck, open(os.path.join(ST, "checks.json"), "w"), indent=1, ensure_ascii=False)
    print(json.dumps({k: out[k] for k in ("RND2_layer", "acceptance", "colour_shares_pct", "grounds", "darkest_ink")}, indent=1, ensure_ascii=False))
    print(json.dumps({fr: {k: (v["dE00_vs_file"], v["dE00_vs_same_sampling"], v["dE00_panel_8bit"], v["cells"]) for k, v in fid[fr]["regions"].items()} for fr in fid}))
    return out


# --------------------------------------------------------------------------------------------------------------- sheet
WALL = (1300, 110, 2470, 460)          # the three frames (canvas px)


def sheet():
    from PIL import ImageFont
    comp = json.load(open(WORK + "compose.json"))
    try:
        font = ImageFont.load_default(size=26)
    except TypeError:
        font = ImageFont.load_default()
    x0, y0, x1, y1 = WALL
    w, h = (x1 - x0) * 2, (y1 - y0) * 2
    tiles = []
    for lab_, path in (("before: today, Type A (K-girl-defaults.png)", os.path.join(ST, "K-girl-defaults.png")),
                       ("after: G1, B05 / B04 / B06 (K-girl-defaults-g1.png)", os.path.join(ST, comp["V1"]["frame"] + ".png"))):
        t = Image.open(path).convert("RGB").crop(WALL).resize((w, h), Image.LANCZOS)
        tiles.append((f"{lab_}; the wall at x2 (canvas {x0}-{x1} x {y0}-{y1}, x2 of the canvas)", t))
    for v in ("V2", "V1", "V3"):
        nm = comp[v]["frame"]
        t = Image.open(os.path.join(ST, nm + "-frame.png")).convert("RGB")
        tiles.append((f"G1 with {v} ({'deep chestnut' if v == 'V2' else 'linen brown, the default' if v == 'V1' else 'pink'}): "
                      f"{nm}-frame.png at x1 (1920 x 1080)", t))
    sw = max(t.size[0] for _, t in tiles)
    out = Image.new("RGB", (sw, sum(t.size[1] + 44 for _, t in tiles)), (250, 250, 248))
    d = ImageDraw.Draw(out)
    y = 0
    for lab_, t in tiles:
        d.text((8, y + 8), lab_, fill=(25, 25, 25), font=font)
        out.paste(t, (0, y + 40))
        y += t.size[1] + 44
    p = os.path.join(ST, "qa-sheet-g1.jpg")
    out.save(p, quality=84, optimize=True)
    print(p, out.size, os.path.getsize(p))


# -------------------------------------------------------------------------------------------------------------- record
def record():
    man, a, g1, bs = _entries()
    comp = json.load(open(WORK + "compose.json"))
    meas = json.load(open(WORK + "quads.json"))
    pr = json.load(open(WORK + "prep.json"))
    rec_place = json.load(open(WORK + "place.json"))
    m1 = json.loads(json.dumps(man))
    m1["id"] = man["id"] + "-g1"
    m1["set"] = "G1"
    m1["rollback"] = "manifest.json (Type A): its layer and frames are kept, unchanged"
    m1["frames"] = {v: dict(overscan=rr["frame"] + ".png", frame=rr["frame"] + "-frame.png") for v, rr in comp.items()}
    acc = json.load(open(os.path.join(ST, "checks.json")))["G1_2026_11_25"]["acceptance"]
    failing = [k for k, v in acc.items() if "FAILS" in v]
    m1["status"] = ("FB12 G1, 2026-11-25: the prints set G1 in place of Type A, by code, 0 tokens; rights unclear: x1 only, not yet for sale, "
                    "HD_PUBLIC=0 only (ב.10.5 (7)). " + (f"Stopped for the manager: {len(failing)} acceptance items fail in code as written "
                    f"({'; '.join(failing)}; checks.json G1_2026_11_25). " if failing else "") + "Not for the site before QA")
    m1["layers"] = [g1 if l["slot"] == "framed-prints" else l for l in man["layers"]]
    m1.setdefault("code_fixes", {})["framed-prints art G1"] = dict(
        rec_place, how="tools/g1_prints.py (girl) -> tools/kids_art.py place (boy) with its G1 options: sizes, panels, paper_ref A (B05), quads "
                       "(re-measured), edge unmix, floor_L 15; the panels cropped from the flat files (scratchpad only) per ב.10.5, the crop "
                       "recomputed by its instruction 3",
        crops={fr: dict(design=SET[fr]["design"], sku=SET[fr]["sku"], crop=pr[fr]["crop"], panel_px=pr[fr]["panel_px"],
                        subject_margins_pct=pr[fr]["subject_margins_pct"]) for fr in "ABC"},
        openings={fr: dict(ratio_rectified=meas[fr]["ratio_rectified"], opening_m=meas[fr]["opening_m"], table_ratio=meas[fr]["table_ratio"])
                  for fr in "ABC"},
        command="python3.12 -I assets/renders/girl/warm-modern/stage1-2026-11-24/tools/g1_prints.py all")
    p = os.path.join(ST, "manifest-g1.json")
    json.dump(m1, open(p, "w"), indent=1, ensure_ascii=False)
    # the root manifest
    rp = os.path.join(REPO, "assets/manifest.json")
    root = json.load(open(rp))
    base = dict(room="girl", style="warm-modern", created="2026-11-25", model="code (0 tokens)", tokens=0)
    status = ("stopped for the manager (FB12 G1: acceptance items fail in code as written, see checks.json G1_2026_11_25); " if failing else
              "for QA (FB12 G1); ") + "not for the site before QA; rights unclear: x1 only, not for sale"
    new = [dict(id="wm-girl-s1-g1-framed-prints", path=os.path.relpath(LAYER, REPO),
                kind="product layer: framed prints, set G1 (B05 / B04 / B06 of the bunny card), straight alpha; shares Type A's shadow", **base,
                status=status, product=G1_ID, sku=g1["sku"])]
    for v, rr in comp.items():
        for suf, kind in (("", "composed frame (overscan)"), ("-frame", "composed frame (16:9)")):
            new.append(dict(id=f"wm-girl-s1-{rr['frame']}{suf}", path=os.path.relpath(os.path.join(ST, rr["frame"] + suf + ".png"), REPO),
                            kind=f"{kind} with set G1, throw {v}: plate + layers in z order + light", **base, status=status))
    new.append(dict(id="wm-girl-s1-qa-sheet-g1", path=os.path.relpath(os.path.join(ST, "qa-sheet-g1.jpg"), REPO),
                    kind="QA sheet: the wall at x2 before (Type A) and after (G1); G1 with V2, V1 and V3 at x1", **dict(base, status="QA material, not for the site")))
    new.append(dict(id="wm-girl-s1-manifest-g1", path=os.path.relpath(p, REPO), kind="room manifest with set G1 as the prints' default "
                    "(manifest.json, Type A, stays the rollback)", **dict(base, status="record")))
    new.append(dict(id="wm-girl-s1-tool-g1-prints", path=os.path.relpath(os.path.abspath(__file__), REPO), kind="tool: G1 measure, prep, place, compose, checks, sheet",
                    **dict(base, status="record")))
    for e in new:
        e["sha256"] = sha(os.path.join(REPO, e["path"]))
        e["bytes"] = os.path.getsize(os.path.join(REPO, e["path"]))
    ids_new = {e["id"] for e in new}
    root["assets"] = [e for e in root["assets"] if e["id"] not in ids_new]
    for e in root["assets"]:
        if e.get("path") in (os.path.relpath(os.path.join(ST, "checks.json"), REPO),):
            e["sha256"] = sha(os.path.join(REPO, e["path"]))
            e["bytes"] = os.path.getsize(os.path.join(REPO, e["path"]))
            e["updated"] = "2026-11-25 (FB12 G1: checks.json G1_2026_11_25)"
    root["assets"] += new
    s = json.dumps(root, indent=1, ensure_ascii=False)
    open(rp, "w").write(s)
    print(p, len(new), "root entries")


if __name__ == "__main__":
    a = sys.argv[1] if len(sys.argv) > 1 else "all"
    os.makedirs(WORK, exist_ok=True)
    if a in ("same", "all"):
        json.dump(same(), open(os.path.join(WORK, "same.json"), "w"), indent=1)
    if a in ("measure", "all"):
        measure()
    if a in ("prep", "all"):
        prep()
    if a in ("place", "all"):
        place()
    if a in ("compose", "all"):
        compose()
    if a in ("checks", "all"):
        checks()
    if a in ("sheet", "all"):
        sheet()
    if a in ("record", "all"):
        record()
