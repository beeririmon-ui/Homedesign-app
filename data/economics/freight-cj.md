# עלויות משלוח CJ לישראל

עודכן: 2026-10-09 21:51 · קריאות API: 106 · מקור: `freight-cj.json` (CJ freightCalculate, מסין לישראל, יחידה אחת).

## סטטוס

| סטטוס | מוצרים |
| --- | --- |
| ok | 109 |
| no_options | 0 |
| no_vid | 0 |
| rate_limited | 0 |
| error | 0 |
| **סה"כ** | **109** |

- חציון המשלוח הזול: **$16.59** (טווח $4.79 עד $491.08).
- חציון המשלוח הזול שמגיע תוך 20 יום: **$35.03** (109 מוצרים עם אפשרות כזו).
- כמעט תמיד הזול הוא CJPacket Eub (12–50 יום). `fastest_under_20d` הוא המהיר ביותר עם מקסימום ≤20 יום (בדרך כלל DHL, יקר); `cheapest_under_20d` (שדה נוסף) הוא הזול שמגיע תוך 20 יום, וזה המספר הריאלי למשלוח "מהיר".
- ה-vid נלקח מההערות בכרטיס (הווריאנט המומלץ); הפירוט ב-`variant_note`. שלושה vid משותפים לשני כרטיסים, והתוצאה שוכפלה בלי קריאה נוספת.
- בלי קו חסכוני (רק To Door / DHL): `rug-cj-braided-wool-natural` $491.08 (DHL Official), `framed-art-cj-morandi-triptych-sage` $130.82 (CJPacket To Door), `bedding-cj-cotton-linen-duvet-beige` $107.99 (CJPacket To Door).
- בדיקה צולבת: כל מחירי Eub שכבר צוטטו בהערות הכרטיסים תואמים ל-API בטווח 10%; הפערים היחידים הם הערכות ("NOT quoted") או מידה אחרת.
- כמות 1 לכל כרטיס. `candle-holders-cj-travertine-pedestal` נמכר כסט של 2 יחידות, והמשלוח כאן ליחידה אחת.

## משלוח מעל 50% מעלות המוצר (103 מוצרים)

לפי המשלוח הזול ביותר. ממוין מהגרוע לטוב.

