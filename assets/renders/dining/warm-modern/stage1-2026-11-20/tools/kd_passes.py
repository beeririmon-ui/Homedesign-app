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
    "B-window-front": dict(frame="D1", ids=(57, 60), lamps=(),            # r1: the curtain and the bench pad (the vase: Bc-corner)
                           sku=["ceda9a99_Sff7ee183e2d44cff966ac2016190b3d8k.jpg", "e29ed3e3_259ba98c-4245-4ef5-8673-64b9f72c09c8_trans.jpeg",
                                "2dc8f07c_Sebb153f4647e4b5bb21ca45afce0f33cf.jpg"]),
    "D-right": dict(frame="D1", ids=(61, 62, 63, 64, 65, 66), lamps=(),
                    sku=["aa7e275e_5072100e-21aa-4730-b534-a1a143a2b694.jpg", "98bd7dbe_812c1dd7-138b-4deb-86e8-f1e2596ee0b0.jpg",
                         "ab7efc82_87c036c4-e87a-4545-837a-23106ff0d858.jpg", "30e3164f_S8900e3282acf4cec8c9222324807f215S.jpg",
                         "da7ade71_1622092597344.jpg"]),
    "E-left": dict(frame="D2o", ids=(67, 68, 69, 71, 72), lamps=(),        # r1: frame, jar, tray, dispenser (sconce, board: Ec)
                   sku=["bcc5256e_f5641c65-29f9-445a-93bd-9c5a4befbbb3_trans.jpeg", "66e3e3e4_51ffdc65-6515-4001-b23f-f85a833b3ba6_trans.jpeg",
                        "743cc564_1712921280555.jpg", "433f5380_13d89976-9fa2-48db-8b57-9d585a7b95bd_trans.jpeg",
                        "b0931b43_S7ff4c16b3f1646ea87189b9f37253118c.png"]),
    "F-niche": dict(frame="D2o", ids=(74, 75, 76, 77), lamps=(),
                    sku=["844a4993_Sc506bfed69284946abe47d6311b90f9cn.jpg", "e26bd334_f6392289455d8f98df8004940562_import.webp",
                         "0c4b09cc_S99aa2c8b1da34791b39d993dacc907b6J.jpg"]),
    # crop edits (kd_crop.py; resumed session): D-right r1 rejected, and the misplaced products of E-left r1 and B r1
    "Dc-right": dict(frame="D1", ids=(61, 62, 63, 64, 65, 66), lamps=(), sku=["aa7e275e_5072100e-21aa-4730-b534-a1a143a2b694.jpg",
                     "98bd7dbe_812c1dd7-138b-4deb-86e8-f1e2596ee0b0.jpg", "ab7efc82_87c036c4-e87a-4545-837a-23106ff0d858.jpg",
                     "30e3164f_S8900e3282acf4cec8c9222324807f215S.jpg", "da7ade71_1622092597344.jpg"]),
    "Ec-sconce-board": dict(frame="D2o", ids=(70, 73), lamps=(70,), sku=["66e3e3e4_51ffdc65-6515-4001-b23f-f85a833b3ba6_trans.jpeg",
                            "b0931b43_S7ff4c16b3f1646ea87189b9f37253118c.png"]),
    "Bc-corner": dict(frame="D1", ids=(58, 59), lamps=(), sku=["e29ed3e3_259ba98c-4245-4ef5-8673-64b9f72c09c8_trans.jpeg"]),
    "V2-pendant": dict(frame="D1", ids=(50,), lamps=(50,), variant=True, sku=["ad70ecd7_c4df701a-6ab2-46a2-a97e-1ca25b5f52dd_trans.jpeg"]),
    "V3-pendant": dict(frame="D1", ids=(50,), lamps=(50,), variant=True, sku=["99604c5b_57063a71-d5ba-4fe6-bdc0-d84c3e5e8aee.jpg"]),  # a crop edit of D1-defaults
    # 10.9 (2026-11-24): stage one's D2 (yaw -91) is "D2o" (the passes above cut there); the new D2 (yaw -86) is composed in code
    # (tools/kd_d2stage.py) and gets these crop edits on top of it
    "G-niche-fill": dict(frame="D2", ids=(65, 77), lamps=(), sku=["30e3164f_S8900e3282acf4cec8c9222324807f215S.jpg", "0c4b09cc_S99aa2c8b1da34791b39d993dacc907b6J.jpg"]),
    # H r1: the frame kept. Rejected: the serving boards (drawn about 1.5x their size and 120-250 px right, standing on the hob, round a
    # caramel board the model moved there too) and the vessel (1.3x wide, 1.2x tall; the branches spread to u 0.53, over the third mug).
    # So only 67 is cut from it; Hb-boards (the boards' whole outline, the 280363 board left out) and Hv-vessel are crops of their own
    "H-islands": dict(frame="D2", ids=(67, 68), lamps=(), sku=["fc079e4c_8474963a-3ecf-4139-b6fa-3f9b0a877704.jpg",
                      "76dd96fd_7ae8b455-7b8a-4788-9196-1f7196679bb8.png", "0b6b66da_2930584804988.png"]),
    "Hv-vessel": dict(frame="D2", ids=(78, 80), lamps=(), sku=["fc079e4c_8474963a-3ecf-4139-b6fa-3f9b0a877704.jpg"]),
    "Hb-boards": dict(frame="D2", ids=(79,), lamps=(), sku=["76dd96fd_7ae8b455-7b8a-4788-9196-1f7196679bb8.png", "0b6b66da_2930584804988.png"]),
}
# 10.9: retired layers (kept on disk for the record, never composed or projected)
RETIRED = {("D2o", "framed-art"): "10.9 row 3: the 64 x 49 frame (H-islands) replaces the 44 x 34",
           ("D2o", "open-shelf-ceramics"): "10.9 row 3: the moon jar moves to Y 1.735 (tools/kd_d2stage.py jar)",
           ("D2o", "tea-towel"): "10.9 row 6: the set of 2 on the oven handle (G-niche-fill)",
           ("D1", "tableware-set"): "10.9 row 2: the set moves from the right shelf into the niche (G-niche-fill)",
           ("D1", "dining-pendant/pendant-cj-silk-pumpkin-lantern-50cm-warm-light"): "10.9.6 KD-L3: V2 leaves the wheel (V1 + V3)"}
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
    67: ("framed-art", "framed-art-aliexpress-misty-landscape-386242-work-05-40x50", 12),       # 10.9 (was -05-30x40, stage one)
    69: ("open-shelf-ceramics", "vase-cj-matte-moon-jar-white-styleg", 14),
    70: ("kitchen-sconce", "wall-sconce-cj-travertine-dome-15-alt-warm-light", 16),
    71: ("sink-set", "key-tray-cj-black-walnut-tray-20x13", 18),
    72: ("sink-set", "soap-dispenser-cj-sand-ribbed-ceramic-pump-bottle-striped", 18),
    73: ("cutting-boards", "cutting-boards-aliexpress-2pcs-1pc-wooden-cutting-280363-l", 16),
    74: ("paper-towel-holder", "paper-towel-holder-aliexpress-solid-wood-slotted-paper-towel-stand-style-c", 18),
    76: ("canisters", "zendrop-2814530-white", 14),
    77: ("tea-towel", "tea-towel-aliexpress-pure-linen-towel-38x55-caramel-2pc", 22),          # 10.9 (was -caramel, 1 pc)
    78: ("counter-vessel", "vase-cj-white-textured-jar-medium-bottle", 18),                    # 10.9 row 4, a new slot (KD-17)
    79: ("serving-boards", "cutting-boards-cj-black-walnut-paddle-pair-39-34-b-spliced-39x18-f-34x19", 15),   # 10.9 row 5 (KD-17)
}
FILLERS = {51: 50, 54: 53, 56: 55, 59: 58, 64: 63, 68: 67, 75: 74, 80: 78}
VARIANTS = {"V2-pendant": ("dining-pendant", "pendant-cj-silk-pumpkin-lantern-50cm-warm-light"),
            "V3-pendant": ("dining-pendant", "pendant-cj-scalloped-pleated-bell-45")}
SKUS = {50: "CJYD304604003CX", 52: "12000044133070215", 53: "CJYD234431803CX", 55: "12000057351444960", 57: "12000059196236244",
        58: "CJYD219411603CX", 60: "12000045641914363", 61: None, 62: "CJYD289918002BY", 63: None, 65: "12000057617920292",
        66: "CJHS114636401AZ", 67: "12000038963447944", 69: "CJJT276473907GT", 70: "CJYD219925401AZ", 71: "CJJJJTJT41624-Brown",
        72: "CJYD301460604DW", 73: "12000059298718531", 74: "12000060575834324", 76: None, 77: "12000059652536006",
        78: "CJYD219407502BY", 79: "CJJJCFCJ01542-Section B splicing-39x18.5 + CJJJCFCJ01542-Section F-34x19.5"}


def owner(k):
    return FILLERS.get(k, k)
