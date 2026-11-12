# Brief: S23, fixes from QA S21 (frontend-dev, 2026-11-12)

This continues the interface track, `briefs/site-interface-track-2026-11-07.md`, with the same working rules. It starts **after S22** (`briefs/site-s22-qa-fixes-2026-11-12.md`). Read S22's README first: `qa/reports/2026-11-07-site-track/s22/README.md`.
- **The source:** `qa/reports/2026-11-12-site-track-qa-s21.md` plus `.json`, and the tools, data and screens in the folder of the same name. It was measured on `7b42ddc1`.
- **The verdict:** S21 passes on condition. ת63 is closed in the shop; ת64–ת66 are closed; both P3 extensions are approved.
- **QA's tools are yours to reuse:** `tools/cart-flash.mjs`, `tools/bfcache.mjs`, `tools/history-db.mjs`, `tools/qa-s21-log.test.ts.txt`. Run them on your build as the acceptance for each item below. Note that Playwright turns the back/forward cache off by default; QA turned it on.

## Before `HD_PUBLIC=1`: ת72, the `#c=` carrier
- **(a) Planting:** any page adopts a cart id from a link when storage has no cart, even when storage works. A link with someone else's `#c=` plants their cart, and the visitor sees and changes it up to checkout.
  - **The fix:** adopt `#c=` only when storage is not usable (`!usable()`), and only on `/cart/` and `/checkout/`. Everywhere else, ignore it and strip it.
- **(b) Same-document link:** without storage, "סל" in the header while already on the cart leaves `#c=` in the URL and in the tab's history.
  - **The fix:** don't add the id to a same-document link.
- **(c) Browser history:** the profile's History database keeps `/cart/#c=` and `/checkout/#c=`.
  - **The fix:** carry the id in `window.name` (or another non-URL channel that survives the navigation) instead of the URL. If that isn't reliable across the browsers we support, document it as a known limit in the README and the launch checklist, with the reason.
- **An e2e for each of (a), (b) and (c).**

## Recommended before `HD_PUBLIC=1`, and required before the story is public: ת73 and ת74
- **ת73 (a), the shop:** an add after a failed load overwrites the quantity (×2 → ×1 on the server).
  - **The fix:** an add after a failure loads again first. If the load still fails, refuse the add and show the error.
- **ת73 (b), the story:** "המראה כולו לסל" before the saved cart loads takes ×3 down to ×1 and doesn't see "already in the cart". This is S21's old bug, in the story.
  - **The fix:** `add` and `addLook` wait for the load, as in the shop.
- **ת74, the story:** a failed load (500, 503, no network) shows "0" and "הסל ריק." over a saved cart of 6, with no error and no retry.
  - **The fix:** tell 404/409 (really no cart) apart from failure. On failure: an empty counter, the error, and "לנסות שוב", as in the shop.
- **An e2e for each,** in the shop and the story.

## Low
- **ת75, back/forward cache:** a page restored from the cache shows a stale count ("סל (1)" when the cart has 2).
  - **The fix:** on `pageshow` with `persisted`, load the cart again, in the shop and the story. Add an e2e with the cache on.
- **ת76, log redaction residue:**
  - split before a capital that starts a Camel word: `(\p{Lu})(?=\p{Lu}\p{Ll})` (DANAGat, XMLDana);
  - match a multi-word value without its spaces too (danagat, TELAVIV, נועהבןדוד);
  - decode %XX and \uXXXX before matching;
  - treat a switch between scripts as a boundary (Noaלוי).
  - Keep ordinary words whole (QA's 36-word list), and report the new cost honestly (ה36: `max_retries`).
- **ת77, `house.spec` (ת22):** it repeats Enter every 5 s, even after hydrate, so a click lost after hydrate would pass unseen.
  - **The fix:** retry only while the hotspot has no listener; or wait for hydrate, then one click with a 15 s timeout.
- **ה29:** when the PUT takes more than 4 s, the cart says "הסל ריק." and "סל (0)", and the line reaches the server later without the page updating.
  - **The fix:** mark a pending write so the cart page reads again when it lands. Never show "empty" while a write is pending.
- **ה30:** without JS, the cart and checkout stay "loading" forever. Add a `noscript` line that says what to do, using existing copy where it exists; otherwise take a default and list it for master-designer.
- **ה32 and ה33, the rights gate:**
  - print the known limits in the console line too, and add the negative (inverted image) to the list;
  - make `npm run check:rights` write its JSON;
  - print how many flat supplier forms there are.

## For the designer, not this sprint
ה28 (a visual for the up-to-4 s wait) and ה35 ("נסו לרענן את הדף" next to "לנסות שוב") go to master-designer. Don't invent copy or a visual for them now.

## Acceptance
- **All the checks:** typecheck, lint, format:check, vitest, e2e, a11y, budget, check:config, check:rights, check:promises, and the encoding gate.
- **New tests:** for ת72 (a)–(c), ת73 (a) and (b), ת74, ת75, ת76 (QA's residue list as an external file) and ה29.
- **QA's `cart-flash.mjs`:** still 0 empty states in every condition, including the story with a failed load.
- **No regression:** S21's ת63 numbers; S20's `mut-s20.sh` (no new gaps beyond what S22 closes); the site's honest lines (0 findings in every build).
- **Weights:** room JS ≤ 74 KB is the goal set in S13; report it, and don't raise the budget.
- **Evidence:** in `qa/reports/2026-11-07-site-track/s23/`, with a README and the numbers per item.

## Fixed rules
- No commits, no var2, no keys, no network beyond npm. Every `npx` with `--no-install`.
- No real contact details, names or phone numbers in any file. Test names are made up.
- If your context runs low, stop where the checks are green and write a "where I stopped" section.
- Return a short Hebrew summary that ends with your open questions and the default you took for each.
