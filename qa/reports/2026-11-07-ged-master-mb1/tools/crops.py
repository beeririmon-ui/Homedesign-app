"""
qa-agent 2026-11-07: MB1 G-ED crops. Per product: the crop from the frame (box by eye on the full frame, 2736 x 1536) beside the reference
crop render-agent used (view only, session scratchpad master-refs/), at the same height. Writes overlays/<frame>-<n>-<product>.jpg and
data/boxes.json (the boxes, for the measurements). Usage: ~/.venvs/motion/bin/python -I crops.py
"""
import json
import os

from PIL import Image

REPO = "/home/user/homedesign-app"
B = os.path.join(REPO, "assets/renders/master/editorial-2026-11-07")
OUT = os.path.join(REPO, "qa/reports/2026-11-07-ged-master-mb1")
REF = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/master-refs/"
BOXES = {
    "nordic-MB-A": {
        "bedding": ((300, 860, 2500, 1480), "crop_bedding_natural.png"),
        "pillowcases": ((1480, 610, 2400, 940), "crop_pillow_natural.png"),
        "lumbar": ((1590, 710, 2040, 880), "crop_cushion_white.png"),
        "throw": ((940, 1140, 2520, 1536), "crop_throw_lightgray.png"),
        "bottle": ((2400, 560, 2580, 960), "crop_vaseD.png"),
        "candle-holders": ((2530, 720, 2720, 1000), "crop_candles.png"),
        "sconce-left": ((1370, 390, 1520, 540), "crop_sconce_wave.png"),
        "sconce-right": ((2446, 300, 2686, 510), "crop_sconce_wave.png"),
        "curtains": ((490, 0, 770, 1010), "crop_curtain_sfold.png"),
        "sill-vase": ((310, 560, 434, 740), "crop_claysvase.png"),
        "planter": ((746, 720, 946, 970), "crop_planter_seagrass.png"),
        "basket": ((646, 790, 820, 1010), "crop_basket.png"),
        "chair-cloth": ((0, 660, 400, 1190), None),
    },
    "warm-modern-MB-A": {
        "bedding": ((1120, 900, 2736, 1260), "crop_bedding_natural.png"),
        "pillowcases": ((1400, 640, 2650, 960), "crop_pillow_caramel.png"),
        "lumbar": ((1790, 770, 2294, 940), "crop_cushion_milktea.png"),
        "throw": ((940, 1110, 2736, 1536), "crop_muslin_pecan.png"),
        "sconce-left": ((1180, 410, 1334, 590), "crop_sconce_cone.png"),
        "sconce-right": ((2576, 414, 2734, 590), "crop_sconce_cone.png"),
        "candle-holders": ((1080, 746, 1240, 946), "crop_candles.png"),
        "bottle": ((1222, 600, 1334, 946), "crop_vaseD.png"),
        "floor-lamp": ((426, 220, 700, 1190), "crop_floorlamp.png"),
        "planter": ((600, 810, 914, 1150), "crop_planter_cement.png"),
        "sill-vase": ((106, 710, 214, 986), "crop_sillvase.png"),
        "basket": ((730, 946, 954, 1250), "crop_basket.png"),
        "curtains": ((310, 0, 540, 1220), "crop_curtain_sheer.png"),
    },
}
if __name__ == "__main__":
    json.dump({f: {k: v[0] for k, v in d.items()} for f, d in BOXES.items()}, open(os.path.join(OUT, "data", "boxes.json"), "w"), indent=1)
    for frame, d in BOXES.items():
        sub = "nordic" if frame.startswith("nordic") else "warm-modern"
        im = Image.open(os.path.join(B, sub, frame + ".png")).convert("RGB")
        for i, (name, (box, ref)) in enumerate(d.items()):
            c = im.crop(box)
            hh = 360
            tiles = [c.resize((max(1, int(c.width * hh / c.height)), hh))]
            if ref:
                r = Image.open(REF + ref).convert("RGB")
                tiles.append(r.resize((max(1, int(r.width * hh / r.height)), hh)))
            o = Image.new("RGB", (sum(t.width for t in tiles) + 12, hh), (40, 40, 40))
            x = 0
            for t in tiles:
                o.paste(t, (x, 0))
                x += t.width + 12
            o.save(os.path.join(OUT, "overlays", f"{frame}-{i:02d}-{name}.jpg"), quality=88)
    print("ok")
