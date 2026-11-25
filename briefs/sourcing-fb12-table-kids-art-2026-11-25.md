# Brief: FB12 sourcing, the coffee table and kids' art (sourcing-agent, 2026-11-25)

## Why
The owner asked for a new living-room coffee table, and for child-appropriate art in the kids' rooms with many options (FB12). The designer's proposal is `docs/proposals/wm-fb12-2026-11-25.md`. Read part א.3 (the table spec), ב.3 (the art spec per room), and the two line tables in chapter ג.

The owner wants faster progress. When the table candidates are back, the manager asks the owner one question (FB12-T).

## The task
1. **The coffee table: ג.1, rows 1–6.**
   - Israel first. 6–8 candidates.
   - For each:
     - URL, model and price;
     - stock or lead time, shipping, assembly and warranty;
     - dimensions, including top thickness and leg section;
     - solid or veneer;
     - finishes by name;
     - **at least 3 photos of a real unit:** straight side, three-quarter, and a close-up of edge and grain. Give the URLs. Don't download into the repo;
     - an estimated L\* of the finish, against א.3.
   - Apply the field rejection list in ג.1.
2. **Kids' art: ג.2, rows 5–6.**
   - Israeli artists who sell their own prints, and Israeli print shops with a declared licensed kids' collection. **Listing only. No contact.**
   - Up to 4 artists per room, and 1–2 shops.
   - For each: URL, the series (at least 3 designs in 30×40 or A3), the price, and the rights wording quoted, or "not stated".
   - Apply the field rejection list in ג.2.
3. **Not this run:**
   - rows 1–2 of ג.2, the existing AE cards. Their designs need an image review, which another agent does.
   - rows 3–4 (CJ and new AE). They wait for the CJ API to be reactivated and a new AE token.

## Cards
- **The table:** one card per candidate, per `data/product-card.schema.json`, in `data/products/living-room/coffee-table/`. The slot isn't registered for warm-modern yet; the manager knows. Fill in:
  - `style_scores.warm-modern` with a one-line reason;
  - `kind`: a sold product;
  - anything you couldn't verify, marked as such.
- **The art:** no cards this run. A ranked list is enough.

## Outputs
- the table cards;
- **`data/leads/fb12-2026-11-25.md`:**
  - the table: the ranking, with the best three and the reasons;
  - the art: per room, the artists and shops, with their series and the rights wording.

## Fixed rules
- Official public pages only. No scraping AliExpress or BigBuy, no scraper services, no CAPTCHA bypass, no user-agent spoofing, no sign-ups.
- **No contact with any supplier, store, maker or artist.**
- Never write a key, token, phone number or business id into any file.
- Supplier images stay out of the repo: URLs only.
- Don't edit binding documents or slots. No commits.
- Return a short Hebrew summary:
  - the table: the count and the top three, with price and real-photo status;
  - the art: the artists and shops per room;
  - what you couldn't reach.
