"""
stack.py: the warm-modern tool's layer stack in the ungraded v3 space, and the one v3c display grade (render-agent, 2026-11-10).

The stack, bottom to top (slot z; ties by the plan's order): base (phase 1: shell v3 + the code furniture shadow + the fixed furniture),
curtains 10, framed-art 12, accent-sconces 12, vase 16, rug 20, floor-lamp 30, planter 32, cushions 55 (set A / B / C), basket 60,
magazine-holder 60, bowl 65, candle-holders 65, pendant 80. Each product: a shadow (multiply) and the product (source-over).

Items that stand BEHIND the fixed furniture (the rug under it, the curtains behind the armchair, the floor lamp behind the sofa's arm)
are composed physically: on the scene behind the furniture (shell v3 x the furniture's code shadow, plus earlier items behind it), and
the furniture over them with its own soft alpha:  U = (behind x shadow x (1 - a) + product x a) x (1 - fa) + furniture x fa.
Every step changes U only inside that product's region (alpha > 0 or shadow < 1, the saved 8-bit files): outside it U is untouched.

The grade is phase 1's grade_v3c, recomputed and checked to give base.png byte for byte (0 px differ): the v3b exposure (gain 1.0008,
shoulder L 88-97), ONE toe from the base (black point 6.14 -> 12.5, faded out by L 25), and the bench slab's chroma clamped along the
stone's hue. The slab's share of a pixel is stone x (1 - furniture alpha) x (1 - every product's alpha): a product standing on the
bench (the vase) is not stone. It is one per-pixel function for every file, so no layer is graded on its own.
"""
import json
import os

import cv2
import numpy as np
from PIL import Image

import phase2_wm as W
from phase2_wm import PW, P1

ORDER = ["curtains", "framed-art", "accent-sconces", "vase", "rug", "floor-lamp", "planter", "cushions", "basket", "magazine-holder",
         "bowl", "candle-holders", "pendant"]
Z = {"curtains": 10, "framed-art": 12, "accent-sconces": 12, "vase": 16, "rug": 20, "floor-lamp": 30, "planter": 32, "cushions": 55,
     "basket": 60, "magazine-holder": 60, "bowl": 65, "candle-holders": 65, "pendant": 80}
BEHIND = W.BEHIND_FURNITURE


def f8(p, mode=None):
    im = Image.open(p)
    if mode:
        im = im.convert(mode)
    return np.asarray(im).astype(np.float32) / 255.0


def base_parts():
    U0 = f8(os.path.join(P1, "shell-furniture-v3.png"), "RGB")
    F = f8(os.path.join(P1, "fixed-furniture.png"))
    S = f8(os.path.join(P1, "fixed-furniture-shadow.png"), "L")
    shell = f8(os.path.join(P1, "shell-v3.png"), "RGB")
    behind0 = shell * S[..., None]
    return dict(U0=U0, behind0=behind0, F=F[..., :3], fa=F[..., 3])


def product(k, s=None):
    """(rgb, alpha, shadow) of one product, ungraded, from the saved 8-bit files. For items behind the furniture the alpha is the
    'free' alpha (before the furniture in front is taken out). Cushions: phase 1's cut of set s."""
    if k == "cushions":
        L = f8(os.path.join(P1, f"layers/cushions/set-{s}.png"))
        Sh = f8(os.path.join(P1, f"shadows/cushions/set-{s}.png"), "L")
        return L[..., :3], L[..., 3], Sh
    L = f8(os.path.join(W.WORK, "layers", f"{k}.png"))
    a = L[..., 3]
    fp = os.path.join(W.WORK, "layers", f"{k}-free-alpha.png")
    if k in BEHIND and os.path.exists(fp):
        a = f8(fp, "L")
    Sh = f8(os.path.join(W.WORK, "shadows", f"{k}.png"), "L")
    return L[..., :3], a, Sh


