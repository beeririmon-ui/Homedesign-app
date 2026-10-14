# Small Israeli lighting suppliers for a first outreach round (2026-10-14)

The owner (2026-10-14):
- "תאורה זה חלק חשוב מחווית האתר".
- On outreach to Israeli lighting suppliers: "עדיף לספקים קטנים קודם ... קמחי תאורה הם גדולים, מפרסמים ברדיו ובטלוויזיה, אולי למצוא ספקים קטנים שישמחו לסטארטאפים ולא כאלה שרוצים בידול וייחוד".

The full rule is in `docs/studio-rules.md`, section ז. The outreach text is `docs/suppliers/outreach/lighting-il.md`.

## The task
Find **8–12 small Israeli lighting suppliers** that would welcome a startup partnership, and match their models to our lighting gaps. This is research only.

**Who counts as "small"?**
- Any of these:
  - a local maker or workshop (wood, ceramic, linen, paper, rattan, concrete);
  - a design studio with its own line;
  - a small importer or online-only shop;
  - one or two showrooms.
- Not:
  - chains;
  - brands with radio or TV campaigns, or many branches (Kamchi Lighting, Deal Teora, ACE, Home Center and the like);
  - "collectible design" studios that sell one-off pieces under their own exclusive brand.

**Good signs of openness:**
- They already sell through other shops or marketplaces: SAGA TLV, concept stores, Etsy, Instagram shops, design markets.
- They have a "לעסקים", "לאדריכלים ומעצבים" or "סיטונאות" page.
- They do collaborations, take custom orders, or offer consignment.

## Already known: re-check, and classify by size
- In `docs/suppliers/decor-il-2026-10-12.md` §2: Nord Light, Fine Lab Home, Or-Ad, Orban. Kamchi and Deal Teora are large, so list them as "later".
- In `docs/suppliers/masterpiece-makers-2026-10-12.md`: LALAMPA and other lighting makers. These are premium and may be masterpiece-only, so say so.
- In `docs/suppliers/directory.md`: Iris Design Studio, Divolight, La Lampa.
- In `data/leads/final-2026-10-13/results/il-lighting.json`: 105 Israeli-shop lights already matched to slots. Find the shops behind them that are small.

## What fits
- **The gaps:**
  - lighting gaps in `data/leads/final-2026-10-13/coverage.json` → `remaining.<style>`, where category contains "light";
  - slot envelope and electrical needs in `data/slots/<room>.json`.
  - The biggest needs are floor lamps (living, master), wall sconces (living, kids, work), the hall table lamp, the work desk lamp, picture lights, the bath ceiling light (IP44), and pendants for mediterranean, modern-country and boho (rattan, woven, linen, pleated fabric, 45–55 cm).
- **Styles:**
  - `docs/design-bible/nordic.md` and `nordic-dining.md`;
  - `docs/design-bible/<style>-brief-draft.md` for the other five styles;
  - `.claude/skills/interior-design-rules/`.
- **Standard:** lighting sold in Israel needs ת"י 20 (studio rules ד.3). Record what each supplier declares. Missing information isn't a reason to drop a small maker; mark it "to ask in message 2".
- **Price:**
  - Note the retail price.
  - The owner will ask for a trade price, so estimate the margin at a 30% and a 40% trade discount, using the studio formula: net = price/1.18; contribution = net − cost − (0.02·price + 1.2) − 0.08·net.

## Hard limits
- Public pages only, at a human pace. Stop at any login wall or block.
- No contact forms, messages, sign-ups or emails.
- Don't write product cards. Don't edit binding docs, slots or cards.
- Personal phone numbers of private people stay out of the repo; business contact details from public pages are fine.

## Output
1. `docs/suppliers/lighting-il-small-2026-10-14.md`, in Hebrew:
   - a ranked table: supplier, what they make, size and why "small", signs of openness, standard status, public email or contact page, styles, and the gaps they can fill;
   - per supplier:
     - the **personal line** for message 1, one sentence on what we genuinely liked;
     - the **model list** for message 2: 3–6 models, each with URL, dimensions, retail price, the slot or style it's for, style fit (1–10), and the margin estimate at a 30% and a 40% discount.
   - A short "later" list: the large suppliers, and why.
2. `data/leads/final-2026-10-13/lighting-il-small-2026-10-14.json`, the same data as JSON:
   ```json
   {"date": "2026-10-14", "suppliers": [{"name": "", "url": "", "type": "maker|studio|small-importer|online-shop", "size_note": "",
     "openness": "", "standard": "", "contact_public": "", "personal_line_he": "",
     "models": [{"title": "", "url": "", "dims_cm": "", "price_ils": 0, "slot": "<room>/<slot>",
       "style_fit_guess": {"nordic": 0, "warm-modern": 0, "japandi": 0, "mediterranean": 0, "modern-country": 0, "boho": 0},
       "margin_at_30_off": null, "margin_at_40_off": null}]}],
    "later": [{"name": "", "why": ""}]}
   ```
   Make it valid JSON. The art director checks it with Python. Put it in this folder, **not** in `results/`.

## Acceptance
- At least 8 suppliers that are small by the definition above. If fewer exist, say so honestly.
- Each one has a public way to reach them (email preferred), and a URL for every claim.
- Each one has at least 2 models with style fit ≥ 7 in a style that needs that slot.

Return a short Hebrew summary:
- how many suppliers you found, and the top 5;
- which gaps they cover;
- who has the Israeli standard declared.
