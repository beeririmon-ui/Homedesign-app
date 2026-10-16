# Israeli online rug retailers like Karpetim, for an affordable tier (2026-10-16)

The owner (2026-10-16): "תחפשי עוד אתרים שדומים לקרפטים ולפה בארץ, וננסה להציע להם שת"פ". Full rule: `docs/studio-rules.md` ז.

## What we want
- **Israeli rug retailers that sell online and deliver to the customer's home**, like carpetim.co.il.
  - This time chains and mass retailers are welcome. This is the **affordable tier**, next to the boutiques.
- **Find 10–15 of them**, excluding:
  - Karpetim, which is already done (`data/leads/final-2026-10-13/rugs-il-karpetim-2026-10-16.json`);
  - the boutiques in `data/leads/final-2026-10-13/rugs-il-boutique-2026-10-16.json`;
  - anyone already contacted: Nesicha Online, NOOL, KADO HOME;
  - קבוצת כרמל / Carmel Carpets (a sensitivity note; the owner decides).
- **Names to start from:** names our earlier research excluded as mass market or that were blocked (`docs/suppliers/rugs-il-boutique-2026-10-16.md`, near the end):
  - Carpetland, קואלה, סולה, הום אנד קארפטס, מחסני שטיחים יפו;
  - BuyCarpet, השטיח האדום / HōM, which has a B2B page (`docs/suppliers/decor-il-2026-10-12.md`);
  - צמר / שאפור, הוגה, טולמנ'ס;
  - שטיחי ירושלים, בית השטיחים אונליין, Israelcarpet, מילמור, Sleeperz.
  - Plus others you find ("שטיחים אונליין משלוח עד הבית", "חנות שטיחים אונליין").
  - If a site blocks you (403, Cloudflare), record it as blocked and move on. Don't work around it.

## For each retailer
- name, website, city or showroom, and size (branches, online only);
- importer or maker;
- delivery terms and cost;
- returns;
- any business, trade, designers or wholesale page (B2B signs);
- a **public business email**, otherwise the contact page;
- a one-sentence Hebrew personal line, starting "אהבנו את ...".
- **5–8 rugs that fit our slots** (envelopes in `BRIEF-rugs-il-boutique.md`):
  - prefer natural materials (wool, cotton, jute, sisal) and quality looks;
  - synthetics are allowed but must be flagged;
  - include runners (70–80×250–270, 58–65×680–710, 45–60×240–280), kids 140×200, and dining 200–240×200–230 wherever they exist.
  - For each rug: URL, every size with its price, material, colours, a style-fit guess for the six styles, the slot(s), and the envelope fit (yes / borderline ±10 cm / no).
  - **Download the main image** to `/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/rugs/<retailer-slug>/<rug-slug>.jpg`, using curl, at about 1000 px and under 400 KB, then check it with `file`.

## Limits
- Public pages at a human pace.
- No forms, carts, messages, sign-ups or logins.
- No user-agent tricks.
- Don't edit existing repo files.
- Leave out the mobile numbers of individuals.

## Output
1. `data/leads/final-2026-10-13/rugs-il-online-2026-10-16.json`, in the same shape as `rugs-il-boutique-2026-10-16.json`. Add `"natural": true|false` per rug. Validate it with Python.
2. `docs/suppliers/rugs-il-online-2026-10-16.md`: a short Hebrew report, with a ranked table (email, B2B signs, delivery) and the best rugs.

Return a short Hebrew summary:
- how many retailers;
- which look open to B2B;
- the best rugs and price ranges;
- the slots and styles covered (runners, kids);
- anything blocked.
