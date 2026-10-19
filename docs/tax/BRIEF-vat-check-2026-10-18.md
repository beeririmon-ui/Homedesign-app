# A tax check on VAT, customs and dropshipping (2026-10-18)

The owner (2026-10-18): "תוכלי לעשות בדיקת רואה חשבון לעניין?". This follows VAT1 in `status/decisions.json`.

**This is research, not professional advice.** The output says so at the top. It prepares the owner for a short, precise meeting with a CPA or a customs broker, and it shows what the law and the Tax Authority actually say, with sources.

## Background (read first)
- `docs/suppliers/china-hub-r2-lines-2026-10-18.md` §4: the VAT exemption is back at $75 since 2026-06-01. Above $75, 18% applies on the CIF value, plus release fees. Shipments from one supplier within 72 hours count as one.
- `docs/suppliers/china-hub-r2-2026-10-18.md` §3: 34 imported products are priced above ₪247. If the declared value is the customer price, all 34 cross $75, and the customer pays ₪158–338 at the door (estimate). §3.4 has the 3 questions for an accountant.
- `data/economics/fulfillment-research.md` §1: earlier findings.
  - The customer is the importer in dropshipping.
  - The sale is taxed at 18% as an Israeli transaction, per two accountants' blogs (thebookkeepers 2018, Ziv Shifer).
  - The import VAT can't be offset, so above $75 VAT is paid twice.
  - Customs on our categories is 0%.
  - Lighting standards may apply even to personal import.
  - **No official ruling was found.**
- The Studio economics assume an עוסק מורשה: net = P/1.18 (`data/economics/settings.json`). The owner's VAT status is not recorded in the repo. Cover both עוסק מורשה and עוסק פטור.

## Questions to answer, from primary sources first
1. **The declared customs value in dropshipping.**
   - Which value goes on the parcel (CN22/CN23) and into the customs valuation: the supplier's price to us, or the customer's price to us?
   - Check פקודת המכס on transaction value ("המחיר ששולם או שישולם... כשנמכרו לייצוא לישראל"), the customs procedures for personal import (נוהל יבוא אישי), and what Israel Post and couriers ask for.
   - Who is the importer when the supplier ships directly to the customer?
   - What are the risks of an under-declared value?
2. **Is VAT charged twice?**
   - Does an Israeli dealer who sells goods that sit abroad at the time of sale, delivered from abroad to an Israeli consumer, have to charge VAT on the sale? Check חוק מס ערך מוסף: "עסקה", "מכירה", "עסקה בישראל", the place of supply of goods, and section 30 (zero rate).
   - Is there a Tax Authority circular, ruling (החלטת מיסוי), court decision or official FAQ on dropshipping or on selling goods located abroad?
   - Which positions do Israeli CPAs publish, and do they agree?
3. **Legal ways to avoid double tax and charges at the door**, with what each requires:
   - the business as importer of record (DDP courier, then deduct the import VAT as input tax);
   - collecting the import VAT at checkout, as AliExpress does above $75;
   - splitting an order (and the 72-hour rule);
   - a local stock model.
4. **עוסק פטור vs עוסק מורשה in 2026:**
   - the turnover ceiling for עוסק פטור in 2026;
   - whether it's allowed for this kind of trade;
   - what changes in the price formula (no VAT charged, no input deduction);
   - what happens when the ceiling is crossed.
5. **The product page and checkout:** what חוק הגנת הצרכן requires about taxes and fees that may be charged on delivery. Check עסקת מכר מרחוק (14ג), the full price display (17ב) and gilui naot. Give recommended wording.
6. **Standards on personal import** for our categories: lighting (ת"י 20), kids' items and food-contact ceramics. Has the "מה שטוב לאירופה" reform or the 2024–2026 changes to צו יבוא חופשי changed what applies to a consumer's personal import? Resolve the conflict between sources noted in Track A.

## Sources
- Use, in order:
  - laws on he.wikisource.org or the Knesset site;
  - Tax Authority and customs publications;
  - Israel Post and the Consumer Protection Authority;
  - court decisions on public sites;
  - CPA and lawyer blogs, marked as opinion.
- Date every source. Mark: **מקור רשמי**, **דעה מקצועית** (a blog), **לא אומת**, **ישן** (before 2024).
- Public pages only. Stop at any login, paywall, CAPTCHA or 403, and never bypass it.
- No contact with anyone. No forms. No ruling requests.

## Output
- `docs/tax/vat-import-check-2026-10-18.md`, in Hebrew:
  - a disclaimer line;
  - a bottom line of at most 8 points;
  - for each question: the short answer, the legal basis with sources, the confidence (high, medium or low), and what a CPA must confirm;
  - **"מה זה אומר למחירים שלנו":** the effect on the Studio formula, in each status (מורשה, פטור), for the 34 products above ₪247. Don't change any price or file.
  - a sharper list of questions for the CPA or customs broker, at most 8. No personal details.
- `data/economics/vat-import-check-2026-10-18.json`: the answers, the sources and the confidence, in machine form.

## Rules
- Don't edit any existing file.
- No personal details of the owner.
- No commits.
- Validate the JSON.
