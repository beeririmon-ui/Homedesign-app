# A middle station in China, round 2: deep (2026-10-18)

The owner (2026-10-18): "מה עם תחנת אמצע בסין שחיפשנו? בואי נבדוק את האופציה לעומק עוד פעם. אם יש מישהו שימתג וישלח את זה מסין ישירות בזמן קצר יותר."

## The question
Is there a company that does three things for us?
- It receives our orders in China.
- It repacks them in our brand.
- It ships them to Israel **faster than today**, at a price that keeps the margin.

Today's baseline:
- CJ Eub: 12–50 days, billed by actual weight.
- AliExpress: about 10–15 days.
- The market median from China to Israel: 10 days, with 90% within 18 (ParcelsApp).

"Faster" means **measured** delivery days, not the days a company claims.

## Round 1 is the base. Read it, don't repeat it.
- `docs/suppliers/china-hub-branding-2026-10-17.md` and `data/suppliers/china-hub-branding-2026-10-17.json`: 21 companies, 6 lines, 3 Israeli 3PLs, the economics for a throw, a vase and a basket, and email drafts for Tizmun, BuckyDrop and ARTEX.
- Round 1's own list of what it could not verify (§7):
  - **No current Israel-line price.** Uspeed's is from 2022 and "from", Takesend's from 2020, and no agent publishes a price for Israel.
  - **Tizmun:** whether its ₪29–36 packs cover the whole route from China, and the weight limits.
  - **BuckyDrop:** the days and price on its EMS line to Israel, and whether it accepts parcels from other suppliers.
  - **CJ:** the price of custom packaging.
  - **Ceramics:** no breakage policy anywhere.
  - **Speed:** every "5–10 days" is a claim; nothing is measured per carrier.
- The key finding: **fast lines bill by volume.** That kills the margin on vases and baskets. The key question for every line is: actual weight or volumetric, and with which divisor and threshold.
- Older research: `docs/suppliers/deep-research-2026-10.md`, `aggregators-2026-10.md`, `yakkyofy.md`, `data/economics/fulfillment-research.md`, `docs/suppliers/outreach/README.md` (OneStop said no: it wants 200 orders a month).

## Track A: the lines (speed and price)
Output: `docs/suppliers/china-hub-r2-lines-2026-10-18.md` (Hebrew) and `data/suppliers/china-hub-r2-lines-2026-10-18.json`.

1. **Current published rates for Israel lines (2025–2026).** The terms to search: 以色列专线, 以色列小包, 以色列专线 双清包税, 以色列 e邮宝, 以色列 报价.
   - Lines to check: Uspeed/优时派 with RunnerExpress, Takesend/泰嘉, J-NET/捷网, YunExpress/云途, 4PX/递四方, Yanwen/燕文, Cainiao (the AliExpress lines to Israel), SF International/顺丰国际, China Post e邮宝/ePacket, Wanb/万邦, SFC/三态, Equick, Flyt/飞特, 中通国际, YTO International. Add any other line that publishes an Israel price.
   - For each line:
     - the route type;
     - the claimed days;
     - the rate structure: first weight plus per kg, or per 100 g;
     - **actual or volumetric billing, the divisor, and when volumetric applies;**
     - the size and weight limits;
     - battery and liquid rules;
     - tracking end to end;
     - the last-mile partner in Israel: Israel Post, HFD, Done, Cheetah or pickup points;
     - the warehouse cities;
     - **whether a small shipper can open an account directly:** minimum daily volume and prepayment.
   - Record each price in its original currency, with its date and URL.
   - Acceptable sources:
     - official sites;
     - published price sheets;
     - forwarders' public posts (Baidu, Sohu, public WeChat articles, Zhihu if it opens);
     - public 1688 logistics listings (stop at any login).
2. **Measured speed, per carrier, China to Israel:**
   - ParcelsApp's per-carrier pages and destination report;
   - 17TRACK and AfterShip carrier statistics.
   - Also measure the benchmarks: AliExpress Choice, Temu and SHEIN to Israel.
   - Give medians and P90 where they are published, with dates and sample sizes.
