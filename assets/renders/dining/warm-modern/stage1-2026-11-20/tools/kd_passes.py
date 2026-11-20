#!/usr/bin/env python3
"""
kd_passes.py: the mask-edit passes of stage one (render-agent, 2026-11-20): which clay ids each pass turns into products, in which frame,
the SKU photos of its reference board (scratchpad only: supplier photos never enter the repo), the slot, product id, z (data/slots/
dining-room.json 0.2.3) and the lamps lit. The plan of 6.2 with one change: D1-B (window and corner) and D1-C (the bench pad) are one
pass here (three simple products, far apart; 400 saved toward a retry).
"""
PASSES = {
    "A-table": dict(frame="D1", ids=(50, 51, 52, 53, 54, 55, 56), lamps=(50,),
                    sku=["db2b0521_6d1ee6b1-34a5-4686-97e6-19dca8ec7cf0_trans.jpeg", "bde10391_S0cf60eb6e8634640a5a28fe5c5794426P.jpg",
                         "5cb24e35_d3e30ddb-9574-480e-9296-8996be45334c_trans.jpeg", "9a0b98cc_S933d194167a24cfa9480d1d58b8cb6252.jpg"]),
    "B-window-front": dict(frame="D1", ids=(57, 58, 59, 60), lamps=(),
                           sku=["ceda9a99_Sff7ee183e2d44cff966ac2016190b3d8k.jpg", "e29ed3e3_259ba98c-4245-4ef5-8673-64b9f72c09c8_trans.jpeg",
                                "2dc8f07c_Sebb153f4647e4b5bb21ca45afce0f33cf.jpg"]),
    "D-right": dict(frame="D1", ids=(61, 62, 63, 64, 65, 66), lamps=(),
                    sku=["aa7e275e_5072100e-21aa-4730-b534-a1a143a2b694.jpg", "98bd7dbe_812c1dd7-138b-4deb-86e8-f1e2596ee0b0.jpg",
                         "ab7efc82_87c036c4-e87a-4545-837a-23106ff0d858.jpg", "30e3164f_S8900e3282acf4cec8c9222324807f215S.jpg",
                         "da7ade71_1622092597344.jpg"]),
    "E-left": dict(frame="D2", ids=(67, 68, 69, 70, 71, 72, 73), lamps=(70,),
                   sku=["bcc5256e_f5641c65-29f9-445a-93bd-9c5a4befbbb3_trans.jpeg", "66e3e3e4_51ffdc65-6515-4001-b23f-f85a833b3ba6_trans.jpeg",
                        "743cc564_1712921280555.jpg", "433f5380_13d89976-9fa2-48db-8b57-9d585a7b95bd_trans.jpeg",
                        "b0931b43_S7ff4c16b3f1646ea87189b9f37253118c.png"]),
    "F-niche": dict(frame="D2", ids=(74, 75, 76, 77), lamps=(),
                    sku=["844a4993_Sc506bfed69284946abe47d6311b90f9cn.jpg", "e26bd334_f6392289455d8f98df8004940562_import.webp",
                         "0c4b09cc_S99aa2c8b1da34791b39d993dacc907b6J.jpg"]),
    "V2-pendant": dict(frame="D1", ids=(50,), lamps=(50,), variant=True, sku=["ad70ecd7_c4df701a-6ab2-46a2-a97e-1ca25b5f52dd_trans.jpeg"]),
    "V3-pendant": dict(frame="D1", ids=(50,), lamps=(50,), variant=True, sku=["99604c5b_57063a71-d5ba-4fe6-bdc0-d84c3e5e8aee.jpg"]),
}
# clay id -> (slot, product id (card + SKU option), z, layer name suffix); fillers carry their product's id
PRODUCTS = {
    50: ("dining-pendant", "pendant-cj-silk-ribbed-pumpkin-40-50cm-warm-light", 80),
    52: ("table-runner", "table-runner-aliexpress-french-linen-stonewash-40x140-caramel", 52),
    53: ("centerpiece-vase", "nightstand-vase-cj-unglazed-white-amphora-26-type-c", 56),
    55: ("candle-holders", "candle-holders-aliexpress-matte-black-iron-pillar-set2", 56),
    57: ("curtains", "curtains-aliexpress-linen-blend-s-fold-180502", 10),
    58: ("floor-vase", "pool-cj-wabi-sabi-floor-vase-white", 30),
    60: ("bench-pad", "bench-pad-aliexpress-linen-look-box-cushion-130x35x5-khaki", 72),
    61: ("condiment-set", "condiment-set-cj-rubberwood-mill-pair-6in", 18),
    62: ("condiment-set", "condiment-set-cj-kiln-stoneware-oil-cruet-trio-kiln-baked-white", 18),
    63: ("bowl", "bowl-cj-glutinous-white-belly-bowl-21", 20),
    65: ("tableware-set", "tableware-set-aliexpress-kiln-corrugated-stoneware-set-300525", 14),
    66: ("mug-set", "mug-set-cj-sandy-stoneware-mug-glazed-rim-set3-light-brown", 14),
    67: ("framed-art", "framed-art-aliexpress-misty-landscape-386242-work-05-30x40", 12),
    69: ("open-shelf-ceramics", "vase-cj-matte-moon-jar-white-styleg", 14),
    70: ("kitchen-sconce", "wall-sconce-cj-travertine-dome-15-alt-warm-light", 16),
    71: ("sink-set", "key-tray-cj-black-walnut-tray-20x13", 18),
    72: ("sink-set", "soap-dispenser-cj-sand-ribbed-ceramic-pump-bottle-striped", 18),
    73: ("cutting-boards", "cutting-boards-aliexpress-2pcs-1pc-wooden-cutting-280363-l", 16),
    74: ("paper-towel-holder", "paper-towel-holder-aliexpress-solid-wood-slotted-paper-towel-stand-style-c", 18),
    76: ("canisters", "zendrop-2814530-white", 14),
    77: ("tea-towel", "tea-towel-aliexpress-pure-linen-towel-38x55-caramel", 22),
}
FILLERS = {51: 50, 54: 53, 56: 55, 59: 58, 64: 63, 68: 67, 75: 74}
VARIANTS = {"V2-pendant": ("dining-pendant", "pendant-cj-silk-pumpkin-lantern-50cm-warm-light"),
            "V3-pendant": ("dining-pendant", "pendant-cj-scalloped-pleated-bell-45")}
SKUS = {50: "CJYD304604003CX", 52: "12000044133070215", 53: "CJYD234431803CX", 55: "12000057351444960", 57: "12000059196236244",
        58: "CJYD219411603CX", 60: "12000045641914363", 61: None, 62: "CJYD289918002BY", 63: None, 65: "12000057617920292",
        66: "CJHS114636401AZ", 67: "12000038963447935", 69: "CJJT276473907GT", 70: "CJYD219925401AZ", 71: "CJJJJTJT41624-Brown",
        72: "CJYD301460604DW", 73: "12000059298718531", 74: "12000060575834324", 76: None, 77: "12000059652536005"}


def owner(k):
    return FILLERS.get(k, k)
