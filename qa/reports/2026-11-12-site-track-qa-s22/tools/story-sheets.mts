/**
 * QA S20, ת56: every story page behind the flag (every index.html under dist/story: the frames and the detail pages), every sheet
 * opened the way a customer opens it: a click on each "קנה את המראה" credit (.st-open), a click on each mark (.st-mark,
 * shown by moving the mouse over the frame), and "הבא" through the whole sheet. No test hook. In each sheet: the status
 * line (#st-why), the gate's promiseFindings on the sheet's text (visible, hidden, every attribute), my words for a
 * waiting list or an update, and any offer of contact. Then "קנה את המראה" whole, and the cart dialog with what is held.
 *   cd <copy>/site && node node_modules/tsx/dist/cli.mjs <this> --base=… --site=<copy>/site --out=<json>
 */
import { writeFileSync } from 'node:fs';
import { join, relative } from 'node:path';
import { pathToFileURL } from 'node:url';
import { chromium, type Page } from '@playwright/test';

const arg = (n: string) => process.argv.find((a) => a.startsWith(`--${n}=`))?.slice(n.length + 3);
const BASE = arg('base')!;
const SITE = arg('site')!;
const OUT = arg('out')!;
const { promiseFindings } = (await import(pathToFileURL(join(SITE, 'tools/lib/promises.ts')).href)) as typeof import('../build-s22/site/tools/lib/promises');
const { walk } = (await import(pathToFileURL(join(SITE, 'tools/lib/promise-scan.ts')).href)) as typeof import('../build-s22/site/tools/lib/promise-scan');
const WORDS = /לבקש עדכון|עדכנו אותי|כשהוא חוזר|כשהמוצר חוזר|רשימת המתנה|רשימת ההמתנה|נעדכן|נודיע|הודעה|במייל|באימייל|כתבו לנו|פנו אלינו|צרו קשר/;
const dist = join(SITE, 'web/dist/story');
const pages = walk(dist, (r) => r.endsWith('index.html')).map((p) => `/story/${relative(dist, p).replace(/index\.html$/, '')}`);

