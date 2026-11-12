/**
 * QA S22, the manager's addendum (the cards): my own comparison of two clean builds in the CI order, the S21 copy
 * (7b42ddc1, QA S21's) against the S22 copy (9b6c6746). Independent of frontend-dev's cat-diff.mjs / option-prices.mjs.
 * - the two floor-lamp ids (…062736 and …062736-master): every file of .generated and web/dist that names them, before and after;
 * - the catalogs (shop, story, test page, the warm-modern house): products in/out, card ids, headline price and SKU;
 * - every option price of every product in both: what moved;
 * - the pages (every index.html in web/dist), the sitemap, _redirects and story-redirects: what changed;
 * - dangling: every /p/<id>/ and /story/…/p/<id>/ link in every built page has a page (or a redirect); every product the
 *   story and the house name is in the story catalog or hidden with a reason; no product from a card whose status is
 *   rejected.
 *   node cards-s22qa.mjs --old=<S21 copy> --new=<S22 copy> --out=<json>
 */
import { existsSync, readFileSync, readdirSync, statSync, writeFileSync } from 'node:fs';
import { join, relative } from 'node:path';

const arg = (n) => process.argv.find((a) => a.startsWith(`--${n}=`))?.slice(n.length + 3);
const OLD = arg('old');
const NEW = arg('new');
const OUT = arg('out');
const LAMP = /floor-lamp-aliexpress-pleated-walnut-37x158-062736|1005009987062736|pleated-walnut-37x158/;
const walk = (d, f = () => true) =>
  existsSync(d) ? readdirSync(d).flatMap((e) => (statSync(join(d, e)).isDirectory() ? walk(join(d, e), f) : f(e) ? [join(d, e)] : [])) : [];
const J = (p) => JSON.parse(readFileSync(p, 'utf8'));
const res = {};
const log = (...a) => console.log(...a);

// 1. the lamp ids anywhere in what the site builds
for (const [name, root] of [['old', OLD], ['new', NEW]]) {
  const files = [...walk(join(root, 'site/.generated')), ...walk(join(root, 'site/web/dist')), ...walk(join(root, 'site/api/dist'))].filter((f) => !/\.(?:avif|webp|png|jpe?g|woff2?|ico)$/.test(f));
  const hits = files.filter((f) => LAMP.test(readFileSync(f, 'utf8'))).map((f) => relative(root, f));
  res[`lamp_files_${name}`] = hits;
  log(`floor-lamp ids in ${name} build output (${files.length} text files): ${hits.length ? hits.join(', ') : 'none'}`);
}

// 2. catalogs
const CATS = ['catalog.full.json', 'catalog.public.json', 'catalog.story.full.json', 'catalog.story.public.json', 'catalog.test-page.full.json', 'catalog.test-page.public.json', 'house.living-room.warm-modern.json'];
const cards = new Map();
for (const f of walk(join(NEW, 'data/products'), (e) => e.endsWith('.json'))) {
  try {
    const c = J(f);
    if (c.id) cards.set(c.id, { status: c.status, file: relative(NEW, f) });
  } catch {}
}
const prodsOf = (c) => (Array.isArray(c.products) ? c.products : []);
const optPrices = (p) => {
  const out = {};
  for (const o of p.variants_full ?? []) out[o.id] = { price: o.retail_agorot ?? null, sku: o.supplier_sku ?? null, label: o.option_label_he ?? o.label_he ?? null, cost: o.cost_usd_cents ?? null };
  return out;
};
res.catalogs = {};
res.option_moves = [];
for (const c of CATS) {
  const a = join(OLD, 'site/.generated', c);
  const b = join(NEW, 'site/.generated', c);
  if (!existsSync(a) || !existsSync(b)) {
    log(`${c}: missing (${existsSync(a)}, ${existsSync(b)})`);
    continue;
  }
  const A = J(a), B = J(b);
  const pa = new Map(prodsOf(A).map((p) => [p.id, p]));
  const pb = new Map(prodsOf(B).map((p) => [p.id, p]));
  const added = [...pb.keys()].filter((k) => !pa.has(k));
  const removed = [...pa.keys()].filter((k) => !pb.has(k));
  const changed = [];
  for (const [k, p] of pb) {
    const q = pa.get(k);
    if (!q) continue;
    const head = (x) => JSON.stringify({ price: x.price_agorot ?? x.price ?? null, sku: x.variants_full?.[0]?.supplier_sku ?? null, cost: x.cost_usd_cents ?? null, name: x.name_he ?? null, card: x.card_id ?? null });
    if (head(p) !== head(q)) changed.push({ id: k, before: JSON.parse(head(q)), after: JSON.parse(head(p)) });
    const oa = optPrices(q), ob = optPrices(p);
    for (const o of new Set([...Object.keys(oa), ...Object.keys(ob)])) {
      if (JSON.stringify(oa[o]?.price) !== JSON.stringify(ob[o]?.price)) res.option_moves.push({ catalog: c, product: k, option: o, label: ob[o]?.label ?? oa[o]?.label, sku: ob[o]?.sku ?? oa[o]?.sku, before: oa[o]?.price ?? null, after: ob[o]?.price ?? null });
    }
  }
  const rejected = prodsOf(B).filter((p) => cards.get(p.card_id)?.status === 'rejected').map((p) => p.id);
  const hidden = Array.isArray(B.hidden) ? B.hidden.length : null;
  const hiddenA = Array.isArray(A.hidden) ? A.hidden.map((h) => h.id).sort() : null;
  const hiddenB = Array.isArray(B.hidden) ? B.hidden.map((h) => h.id).sort() : null;
  res.catalogs[c] = { before: pa.size, after: pb.size, added, removed, headline_changed: changed, from_rejected_cards: rejected, hidden, hidden_same: JSON.stringify(hiddenA) === JSON.stringify(hiddenB) };
  log(`${c}: ${pa.size} → ${pb.size} products; added ${added.length}, removed ${removed.length}; headline changed: ${changed.map((x) => x.id).join(', ') || 'none'}; from rejected cards: ${rejected.length}; hidden ${hidden ?? '-'} (same as before: ${res.catalogs[c].hidden_same})`);
}
const byProd = {};
for (const m of res.option_moves) (byProd[`${m.catalog} ${m.product}`] ??= []).push(m);
for (const [k, v] of Object.entries(byProd)) log(`  option prices moved: ${k}: ${v.length}`);

