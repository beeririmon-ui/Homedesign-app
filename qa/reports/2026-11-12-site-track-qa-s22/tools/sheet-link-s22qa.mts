/**
 * QA S22, ת70, by real clicks (no test hook): a scratch site with a `back_in_stock` test provider (frontend-dev's own
 * e2e/scratch-site.ts from the copy, on my own port), then, for EVERY unavailable item of EVERY story page, from EVERY way a
 * customer opens its sheet (the "קנה את המראה" credit and the mark on the frame): the sheet's status line and its link;
 * a real click on the link; the shop page (/p/<id>/); "עדכנו אותי כשחוזר"; an address; "עדכנו אותי"; the POST
 * /api/waitlist (status, and what it registers: product and SKU) against the option the frame shows (st-data `values`).
 * Then the story's own detail page of the item: no form there.
 *   cd <copy>/site && node node_modules/tsx/dist/cli.mjs <this> --site=<copy>/site --port=8842 --out=<json> --shots=<dir>
 */
import { mkdirSync, readFileSync, readdirSync, statSync, writeFileSync } from 'node:fs';
import { dirname, join, relative } from 'node:path';
import { pathToFileURL } from 'node:url';
import { chromium, type Page } from '@playwright/test';

const arg = (n: string) => process.argv.find((a) => a.startsWith(`--${n}=`))?.slice(n.length + 3);
const SITE = arg('site')!;
const PORT = Number(arg('port') ?? 8842);
const OUT = arg('out')!;
const SHOTS = arg('shots')!;
mkdirSync(SHOTS, { recursive: true });
const { startScratchSite } = (await import(pathToFileURL(join(SITE, 'e2e/scratch-site.ts')).href)) as typeof import('../build-s22/site/e2e/scratch-site');
const t0 = Date.now();
const site = await startScratchSite({ port: PORT });
console.log(`scratch site up on ${site.url} in ${((Date.now() - t0) / 1000).toFixed(1)} s`);
const BASE = site.url;
const rows: Record<string, unknown>[] = [];
const problems: string[] = [];
const browser = await chromium.launch({ executablePath: process.env.PW_CHROMIUM ?? '/opt/pw-browsers/chromium', args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
try {
  const ctx = await browser.newContext({ locale: 'he-IL', viewport: { width: 1280, height: 900 } });
  await ctx.addInitScript({ content: 'window.__name = (f) => f;' });
  const page = await ctx.newPage();
  // every story page that carries sheet data (st-data), from the copy's built pages (the scratch site serves the same)
  const walk = (d: string): string[] =>
    readdirSync(d).flatMap((e) => (statSync(join(d, e)).isDirectory() ? walk(join(d, e)) : e === 'index.html' ? [join(d, e)] : []));
  const storyDir = join(SITE, 'web/dist/story');
  const sp = new Set<string>(
    walk(storyDir)
      .filter((f) => /id="st-data"/.test(readFileSync(f, 'utf8')))
      .map((f) => `/story/${relative(storyDir, dirname(f)).split('\\').join('/')}/`.replace('/story//', '/story/')),
  );
  let n = 0;
  let mail = 0;
  for (const path of [...sp].sort()) {
    await page.goto(BASE + path, { waitUntil: 'domcontentloaded' });
    await page.waitForLoadState('networkidle', { timeout: 10_000 }).catch(() => undefined);
    const data = await page.evaluate(() => {
      const el = document.getElementById('st-data');
      return el ? (JSON.parse(el.textContent ?? '{}') as { items?: Record<string, { status: string; product: string; shop_href?: string | null; href?: string | null; values?: Record<string, string> | null }> }) : null;
    });
    if (!data?.items) continue;
    const un = Object.entries(data.items).filter(([, it]) => it.status === 'unavailable');
    for (const [item, it] of un)
      for (const how of ['credit', 'mark'] as const) {
        await page.goto(BASE + path, { waitUntil: 'domcontentloaded' });
        await page.waitForFunction(() => !!(window as unknown as { __story?: unknown }).__story, null, { timeout: 15_000 }).catch(() => undefined);
        const sel = how === 'credit' ? `.st-open[data-item="${item}"]` : `.st-mark[data-item="${item}"]`;
        const el = page.locator(sel).first();
        if (!(await el.count())) {
          rows.push({ path, item, how, reached: false, note: 'no such control on the page' });
          continue;
        }
        await el.scrollIntoViewIfNeeded().catch(() => undefined);
        if (how === 'mark') {
          const box = await el.boundingBox();
          if (box) await page.mouse.move(box.x + box.width / 2 + 3, box.y + box.height / 2 + 3);
          await page.waitForTimeout(150);
        }
        const clicked = await el.click({ timeout: 5_000 }).then(() => true).catch(() => false);
        if (!clicked) {
          rows.push({ path, item, how, reached: false, note: 'not clickable' });
          problems.push(`${path} ${item} ${how}: not clickable`);
          continue;
        }
        await page.locator('dialog[open]').waitFor({ timeout: 5_000 });
        const why = await page.locator('#st-why').innerText();
        const link = page.locator('#st-why a');
        const linkText = (await link.count()) ? await link.innerText() : null;
        const linkHref = (await link.count()) ? await link.getAttribute('href') : null;
        const detail = await page.locator('#st-page').getAttribute('href').catch(() => null);
        const row: Record<string, unknown> = { path, item, how, product: it.product, values: it.values ?? null, why, linkText, linkHref, shop_href: it.shop_href ?? null, detail };
        if (!linkHref) {
          problems.push(`${path} ${item} ${how}: no link in the sheet ("${why}")`);
          rows.push(row);
          continue;
        }
        // the real click on the line
        await link.click();
        await page.waitForURL(new RegExp(`${linkHref.replace(/[/]/g, '\\/')}$`), { timeout: 15_000 });
        row.landed = new URL(page.url()).pathname;
        const wl = page.locator('.waitlist').first();
        await wl.waitFor({ timeout: 10_000 });
        row.status_on_page = await wl.locator('.waitlist-status').innerText().catch(() => null);
        const shownOption = await page.evaluate(() => Array.from(document.querySelectorAll('input[type=radio]:checked')).map((i) => `${(i as HTMLInputElement).name}=${(i as HTMLInputElement).value}`));
        row.page_option = shownOption;
        await wl.getByRole('button', { name: 'עדכנו אותי כשחוזר' }).click();
        mail++;
        await wl.getByLabel('אימייל').fill(`qa22.sheet${mail}@example.com`);
        const resp = page.waitForResponse((r) => r.url().endsWith('/api/waitlist') && r.request().method() === 'POST');
        await wl.getByRole('button', { name: 'עדכנו אותי', exact: true }).click();
        const r = await resp;
        row.post_status = r.status();
        row.post_body = r.request().postDataJSON();
        row.after = await wl.getByRole('status').innerText().catch(() => null);
        if (r.status() !== 201) problems.push(`${path} ${item} ${how}: POST ${r.status()}`);
        n++;
        if (n <= 2) await page.screenshot({ path: join(SHOTS, `qa-t70-${n}-${how}-shop-page-after-submit.png`), fullPage: false });
        rows.push(row);
      }
  }
  // the detail page of the story: no form
  const det = rows.find((r) => r.detail) as { detail: string } | undefined;
  let detailForms: number | null = null;
  if (det) {
    await page.goto(BASE + det.detail);
    detailForms = await page.locator('form.waitlist-form, .waitlist, input[type=email]').count();
  }
  // the D1 of the scratch site: what the waiting list holds
  const summary = {
    base: BASE,
    story_pages: sp.size,
    unavailable_sheets_opened: rows.length,
    by_how: { credit: rows.filter((r) => r.how === 'credit').length, mark: rows.filter((r) => r.how === 'mark').length },
    submitted: n,
    status_201: rows.filter((r) => r.post_status === 201).length,
    lines: [...new Set(rows.map((r) => r.why))],
    detail_page_forms: detailForms,
    problems,
  };
  console.log(JSON.stringify(summary, null, 1));
  for (const r of rows) console.log(`${r.path} ${r.item} ${r.how}: ${r.linkHref} → ${r.landed} · POST ${r.post_status} ${JSON.stringify(r.post_body)} · frame values ${JSON.stringify(r.values)} · page ${JSON.stringify(r.page_option)}`);
  writeFileSync(OUT, JSON.stringify({ summary, rows }, null, 1) + '\n');
  await ctx.close();
} finally {
  await browser.close();
  await site.stop();
}
