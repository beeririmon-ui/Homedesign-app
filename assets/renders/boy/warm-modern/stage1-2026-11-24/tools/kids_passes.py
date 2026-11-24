#!/usr/bin/env python3
"""
kids_passes.py: the crop-edit passes of the kids' stage one (render-agent, 2026-11-24) and the products they make.
The order is the order of the sends: the lit pendant first (its glow is then in every later input, so the textiles carry it), then the
bed, the nest on the bed, the shelf and the desk. The girl's room takes the boy's family layers above the band and on the desk by code
(ב.6: the background is the same) and has its own two passes, the bed and the nest. Crop boxes are canvas px of the 2720 x 1530 canvas;
each crop goes to nano-banana-2 at 2K (kids_crop.py), so a placeholder is 2-4x larger in the model's input than in the full frame
(the kitchen's finding, 2026-11-20).
"""
# clay id -> slot key in framing_wm_kids.py
CLAY = {40: "roman-blind", 41: "pendant", 42: "framed-prints", 43: "framed-prints", 44: "framed-prints", 45: "framed-prints",
        46: "bookshelf", 47: "bookshelf", 48: "pen-cup", 49: "pen-cup", 50: "bookends", 51: "bookends", 52: "toy-cars", 53: "bedding",
        54: "pillow-lying", 55: "pillow-standing", 56: "bedspread", 57: "cushions-pair", 58: "soft-toy", 59: "toy-basket", 60: "toy-basket"}
FILLERS = {47, 49, 51, 60}
ART = {43, 45}

# product key -> (slot in the site, product id (card + option), z, clay ids, sku) per room
PRODUCTS = {
    "boy": {
        "roman-blind": ("roman-blind", "roman-blind-aliexpress-modern-beige-color-flat-868827-light-filter-136", 10, (40,), "868827 Light Filter, to 136"),
        "pendant": ("pendant", "ceiling-lights-cj-silk-pumpkin-lantern-30-warm-light", 80, (41,), "CJYD243199105EV"),
        "framed-prints": ("framed-prints", "framed-prints-cj-charcoal-flower-silhouette-set3-30x40-boy-type-c", 12, (42, 43, 44, 45), "CJJT261357805EV"),
        "bookshelf": ("bookshelf", "bookshelf-cj-natural-wood-ledge-pair-42-x2", 12, (46, 47), "CJYD215954401AZ (two pairs)"),
        "pen-cup": ("pen-cup", "desk-organizer-cj-walnut-beech-square-pen-cup-8x11-black-walnut", 46, (48, 49), "CJYD204195901AZ"),
        "bookends": ("bookends", "bookends-cj-black-walnut-l-bookend-pair", 46, (50, 51), "CJJT153259701AZ"),
        "toy-cars": ("toy-cars", "toy-cars-aliexpress-4pc-wooden-baby-car-754833-car", 46, (52,), "12000058783707673"),
        "bedding": ("bedding", "bedding-cj-stripe-cotton-single-set-light-brown-xs", 50, (53, 54), "CJJJJFCS00695-Light Brown-XS-Bed sheet"),
        "pillowcase": ("pillowcase", "pillowcases-cj-pure-linen-envelope-pair-48x74-rain-and-dew-hemp", 51, (55,), "CJYD223749801AZ"),
        "bedspread": ("bedspread", "bedspread-cj-waffle-gauze-fringe-150x200-deep-chestnut-brown", 52, (56,), "CJZW264585012LO"),
        "cushions-pair": ("cushions", "cushions-cj-corduroy-patchwork-reindeer-brown-45", 55, (57,), "CJZT189401911KP"),
        "soft-toy": ("soft-toy", "soft-toy-aliexpress-stuffed-bunny-cloth-dress-063285-bear", 57, (58,), "12000050510684712"),
        "toy-basket": ("toy-basket", "basket-cj-jute-rope-cylinder-large", 60, (59, 60), "CJYD186026903CX"),
    },
    "girl": {
        "roman-blind": ("roman-blind", "roman-blind-aliexpress-modern-beige-color-flat-868827-light-filter-136", 10, (40,), "868827 Light Filter, to 136"),
        "pendant": ("pendant", "ceiling-lights-cj-silk-pumpkin-lantern-30-warm-light", 80, (41,), "CJYD243199105EV"),
        "framed-prints": ("framed-prints", "framed-prints-cj-flower-cutout-set-30x40-type-a", 12, (42, 43, 44, 45), "CJJT261357801AZ"),
        "bookshelf": ("bookshelf", "bookshelf-cj-natural-wood-ledge-pair-42-x2", 12, (46, 47), "CJYD215954401AZ (two pairs)"),
        "pen-cup": ("pen-cup", "desk-organizer-cj-walnut-beech-square-pen-cup-8x11-beech", 46, (48, 49), "CJYD204195902BY"),
        "bookends": ("bookends", "bookends-cj-black-walnut-l-bookend-pair", 46, (50, 51), "CJJT153259701AZ"),
        "bedding": ("bedding", "bedding-cj-muslin-cotton-duvet-dune-229x173", 50, (53,), "CJCS281437509IR (open: real-unit photo)"),
        "pillowcase": ("pillowcase", "pillowcases-cj-washed-linen-double-ruffle-48x74-primary-color", 51, (54, 55), "CJJT165654102BY"),
        "bedspread": ("bedspread", "bedspread-cj-waffle-gauze-fringe-150x200-linen-brown", 52, (56,), "CJZW264585004DW"),
        "cushions-pair": ("cushions", "cushions-cj-dusty-pink-corduroy-patchwork-45", 55, (57,), "CJKD172412101AZ"),
        "soft-toy": ("soft-toy", "soft-toy-aliexpress-stuffed-bunny-cloth-dress-063285-girl-35", 57, (58,), "12000046795670253"),
        "toy-basket": ("toy-basket", "basket-cj-cotton-rope-white-l", 60, (59, 60), "CJJT167870901AZ"),
    },
}
# the sample slot (ד.4): colour-only variants of one listing, made in code (all six SKU photos are one scene recoloured)
VARIANTS = {
    "boy": {"V1": ("bedspread-cj-waffle-gauze-fringe-150x200-deep-chestnut-brown", "spread-chestnut"),
            "V2": ("bedspread-cj-waffle-gauze-fringe-150x200-coffee", "spread-coffee"),
            "V3": ("bedspread-cj-waffle-gauze-fringe-150x200-green", "spread-green")},
    "girl": {"V1": ("bedspread-cj-waffle-gauze-fringe-150x200-linen-brown", "spread-linen"),
             "V2": ("bedspread-cj-waffle-gauze-fringe-150x200-deep-chestnut-brown", "spread-chestnut"),
             "V3": ("bedspread-cj-waffle-gauze-fringe-150x200-pink", "spread-pink")},
}
VARIANT_SKU = {"spread-chestnut": "CJZW264585012LO", "spread-coffee": "CJZW264585008HS", "spread-green": "CJZW264585024XC",
               "spread-linen": "CJZW264585004DW", "spread-pink": "CJZW264585020TG"}

