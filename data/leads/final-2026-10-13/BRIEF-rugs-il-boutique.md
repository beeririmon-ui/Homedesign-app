# Boutique, handmade and special rugs from Israeli suppliers (2026-10-16)

The owner (2026-10-16), recorded in `docs/studio-rules.md` ז:
- Find **at least 15 Israeli suppliers** of boutique, handmade or special rugs that suit our six styles.
- First pick the rugs and show them to the owner, with image and price.
- Only then email the suppliers, with the same opening email as the lighting outreach.
- Beautiful rugs raise the level of the site, next to the premium lighting.

## Why
Rugs are one of our biggest gaps:
- Almost every rug slot has **0 ready options** in most styles (`data/leads/final-2026-10-13/coverage.json` → `remaining`).
- From China they lose money on shipping. A 200×290 rug weighs about 10–12 kg, and DHL alone costs more than the price.

## The rug slots (`data/slots/<room>.json`)
| Slot | Size (cm) | Note |
| --- | --- | --- |
| living-room/rug | 200–240 × 290–340 | the biggest one, about 60% of the floor in frame |
| master/rug | 280–300 × 200–220 | |
| dining-room/dining-rug | 200–240 × 200–230 | |
| work/rug | 160–180 × 200–220 | |
| kids/rug | 140 × 200 | |
| hall/runner-rug | 70–80 × 250–270 | |
| corridor/runner-rug | 58–65 × 680–710 | made to measure |
| dining-room/kitchen-runner | 45–60 × 240–280 | |

## Styles (one line each; details in `docs/design-bible/`)
- **Nordic:** warm white, oat, mist grey; wool, wool-cotton, jute-wool or flatweave cotton; low pile; no strong pattern.
- **Warm modern:** sand, cream, mocha, chocolate; textured wool, tone-on-tone, soft geometry.
- **Japandi:** stone, charcoal, natural; flatweave, jute, minimal.
- **Mediterranean:** natural jute, sisal, white, terracotta; flatweave and kilim.
- **Modern country:** faded wash, vintage-look, small floral or check, soft colour.
- **Boho:** Beni Ourain, Moroccan, kilim, fringe, berber; ivory with black lines, rust and terracotta.
- **No replicas** of designer rugs.

## Who to look for
Small and boutique first, not chains:
- Israeli weavers and handmade studios, including weaving cooperatives (for example, Bedouin women's weaving projects in the Negev).
- Boutique importers of handmade rugs: Moroccan (Beni Ourain, Azilal, Boucherouite), kilims, Afghan or Turkish flatweaves, vintage and overdyed.
- Designer and custom rug makers who make to measure. They matter especially for the 680 cm corridor runner and the custom runners.
- Natural-fibre specialists: jute, sisal, wool flatweave.

**Not:**
- Big chains and mass retailers, or anyone with radio or TV campaigns.
- Suppliers already contacted: הנסיכה אונליין (Nesicha Online), NOOL, KADO HOME.
- קבוצת כרמל / Carmel Carpets: a sensitivity note in `docs/suppliers/directory.md`; the owner decides first.
- If a supplier's location looks like it may be in the West Bank, flag it for the owner and don't include it as a recommendation.
- Known from earlier research (re-check and include only if boutique): השטיח האדום / HōM Business and BuyCarpet (`docs/suppliers/decor-il-2026-10-12.md`), and the Israeli shops in `data/leads/final-2026-10-13/results/il-textiles.json`.

## For each supplier
- name, website, city, type (weaver / studio / boutique importer / custom maker);
- why it's small or boutique;
- signs it's open to working with other sellers: stockists, a trade or designers page, custom orders;
- a **public business email**; otherwise the contact page or form;
- a one-sentence Hebrew personal line, starting "אהבנו את ...", genuine and specific;
- **3–6 rugs that fit our slots and styles**, each with:
  - URL;
  - every size offered, each with its price (ILS);
  - material, pile or weave, and colours;
  - a style-fit guess for the 6 styles;
  - the slot it fits, and whether the size is within the envelope (±10 cm counts as borderline for rugs);
  - **the main image downloaded** to `/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/rugs/<supplier-slug>/<rug-slug>.jpg`, using curl with no user-agent tricks, at about 1000 px and under 400 KB, then checked with `file`.

## Hard limits
- Public pages only, at a human pace. Stop at any login, CAPTCHA or block.
- No forms, messages, sign-ups or emails.
- Don't edit binding docs, slots or cards. No product cards.
- Leave out the personal mobile numbers of individuals. Business landlines and emails are fine.

## Output
1. `data/leads/final-2026-10-13/rugs-il-boutique-2026-10-16.json`, validated with Python:
   ```json
   {"date": "2026-10-16",
    "suppliers": [{"slug": "", "name": "", "url": "", "city": "", "type": "", "boutique_note": "", "openness": "", "email_public": null, "contact_page": "", "personal_line_he": "", "flags": "",
      "rugs": [{"slug": "", "name": "", "url": "", "sizes": [{"label": "", "w": null, "l": null, "price_ils": null}], "material": "", "colors": "", "style_fit_guess": {"nordic": 0, "warm-modern": 0, "japandi": 0, "mediterranean": 0, "modern-country": 0, "boho": 0}, "slots": ["<room>/<slot>"], "envelope": "yes|borderline|no", "image": "<absolute local path>"}]}]}
   ```
2. `docs/suppliers/rugs-il-boutique-2026-10-16.md`, in Hebrew: a ranked table of the suppliers (with email), and per supplier its rugs.

## Acceptance
- At least 15 suppliers that really are boutique, handmade or special, and Israeli (selling in Israel).
- Each has a public way to reach them, and a URL for every claim.
- At least 2 fitting rugs per supplier, with images downloaded.
- No invented numbers: use null and "לא צוין".

Return a short Hebrew summary:
- how many suppliers;
- the best 5;
- which slots and styles they cover;
- the price range;
- anything blocked.