const browser = await chromium.launch({ executablePath: process.env.PW_CHROMIUM ?? '/opt/pw-browsers/chromium', args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
const ctx = await browser.newContext({ locale: 'he-IL', viewport: { width: 1280, height: 900 } });
await ctx.addInitScript({ content: 'window.__name = (f) => f;' });
const page = await ctx.newPage();
const texts = (p: Page, sel: string) =>
  p.evaluate((s) => {
    const root = document.querySelector(s) as HTMLElement | null;
    if (!root) return [] as string[];
    const out = [root.innerText, root.textContent ?? ''];
    for (const el of [root, ...Array.from(root.querySelectorAll('*'))]) for (const a of Array.from(el.attributes)) if (a.name !== 'class' && a.name !== 'style' && a.name !== 'd') out.push(a.value);
    return out;
  }, sel);
const check = (t: string[]) => {
  const f = new Set<string>();
  for (const x of t) {
    for (const p of promiseFindings(x)) f.add(`${p.rule}:"${p.sentence}"`);
    for (const s of x.split(/[.!?\n]+/)) if (WORDS.test(s)) f.add(`word:"${s.trim().slice(0, 120)}"`);
  }
  return [...f];
};
type Sheet = { page: string; item: string; how: string; why: string; findings: string[] };
const sheets: Sheet[] = [];
const pageFindings: string[] = [];
let ids = 0;
const seen = new Set<string>();
for (const path of pages) {
  await page.goto(BASE + path, { waitUntil: 'domcontentloaded' });
  await page.waitForLoadState('networkidle', { timeout: 10_000 }).catch(() => undefined);
  for (const f of check(await texts(page, 'body'))) pageFindings.push(`${path} ${f}`);
  const items: string[] = await page.evaluate(() => {
    const el = document.getElementById('st-data');
    return el ? Object.keys((JSON.parse(el.textContent ?? '{}') as { items?: Record<string, unknown> }).items ?? {}) : [];
  });
  if (!items.length) continue;
  ids += items.length;
  await page.waitForFunction(() => !!(window as unknown as { __story?: unknown }).__story, null, { timeout: 15_000 }).catch(() => undefined);
  const readSheet = async (item: string, how: string) => {
    await page.locator('dialog[open]').waitFor({ timeout: 5_000 });
    await page.waitForTimeout(150);
    const why = (await page.locator('#st-why').isVisible()) ? await page.locator('#st-why').innerText() : '';
    sheets.push({ page: path, item, how, why, findings: check(await texts(page, 'dialog[open]')) });
    seen.add(`${path}#${item}`);
  };
  const close = async () => {
    await page.locator('#st-sheet-close').click().catch(() => page.keyboard.press('Escape'));
    await page.locator('dialog[open]').waitFor({ state: 'detached', timeout: 3_000 }).catch(() => page.keyboard.press('Escape'));
    await page.waitForTimeout(250);
  };
  // the credits ("קנה את המראה")
  for (const id of await page.locator('.st-open').evaluateAll((els) => els.map((e) => (e as HTMLElement).dataset.item!))) {
    const b = page.locator(`.st-open[data-item="${id}"]`).first();
    await b.scrollIntoViewIfNeeded();
    await b.click();
    await readSheet(id, 'credit');
    await close();
  }
  // the marks on the frame: the mouse over the frame shows them
  for (const id of await page.locator('.st-mark').evaluateAll((els) => els.map((e) => (e as HTMLElement).dataset.item!))) {
    const m = page.locator(`.st-mark[data-item="${id}"]`).first();
    await m.scrollIntoViewIfNeeded().catch(() => undefined);
    const box = await m.boundingBox();
    if (!box) continue;
    await page.mouse.move(box.x + box.width / 2 + 3, box.y + box.height / 2 + 3);
    await page.waitForTimeout(120);
    const clicked = await m.click({ timeout: 3_000 }).then(() => true).catch(() => false);
    if (!clicked) {
      sheets.push({ page: path, item: id, how: 'mark: not clickable', why: '', findings: [] });
      continue;
    }
    await readSheet(id, 'mark');
    await close();
  }
  // "הבא" through the whole sheet, from the first credit
  const first = page.locator('.st-open').first();
  if (await first.count()) {
    await first.scrollIntoViewIfNeeded();
    await first.click();
    for (let i = 0; i < items.length + 1; i++) {
      const cur = await page.evaluate(() => document.querySelector('dialog[open] [data-item]')?.getAttribute('data-item') ?? document.querySelector('dialog[open]')?.getAttribute('data-item') ?? '');
      await readSheet(cur || `next-${i}`, 'next');
      const next = page.locator('#st-next');
      if (!(await next.isVisible()) || (await next.isDisabled())) break;
      await next.click();
      await page.waitForTimeout(200);
    }
    await close();
  }
  // the whole look into the cart, then the cart: what is held is said, nothing promised
  const look = page.locator('.st-look-btn').first();
  if (await look.count()) {
    await look.scrollIntoViewIfNeeded();
    await look.click();
    await page.waitForTimeout(800);
    await page.locator('#st-cart-open').click().catch(() => undefined);
    await page.locator('#st-cart[open]').waitFor({ timeout: 5_000 }).catch(() => undefined);
    sheets.push({ page: path, item: 'cart', how: 'cart after the whole look', why: await page.locator('#st-cart-held').innerText().catch(() => ''), findings: check(await texts(page, '#st-cart')) });
    await page.locator('#st-cart-clear').click().catch(() => undefined);
    await page.locator('#st-cart-close').click().catch(() => page.keyboard.press('Escape'));
  }
}
await browser.close();
const unavailable = sheets.filter((s) => /המלאי אינו זמין כעת/.test(s.why));
const bad = sheets.filter((s) => s.findings.length || (/המלאי אינו זמין כעת/.test(s.why) && s.how !== 'cart after the whole look' && s.why !== 'המלאי אינו זמין כעת.'));
const summary = {
  base: BASE,
  story_pages: pages.length,
  pages_with_sheets: new Set(sheets.map((s) => s.page)).size,
  items: ids,
  sheets_opened: sheets.filter((s) => s.how !== 'mark: not clickable' && s.item !== 'cart').length,
  items_reached: seen.size,
  by: Object.fromEntries(['credit', 'mark', 'next', 'mark: not clickable'].map((h) => [h, sheets.filter((s) => s.how === h).length])),
  unavailable_sheets: unavailable.length,
  unavailable_lines: [...new Set(unavailable.map((s) => s.why))],
  page_findings: pageFindings,
  bad: bad.map((s) => `${s.page} ${s.item} (${s.how}): ${s.why} ${s.findings.join(' ')}`),
};
writeFileSync(OUT, JSON.stringify({ summary, sheets }, null, 1) + '\n');
console.log(JSON.stringify(summary, null, 1));
