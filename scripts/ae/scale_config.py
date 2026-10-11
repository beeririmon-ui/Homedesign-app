"""Search plan for the AliExpress scale run (scripts/ae/scale.py, 2026-10-11).

SLOTS: one entry per product slot (data/slots/*.json, fixed-product furniture excluded: it comes from Israeli suppliers).
  q     base English noun phrase; the run searches "<style word> <q>" for two style words per style
  must  regex: the title must name the product (else the row scores very low)
  band  market category in data/economics/market-prices.json, or an explicit [lo, hi] ILS band (estimated, flagged)
  size  regexes tried in order on the SKU text to pick the SKU that fits the room (envelope_cm in the slot file)
  ship  USD shipping estimate used only for screening (the detailed stage queries the real freight)
  bad   extra excluded words for this slot
  qty   units sold per slot item when the slot is a set of separately sold units bought as one listing (info only)
STYLES: two search words per style, bonus words (fit), and excluded words.
"""

GLOBAL_BAD = r"\b(plastic|pvc|acrylic|neon|rgb|led strip|cartoon|anime|christmas|xmas|halloween|glitter|sequin|hologram|car\b|phone|sticker|decal|3d wallpaper|diy kit|toy gun|gun|tactical|molle|airsoft|ammo|holster|wholesale lot|dropshipping)\b"

STYLES = {
    "nordic": {"words": ["nordic", "scandinavian"],
               "bonus": r"\b(nordic|scandinavian|scandi|linen|oak|beech|matte|white|cream|beige|natural|minimalist|stoneware|wool|cotton|ceramic|wood(en)?|simple|grey|gray)\b",
               "bad": r"\b(gold(en)?|crystal|velvet|baroque|luxury|ornate|glossy|mirror(ed)? finish|chrome|leopard|pink|purple)\b"},
    "warm-modern": {"words": ["modern minimalist", "travertine"],
                    "bonus": r"\b(modern|minimalist|travertine|walnut|boucle|teddy|beige|sand|brown|mocha|camel|caramel|curved|round(ed)?|cream|stone|marble|ceramic|linen|textured)\b",
                    "bad": r"\b(crystal|baroque|ornate|glossy|chrome|leopard|cartoon|neon)\b"},
    "japandi": {"words": ["japandi", "wabi sabi"],
                "bonus": r"\b(japandi|japanese|wabi|sabi|zen|walnut|oak|linen|stoneware|clay|handmade|matte|minimalist|bamboo|paper|rice paper|natural|wood(en)?|earth|black)\b",
                "bad": r"\b(gold(en)?|crystal|velvet|baroque|glossy|chrome|leopard|pink|purple|neon)\b"},
    "mediterranean": {"words": ["mediterranean", "terracotta"],
                      "bonus": r"\b(mediterranean|terracotta|terra cotta|clay|rattan|wicker|jute|olive|linen|plaster|handmade|rustic|white|blue|greek|spanish|moroccan|ceramic|cotton|natural)\b",
                      "bad": r"\b(crystal|velvet|baroque|glossy|chrome|neon|cartoon)\b"},
    "modern-country": {"words": ["farmhouse", "rustic"],
                       "bonus": r"\b(farmhouse|rustic|vintage|country|cottage|wood(en)?|linen|check|gingham|plaid|enamel|stoneware|cotton|natural|antique|french|retro|weathered)\b",
                       "bad": r"\b(crystal|velvet|glossy|chrome|neon|cartoon|futuristic)\b"},
    "boho": {"words": ["boho", "bohemian"],
             "bonus": r"\b(boho|bohemian|rattan|wicker|jute|macrame|woven|seagrass|tassel|fringe|tufted|handmade|natural|ethnic|moroccan|rustic|cotton|bamboo)\b",
             "bad": r"\b(crystal|glossy|chrome|neon|futuristic)\b"},
}

S = r"(?:\s*[xX*×]\s*)"  # size separator (SKU text is normalized by scale.sku_text: "W132 x H264cm" -> "132 x 264 cm")


def _s(a, b):
    return r"(?<!\d)(?:%s)%s(?:%s)(?!\d)" % (a, S, b)


