# Solutions for import VAT and charges at the door (2026-10-19)

The owner (2026-10-19): "אין פתרון לזה? עמיל דיגיטלי שלא חושף? מערכת שמזמינה בחבילות נפרדות לארץ? פורוורדר שיודע לשלם מע"מ מראש?"

**Read first:** `docs/tax/README.md` and `docs/tax/vat-import-check-2026-10-18.md`. The problem in short:
- Above $75, the customer pays 18% import VAT plus release fees at the door.
- If our sale is taxed too, VAT is paid twice, and we can't offset the import VAT.
- 34 imported products are priced above about ₪247.

**This is research, not professional advice.** Only legal methods count. A method that works by under-declaring the value, or by splitting an order on purpose to stay under $75, is **not** a solution. If you find one, list it under "not allowed" with the reason and the source, and don't recommend it. Many Chinese "tax-included" (包税) lines may work by under-declaring; check how each one actually settles the VAT.

## Check, for each solution
1. **VAT collected in advance (IOSS-like).**
   - Is there an Israeli regime in 2026 that lets a foreign seller or platform collect the import VAT at checkout, so nothing is due at the door? AliExpress has done this above $75 since mid-2026: how does it work legally?
   - Can an Israeli business, or its supplier, use it?
2. **DDP / tax-paid lines and couriers:**
   - DHL Express "duties and taxes paid", UPS, FedEx;
   - Chinese DDP lines to Israel (双清包税, the Xinhan line in `docs/suppliers/china-hub-r2-lines-2026-10-18.md`).
   - Who is the importer of record? Who pays the VAT, and on what value? Does the customer get a receipt? Is it legal and clean?
3. **A digital customs broker, or the business as importer of record:**
   - Israeli brokers that clear small B2C parcels **in the business's name**, so the business deducts the import VAT as input tax and the customer pays nothing at the door.
   - The cost per parcel. Earlier estimate: about ₪89.
   - Does each parcel need its own customs entry (רשמון)?
   - Do the standards for commercial import then apply (lamps, kids' items)?
4. **The seller pays on the customer's behalf.** Can the seller prepay the import VAT and fees for the customer, through Israel Post's or a courier's online payment before delivery? How is it recorded? It's still the customer's import, so does it remove the double VAT or only the surprise?
5. **Separate parcels.**
   - The exact rule on aggregating shipments (72 hours, same sender), with the source.
   - When separate parcels are legitimate, for example genuinely different suppliers shipping different items.
   - Why splitting doesn't help a single item above $75.
6. **Structure:**
   - **Agent or marketplace model:** the customer buys from the supplier, and we earn a commission, so VAT is only on the commission. What does it require, and what are the risks?
   - **Terms that move delivery abroad** (VAT law s.14, Sale Law s.8(c)): add any source not in the 2026-10-18 check.
7. **Local stock for the bestsellers:** a bulk import with the business as importer (input VAT deducted), plus a 3PL. Link to `data/economics/fulfillment-research.md`; don't redo it.

For each solution give:
- how it works;
- the legal basis, with dated sources;
- the cost per parcel;
- whether the customer pays at the door;
- whether it removes the double VAT;
- who offers it, by public name only;
- the confidence;
- what a CPA or customs broker must confirm.

## Sources and rules
- Primary sources first: laws on he.wikisource.org, Tax Authority and customs publications, Israel Post, the couriers' official pages. Blogs are opinion. Date every source and mark it: מקור רשמי / דעה מקצועית / לא אומת / ישן.
- Public pages only, at a human pace. Stop at any login, paywall, CAPTCHA or 403. No scraper APIs, no user-agent tricks.
- No contact, no forms, no quotes.
- No personal details of the owner.
- Don't edit any existing file.
- No commits.

## Output
- `docs/tax/door-charges-solutions-2026-10-19.md`, in Hebrew:
  - a disclaimer line;
  - a bottom line of at most 8 points;
  - a ranked table of the legal solutions;
  - the "not allowed" list;
  - questions to add to the CPA list.
- `data/economics/door-charges-solutions-2026-10-19.json`. It must pass `python3 -m json.tool`.