3. **Israeli import rules in 2026.** These decide whether consolidating several items into one parcel helps or hurts.
   - **The VAT exemption threshold:** is it still $75, or is the raise to $150 in force? Give the law or regulation, the effective date and the source.
   - Customs on home goods.
   - What happens when one consolidated parcel crosses the threshold.
   - Israel Post or courier handling fees charged to the recipient.
   - Standards rules on personal import for lighting and kids' items.
   - Any 2026 reform that changes small parcels.
4. A short ranking: **the 5 lines with the best measured speed per shekel** for a 0.6 kg soft parcel and a 1.2 kg boxed ceramic (22×22×30).

## Track B: the operators (who brands and ships)
Output: `docs/suppliers/china-hub-r2-operators-2026-10-18.md` (Hebrew) and `data/suppliers/china-hub-r2-operators-2026-10-18.json`.

1. **Go deeper on round 1's leaders:** Tizmun, ARTEX and BuckyDrop. Find everything that's public:
   - price pages, terms and FAQ;
   - reviews: Google, Trustpilot, public Facebook pages, Israeli forums;
   - the company registration (company number, founding year) from public sources;
   - which carrier or line they actually use to Israel.
2. **At least 15 new candidates that are not in round 1's table.** Kinds to look for:
   - Chinese dropshipping agents that brand and **publish** shipping to Israel. Try NicheDropshipping again (it returned 521 in round 1).
   - Fulfilment warehouses in Yiwu, Shenzhen or Guangzhou that ship one piece at a time (一件代发, 代发仓) with labelling, repacking, photos and QC (贴标, 换包装, 拍照质检), and are linked to an Israel line.
   - **Israel-line forwarders with their own warehouse services.** For example: does Uspeed's Shenzhen warehouse store, repack and ship one piece at a time?
   - Israeli-run or Hebrew-speaking agents in Yiwu or Guangzhou. Use only public pages; stop at a Facebook login.
   - A "Shopify only" app is out, unless it also takes orders by API, CSV or manual entry.
3. For each operator, fill round 1's fields:
   - branding;
   - minimums and fees;
   - sources and consolidation;
   - QC and photos;
   - API or no-Shopify use;
   - public contact;
   - reliability.
   Add:
   - **which Israel line they use;**
   - the price per kg if published, billed by actual or volumetric weight;
   - the measured days if known (link to Track A);
   - the breakage and lost-parcel policy;
   - whether they accept goods from CJ, AliExpress and our own suppliers.
4. **Branding costs for small runs:** custom poly mailer, box, tissue, insert card, sticker and tape. Published prices and minimums, from the operators or from public Alibaba or 1688 listings.

## Rules (both tracks)
- **Public pages only, at a human pace.**
  - Stop at any login, CAPTCHA, validation page or block. Never bypass it.
  - No scraper APIs and no user-agent tricks.
  - Chinese-language pages are fine.
- **No contact of any kind:** no sign-ups, forms, chats, WhatsApp, email or quote requests. Contact waits for the owner.
- **No invented numbers.** Use null or "לא פורסם", and give a URL and a date for every claim.
- **Mark every uncertain number:**
  - **לא אומת:** not from an official source;
  - **הערכה:** your own estimate;
  - **ישן:** from before 2025.
- Currency: 6.72 CNY per USD and ₪3.3 per USD, unless you find and cite a current rate.
- Don't edit binding docs, round 1's files or any existing file. Write only your two new files.
- No personal details of the owner in any file.
- No commits.
- Validate the JSON (`python3 -m json.tool`).

## Return
A short Hebrew summary:
- the top findings;
- the best measured line, with its days and its price for 0.6 kg and 1.2 kg;
- the top 3 operators, and whether each one brands, which line it uses, and at what price;
- what's still unverified.
