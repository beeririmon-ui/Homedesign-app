# Israeli rugs, round 2: handmade, natural and full of character (2026-10-20)

The owner (2026-10-20): "קיוויתי לראות שטיחים מחומרים טבעיים יותר באוסף שאספת, עבודות יד ודוגמאות צבעוניות. אספת שטיחים מאוד בנאליים".

## What went wrong in round 1
- The 2026-10-16 research (`docs/suppliers/rugs-il-boutique-2026-10-16.md`, `rugs-il-online-2026-10-16.md`) leaned on catalogue retailers.
- The designer's 19 picks (`rugs-il-picks-2026-10-19.*`) leaned on plain neutrals: plain wool, plain jute, sisal.
- The colourful handmade rugs that were found were dropped as "one-off" or "too saturated".

The owner wants the opposite: **handmade, natural fibre, patterned and colourful rugs with character.** Plain machine-made neutrals are the last resort, not the default.

## What we want
- **Handmade:** hand-knotted, hand-woven, flatweave, kilim, dhurrie, sumak, Beni Ourain, Azilal, Boujad, gabbeh, Bedouin and Druze weaving, Israeli weavers and textile artists.
- **Natural fibre, 80% or more:** wool, cotton, jute, hemp, linen, silk. Boucherouite is often synthetic rags, so check the fibre.
- **Pattern and colour:** geometric, striped, tribal and Berber motifs, overdyed, earthy colours (terracotta, ochre, rust, indigo, olive, saffron), and some bold ones.
  - Nordic and japandi still need calm, but with a handmade texture: a Beni Ourain with fine lines, an undyed wool kilim, a hand-loomed stripe.
  - The other four styles should get real colour and pattern.
- **Repeatable:** catalogue items, or made to order: "a rug like this one, in this size".
  - A one-off vintage piece counts only if the supplier says it can supply similar pieces again. Mark each rug: catalogue / made to order / one-off.
- **Sizes:** the slot envelopes in `data/slots/*.json`. The main ones:
  - living-room 200–240 × 290–340;
  - master 280–300 × 200–220;
  - dining 200–240 × 200–230 (the designer's spec after LQ2 is 230–240 × 245–250);
  - kids 120–160 × 170–220;
  - kitchen runner 45–60 × 240–280.
  Made to order is welcome for every size.

## Where to look
- **Israeli handmade and weaving:**
  - Bedouin women's weaving projects in the Negev (Lakiya / Sidreh, Desert Embroidery and others);
  - Druze weaving;
  - Israeli weavers and textile studios that sell rugs;
  - Bezalel and Shenkar graduates with rug studios;
  - craft fairs' public exhibitor pages.
- **Israeli importers and galleries of handmade rugs:** Moroccan, Afghan, Persian gabbeh, Indian dhurrie, vintage kilims, overdyed.
- **Re-check, with the new taste**, the colourful sellers we already found: פנטזיה מרוקאית, דאר מרקש (real photos only), הבית המרוקאי, גלריה קילימס, Art Java, Tomik, the kilims of מתריב, Afrita, David Ashkenazi, Elsebeth Studio, לקייה via אחותי, and the kilim lines of HōM and others.
- **Israeli sellers on Etsy and on marketplaces:** only if the public pages open.
- **Sensitive locations:** a seller in the West Bank, or linked to the Carmel group, is listed with a flag and **not** contacted until the owner decides. This is studio rule ז.

## For each supplier
- name, site, city;
- the public contact: email, form or phone;
- any trade or B2B signal;
- **at least 3 rugs that fit**, each with:
  - link, size, price;
  - material and fibre %;
  - technique and origin;
  - catalogue / made to order / one-off;
  - one image downloaded to `/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/rugs2/<supplier>/<rug>.jpg`, with plain curl, resized to about 1,000 px, as a JPEG under 400 KB, checked with `file`.

**Target:** 15–25 suppliers and 60+ rugs, with **at least half of them patterned or colourful.**

## Output (no commits)
- `docs/suppliers/rugs-il-handmade-2026-10-20.md` (Hebrew): a bottom line, the suppliers table, and the rugs per supplier.
- `data/leads/final-2026-10-13/rugs-il-handmade-2026-10-20.json`: the same shape as `rugs-il-boutique-2026-10-16.json`, plus the fields `technique`, `pattern` (plain / textured / patterned / colourful) and `repeatable`.

## Rules
- Public pages only, at a human pace. Stop at any login, CAPTCHA, Cloudflare or block. No scraper APIs, no user-agent tricks.
- No contact, forms or sign-ups.
- Don't edit any existing file.
- No personal phone numbers of private people in files; business lines only.
- Validate the JSON.
