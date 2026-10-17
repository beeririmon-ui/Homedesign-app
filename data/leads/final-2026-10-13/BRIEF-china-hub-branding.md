# A middle station in China: branding and faster shipping to Israel (2026-10-17)

The owner (2026-10-17): "במקביל נחפש חברה שמשמשת כמעין תחנת ביניים בשילוח בסין שיכולה אולי למתג ולזרז שליחויות? או פתרון אחר?"

## What we need
- **Collect and repack:** a company in China that receives our orders from several suppliers (CJ, AliExpress, 1688/Taobao, factories) and checks them (QC, photos). It **repacks them in our brand**: a box or mailer with a logo, tissue, an insert card, a sticker. The order then leaves as one parcel.
- **Faster delivery:** today CJPacket to Israel takes 12–50 days, and the AliExpress median is about 10–15. We want a dedicated Israel line, about 5–10 days, with tracking and VAT/DDP handled.
- **Start small:** from 1 order a day, with no high minimum. OneStop refused: they want 200 orders a month.
- **Heavy items as a bonus:** sea consolidation to Israel for heavy goods. This ties to the owner's decision of 2026-10-17: heavy products are shown as "המלאי אינו זמין כעת" with a waitlist, and are ordered in bulk when there is demand.

## Already researched, don't repeat it
- `docs/suppliers/deep-research-2026-10.md`: agents, ePacket, LCL, BuckyDrop, HyperSKU, Supplyia, Leeline, Superbuy, Cainiao/Uspeed IL FC.
- `docs/suppliers/yakkyofy.md`.
- `docs/suppliers/aggregators-2026-10.md`.
- `data/economics/fulfillment-research.md`.
- `docs/suppliers/outreach/README.md`: OneStop said no.

Use these as a base. Go deeper only where they say "לא אומת" for Israel, and add what's new.

## Research
1. **Agents with branding and an Israel line.** Check at least 12 companies (agents, fulfillment centres or 3PLs in Shenzhen, Yiwu or Guangzhou). For each:
   - **Branding:** what they offer (custom box, poly mailer, insert, thank-you card, logo tape, hang tag), and the minimum and price per unit.
   - **Shipping to Israel:**
     - is Israel on their country list or shipping calculator;
     - which line (YunExpress, 4PX, Yanwen, Cainiao, an Israel special line, DDP);
     - days and price for 0.5, 1.5 and 3 kg;
     - the limits on size and weight.
   - **Minimums:** order volume, monthly fee, storage.
   - **Sources they buy from:** 1688, Taobao or AliExpress; whether they take goods from CJ or from our suppliers; whether they consolidate several items into one parcel.
   - **QC:** QC and photos.
   - **API or no-Shopify use:** our store is custom-built, so a "Shopify only" app is a problem.
   - **Contact:** a public email or form. **No contact.**
   - **Reliability:** reviews from Trustpilot or forums, and years in business.
2. **Israel-specific options:**
   - Israeli-owned or Hebrew-speaking agents in China.
   - Israeli companies with a warehouse in China (like OneStop).
   - The lines that go into Israel, such as GAASH, the Uspeed/Cainiao IL FC, and Israel Post ePacket.
   - Where is the real speed? For example, dedicated air lines with Israeli customs clearance.
3. **CJ itself:** CJ has packaging and branding services (custom packaging, inserts) and private inventory. Check:
   - what CJ offers;
   - its price and minimums;
   - whether the faster line to Israel exists (CJPacket Fast, or a DHL eCommerce line);
   - whether CJ can collect goods from 1688 (sourcing) and pack them together with its own products.
   This may be the simplest solution, without a new company.
4. **Zendrop:** check its branding (Zendrop Plus, custom packaging) and its shipping to Israel. Don't use the Zendrop account; public pages only.
5. **Other options:**
   - **An Israeli 3PL** with sea consolidation from China, so we hold local stock for the fastest-selling items. Who in Israel serves small e-commerce brands? Minimums and prices.
   - **A hybrid model:** we brand only the bestsellers and keep the rest unbranded.

## Example economics
For 3 typical products, compare **CJ direct** with **agent + Israel line + branding**:
- a 0.6 kg cotton throw;
- a 1.2 kg ceramic vase;
- a 0.8 kg seagrass basket.

For each, give:
- the cost per unit;
- the days;
- the branding added;
- a one-time setup cost, if there is one.

Use the Studio formula: fx 3.3, VAT 18%, fee 2% + ₪1.2, returns 8%. Every number needs a source, or is marked as an estimate.

## Output
- `docs/suppliers/china-hub-branding-2026-10-17.md`, in Hebrew:
  - **the bottom line:** 3–5 recommendations, ranked;
  - **a table** of every company checked;
  - **the economics;**
  - **for each of the top 3:** what to ask in the first email (a draft only, not sent).
- `data/suppliers/china-hub-branding-2026-10-17.json`, in machine form.

## Rules
- Public pages only, at a human pace. Stop at any login, CAPTCHA or block.
- No sign-ups, forms, emails, chats or quotes. Contact waits for the owner (studio-rules ז, "קודם אתר עובד").
- No invented numbers: use null or "לא פורסם", and give a URL for every claim.
- Don't edit binding docs or the existing research. Only add the two new files.
- No commits.

Return a short Hebrew summary:
- the top 3;
- whether a real Israel line was found, with its days and price;
- CJ branding: yes or no, and at what price;
- your recommendation.
