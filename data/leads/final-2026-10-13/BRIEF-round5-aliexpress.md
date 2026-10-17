# Round 5, AliExpress: for the session that has the AliExpress keys (2026-10-17)

This is the AliExpress part of the massive round to 80% in every style. The rest of the round runs in the cloud session (CJ, Zendrop and the local cache): `BRIEF-round5-massive.md`. **Read that brief first.** Its rules hold here too:
- the goal and the order of work;
- Israeli-value pricing with comps;
- honest fit guesses;
- the card rules;
- the cap;
- the output shape.

## Update 2026-10-17 (owner decisions, read on every pull)
The owner decided on the round-5 audit questions. See `docs/studio-rules.md` ה.10 "מוצר שנראה איכותי" and ז "החלטות המשתמש על ביקורת המעצב".
- **Premium pricing:** a product that looks high-quality may be priced up to the typical Israeli comp. Never above the highest comp, and still no loss.
- **Furniture-type slots stay for sale:** shower stool, towel ladder, step stool, kids' chair, kids' bookshelf, gallery stool, pouf, planters.
- **New envelopes:**
  - `work/shelf-boxes`: both boxes h 12–18.
  - `hall/storage-boxes`: each box 26–34 × 20–30 × 20–35, or one long basket 55–68 × 25–30 × 20–30.
- **Prints:** sold unframed, and the product page says "ללא מסגרת".
- **The sofa slot outside Nordic** is a designed fabric laid on the sofa. See `round5/sofa-fabric-brief.md` once it's pushed.
- **Coverage:** `final_round_coverage.py` now applies the master-designer's audit (`round5/designer-audit.json`).
  - Near-identical items count as one option: the pleated walnut floor lamps were all one look.
  - Kids' items need EN71 declared, not only CE.
- **Round 5b:** a cloud team is on furniture and boxes now. Its queue is `round5/ae-queue-5b.json`.

## Step 0. Access
1. Pull the branch `claude/agent-system-brand-launch-ax87dv`.
2. Check that the token is there: `python3 scripts/ae/auth.py status`.
   - If there is no token, or it can't be refreshed, the owner authorizes once, per `scripts/ae/README.md` §2.
   - In a terminal, the owner types the code himself. In a cloud session the owner may paste the redirect link (`127.0.0.1/callback?code=...`) into the chat: the code is single-use and expires in minutes (studio-rules ח.3). Exchange it at once with `auth.py code`. Never a key, a secret or a token in a chat or a file.
   - The app is in Test status, so the token lasts about a day and the refresh about two. `ds.py` refreshes by itself while it can.
3. Refresh the targets, so you work on what is still missing after the cloud teams:
   ```bash
   python3 scripts/sourcing/final_round_coverage.py
   python3 scripts/sourcing/round5_targets.py
   ```

## Step 1. Open the queue
The cloud teams could not open AliExpress listings. They put the best ones in `data/leads/final-2026-10-13/round5/ae-queue-*.json`, each with a slot, styles and a reason.

For each item:
- Open it: `product <id> --slot <room>/<slot>`, then `freight` for the fitting SKU.
- Check it against the slot and the styles.
- Write a card where it passes: `card <id> --slot <room>/<slot> --sku <sku>`. Then complete the DRAFT fields (colours, dimensions, materials) from the photos and the description.

## Step 2. New searches for what is still short
For each target in `round5/targets.json` that is still short:
- **Skip** queries already run: `already_searched_aliexpress`, and the cached queries under `data/sources/aliexpress/queries/`.
- **Skip** products already judged in `results/round5-*.json`.
- Use the new vocabulary from `BRIEF-round5-massive.md` step 3:
  - seller style words, such as "pastoral", "french retro", "ins style", "wabi sabi", "coarse pottery", "cream style";
  - material plus form;
  - trade names;
  - cm and inch sizes.
- Sort by `orders,desc`, then look at quality, not price.
- **Image search** (`image-search <url> --type similar`), from near misses: the right look in the wrong size, or a loss on freight.
- **Lighting:** CE and 220–240V as stated, or shade-only for pendant and ceiling slots (rule ז, 2026-10-14). `specialinfo` is not allowed for our app, so read the Certification field in the product properties.

Command shape:
```bash
python3 scripts/ae/ds.py --by round5-ae --run-id round5-ae --max-calls 4000 --hide-seen search "<words>" --sort orders,desc
```
The daily AliExpress budget is in `scripts/sourcing/budget.py`.

## Output (no commits from agents; the session that runs this commits and pushes)
- **Cards**, per `data/product-card.schema.json`, with `status: "candidate"` and a `notes` line "round5 2026-10-17 (AliExpress):".
- `data/leads/final-2026-10-13/results/round5-aliexpress.json`, in the same shape as the other round-5 results. Every candidate you judged, with `card_id` where a card was written.
- `data/leads/final-2026-10-13/results/round5-aliexpress.md`, a short Hebrew summary:
  - per style, how many slots now reach 3 options;
  - the queue items opened;
  - the new words that worked;
  - calls used;
  - what's still blocked.
- At the end, run `python3 scripts/sourcing/final_round_coverage.py` and put the new numbers in the summary.

## Rules
- Official API only: no scraping, no scraper APIs and no user-agent tricks.
- Never contact a seller, order or import.
- Never print, read or write keys, secrets or tokens. Only the scripts touch `~/.cache/ae/`.
- Do not edit existing cards, binding docs, `data/slots/`, `targets.json`, or the Studio.
- Validate every JSON you write (`python3 -m json.tool`).
