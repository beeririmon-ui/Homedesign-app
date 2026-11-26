#!/usr/bin/env python3
"""The FB20 studio standard as prompts: one studio suffix for every variant, the product text per variant."""
import json
STUDIO = ("Shot on a seamless warm off-white paper backdrop that sweeps from wall to floor in one even very light warm off-white tone (about #F0E7DB, neither yellow nor grey), "
          "no horizon line, no texture. One large soft key light from the upper left with gentle fill; a soft, gentle contact shadow under "
          "the product, falling slightly to the lower right. Camera: a three-quarter view from the front-left, the lens about 30 degrees above "
          "the floor plane looking down at the product at an angle, not a top-down flat lay, so the front edge, the thickness and the sides of the "
          "product and the backdrop sweep behind it are visible; the product centred and filling about 70 percent of the square frame, the whole "
          "product in frame with clear empty backdrop margins on all sides. Premium interior catalogue product photograph, photorealistic, "
          "crisp true-to-life textile texture, accurate colours, neutral white balance. No props, no plants, no furniture, no people, no text, no logos.")
SET = ("Studio product photograph of a cushion set exactly as sold, made of the four products shown in the reference image, each reproduced "
       "faithfully in colour, weave, texture and proportion: {items} Composition: the throw is folded neatly into a flat soft rectangle lying on "
       "the floor of the backdrop, its short frayed fringe visible along the front edge; the two square cushions stand upright side by side on the "
       "folded throw, slightly overlapping, plump, with soft corners; the lumbar cushion stands in front of them, lower. ")
THROW = ("Studio product photograph of one {size} {what} in {colour}, exactly as in the reference image (same colour, weave and texture): {tex} "
         "Folded neatly, as sold, into a thick soft rectangle lying flat on the floor of the backdrop, the folded layers visible at the side; one "
         "fringed end drapes softly over the front fold so the short frayed fringe is clearly visible along the front, and the fringe also shows "
         "at the folded side edges. Only the textile, nothing else. ")
