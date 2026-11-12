# Brief: S21, fixes from QA S19 (frontend-dev, 2026-11-12)

This continues the interface track (`briefs/site-interface-track-2026-11-07.md`), with the same rules. It starts after S20. The source is `qa/reports/2026-11-12-site-track-qa-s19.md` plus `.json`, with its tools, data and screens.

## Before launch: ת63, the cost of the full-page cart and checkout
- **No "סל (0)", "הסל ריק." or "הסל ריק, אין מה לשלם."** while a saved cart is loading. Show a quiet loading state (`aria-busy`) instead. Measure it with QA's slow-API case (800 ms).
- **No storage:** carry the cart id in the load's fragment (`#c=`), and remove it after reading. The cart must survive the full-page navigation.
- **An add still in flight** when the cart is opened must not be lost: use `keepalive` for cart writes, or wait for it.
- **An e2e for each.**

## Small
- **ת64:** use letter-only word boundaries for log redaction, `(?<!\p{L})…(?!\p{L})`.
- **ת65:** a closed list of system error codes. A supplier code shaped like one (`E_ORNA`) never passes.
- **ת66:** rule A normal-vs-normal applies only when d ≤ (bits a + bits b) / 2 (QA's P3). Prove 321/321 and 12/12 are kept, and that the margin improves.
- **QA note ה14:** 11 more negations ("w/o", "texture-less", "Texture: N/A", "Smooth", "flat", "Embossed: N", "Textured: False", "isnt", "doesnt", "(texture? no)").
- **QA note ה15:** document flip-with-colour and collage as known limits, in launch checklist line 1.5 and in the gate's header.
- **QA note ה17:** make the encoding e2e robust to load. Capture only when the page is settled. Don't skip it.
- **Update the launch checklist** lines 1.5, 6.1 and 6.2 with QA's proposed text.

## Acceptance
- All the checks pass, with new tests.
- The evidence goes in `qa/reports/2026-11-07-site-track/s21/`.

## Fixed rules
- No commits, no var2, no keys, no network beyond npm.
- Never `npx` without `--no-install`.
- Return a short Hebrew summary.
