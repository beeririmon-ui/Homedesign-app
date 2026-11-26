"""FB16 room table: the latest manifest (fb15 where it exists), the clay, the plate kind, the targets (spec section 2)"""
import os
HERE = os.path.dirname(os.path.abspath(__file__))
R = "/home/user/homedesign-app/assets/renders"
CL = "/home/user/homedesign-app/assets/blockout/house/framing"
WING = dict(L=75.0, Lr=(72, 78), b=8.0, br=(7, 9), a=2.0)
ROOMS16 = {
    "W0": dict(manifest="work/warm-modern/stage1-2026-11-20/layers/manifest-fb15.json", finish="work/warm-modern/stage1-2026-11-20/w0-defaults-fb15-finish.png",
               clay=f"{CL}/wm-work-2026-11-20/W0-plate", lock=f"{CL}/wm-work-2026-11-20/lock-target.json", legend=f"{CL}/wm-work-2026-11-20/selfcheck.json",
               outside="west", glow=True, t=WING, az_off=0.0),
    "MB0": dict(manifest="master/warm-modern/stage1-2026-11-17/layers/manifest-fb15.json", finish="master/warm-modern/stage1-2026-11-17/mb0-defaults-fb15-finish.png",
                clay=f"{CL}/wm-master-2026-11-17/MB0-plate", lock=f"{CL}/wm-master-2026-11-17/lock-target.json", legend=f"{CL}/wm-master-2026-11-17/selfcheck.json",
                outside="west", glow=True, t=WING, az_off=14.0),
    "MB1": dict(manifest="master/warm-modern/mb1-2026-11-19/layers/manifest-fb15.json", finish="master/warm-modern/mb1-2026-11-19/mb1-defaults-fb15-finish.png",
                clay=f"{R}/master/warm-modern/mb1-2026-11-19/clay/MB1-plate", lock=f"{R}/master/warm-modern/mb1-2026-11-19/clay/selfcheck.json",
                legend=f"{R}/master/warm-modern/mb1-2026-11-19/clay/selfcheck.json", outside="west", emit_lo=76.0, glow=True, t=WING, az_off=20.0),
    "K-boy": dict(manifest="boy/warm-modern/stage1-2026-11-24/manifest-fb15.json", finish="boy/warm-modern/stage1-2026-11-24/K-boy-defaults-fb15-finish.png",
                  clay=f"{CL}/wm-kids-2026-11-24/K-boy-plate", lock=f"{CL}/wm-kids-2026-11-24/boy-lock-target.json", legend=f"{CL}/wm-kids-2026-11-24/selfcheck.json",
                  outside="west", glow=True, t=WING, az_off=-12.0),
    "K-girl": dict(manifest="girl/warm-modern/stage1-2026-11-24/manifest-g1-fb15.json", finish="girl/warm-modern/stage1-2026-11-24/K-girl-defaults-g1-fb15-finish.png",
                   clay=f"{CL}/wm-kids-2026-11-24/K-girl-plate", lock=f"{CL}/wm-kids-2026-11-24/girl-lock-target.json", legend=f"{CL}/wm-kids-2026-11-24/selfcheck.json",
                   outside="west", glow=True, t=WING, az_off=-30.0),
    "D1": dict(manifest="dining/warm-modern/stage1-2026-11-20/manifest-fb15.json", finish="dining/warm-modern/stage1-2026-11-20/D1-defaults-fb15-finish.png",
               clay=f"{CL}/wm-dining-2026-11-20/D1-plate", lock=f"{CL}/wm-dining-2026-11-20/D1-lock-target.json", legend=f"{CL}/wm-dining-2026-11-20/selfcheck.json",
               outside="north", glow=True, t=dict(L=76.5, Lr=(74, 79), b=6.5, br=(5, 8), a=1.5), lamps=["kitchen-sconce"], az_off=0.0),
    "D2": dict(manifest="dining/warm-modern/stage1-2026-11-20/manifest-fb15.json", finish="dining/warm-modern/stage1-2026-11-20/D2-defaults-fb15-finish.png",
               clay=f"{CL}/wm-dining-2026-11-24/D2-plate", lock=f"{CL}/wm-dining-2026-11-24/D2-lock-target.json", legend=f"{CL}/wm-dining-2026-11-24/selfcheck.json",
               outside=None, glow=False, t=dict(L=76.5, Lr=(74, 79), b=6.5, br=(5, 8), a=1.5), lamps=["kitchen-sconce"]),
    "B1": dict(manifest="bath/warm-modern/b1-2026-11-19/layers/manifest-fb15.json", finish="bath/warm-modern/b1-2026-11-19/b1-defaults-fb15-finish.png",
               clay=f"{CL}/wm-bath-b1-2026-11-19/B1-plate", lock=f"{CL}/wm-bath-b1-2026-11-19/lock-target.json", legend=f"{CL}/wm-bath-b1-2026-11-19/selfcheck.json",
               outside=None, glow="fluted", t=dict(L=75.0, Lr=(72, 78), b=7.0, br=(6, 8), a=1.5)),
    "B2": dict(manifest="bath/warm-modern/stage1-2026-11-17/layers/manifest.json", finish="bath/warm-modern/stage1-2026-11-17/b2-defaults-fb13prep.png",
               clay=f"{CL}/wm-bath-2026-11-17/B2-plate", lock=f"{CL}/wm-bath-2026-11-17/lock-target.json", legend=f"{CL}/wm-bath-2026-11-17/selfcheck.json",
               outside=None, glow=False, t=dict(L=75.0, Lr=(72, 78), b=7.0, br=(6, 8), a=1.5)),
    "HT2": dict(manifest="hall/warm-modern/hall-products-2026-11-19/layers/manifest.json", finish="hall/warm-modern/hall-products-2026-11-19/ht2-products-fb13prep.png",
                clay=f"{CL}/wm-hall-2026-11-18/HT", lock=os.path.join(HERE, "HT-lock.json"), legend=f"{CL}/wm-hall-2026-11-18/clay-meta.json", frame="HT",
                plaster_ids=[11, 12, 13, 17], window_wall_ids=[32], outside_ids=[0], frame_ids=[39], az_off=8.0,
                outside="west-hall", glow=False, t=dict(L=69.5, Lr=(67, 72), b=8.0, br=(7, 9), a=2.0)),
    "HDx2": dict(manifest="hall/warm-modern/hall-products-2026-11-19/hdx2/manifest.json", finish="hall/warm-modern/hall-products-2026-11-19/hdx2-products-fb13prep.png",
                 clay=f"{CL}/wm-hall-2026-11-18/HDx", lock=os.path.join(HERE, "HDx-lock.json"), legend=f"{CL}/wm-hall-2026-11-18/clay-meta.json", frame="HDx",
                 plaster_ids=[11, 12, 13, 17], window_wall_ids=[32], outside_ids=[0], frame_ids=[39], az_off=0.0,
                 outside="living", glow=False, t=dict(L=69.5, Lr=(67, 72), b=8.0, br=(7, 9), a=2.0)),
}
BLACK = (11.0, 12.0)