P = {
 'set-B': SET.format(items="(1, top-left in the reference) a 50 x 50 cm square cushion in oatmeal light grey-beige boucle with a nubby curled surface; "
        "(2, top-right) a 50 x 50 cm square cushion in camel wide-stripe corduroy with deep raised vertical ribs; (3, bottom-left) a 30 x 50 cm "
        "rectangular lumbar cushion in plain beige linen-look woven fabric; (4, bottom-right) a 150 x 200 cm throw in pecan, a warm reddish brown, "
        "crinkled multi-layer cotton muslin with a small waffle grid and short frayed fringe on all edges."),
 'set-A': SET.format(items="(1, top-left in the reference) a 50 x 50 cm square cushion in white teddy boucle with a dense curly surface; (2, top-right) "
        "a 45 x 45 cm square cushion in taupe knitted chenille, soft heathered grey-brown with a velvety woven texture, slightly smaller than the first; "
        "(3, bottom-left) a 30 x 50 cm rectangular lumbar cushion in milk-tea teddy boucle, a pale warm beige; (4, bottom-right) a 150 x 200 cm throw "
        "in flax brown, a light sandy beige, crinkled multi-layer cotton muslin with a small waffle grid and short frayed fringe on all edges."),
 'set-C': SET.format(items="(1, top-left in the reference) a 50 x 50 cm square cushion in light-brown teddy boucle, a warm caramel brown with a curly "
        "surface; (2, top-right) a 45 x 45 cm square cushion in dark-coffee corduroy patchwork, a deep reddish brown, its front divided into four "
        "quarters with the ribs running in alternating directions, with a narrow flanged edge, slightly smaller than the first; (3, bottom-left) a "
        "30 x 50 cm rectangular lumbar cushion in light beige-grey linen-look woven fabric; (4, bottom-right) a 150 x 200 cm throw in clay, a deep "
        "chocolate brown, crinkled multi-layer cotton muslin with a small waffle grid and short frayed fringe on all edges."),
 'hand-towel-aliexpress-pure-linen-towel-38x55-caramel': "Studio product photograph of one 38 x 55 cm hand towel in caramel, a warm rust-orange brown, pure washed linen with a soft natural crumple and a plain double hem, exactly as in the reference image (same colour and texture). Folded neatly in thirds into a soft flat rectangle lying on the floor of the backdrop, as sold. Only the towel, nothing else. ",
 'hand-towel-aliexpress-pure-linen-towel-38x55-linen': "Studio product photograph of one 38 x 55 cm hand towel in natural undyed linen, a light warm grey-beige flax colour with visible slub yarns, pure washed linen with a soft natural crumple and a plain double hem, exactly as in the reference image (same colour and texture). Folded neatly in thirds into a soft flat rectangle lying on the floor of the backdrop, as sold. Only the towel, nothing else. ",
 'tea-towel-cj-waffle-cotton-beige-45x65-pair-khaki': "Studio product photograph of one 45 x 65 cm cotton towel in khaki, a warm taupe brown, with a clear small square waffle weave and a plain stitched hem, exactly as in the reference image (same colour and waffle texture). Folded neatly in thirds into a soft flat rectangle lying on the floor of the backdrop, as sold. Only the towel, nothing else. ",
 'pendant-cj-silk-ribbed-pumpkin-40-50cm-warm-light': "Studio product photograph of one pendant lamp exactly as in the reference image: a flattened pumpkin-shaped shade 50 cm in diameter and about 19 cm tall, smooth off-white silk fabric stretched over soft vertical ribs, a small metal ring at the bottom opening, hanging from a slim black rod and a black cord that runs straight up out of the top of the frame. The lamp is switched on and glows a warm 2700 K from within, the silk evenly luminous, the ribs reading as soft darker lines. The lamp hangs in the middle of the frame, seen from slightly above in a three-quarter view. ",
 'pendant-cj-scalloped-pleated-bell-45': "Studio product photograph of one pendant lamp exactly as in the reference image: a bell-shaped shade 45 cm in diameter and about 30 cm tall, made of eight soft petal panels of fine vertical micro-pleats in warm off-white cream fabric with a scalloped hem, topped by a cream ceramic ball finial with a small brushed-silver collar, hanging from a black cord that runs straight up out of the top of the frame. The lamp is switched on and glows a warm 2700 K from within, the pleats luminous. The lamp hangs in the middle of the frame, seen from slightly above in a three-quarter view. ",
}
BS = dict(size='150 x 200 cm', what='waffle-gauze bedspread', tex="deep waffle-textured multi-layer cotton gauze, soft and airy, short frayed fringe on all four edges, a small sewn-in cream fabric label at one corner.")
for k, c in (('deep-chestnut-brown', 'deep chestnut brown, a muted greyish cocoa brown'), ('coffee', 'coffee, a warm tan camel beige'),
             ('green', 'green, a deep olive green'), ('linen-brown', 'linen brown, a light sandy beige'), ('pink', 'pink, a soft blush pink')):
    P[f'bedspread-cj-waffle-gauze-fringe-150x200-{k}'] = THROW.format(colour=c, **BS)
TH = dict(size='150 x 200 cm', what='throw blanket', tex="crinkled, softly wrinkled multi-layer cotton muslin gauze with a fine shallow grid (not a thick waffle knit), matte, short frayed fringe on all edges.")
for k, c in (('pecan', 'pecan, a warm reddish brown'), ('flax-brown', 'flax brown, a light sandy beige'), ('clay', 'clay, a deep chocolate brown')):
    P[f'sofa-cover-cj-cotton-muslin-fringe-{k}-150x200'] = THROW.format(colour=c, **TH)
P['work-frame-blank'] = ("Studio product photograph of one framed picture standing upright on the floor of the backdrop, front-facing, leaning very slightly "
    "back. A landscape frame about 52 x 42 cm with a slim 2 cm matte walnut moulding and a wide bone-white mat; inside the mat an empty flat "
    "canvas of one uniform pale sand colour (#D8C8AE) with no image, no texture and no glass. The frame faces the camera squarely. ")
P = {k: v + STUDIO for k, v in P.items()}
json.dump(P, open('prompts.json', 'w'), indent=1)
print(len(P), max(len(v) for v in P.values()))
