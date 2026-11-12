/**
 * QA S18, questions 1 and 5: every page of the sitemap (and the cart, the empty checkout, 404, the test-only pages if
 * asked), rendered in Chromium against my own server, after hydration. For each page:
 * - what a person reads: body.innerText (visible), and body.textContent (hidden too: sr-only, closed dialogs);
 * - every attribute a person or a screen reader meets: aria-label, aria-description, aria-roledescription,
 *   aria-placeholder, aria-valuetext, title, alt, placeholder, value of buttons, label, meta content;
 * - the gate's promiseFindings on every sentence, and my own net (net-scan.mts NET) for review by hand;
 * - leftovers of hidden controls: aria-describedby / aria-labelledby / aria-controls / label[for] that point to no
 *   element, empty headings, empty fieldsets / legends / forms, empty lists, any .waitlist / consent / newsletter node.
 *   cd <copy>/site && node node_modules/tsx/dist/cli.mjs <this> --base=http://127.0.0.1:8798 --site=<copy>/site --out=<json> [--extra=/a/,/b/]
 */
import { writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';
import { chromium } from '@playwright/test';

const arg = (n: string) => process.argv.find((a) => a.startsWith(`--${n}=`))?.slice(n.length + 3);
const BASE = arg('base')!;
const SITE = arg('site')!;
const OUT = arg('out')!;
const EXTRA = (arg('extra') ?? '').split(',').filter(Boolean);
const { promiseFindings, sentences } = (await import(pathToFileURL(join(SITE, 'tools/lib/promises.ts')).href)) as typeof import('../build-s18/site/tools/lib/promises');
const { NET } = (await import(pathToFileURL(join(import.meta.dirname, 'net-scan-net.mts')).href)) as { NET: RegExp };

const browser = await chromium.launch({ executablePath: process.env.PW_CHROMIUM ?? '/opt/pw-browsers/chromium', args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
const ctx = await browser.newContext({ locale: 'he-IL', viewport: { width: 1280, height: 900 } });
// tsx (esbuild keepNames) wraps named functions in __name(); define it in the page so page.evaluate runs
await ctx.addInitScript({ content: 'window.__name = (f) => f;' });
const page = await ctx.newPage();
const sitemap = await (await fetch(`${BASE}/sitemap.xml`)).text();
const paths = [...sitemap.matchAll(/<loc>([^<]+)<\/loc>/g)].map((m) => {
  const u = new URL(m[1]!.replace(/&amp;/g, '&'));
  return `${u.pathname}${u.search}`;
});
const all = [...paths, '/cart/', '/checkout/', '/no-such-page/', ...EXTRA];

type PageOut = { path: string; status: number | null; gate: string[]; net: string[]; hidden_only_net: string[]; leftovers: string[]; nodes: string[] };
const pages: PageOut[] = [];
const netAll = new Map<string, Set<string>>();
for (const path of all) {
  const res = await page.goto(BASE + path, { waitUntil: 'domcontentloaded' }).catch(() => null);
  await page.waitForLoadState('networkidle', { timeout: 8_000 }).catch(() => undefined);
  const got = await page.evaluate(() => {
    const ATTRS = ['aria-label', 'aria-description', 'aria-roledescription', 'aria-placeholder', 'aria-valuetext', 'title', 'alt', 'placeholder', 'label'];
    const attrs: string[] = [];
    for (const el of Array.from(document.querySelectorAll('*'))) {
      for (const a of ATTRS) {
        const v = el.getAttribute(a);
        if (v) attrs.push(v);
      }
      if ((el instanceof HTMLInputElement && ['button', 'submit', 'reset'].includes(el.type)) || el instanceof HTMLButtonElement) {
        const v = el.getAttribute('value');
        if (v) attrs.push(v);
      }
    }
    for (const m of Array.from(document.querySelectorAll('meta[content]'))) attrs.push(m.getAttribute('content') ?? '');
    // leftovers of hidden controls
    const leftovers: string[] = [];
    const ids = (v: string | null) => (v ?? '').split(/\s+/).filter(Boolean);
    for (const a of ['aria-describedby', 'aria-labelledby', 'aria-controls', 'aria-owns', 'aria-errormessage'])
      for (const el of Array.from(document.querySelectorAll(`[${a}]`)))
        for (const id of ids(el.getAttribute(a))) if (!document.getElementById(id)) leftovers.push(`${a}→#${id} missing on <${el.tagName.toLowerCase()} ${el.id ? `id=${el.id}` : el.className}>`);
    for (const el of Array.from(document.querySelectorAll('label[for]'))) {
      const f = el.getAttribute('for')!;
      if (!document.getElementById(f)) leftovers.push(`label[for=${f}] → no control`);
    }
    for (const el of Array.from(document.querySelectorAll('h1,h2,h3,h4,h5,h6,legend,fieldset,form,ul,ol,dl,button,label')))
      if (!(el.textContent ?? '').trim() && !el.querySelector('img,svg,input,select,textarea,picture,canvas,video')) leftovers.push(`empty <${el.tagName.toLowerCase()} class="${el.className}">`);
    for (const el of Array.from(document.querySelectorAll('[role=status],[role=alert],[aria-live]')))
      if (!(el.textContent ?? '').trim()) leftovers.push(`empty live region <${el.tagName.toLowerCase()} class="${el.className}" ${el.getAttribute('role') ? `role=${el.getAttribute('role')}` : `aria-live=${el.getAttribute('aria-live')}`}> (may be intended)`);
    const nodes = Array.from(document.querySelectorAll('.waitlist, [class*="consent"], [class*="newsletter"], [class*="marketing"], [name*="marketing"], [id*="marketing"], [class*="notify"]')).map((el) => el.outerHTML.slice(0, 300));
    return { visible: document.body.innerText, all: document.body.textContent ?? '', attrs, leftovers, nodes };
  });
  const gate: string[] = [];
  const net = new Set<string>();
  const visibleSentences = new Set(sentences(got.visible));
  for (const t of [got.visible, ...got.attrs]) {
    for (const f of promiseFindings(t)) gate.push(`${f.rule}:"${f.sentence}"`);
    for (const s of sentences(t)) if (NET.test(s)) net.add(s);
  }
  const hiddenOnly = new Set<string>();
  for (const s of sentences(got.all)) {
    if (visibleSentences.has(s)) continue;
    for (const f of promiseFindings(s)) gate.push(`hidden ${f.rule}:"${f.sentence}"`);
    if (NET.test(s) && !net.has(s)) hiddenOnly.add(s);
  }
  for (const s of [...net, ...hiddenOnly]) (netAll.get(s) ?? netAll.set(s, new Set()).get(s)!).add(path);
  pages.push({ path, status: res?.status() ?? null, gate, net: [...net], hidden_only_net: [...hiddenOnly], leftovers: got.leftovers, nodes: got.nodes });
}
await browser.close();
const net = [...netAll.entries()].map(([s, p]) => ({ sentence: s, pages: p.size, example: [...p].slice(0, 3) })).sort((a, b) => b.pages - a.pages);
const summary = {
  base: BASE,
  pages: pages.length,
  sitemap_pages: paths.length,
  non_200: pages.filter((p) => p.status !== 200).map((p) => `${p.path} ${p.status}`),
  gate_findings: pages.flatMap((p) => p.gate.map((g) => `${p.path} ${g}`)),
  net_unique_sentences: net.length,
  leftovers: [...new Set(pages.flatMap((p) => p.leftovers))],
  nodes: [...new Set(pages.flatMap((p) => p.nodes))].slice(0, 20),
};
writeFileSync(OUT, JSON.stringify({ summary, net, pages }, null, 1) + '\n');
console.log(JSON.stringify({ ...summary, nodes: summary.nodes.length }, null, 1));