# pass -> kid, products, crop box (x0, y0, x1, y1 canvas px; aspect a standard ratio), lamps lit in it, board, aspect
PASSES = {
    "PB3-window": dict(kid="boy", products=["roman-blind", "pendant"], box=(0, 0, 1040, 585), aspect="16:9", lamps=["pendant"],
                       board="PB3-window.jpg"),
    "PB1-bed": dict(kid="boy", products=["bedding", "pillowcase", "bedspread", "toy-basket"], box=(300, 597, 1544, 1530), aspect="4:3",
                    lamps=[], board="PB1-bed.jpg", clay="K-boy-bed"),
    "PB2-nest": dict(kid="boy", products=["cushions-pair", "soft-toy"], box=(400, 560, 1180, 1080), aspect="3:2", lamps=[], board="PB2-nest.jpg"),
    "PB4-shelf": dict(kid="boy", products=["bookshelf", "framed-prints"], box=(1080, 110, 1590, 620), aspect="1:1", lamps=[],
                      board="PB4-shelf.jpg", only_ids=(44, 45, 46, 47)),
    "PB5-desk": dict(kid="boy", products=["framed-prints", "bookends", "toy-cars", "pen-cup"], box=(1690, 50, 2580, 940), aspect="1:1",
                     lamps=[], board="PB5-desk.jpg", only_ids=(42, 43, 48, 49, 50, 51, 52)),
    "GB1-bed": dict(kid="girl", products=["bedding", "pillowcase", "bedspread", "toy-basket"], box=(300, 597, 1544, 1530), aspect="4:3",
                    lamps=[], board="GB1-bed.jpg", clay="K-girl-bed", canvas_from="GB1b-basket",
                    throw_L_frac=None),     # Linen Brown on Dune: the lit top of the throw is as light as the shaded duvet; the hue alone parts them
    "GB2-nest": dict(kid="girl", products=["cushions-pair", "soft-toy"], box=(400, 560, 1180, 1080), aspect="3:2", lamps=[], board="GB2-nest.jpg"),
    # after QA (2026-11-24): K-B1, the cars redrawn on the boy's canvas without them; K-B2, the set's stripes redrawn on the boy's
    # canvas as it is (no placeholder: only the pattern changes, the bedding layer keeps its alpha and takes the new pixels)
    "PB5b-cars": dict(kid="boy", products=["toy-cars"], box=(1740, 720, 2060, 1040), aspect="1:1", lamps=[], board="PB5b-cars.jpg"),
    "PB1b-stripes": dict(kid="boy", products=["bedding"], box=(300, 597, 1544, 1530), aspect="4:3", lamps=[], board="PB1b-stripes.jpg",
                         no_placeholder=True),
    # the girl's basket again, on GB1's own edit (2026-11-24, later): GB1 drew a squat basket (about 40 x 22 cm, side cut-out handles)
    # where the card and its photo are a tall 40 x 45 cylinder with two long rope loop handles; the clay's basket is pasted over GB1's
    # edit (it covers the squat one) and only the basket is redrawn; GB1 is then cut from this canvas
    "GB1b-basket": dict(kid="girl", products=["toy-basket"], box=(550, 890, 1190, 1530), aspect="1:1", lamps=[], board="GB1b-basket.jpg",
                        clay="K-girl-bed", base_pass="GB1-bed"),
}
# the girl's layers made by code from the boy's (ב.6): above the band and on the desk
GIRL_FROM_BOY = ["roman-blind", "pendant", "framed-prints", "bookshelf", "pen-cup", "bookends"]


def pass_ids(p):
    P = PASSES[p]
    ids = []
    for pr in P["products"]:
        ids += list(PRODUCTS[P["kid"]][pr][3])
    if "only_ids" in P:
        ids = [i for i in ids if i in P["only_ids"]]
    return tuple(sorted(set(ids)))