| מוצר | עלות | משלוח זול | יחס | שיטה (ימים) | זול תוך 20 יום |
| --- | --- | --- | --- | --- | --- |
| `skateboard-cj-blank-maple-43` | $1.93 | $17.60 | 912% | CJPacket Eub (12-50) | $32.09 (CJPacket To Door) |
| `framed-art-cj-morandi-triptych-sage` | $15.75 | $130.82 | 831% | CJPacket To Door (11-18) | $130.82 (CJPacket To Door) |
| `wall-sconce-cj-black-swing-arm-wood-shade` | $10.78 | $86.78 | 805% | CJPacket Sensitive (22-27) | $91.42 (CJPacket To Door) |
| `wall-sconce-cj-black-swing-arm-fabric` | $13.76 | $105.02 | 763% | CJPacket Sensitive (22-27) | $109.66 (CJPacket To Door) |
| `magazine-holder-cj-felt-log-basket` | $1.72 | $10.27 | 597% | CJPacket Eub (12-50) | $31.07 (CJPacket To Door) |
| `wall-sconce-cj-travertine-dome-15-pull` | $16.09 | $84.76 | 527% | CJPacket Sensitive (22-27) | $89.39 (CJPacket To Door) |
| `vase-cj-white-textured-jar` | $6.60 | $33.24 | 504% | CJPacket Eub (12-50) | $54.80 (CJPacket To Door) |
| `cushions-cj-chenille-wide-wale-green` | $1.19 | $5.87 | 493% | CJPacket Eub (12-50) | $11.73 (CJPacket To Door) |
| `pool-cj-cotton-linen-box-camel-40x30` | $1.57 | $7.50 | 478% | CJPacket Eub (12-50) | $16.30 (CJPacket To Door) |
| `cushions-cj-linen-look-ivory` | $2.37 | $10.78 | 455% | CJPacket Eub (12-50) | $19.47 (CJPacket To Door) |
| `pool-cj-wood-sunburst-mirror-43` | $4.86 | $19.99 | 411% | CJPacket Eub (12-50) | $96.78 (CJPacket To Door) |
| `bench-pad-cj-tufted-long-cushion-khaki-120` | $6.30 | $24.53 | 389% | CJPacket Eub (12-50) | $41.11 (CJPacket To Door) |
| `floor-lamp-cj-black-drum-linen` | $9.02 | $34.62 | 384% | CJPacket Eub (12-50) | $56.99 (CJPacket To Door) |
| `bath-mat-cj-solid-wood-slatted-61x45` | $19.70 | $74.85 | 380% | CJPacket Sensitive (22-27) | $79.49 (CJPacket To Door) |
| `basket-cj-jute-rope-cylinder` | $5.17 | $19.11 | 370% | CJPacket Eub (12-50) | $36.93 (CJPacket To Door) |
| `vanity-sconces-cj-ip65-mini-updown-white` | $3.30 | $11.67 | 354% | CJPacket Eub (12-50) | $20.87 (CJPacket To Door) |
| `cushions-cj-wide-wale-corduroy` | $1.72 | $5.98 | 348% | CJPacket Eub (12-50) | $11.93 (CJPacket To Door) |
| `cushions-cj-knitted-chenille-bean-green` | $1.71 | $5.87 | 343% | CJPacket Eub (12-50) | $11.73 (CJPacket To Door) |
| `bowl-cj-speckled-ivory-wide-bowl-21` | $3.50 | $11.92 | 341% | CJPacket Eub (12-50) | $31.68 (CJPacket To Door) |
| `cushions-cj-bubble-chenille-bean-green` | $2.00 | $6.78 | 339% | CJPacket Eub (12-50) | $13.16 (CJPacket To Door) |
| `cushions-cj-corduroy-patchwork` | $1.78 | $5.98 | 336% | CJPacket Eub (12-50) | $11.93 (CJPacket To Door) |
| `magazine-holder-cj-felt-snap-bucket` | $2.55 | $8.51 | 334% | CJPacket Eub (12-50) | $15.90 (CJPacket To Door) |
| `cushions-cj-wide-stripe-corduroy-light-green` | $1.81 | $5.87 | 324% | CJPacket Eub (12-50) | $11.73 (CJPacket To Door) |
| `vanity-sconces-cj-fluted-resin-updown-white` | $7.30 | $23.57 | 323% | CJPacket Sensitive (22-27) | $28.20 (CJPacket To Door) |
| `sofa-cover-cj-knit-thick-slipcover` | $6.97 | $20.75 | 298% | CJPacket Eub (12-50) | $35.15 (CJPacket To Door) |
| `cushions-cj-washed-cotton-frayed` | $1.93 | $5.49 | 284% | CJPacket Eub (12-50) | $11.14 (CJPacket To Door) |
| `table-runner-cj-linen-look-triangle-end` | $2.72 | $7.32 | 269% | CJPacket Eub (12-50) | $14.01 (CJPacket To Door) |
| `vase-cj-textured-white-stoneware` | $10.24 | $27.31 | 267% | CJPacket Eub (12-50) | $76.59 (CJPacket To Door) |
| `framed-art-cj-taupe-block-black-line-30x40` | $10.95 | $29.20 | 267% | CJPacket Eub (12-50) | $48.44 (CJPacket To Door) |
| `bedding-cj-washed-polyester-set-milk-tea` | $9.78 | $24.15 | 247% | CJPacket Eub (12-50) | $40.51 (CJPacket To Door) |
| `mug-set-cj-cream-matte-breakfast-cup` | $3.41 | $8.39 | 246% | CJPacket Eub (12-50) | $15.70 (CJPacket To Door) |
| `table-lamp-cj-white-textured-ceramic-linen-drum` | $15.28 | $37.15 | 243% | CJPacket Eub (12-50) | $243.82 (CJPacket To Door) |
| `ceiling-light-cj-waxwood-dome-ash-40` | $17.58 | $42.19 | 240% | CJPacket Eub (12-50) | $231.43 (CJPacket To Door) |
| `cushions-cj-boucle-teddy` | $3.61 | $8.39 | 232% | CJPacket Eub (12-50) | $15.70 (CJPacket To Door) |
| `soap-dispenser-cj-matte-ceramic-cream-black-pump` | $4.36 | $10.02 | 230% | CJPacket Eub (12-50) | $18.28 (CJPacket To Door) |
| `pool-cj-wabi-sabi-floor-vase-white` | $26.20 | $59.72 | 228% | CJPacket Eub (12-50) | $151.25 (CJPacket To Door) |
| `pool-cj-carbonized-wood-pedestal-candlestick` | $8.45 | $19.11 | 226% | CJPacket Eub (12-50) | $32.57 (CJPacket To Door) |
| `picture-lights-cj-black-tube-rechargeable` | $5.72 | $12.47 | 218% | CJPacket Sensitive (22-27) | $17.29 (CJPacket To Door) |
| `cushions-cj-linen-look-charcoal` | $2.62 | $5.67 | 216% | CJPacket Eub (12-50) | $11.44 (CJPacket To Door) |
| `pool-cj-woven-cotton-runner-fringe` | $3.17 | $6.74 | 213% | CJPacket Eub (12-50) | $13.11 (CJPacket To Door) |
| `wall-decor-cj-macrame-dowel-50x70` | $6.00 | $12.68 | 211% | CJPacket Eub (12-50) | $22.45 (CJPacket To Door) |
| `pendant-cj-fabric-dome-ash-cap-25` | $14.10 | $29.57 | 210% | CJPacket Eub (12-50) | $94.10 (CJPacket To Door) |
| `table-lamp-cj-pleated-shade-wood-column` | $19.73 | $40.24 | 204% | CJPacket Sensitive (22-27) | $44.88 (CJPacket To Door) |
| `table-runner-cj-linen-look-sage-fringe` | $3.68 | $7.38 | 201% | CJPacket Eub (12-50) | $14.12 (CJPacket To Door) |
| `tableware-set-cj-grey-sand-matte-plate` | $7.93 | $15.58 | 196% | CJPacket Eub (12-50) | $27.02 (CJPacket To Door) |
| `bedding-cj-cream-ruffle-rosebud-set` | $16.35 | $31.85 | 195% | CJPacket Eub (12-50) | $52.62 (CJPacket To Door) |
| `toy-cars-cj-beech-peg-bus` | $3.07 | $5.87 | 191% | CJPacket Eub (12-50) | $11.73 (CJPacket To Door) |
| `vase-cj-coarse-sand-white-tall` | $16.25 | $30.84 | 190% | CJPacket Eub (12-50) | $82.78 (CJPacket To Door) |
| `vase-cj-faceted-cream` | $17.41 | $32.29 | 185% | CJPacket Eub (12-50) | $68.20 (CJPacket To Door) |
| `rug-cj-braided-wool-natural` | $267.54 | $491.08 | 184% | DHL Official (3-7) | $491.08 (DHL Official) |
| `cushions-cj-sandstone-chenille-flange` | $3.35 | $6.11 | 182% | CJPacket Eub (12-50) | $12.13 (CJPacket To Door) |
| `sofa-cover-cj-waffle-jacquard-stretch-slipcover` | $12.94 | $22.89 | 177% | CJPacket Eub (12-50) | $38.53 (CJPacket To Door) |
| `wall-sconce-cj-travertine-half-bowl-15` | $11.44 | $20.19 | 176% | CJPacket Sensitive (22-27) | $24.83 (CJPacket To Door) |
| `wall-sconce-cj-travertine-cone-walnut` | $17.08 | $29.57 | 173% | CJPacket Eub (12-50) | $49.04 (CJPacket To Door) |
| `bath-mat-cj-tufted-cotton-frame-beige-40x60` | $5.97 | $10.02 | 168% | CJPacket Eub (12-50) | $31.50 (CJPacket To Door) |
| `pool-cj-linen-look-tassel-curtain` | $9.62 | $15.96 | 166% | CJPacket Eub (12-50) | $27.60 (CJPacket To Door) |
| `wall-sconce-cj-travertine-dome-15-alt` | $18.24 | $30.11 | 165% | CJPacket Sensitive (22-27) | $34.76 (CJPacket To Door) |
| `curtains-cj-japanese-linen-half-shade` | $16.58 | $26.67 | 161% | CJPacket Eub (12-50) | $44.48 (CJPacket To Door) |
| `planter-cj-seagrass-belly` | $8.00 | $12.75 | 159% | CJPacket Eub (12-50) | $158.28 (CJPacket To Door) |
| `basket-cj-seagrass-belly` | $8.00 | $12.75 | 159% | CJPacket Eub (12-50) | $158.28 (CJPacket To Door) |
| `vanity-sconces-cj-flat-halo-disc-white` | $5.92 | $9.40 | 159% | CJPacket Liquid Line (9-23) | $14.31 (CJPacket To Door) |
| `bath-towels-cj-cotton-waffle-white` | $5.47 | $8.51 | 156% | CJPacket Eub (12-50) | $15.90 (CJPacket To Door) |
| `bedspread-cj-six-layer-gauze-quilt` | $8.46 | $12.80 | 151% | CJPacket Eub (12-50) | $22.65 (CJPacket To Door) |
| `candle-holders-cj-travertine-pedestal` | $9.12 | $13.66 | 150% | CJPacket Eub (12-50) | $23.99 (CJPacket To Door) |
| `sofa-cover-cj-polar-fleece-jacquard-slipcover` | $14.87 | $22.20 | 149% | CJPacket Eub (12-50) | $37.44 (CJPacket To Door) |
| `shower-curtain-cj-linen-look-khaki-grommet` | $6.88 | $10.27 | 149% | CJPacket Eub (12-50) | $18.68 (CJPacket To Door) |
| `ceiling-lights-cj-silk-cocoon-flush-40` | $28.83 | $41.93 | 145% | CJPacket Eub (12-50) | $175.81 (CJPacket To Door) |
| `open-shelf-ceramics-cj-morandi-matte-bottle-set` | $6.85 | $9.85 | 144% | CJPacket Eub (12-50) | $42.09 (CJPacket To Door) |
| `tableware-set-cj-speckled-oat-stoneware-bowl-13` | $7.37 | $10.40 | 141% | CJPacket Eub (12-50) | $23.60 (CJPacket To Door) |
| `bowl-cj-glutinous-white-belly-bowl-21` | $6.68 | $9.40 | 141% | CJPacket Eub (12-50) | $27.41 (CJPacket To Door) |
| `basket-cj-seagrass-belly-xl` | $6.56 | $8.64 | 132% | CJPacket Eub (12-50) | $16.09 (CJPacket To Door) |
| `throw-cj-cotton-waffle-ruffle-khaki-150x200` | $13.55 | $17.84 | 132% | CJPacket Eub (12-50) | $30.58 (CJPacket To Door) |
| `pouf-cj-cotton-knit-ball-cover` | $16.72 | $21.88 | 131% | CJPacket Eub (12-50) | $36.93 (CJPacket To Door) |
| `sofa-cover-cj-bubble-stretch-slipcover` | $24.05 | $30.46 | 127% | CJPacket Eub (12-50) | $50.43 (CJPacket To Door) |
| `pendant-cj-tiered-fabric-drum` | $43.28 | $54.80 | 127% | CJPacket Eub (12-50) | $529.21 (CJPacket To Door) |
| `vase-cj-matte-moon-jar-white` | $15.92 | $20.12 | 126% | CJPacket Eub (12-50) | $86.15 (CJPacket To Door) |
| `vase-cj-white-plum-hand-thrown` | $24.05 | $29.57 | 123% | CJPacket Eub (12-50) | $168.92 (CJPacket To Door) |
| `mug-set-cj-oat-speckled-round-mug-wood-saucer` | $8.28 | $10.02 | 121% | CJPacket Eub (12-50) | $18.28 (CJPacket To Door) |
| `sofa-cover-cj-cotton-muslin-fringe` | $11.64 | $14.06 | 121% | CJPacket Eub (12-50) | $24.63 (CJPacket To Door) |
| `pendant-cj-pleated-pumpkin-lantern-40` | $46.10 | $54.80 | 119% | CJPacket Eub (12-50) | $154.61 (CJPacket To Door) |
| `pool-cj-travertine-organic-tray-24` | $17.13 | $19.49 | 114% | CJPacket Eub (12-50) | $33.17 (CJPacket To Door) |
| `framed-prints-cj-charcoal-line-black-frame-35x45` | $21.23 | $23.90 | 113% | CJPacket Eub (12-50) | $40.12 (CJPacket To Door) |
| `framed-art-cj-swinging-line-black-frame-mat-35x45` | $21.23 | $23.90 | 113% | CJPacket Eub (12-50) | $40.12 (CJPacket To Door) |
| `basket-cj-cotton-rope-white` | $12.86 | $14.44 | 112% | CJPacket Eub (12-50) | $25.22 (CJPacket To Door) |
| `bedding-cj-muslin-cotton-duvet-dune` | $14.93 | $16.59 | 111% | CJPacket Eub (12-50) | $28.61 (CJPacket To Door) |
| `bedspread-cj-muslin-blanket-beige-150x200` | $11.61 | $12.68 | 109% | CJPacket Eub (12-50) | $22.45 (CJPacket To Door) |
| `bowl-cj-reactive-white-rimmed-plate-21` | $9.62 | $10.27 | 107% | CJPacket Eub (12-50) | $26.95 (CJPacket To Door) |
| `pendant-cj-silk-pumpkin-lantern` | $29.85 | $29.20 | 98% | CJPacket Eub (12-50) | $48.44 (CJPacket To Door) |
| `magazine-holder-cj-gunmetal-leather-strap` | $31.08 | $29.57 | 95% | CJPacket Eub (12-50) | $68.83 (CJPacket To Door) |
| `wall-sconce-cj-travertine-disc-25` | $38.14 | $35.76 | 94% | CJPacket Eub (12-50) | $58.77 (CJPacket To Door) |
| `bedding-cj-washed-linen-natural-set` | $48.68 | $43.96 | 90% | CJPacket Eub (12-50) | $71.67 (CJPacket To Door) |
| `bedding-cj-cotton-linen-duvet-beige` | $128.36 | $107.99 | 84% | CJPacket To Door (11-18) | $107.99 (CJPacket To Door) |
| `ceiling-lights-cj-pleated-fabric-saucer-flush-50` | $36.15 | $30.20 | 84% | CJPacket Eub (12-50) | $231.95 (CJPacket To Door) |
| `magazine-holder-cj-arch-iron-cane` | $21.96 | $17.84 | 81% | CJPacket Eub (12-50) | $30.58 (CJPacket To Door) |
| `vase-cj-charcoal-carved` | $26.53 | $21.38 | 81% | CJPacket Eub (12-50) | $97.57 (CJPacket To Door) |
| `gallery-art-cj-black-botanical-cutout-set3` | $14.53 | $10.65 | 73% | CJPacket Eub (12-50) | $51.42 (CJPacket To Door) |
| `pillowcases-cj-linen-pair-coconut-button` | $13.23 | $9.15 | 69% | CJPacket Eub (12-50) | $16.89 (CJPacket To Door) |
| `vase-cj-french-matte-white-35` | $42.79 | $29.57 | 69% | CJPacket Eub (12-50) | $91.04 (CJPacket To Door) |
| `framed-prints-cj-flower-cutout-set-30x40` | $12.74 | $8.14 | 64% | CJPacket Eub (12-50) | $35.03 (CJPacket To Door) |
| `toothbrush-cup-cj-silver-travertine-cup` | $19.73 | $11.92 | 60% | CJPacket Eub (12-50) | $21.26 (CJPacket To Door) |
| `sofa-cover-cj-linen-feel-chenille-slipcover` | $19.40 | $11.67 | 60% | CJPacket Eub (12-50) | $20.87 (CJPacket To Door) |
| `dining-pendant-cj-black-ring-cloth-lantern-50` | $51.79 | $29.57 | 57% | CJPacket Eub (12-50) | $294.57 (CJPacket To Door) |
| `planter-cj-cement-ribbed-belly` | $31.16 | $16.59 | 53% | CJPacket Eub (12-50) | $269.58 (CJPacket To Door) |

## אין אפשרות משלוח לישראל

- אין. לכל המוצרים שנבדקו בהצלחה יש לפחות אפשרות משלוח אחת לישראל.
