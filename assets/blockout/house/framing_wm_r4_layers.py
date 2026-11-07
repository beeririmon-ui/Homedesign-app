#!/usr/bin/env python3
"""
framing_wm_r4_layers.py: the warm-modern clay r4 (framing_wm_r4.py: WMC1-WMC10, house plan 1.3.5) rendered as LAYER clays for the
tool pilot phase 1 (briefs/render-warm-modern-pilot-phase1-2026-11-07.md), render-agent, 2026-11-07. 0 var2 tokens.
Same scene, camera, lens, light and samples as r4; only render visibility changes:
  --layer shell   the room shell alone: walls, glazing, bench, rounded corner, ceiling band and track slot, floor, skirting
                  (the fixed furniture 1-3 and every product proxy hidden)
  Both layers: the living lamps' light objects off (daylight + sky only, ARC2's window light); lamp halos are product light layers.
  --layer furn    the shell + the fixed furniture (sofa 1, coffee table 2, armchair 3), every product proxy hidden
  furn also carries the Bible's furniture changes on the same footprints (bible_furniture(): table top 5 cm on two oval drums, sofa on a
  recessed 6 cm plinth); --nordic-furniture keeps the r4 clay furniture as it is.
The ratio furn / shell outside the furniture is the furniture's shadow and contact occlusion on the shell (the code shadow layer of step 3).
Outputs: framing/warm-modern-r4/layers/<layer>/M0.png (+ selfcheck), index pass in the scratchpad wm-r4-<layer>-idx/.
  blender -b -P framing_wm_r4_layers.py -- --layer shell --frames M0 --res 3840 --samples 16
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

argv0 = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
LAYER = argv0[argv0.index("--layer") + 1] if "--layer" in argv0 else "shell"
assert LAYER in ("shell", "furn"), LAYER
argv = [a for i, a in enumerate(argv0) if a not in ("--layer", "--nordic-furniture") and (i == 0 or argv0[i - 1] != "--layer")]

import bpy  # noqa: E402
import framing_wm_r4 as W  # noqa: E402  (applies all r4 monkeypatches on import)

FURNITURE = {1, 2, 3}
ARCH_KEEP = {520, 521, 522}                      # living/window-bench, living/rounded-corner, living/curtain-track
PROXY = set(range(30, 61)) | {k for k in range(440, 600) if k not in ARCH_KEEP}
HIDE = PROXY | (FURNITURE if LAYER == "shell" else set())

OUT = os.path.join(W.OUT, "layers", LAYER)
W.IDX_DIR = os.path.join(W.SCRATCH, f"wm-r4-{LAYER}-idx")
W.r4.EXR_DIR = os.path.join(W.SCRATCH, f"wm-r4-{LAYER}-exr")

_render_prev = W.fr.render
BIBLE_FURN = []


def bible_furniture():
    """Bible warm-modern 1.0 'fixed furniture' on the r4 clay's footprints (render-agent's reading, for the designer): the coffee table's
    top 5 cm (Z 0.33-0.38, was 3) on two oval drum bases recessed 12 cm from the ends (32 x 40, centres X -0.22 / 0.62, Y 1.72), the four
    legs gone; the sofa on a recessed plinth 6 cm high (inset 4 cm), its body carried down from Z 0.15 to 0.06, the four oak legs gone
    (seat height 44 unchanged). The armchair keeps the Nordic geometry (WM-F1). Same pass indices (1 sofa, 2 table), clay materials."""
    import math
    if BIBLE_FURN:
        return
    wood, sofa = bpy.data.materials.get("wood"), bpy.data.materials.get("sofa")
    for ob in bpy.data.objects:
        if ob.name.startswith(("table_leg", "sofa_leg")):
            ob.hide_render = True
            BIBLE_FURN.append("hid " + ob.name)
    top = bpy.data.objects["table_top"]
    t2 = top.copy()
    t2.data = top.data.copy()
    t2.name = "table_top_wm5"
    t2.location.z -= 0.02
    (top.users_collection[0] if top.users_collection else bpy.context.scene.collection).objects.link(t2)
    BIBLE_FURN.append("table top 5 cm")
    for i, cx in enumerate((-0.22, 0.62)):
        pts = [(cx + 0.16 * math.cos(2 * math.pi * k / 40), 1.72 + 0.20 * math.sin(2 * math.pi * k / 40)) for k in range(40)]
        W.prism(f"table_drum_wm{i}", pts, 0.0, 0.33, wood, 2, coll="furniture")
    BIBLE_FURN.append("two oval drums 32 x 40, Z 0-0.33")
    W.prism("sofa_body_wm", [(-0.9, 0.03), (1.3, 0.03), (1.3, 0.95), (-0.9, 0.95)], 0.06, 0.1505, sofa, 1, coll="furniture")
    W.prism("sofa_plinth_wm", [(-0.86, 0.07), (1.26, 0.07), (1.26, 0.91), (-0.86, 0.91)], 0.0, 0.06, wood, 1, coll="furniture")
    BIBLE_FURN.append("sofa body down to 0.06 on a plinth 6 cm, inset 4 cm")


HIDDEN = []
LAMPS_OFF = []


def render_layer(path, tmp, res, samples, ao=0.30, passes=True, exposure=None):
    HIDDEN.clear()
    LAMPS_OFF.clear()
    for ob in bpy.data.objects:
        if ob.type != "LIGHT" and getattr(ob, "pass_index", 0) in HIDE:
            ob.hide_render = True
            HIDDEN.append(ob.name)
        elif ob.type == "LIGHT" and ob.name.startswith("lv_") and not ob.hide_render:
            ob.hide_render = True                    # the living lamps (sconces lv_cube_L0/1, pendant lv_pend_L5): their light is a
            LAMPS_OFF.append(ob.name)                # product light layer (skeleton spec), not part of the shell or furniture layers
    if LAYER == "furn" and "--nordic-furniture" not in argv0:
        bible_furniture()
    print(f"LAYER {LAYER}: bible furniture {BIBLE_FURN}")
    print(f"LAYER {LAYER}: hid {len(HIDDEN)} objects (pass indices {sorted({bpy.data.objects[n].pass_index for n in HIDDEN})}); lamps off {LAMPS_OFF}")
    return _render_prev(path, tmp, res, samples, ao=ao, passes=passes, exposure=exposure)


W.fr.render = render_layer

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    a = list(argv)
    if "--out" not in a:
        a += ["--out", OUT]
    if "--plan" not in a:
        a += ["--plan", os.path.join(W.OUT, "plan.json")]
    W.main(a)