// 3. pages, sitemap, redirects
const pages = (root) => new Set(walk(join(root, 'site/web/dist'), (e) => e.endsWith('.html')).map((f) => relative(join(root, 'site/web/dist'), f)));
const pA = pages(OLD), pB = pages(NEW);
res.pages = { before: pA.size, after: pB.size, added: [...pB].filter((x) => !pA.has(x)), removed: [...pA].filter((x) => !pB.has(x)) };
log(`html pages: ${pA.size} → ${pB.size}; added ${res.pages.added.join(', ') || 'none'}; removed ${res.pages.removed.join(', ') || 'none'}`);
for (const f of ['sitemap.xml', '_redirects', 'robots.txt', '_headers']) {
  const a = join(OLD, 'site/web/dist', f), b = join(NEW, 'site/web/dist', f);
  const same = existsSync(a) && existsSync(b) && readFileSync(a, 'utf8') === readFileSync(b, 'utf8');
  res[`same_${f}`] = existsSync(a) || existsSync(b) ? same : 'absent in both';
  log(`${f}: ${existsSync(a) || existsSync(b) ? (same ? 'identical' : 'DIFFERENT') : 'absent in both'}`);
}
{
  const a = join(OLD, 'site/.generated/story-redirects.txt'), b = join(NEW, 'site/.generated/story-redirects.txt');
  res.same_story_redirects = readFileSync(a, 'utf8') === readFileSync(b, 'utf8');
  log(`story-redirects.txt: ${res.same_story_redirects ? 'identical' : 'DIFFERENT'}`);
}
const sm = (root) => (readFileSync(join(root, 'site/web/dist/sitemap.xml'), 'utf8').match(/<loc>[^<]+<\/loc>/g) ?? []).length;
res.sitemap_urls = [sm(OLD), sm(NEW)];
log(`sitemap URLs: ${res.sitemap_urls.join(' → ')}`);

// 4. dangling links in the new build
const dist = join(NEW, 'site/web/dist');
const redirects = readFileSync(join(dist, '_redirects'), 'utf8')
  .split('\n')
  .map((l) => l.trim().split(/\s+/)[0])
  .filter(Boolean);
const dangling = [];
let links = 0;
for (const f of walk(dist, (e) => e.endsWith('.html'))) {
  const t = readFileSync(f, 'utf8');
  for (const m of t.matchAll(/(?:href|"shop_href"|"href")\s*[=:]\s*"((?:\/story\/[^"#?]*)?\/p\/[^"#?/]+\/)"/g)) {
    links++;
    const target = join(dist, m[1], 'index.html');
    if (!existsSync(target) && !redirects.some((r) => r === m[1] || (r.endsWith('*') && m[1].startsWith(r.slice(0, -1))))) dangling.push(`${relative(dist, f)} → ${m[1]}`);
  }
}
res.product_links = links;
res.dangling = [...new Set(dangling)];
log(`product links in built pages: ${links}; dangling: ${res.dangling.length ? res.dangling.slice(0, 20).join('; ') : 'none'}`);
// what the story and the house name
const story = J(join(NEW, 'site/.generated/catalog.story.full.json'));
const known = new Set([...prodsOf(story).map((p) => p.card_id), ...(story.hidden ?? []).map((h) => h.id)]);
const named = new Set();
const collect = (x) => {
  if (Array.isArray(x)) x.forEach(collect);
  else if (x && typeof x === 'object')
    for (const [k, v] of Object.entries(x)) {
      if ((k === 'product' || k === 'card_id') && typeof v === 'string') named.add(v);
      collect(v);
    }
};
collect(J(join(NEW, 'data/story/story.json')));
collect(J(join(NEW, 'site/tools/house/living-room.warm-modern.json')));
res.named = named.size;
res.named_unknown = [...named].filter((id) => !known.has(id) && cards.has(id));
res.named_not_a_card = [...named].filter((id) => !cards.has(id));
log(`ids the story and the house name (any "product"/"card_id" key): ${named.size}; a card but neither built nor hidden: ${res.named_unknown.join(', ') || 'none'}; not a card id: ${res.named_not_a_card.length} (${res.named_not_a_card.slice(0, 8).join(', ')})`);
log(`hidden without a reason: ${(story.hidden ?? []).filter((h) => !h.reason).map((h) => h.id).join(', ') || 'none'}`);
writeFileSync(OUT, JSON.stringify(res, null, 1) + '\n');