SLOTS = {
    # ------------------------------------------------------------------ living-room
    "living-room/curtains": dict(q="linen curtains", must=r"curtain|drape|panel", band="curtains", size=[_s(r"1[3-5]\d", r"2[6-9]\d"), r"\b2[6-9]\d\s*cm", r"\b2[6-9]\d\b"], ship=5),
    "living-room/framed-art": dict(q="framed wall art print", must=r"frame|framed|canvas|print|painting|poster|wall art", band="framed-print", size=[_s(r"(?:10\d|11\d|12\d)", r"(?:5\d|6\d)"), _s(r"(?:5\d|6\d)", r"(?:8\d|9\d)"), _s(r"50", r"70")], ship=8, bad=r"\b(unframed|no frame|frameless)\b"),
    "living-room/wall-decor": dict(q="wall decor hanging", must=r"wall|hanging|mirror|plate|basket|tapestry|macrame", band="wall-decor", size=[r"\b(5\d|6\d|7\d|8\d)\s*cm"], ship=6),
    "living-room/accent-sconces": dict(q="stone wall sconce lamp", must=r"sconce|wall (lamp|light)", band="wall-sconce", size=[r"\b1[4-8]\s*cm", r"warm|3000"], ship=10, qty=2),
    "living-room/wall-sconce": dict(q="wall sconce lamp linen shade", must=r"sconce|wall (lamp|light)", band="wall-sconce", size=[r"warm|3000"], ship=10),
    "living-room/vase": dict(q="ceramic vase", must=r"vase", band="vase-large", size=[r"\b(2[5-9]|3[0-5])\s*cm", r"\bL\b|large"], ship=5, bad=r"\b(artificial|fake|flowers? included)\b"),
    "living-room/rug": dict(q="living room rug", must=r"rug|carpet", band="rug-large", size=[_s(r"(?:200|190)", r"(?:290|300)"), _s(r"(?:160)", r"(?:230)"), _s(r"200", r"250")], ship=25),
    "living-room/floor-lamp": dict(q="floor lamp with linen shade", must=r"floor (lamp|light)|standing lamp", bad=r"\b(lamp ?shade only|replacement shade|shade cover|lampshade for)\b", band="floor-lamp", size=[r"warm|3000", r"eu"], ship=25),
    "living-room/planter": dict(q="large ceramic floor planter", must=r"planter|pot|flowerpot|plant pot", band="planter", size=[r"\b(2[0-9]|3[0-5])\s*cm", r"\bL\b|large"], ship=6, bad=r"\b(artificial|fake)\b"),
    "living-room/sofa-cover": dict(q="3 seater sofa slipcover", must=r"sofa cover|couch cover|slipcover|sofa slipcover", bad=r"\b(cushion cover|pillow ?case|pillow cover|seat cushion cover only)\b", band="sofa-cover", size=[r"3\s*seat", r"\bL\b|large"], ship=8),
    "living-room/cushions": dict(q="cushion cover", must=r"cushion|pillow", band="cushion-cover", size=[_s("45", "45"), _s("50", "50")], ship=2),
    "living-room/basket": dict(q="large woven floor basket", must=r"basket", band="basket", size=[r"\bL\b|large", r"\b(3\d|4\d)\s*cm"], ship=6),
    "living-room/magazine-holder": dict(q="wooden magazine rack floor", must=r"magazine|newspaper|book rack", band=[89, 129], size=[], ship=6),
    "living-room/table-runner": dict(q="table runner", must=r"runner", band="table-runner", size=[_s(r"3\d", r"1[4-8]\d")], ship=3),
    "living-room/bowl": dict(q="decorative bowl", must=r"bowl|dish|tray", band="ceramic-bowl", size=[r"\b(2[0-9]|3[0-2])\s*cm"], ship=5),
    "living-room/candle-holders": dict(q="candle holder", must=r"candle|candlestick", band="candle-holder", size=[], ship=4),
    "living-room/pouf": dict(q="pouf ottoman", must=r"pouf|pouffe|ottoman|footstool|stool", band="pouf", size=[r"\b(4\d|5\d)\s*cm"], ship=15),
    "living-room/pendant": dict(q="pendant light", must=r"pendant|chandelier|ceiling (lamp|light)|hanging (lamp|light)", band="pendant", size=[r"\b(4\d|5\d)\s*cm", r"warm|3000"], ship=15),
    # ------------------------------------------------------------------ dining-room
    "dining-room/dining-pendant": dict(q="dining pendant light", must=r"pendant|chandelier|hanging (lamp|light)|ceiling (lamp|light)", band="pendant", size=[r"\b(4[5-9]|5[0-5])\s*cm"], ship=15),
    "dining-room/table-runner": dict(q="linen table runner", must=r"runner", band="table-runner", size=[_s(r"3[3-8]", r"1[3-5]\d"), _s(r"3\d", r"1\d\d")], ship=3),
    "dining-room/centerpiece-vase": dict(q="ceramic vase", must=r"vase", band="vase-small", size=[r"\b(2[0-8])\s*cm", r"\bS\b|small"], ship=5, bad=r"\b(artificial|fake)\b"),
    "dining-room/candle-holders": dict(q="taper candle holder", must=r"candle|candlestick", band="candle-holder", size=[], ship=4),
    "dining-room/curtains": dict(q="linen curtain", must=r"curtain|drape|panel", band="curtains", size=[_s(r"1[3-5]\d", r"2[6-9]\d"), r"\b2[6-9]\d\b"], ship=5),
    "dining-room/floor-vase": dict(q="large floor vase", must=r"vase", band="vase-large", size=[r"\b(5[0-9]|6[0-5])\s*cm", r"\bL\b|large"], ship=15, bad=r"\b(artificial|fake)\b"),
    "dining-room/bench-pad": dict(q="bench cushion pad", must=r"bench|cushion|pad|seat", band="seat-cushion", size=[_s(r"1[3-4]\d", r"3\d")], ship=6),
    "dining-room/dining-rug": dict(q="dining room rug", must=r"rug|carpet", band="rug-large", size=[_s(r"2[0-4]\d", r"2[0-3]\d"), _s("200", "200"), _s("200", "250")], ship=25),
    "dining-room/framed-art": dict(q="framed print kitchen", must=r"frame|framed|print|poster|painting", band="framed-print", size=[_s(r"3[0-5]", r"4[0-5]"), _s("30", "40")], ship=5),
    "dining-room/open-shelf-ceramics": dict(q="ceramic jug pitcher", must=r"jug|pitcher|jar|vase|pot", band="vase-small", size=[r"\b(1[8-9]|2[0-6])\s*cm"], ship=6),
    "dining-room/kitchen-sconce": dict(q="kitchen wall lamp", must=r"sconce|wall (lamp|light)", band="wall-sconce", size=[], ship=10),
    "dining-room/sink-set": dict(q="soap dispenser set tray", must=r"soap|dispenser|brush|tray", band="bath-accessories", size=[], ship=5),
    "dining-room/utensil-crock": dict(q="utensil holder crock", must=r"utensil|crock|holder|jar", band="kitchen-canisters", size=[r"\b(1[6-9]|20)\s*cm"], ship=5),
    "dining-room/cutting-boards": dict(q="wooden cutting board", must=r"cutting|chopping|board", band=[59, 89], size=[r"\b(4[0-8])\s*cm", r"\bL\b|large"], ship=5),
    "dining-room/condiment-set": dict(q="salt pepper grinder set", must=r"salt|pepper|grinder|mill|oil|cruet", band="salt-pepper", size=[], ship=5),
    "dining-room/bowl": dict(q="ceramic fruit bowl", must=r"bowl", band="ceramic-bowl", size=[r"\b(2[0-6])\s*cm"], ship=5),
    "dining-room/paper-towel-holder": dict(q="paper towel holder", must=r"paper towel|towel holder|roll holder", band=[59, 89], size=[], ship=5),
    "dining-room/tableware-set": dict(q="stoneware dinnerware set", must=r"plate|dinnerware|tableware|dish", band=[149, 249], size=[], ship=12),
    "dining-room/mug-set": dict(q="ceramic mug", must=r"mug|cup", band="mug", size=[r"\b(3\d\d|4\d\d)\s*ml"], ship=4),
    "dining-room/herb-pots": dict(q="small herb planter pot", must=r"pot|planter", band="planter", size=[r"\b(1[0-2])\s*cm"], ship=4),
    "dining-room/canisters": dict(q="kitchen canister jar set", must=r"canister|jar|container|storage", band="kitchen-canisters", size=[], ship=6),
    "dining-room/tea-towel": dict(q="linen tea towel", must=r"towel|cloth", band=[29, 49], size=[], ship=2),
    "dining-room/kitchen-runner": dict(q="kitchen runner rug", must=r"rug|mat|runner|carpet", bad=r"\b(table runner)\b", band="rug-small", size=[_s(r"(?:4[5-9]|5\d|60)", r"(?:2[4-8]\d)"), _s(r"(?:4\d|5\d|60)", r"(?:1[5-9]\d)")], ship=10),
    "dining-room/step-stool": dict(q="wooden step stool", must=r"stool|step", band=[149, 199], size=[], ship=15),
    # ------------------------------------------------------------------ hall
    "hall/framed-art": dict(q="framed wall art", must=r"frame|framed|print|poster|painting|canvas", band="framed-print", size=[_s(r"5\d", r"5\d"), _s("50", "50"), _s("50", "70")], ship=7),
    "hall/table-lamp": dict(q="table lamp", must=r"table lamp|desk lamp|bedside lamp|lamp", band="table-lamp", size=[r"\b(4[5-9]|5[0-5])\s*cm"], ship=12),
    "hall/key-tray": dict(q="key tray catchall", must=r"tray|dish|plate", band="tray", size=[r"\b(1[6-9]|2[0-2])\s*cm"], ship=4),
    "hall/console-vessel": dict(q="tall ceramic vase", must=r"vase|vessel|jar", band="vase-large", size=[r"\b(2[5-9]|3[0-5])\s*cm"], ship=7),
    "hall/storage-boxes": dict(q="storage box with lid", must=r"box|basket|bin|storage", band="basket", size=[], ship=7),
    "hall/bench-cushion": dict(q="bench seat cushion", must=r"bench|cushion|pad|seat", band="seat-cushion", size=[_s(r"11\d", r"3\d")], ship=6),
    "hall/bench-throw": dict(q="throw blanket", must=r"throw|blanket", band="throw", size=[], ship=6),
    "hall/basket": dict(q="woven basket", must=r"basket", band="basket", size=[r"\b(2[8-9]|3[0-4])\s*cm"], ship=5),
    "hall/wall-hooks": dict(q="wooden peg coat rack wall", must=r"hook|peg|rack|hanger", band=[89, 129], size=[r"\b(6\d|7\d|80)\s*cm", r"\b[3-5]\s*(hooks|pegs)"], ship=6),
    "hall/wall-sconce": dict(q="wall sconce", must=r"sconce|wall (lamp|light)", band="wall-sconce", size=[], ship=10),
    "hall/planter": dict(q="tall planter pot", must=r"planter|pot|flowerpot", band="planter", size=[r"\b(2[2-6])\s*cm"], ship=8, bad=r"\b(artificial|fake)\b"),
    "hall/umbrella-stand": dict(q="umbrella stand", must=r"umbrella", band=[99, 149], size=[], ship=10),
    "hall/runner-rug": dict(q="hallway runner rug", must=r"rug|runner|carpet|mat", bad=r"\b(table runner)\b", band="rug-small", size=[_s(r"(?:7\d|80)", r"(?:2[5-7]\d)"), _s(r"(?:6\d|7\d|80)", r"(?:2\d\d)")], ship=12),
    "hall/ceiling-light": dict(q="flush mount ceiling light", must=r"ceiling|flush|pendant|lamp|light", band="ceiling-light", size=[r"\b(3[5-9]|4[0-5])\s*cm"], ship=12),
    # ------------------------------------------------------------------ corridor
    "corridor/runner-rug": dict(q="long hallway runner rug", must=r"rug|runner|carpet|mat", band="rug-medium", size=[_s(r"(?:6\d)", r"(?:[3-7]\d\d)")], ship=15, bad=r"\b(table runner|cute animal|cartoon)\b"),
    "corridor/ceiling-lights": dict(q="semi flush ceiling light", must=r"ceiling|flush|lamp|light", band="ceiling-light", size=[r"\b(3\d|40)\s*cm"], ship=12, qty=2),
    "corridor/gallery-art": dict(q="framed art print set of 3", must=r"frame|framed|print|poster|painting|canvas", band="framed-print", size=[_s("40", "50"), _s(r"4\d", r"4\d|5\d")], ship=8),
    "corridor/picture-lights": dict(q="picture light wall", must=r"picture light|art light|painting light|wall (lamp|light)|sconce|mirror light", bad=r"\b(photo display|garland|clip|beads?)\b", band="wall-sconce", size=[r"\b(2[5-9]|3[0-2])\s*cm"], ship=8, qty=3),
    "corridor/gallery-stool": dict(q="wooden stool", must=r"stool", band=[149, 199], size=[r"\b(4[2-6])\s*cm"], ship=15),
    # ------------------------------------------------------------------ kids
    "kids/roman-blind": dict(q="linen roman shade blind", must=r"roman (shade|blind)|roman curtain|blind", band="curtains", size=[r"(?<!\d)13\d(?!\d)"], ship=8, bad=r"\b(parts?|cord|bracket|clips?|hardware|motor|track only|accessor(y|ies))\b"),
    "kids/framed-prints": dict(q="nursery framed print", must=r"frame|framed|print|poster|painting|canvas", band="kids-decor", size=[_s("30", "40")], ship=5),
    "kids/bookshelf": dict(q="kids wall bookshelf", must=r"shelf|bookshelf|book rack|ledge", band=[149, 199], size=[r"\b(7\d|8\d)\s*cm"], ship=15),
    "kids/wall-sconce": dict(q="swing arm wall lamp plug in", must=r"sconce|wall (lamp|light)", band="wall-sconce", size=[], ship=10),
    "kids/rug": dict(q="kids room rug 140x200 cotton", must=r"rug|carpet", band="rug-medium", size=[_s("140", "200"), _s("140", r"\d{3}"), _s("120", "170")], ship=15, bad=r"\b(puzzle|foam|play mat|game|car track)\b"),
    "kids/desk-organizer": dict(q="wooden desk organizer pen holder", must=r"pen|pencil|organizer|holder|tray", band=[39, 59], size=[], ship=4),
    "kids/toy-cars": dict(q="wooden toy car set montessori", must=r"car|truck|vehicle", band="toys", size=[], ship=4, bad=r"\b(alloy|die-?cast|remote|rc|electric|ride on|track set|parts?)\b"),
    "kids/doll": dict(q="waldorf doll handmade cotton", must=r"doll", band="toys", size=[r"\b(2[2-9]|3\d)\s*cm"], ship=4, bad=r"\b(miniature|dollhouse|doll house|bjd|reborn|silicone|clothes only|outfit|accessor(y|ies)|1/12|1:12)\b"),
    "kids/bedding": dict(q="kids single duvet cover set cotton", must=r"duvet|bedding|quilt cover", band="duvet-cover", size=[_s(r"14\d", r"20\d"), r"single|twin"], ship=8),
    "kids/bedspread": dict(q="quilted bedspread", must=r"quilt|bedspread|coverlet|blanket", band="throw", size=[r"single|twin|150"], ship=8),
    "kids/cushions": dict(q="kids cushion cover", must=r"cushion|pillow", band="cushion-cover", size=[_s(r"3[5-9]|40", r"3[5-9]|40")], ship=3),
    "kids/soft-toy": dict(q="knitted plush bunny soft toy", must=r"plush|teddy|bunny|rabbit|stuffed|soft toy", band="toys", size=[r"\b(2[5-9]|3[0-5])\s*cm"], ship=4, bad=r"\b(keychain|key chain|pendant|bag charm|mini|pillow)\b"),
    "kids/toy-basket": dict(q="large cotton rope toy storage basket", must=r"basket|bin|storage", band="basket", size=[r"\b(3[2-9]|4\d)\s*cm", r"\bL\b|large"], ship=6, bad=r"\b(mini|desk|cosmetic|car|hanging)\b"),
    "kids/skateboard": dict(q="kids wooden skateboard complete", must=r"skateboard|skate board", band=[149, 199], size=[r"\b(7\d|80)\s*cm"], ship=15, bad=r"\b(finger|fingerboard|mini|deck only|wheels only|grip tape|bearing|truck)\b"),
    "kids/doll-pram": dict(q="wooden doll stroller pram toy", must=r"pram|stroller|carriage|pushchair", band=[199, 249], size=[], ship=20, bad=r"\b(tray|miniature|dollhouse|1/12|1:12|organizer|cup holder|hook|baby stroller accessor)\b"),
    "kids/desk-chair": dict(q="children wooden chair", must=r"chair", band=[249, 349], size=[], ship=25, bad=r"\b(gaming|swivel|office|recliner|cover|cushion only|miniature|dollhouse)\b"),
    "kids/pendant": dict(q="kids pendant light", must=r"pendant|ceiling|hanging|lamp|light", band="pendant", size=[r"\b(1\d|2[0-8])\s*cm"], ship=10),
    # ------------------------------------------------------------------ master
    "master/curtains": dict(q="linen curtains bedroom", must=r"curtain|drape|panel", band="curtains", size=[_s(r"1[3-5]\d", r"2[6-9]\d"), r"\b2[6-9]\d\b"], ship=5, qty=2),
    "master/framed-art": dict(q="large framed wall art", must=r"frame|framed|print|poster|painting|canvas", band="framed-print", size=[_s(r"1[01]\d", r"(?:5\d|6\d)"), _s(r"(?:5\d|6\d)", r"1[01]\d")], ship=10),
    "master/bedside-sconces": dict(q="bedside wall sconce", must=r"sconce|wall (lamp|light)", band="wall-sconce", size=[], ship=10, qty=2),
    "master/sill-vase": dict(q="bud vase ceramic", must=r"vase", band="vase-small", size=[r"\b(2[2-9]|30)\s*cm"], ship=4, bad=r"\b(artificial|fake)\b"),
    "master/planter": dict(q="large ceramic floor plant pot 40cm", must=r"planter|pot|flowerpot", band="planter", size=[r"\b(3[6-9]|4[0-2])\s*cm", r"\bL\b|large"], ship=12, bad=r"\b(artificial|fake)\b"),
    "master/floor-lamp": dict(q="floor lamp with fabric shade", must=r"floor (lamp|light)|standing lamp", bad=r"\b(lamp ?shade only|replacement shade|shade cover|lampshade for)\b", band="floor-lamp", size=[r"\b1[5-6]\d\s*cm"], ship=25),
    "master/nightstand-tray": dict(q="decorative tray", must=r"tray", band="tray", size=[r"\b(2[8-9]|3[0-4])\s*cm"], ship=5),
    "master/nightstand-vase": dict(q="small ceramic vase", must=r"vase", band="vase-small", size=[r"\b(2[2-8])\s*cm"], ship=4, bad=r"\b(artificial|fake)\b"),
    "master/trinket-dish": dict(q="trinket dish jewelry", must=r"dish|tray|plate", band=[29, 49], size=[r"\b(8|9|1[0-2])\s*cm"], ship=3),
    "master/bedside-carafe": dict(q="ceramic water carafe with cup bedside", must=r"carafe|decanter|pitcher|jug|water bottle", band=[59, 89], size=[], ship=6),
    "master/candle-holders": dict(q="candle holder pair", must=r"candle|candlestick", band="candle-holder", size=[], ship=4),
    "master/pillowcases": dict(q="linen pillowcase 50x70 bed pillow", must=r"pillowcase|pillow case|pillow sham|pillowslip", bad=r"\b(cushion|throw pillow|sofa|decorative|lumbar)\b", band="pillowcases", size=[_s(r"(?:4[5-9]|50)", r"(?:6[5-9]|70)"), _s(r"(?:6[5-9]|70)", r"(?:4[5-9]|50)")], ship=3),
    "master/bedding": dict(q="linen duvet cover set", must=r"duvet|bedding|quilt cover", band="bedding-set", size=[_s(r"2[0-2]\d", r"2[0-4]\d"), r"queen|king"], ship=12),
    "master/cushions": dict(q="lumbar pillow cover", must=r"cushion|pillow", band="cushion-cover", size=[_s(r"(?:3[0-9]|40)", r"(?:5[5-9]|6\d)"), _s(r"(?:5[5-9]|6\d)", r"(?:3[0-9]|40)")], ship=3),
    "master/throw": dict(q="knitted throw blanket bed end", must=r"throw|blanket", bad=r"\b(shawl|poncho|wearable|scarf|cape|hoodie)\b", band="throw", size=[_s(r"1[2-5]\d", r"1[7-9]\d|2\d\d")], ship=8),
    "master/rug": dict(q="large area rug 200x300", must=r"rug|carpet", band="rug-large", size=[_s(r"(?:200)", r"(?:2[8-9]\d|300)"), _s("200", r"2\d\d"), _s("160", "230")], ship=25),
    "master/basket": dict(q="large woven laundry basket", must=r"basket", band="basket", size=[r"\b(3[2-8])\s*cm", r"\bL\b|large"], ship=6),
    "master/pendant": dict(q="large pendant lamp 45cm", must=r"pendant|chandelier|ceiling|hanging (lamp|light)", band="pendant", size=[r"\b(4\d|50)\s*cm"], ship=15),
    # ------------------------------------------------------------------ work
    "work/curtains": dict(q="linen curtains", must=r"curtain|drape|panel", band="curtains", size=[_s(r"1[3-5]\d", r"2[6-9]\d"), r"\b2[6-9]\d\b"], ship=5, qty=2),
    "work/framed-art": dict(q="framed wall art", must=r"frame|framed|print|poster|painting|canvas", band="framed-print", size=[_s(r"5[5-9]|60", r"4[5-9]|50"), _s("50", "40")], ship=7),
    "work/wall-sconce": dict(q="wall sconce reading lamp", must=r"sconce|wall (lamp|light)", band="wall-sconce", size=[], ship=10),
    "work/rug": dict(q="rug", must=r"rug|carpet", band="rug-medium", size=[_s(r"1[6-8]\d", r"2[0-2]\d"), _s("160", "230")], ship=20),
    "work/basket": dict(q="woven basket", must=r"basket", band="basket", size=[r"\b(2[8-9]|3[0-2])\s*cm"], ship=5),
    "work/waste-basket": dict(q="waste paper basket", must=r"waste|trash|bin|basket", band="basket", size=[r"\b(2[2-9]|3[0-2])\s*cm"], ship=5),
    "work/planter": dict(q="floor planter pot", must=r"planter|pot|flowerpot", band="planter", size=[r"\b(3[4-8])\s*cm"], ship=12, bad=r"\b(artificial|fake)\b"),
    "work/magazine-holder": dict(q="wooden magazine file holder desk", must=r"magazine|file|holder|organizer", band=[59, 89], size=[], ship=5),
    "work/shelf-boxes": dict(q="storage box with lid", must=r"box|basket|bin", band="basket", size=[], ship=6),
    "work/bookends": dict(q="bookends", must=r"bookend|book end|book stand", band=[69, 99], size=[], ship=5),
    "work/desk-tray": dict(q="desk tray organizer", must=r"tray|organizer", band="tray", size=[r"\b(2[2-8])\s*cm"], ship=4),
    "work/desk-organizer": dict(q="pen holder", must=r"pen|pencil|holder|organizer|cup", band=[39, 59], size=[], ship=4),
    "work/desk-lamp": dict(q="desk lamp", must=r"lamp|light", band="table-lamp", size=[r"\b(4\d|50)\s*cm"], ship=12),
    "work/pendant": dict(q="small pendant light", must=r"pendant|ceiling|hanging|lamp|light", band="pendant", size=[r"\b(1\d|2[0-8])\s*cm"], ship=10),
    # ------------------------------------------------------------------ bath
    "bath/shower-dispensers": dict(q="shower dispenser bottles set", must=r"dispenser|bottle|pump", band="bath-accessories", size=[r"\b(3\d\d|4\d\d|5\d\d)\s*ml"], ship=6, qty=3),
    "bath/wall-sconce": dict(q="bathroom wall sconce", must=r"sconce|wall (lamp|light)", band="wall-sconce", size=[], ship=10),
    "bath/vanity-sconces": dict(q="vanity wall light", must=r"sconce|wall (lamp|light)|vanity", band="wall-sconce", size=[], ship=10, qty=2),
    "bath/bath-mat": dict(q="bath mat", must=r"mat|rug", band="bath-mat", size=[_s(r"(?:4[0-9]|50)", r"(?:5[5-9]|6\d|70)")], ship=6),
    "bath/shower-stool": dict(q="shower stool wooden", must=r"stool|bench|seat", band=[149, 199], size=[], ship=15),
    "bath/shower-curtain": dict(q="shower curtain", must=r"shower curtain|curtain", band="shower-curtain", size=[_s(r"1[8-9]\d|2[0-4]\d", r"2[0-6]\d"), _s("180", "200")], ship=5),
    "bath/floor-planter": dict(q="ceramic planter pot", must=r"planter|pot|flowerpot", band="planter", size=[r"\b(2[6-9]|30)\s*cm"], ship=8, bad=r"\b(artificial|fake)\b"),
    "bath/towel-ladder": dict(q="towel ladder", must=r"ladder|towel rack|towel stand", band=[149, 199], size=[r"\b1[3-6]\d\s*cm"], ship=15),
    "bath/bath-towels": dict(q="cotton bath towel", must=r"towel", band="towels", size=[_s("70", "140")], ship=6),
    "bath/storage-basket": dict(q="storage basket shelf", must=r"basket|bin|storage", band="basket", size=[r"\b(4[0-4])\s*cm"], ship=6),
    "bath/toilet-paper-stand": dict(q="toilet paper holder stand", must=r"toilet paper|tissue|roll holder|paper holder", band=[89, 129], size=[], ship=8),
    "bath/bin": dict(q="pedal bin bathroom", must=r"bin|trash|waste|garbage", band=[89, 129], size=[r"\b[3-6]\s*l\b"], ship=10),
    "bath/toilet-brush": dict(q="toilet brush holder", must=r"toilet brush|brush", band="bath-accessories", size=[], ship=5),
    "bath/ledge-planter": dict(q="small ceramic plant pot", must=r"pot|planter", band="planter", size=[r"\b(1[1-4])\s*cm"], ship=4, bad=r"\b(artificial|fake)\b"),
    "bath/reed-diffuser": dict(q="reed diffuser", must=r"diffuser|reed|aroma", band=[59, 89], size=[], ship=6),
    "bath/candle": dict(q="scented candle jar", must=r"candle", band=[49, 79], size=[], ship=5),
    "bath/soap-dispenser": dict(q="ceramic soap dispenser", must=r"soap|dispenser|lotion", band="bath-accessories", size=[], ship=5),
    "bath/toothbrush-cup": dict(q="toothbrush cup holder", must=r"toothbrush|tumbler|cup", band="bath-accessories", size=[], ship=4),
    "bath/vanity-vase": dict(q="mini bud vase", must=r"vase", band="vase-small", size=[r"\b(1[1-4])\s*cm"], ship=4, bad=r"\b(artificial|fake)\b"),
    "bath/towel-ring": dict(q="towel ring", must=r"towel ring|ring|towel holder", band="bath-accessories", size=[], ship=5),
    "bath/hand-towel": dict(q="hand towel cotton", must=r"towel", band="towels", size=[_s(r"3\d|40", r"5\d|60")], ship=3),
    "bath/ceiling-light": dict(q="bathroom ceiling light", must=r"ceiling|flush|lamp|light", band="ceiling-light", size=[r"\b(2[8-9]|3[0-4])\s*cm"], ship=12),
}

ROOMS = ["living-room", "dining-room", "hall", "master", "work", "kids", "bath", "corridor"]
# where the cards of each room live (data/products/<dir>/<slot>/; the living room has data/products/<slot>/)
ROOM_DIRS = {"living-room": None, "dining-room": "dining", "hall": "entrance", "corridor": "corridor", "master": "master",
             "kids": "kids", "work": "work", "bath": "bath"}