def compose(items, parts=None, cushion_set="B", keep_steps=False):
    """the ungraded composite of the base and the given products (in ORDER); returns U, and per step (U_k, region_k, eff_alpha_k)
    when keep_steps"""
    P = parts or base_parts()
    U, behind = P["U0"].copy(), P["behind0"].copy()
    fa = P["fa"]
    steps = []
    for k in ORDER:
        if k not in items:
            continue
        L, a, Sh = product(k, cushion_set)
        if k in BEHIND:
            a_eff = a * (1 - fa)
            # the item's region in the picture: where the furniture leaves any of it, or of its shadow, visible
            region = ((a > 0) | (Sh < 1)) & (fa < 1)
            nb = behind * Sh[..., None] * (1 - a[..., None]) + L * a[..., None]
            behind = np.where(region[..., None], nb, behind)
            new = behind * (1 - fa[..., None]) + P["F"] * fa[..., None]
        else:
            a_eff = a
            region = (a > 0) | (Sh < 1)
            new = U * Sh[..., None] * (1 - a[..., None]) + L * a[..., None]
            behind = np.where(region[..., None], new, behind)   # in front of nothing fixed: the scene behind is the scene
        U = np.where(region[..., None], new, U)
        if keep_steps:
            steps.append(dict(k=k, U=U.copy(), region=region, a_eff=a_eff, a=a, Sh=Sh, L=L))
    return (U, steps) if keep_steps else U


# ------------------------------------------------------------------------------------------------- the v3c grade
class Grade:
    def __init__(self):
        size = PW.work_size()
        self.g = PW.centre_gain(size)
        base_e = PW._expose(PW.load(os.path.join(P1, "shell-furniture-v3.png")), self.g)
        self.bp = float(np.percentile(cv2.cvtColor(base_e, cv2.COLOR_RGB2LAB)[..., 0], 0.5))
        self.stone = np.asarray(Image.open(os.path.join(P1, "masks/stone-wide.png"))) > 127
        self.fur_w = np.asarray(Image.open(os.path.join(P1, "fixed-furniture.png")))[..., 3].astype(np.float32) / 255
        sh_e = cv2.cvtColor(PW._expose(PW.load(os.path.join(P1, "shell-v3.png")), self.g), cv2.COLOR_RGB2LAB)
        toplit = self.stone & (sh_e[..., 0] > 85)
        self.h_top = float(np.degrees(np.arctan2(np.median(sh_e[..., 2][toplit]), np.median(sh_e[..., 1][toplit]))))
        self.cmax = 12.0 / np.sin(np.radians(self.h_top))

    def record(self):
        return dict(gain=round(self.g, 6), toe=dict(black_point_base_p005=round(self.bp, 4), target=12.5, fade_to_L=25.0, computed_on="shell-furniture-v3.png"),
                    slab=dict(mask="masks/stone-wide.png", h_top_deg=round(self.h_top, 4), chroma_max=round(float(self.cmax), 4),
                              share="stone x (1 - furniture alpha) x (1 - product alpha)"),
                    source="pilot_wm.py grade_v3c (phase 1), recomputed; base.png reproduced byte for byte")

    def __call__(self, U, prod_alpha=None):
        """U: float RGB 0-1 (ungraded); returns the graded 8-bit RGB"""
        e = PW._expose(np.clip(U, 0, 1).astype(np.float32), self.g)
        lab = cv2.cvtColor(e, cv2.COLOR_RGB2LAB)
        L = lab[..., 0]
        if not 11.0 <= self.bp <= 14.0:
            k = np.clip(1 - (L - self.bp) / max(25.0 - self.bp, 1e-3), 0, 1) ** 2
            lab[..., 0] = np.where(L < 25.0, L + (12.5 - self.bp) * k, L)
        wgt = np.where(self.stone, 1.0 - self.fur_w, 0.0).astype(np.float32)
        if prod_alpha is not None:
            wgt = wgt * (1.0 - prod_alpha.astype(np.float32))
        C = np.hypot(lab[..., 1], lab[..., 2])
        Cn = np.minimum(C, self.cmax)
        ca, sa = np.cos(np.radians(self.h_top)), np.sin(np.radians(self.h_top))
        lab[..., 1] = lab[..., 1] + (Cn * ca - lab[..., 1]) * wgt
        lab[..., 2] = lab[..., 2] + (Cn * sa - lab[..., 2]) * wgt
        e = np.clip(cv2.cvtColor(lab, cv2.COLOR_LAB2RGB), 0, 1).astype(np.float32)
        return (np.clip(e, 0, 1) * 255 + 0.5).astype(np.uint8)
