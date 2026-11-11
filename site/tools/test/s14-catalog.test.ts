/**
 * S14, fixes from QA S11–S12 (qa/reports/2026-11-11-site-track-qa-s11-s12.md), on the real cards and a real build (made
 * here, into .generated/catalog.vitest-s14-*.json, so the test needs no earlier build):
 *  - ת27: every variant sold from a card with supplier options asks the supplier for one of the card's option SKUs; the
 *    floor lamp, whose options collapse to one sold row, carries that row's SKU (CJYD224754407GT), never the card's
 *    product-level CJYD2247544. The build check catches the old value.
 *  - ת33: no public name, description or note in Latin; the card's notes never reach a public field; the Morandi
 *    triptych's description is the shop's Hebrew from the card's data. The build check catches an English remark.
 */
import { beforeAll, describe, expect, it } from 'vitest';
import { execFileSync } from 'node:child_process';
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';
import type { FullCatalog, PublicCatalog } from '@hd/shared';
import { REPO, repoPath, sitePath } from '../lib/paths';
import { cjProductOf, singleSku, supplierSkuIssues, type SkuCard } from '../lib/supplier-skus';
import { hasLatinText, latinPublicText, publicDescription, publicTexture } from '../lib/public-text';

type Card = SkuCard & { texture?: string | null; notes?: string | null };
const walk = (d: string): string[] =>
  readdirSync(d).flatMap((f) => (statSync(join(d, f)).isDirectory() ? walk(join(d, f)) : f.endsWith('.json') ? [join(d, f)] : []));
const cards = new Map<string, Card>();
for (const f of walk(repoPath('data/products'))) {
  try {
    const c = JSON.parse(readFileSync(f, 'utf8')) as Card;
    if (typeof c.id === 'string') cards.set(c.id, c);
  } catch {
    /* not a card */
  }
}
const FLOOR_LAMP = 'floor-lamp-cj-pleated-walnut-stem-158';
const TRAVERTINE = 'accent-sconces-cj-ribbed-travertine-half-cylinder-wood-bracket';
const MORANDI = 'framed-art-cj-morandi-triptych-sage';

const BUILDS = {
  shop: [],
  story: ['--rooms=living-room', '--products=../data/story/story.json,tools/house/living-room.warm-modern.json'],
} as const;
const built: Record<string, { pub: PublicCatalog; full: FullCatalog }> = {};
beforeAll(() => {
  for (const [name, args] of Object.entries(BUILDS)) {
    execFileSync(process.execPath, ['--import', 'tsx', 'tools/build-catalog.ts', ...args, `--out=vitest-s14-${name}`], {
      cwd: sitePath(),
      stdio: 'pipe',
    });
    const read = <T>(kind: string) => JSON.parse(readFileSync(sitePath('.generated', `catalog.vitest-s14-${name}.${kind}.json`), 'utf8')) as T;
    built[name] = { pub: read<PublicCatalog>('public'), full: read<FullCatalog>('full') };
  }
}, 120_000);
const cardOf = (p: { card_id?: string; id: string }) => cards.get(p.card_id ?? p.id);

describe('ת27: the supplier is asked for the very option sold', () => {
  it('the floor lamp: one sold option left (the others excluded), sold as :default with that option’s SKU', () => {
    const card = cards.get(FLOOR_LAMP)!;
    expect(card.supplier?.sku).toBe('CJYD2247544');
    expect(card.options?.default_sku).toBe('CJYD224754407GT');
    for (const name of Object.keys(BUILDS)) {
      const p = built[name]!.full.products.find((x) => x.card_id === FLOOR_LAMP);
      if (!p) continue; // the shop's room may not list it; the story sells it
      expect(p.variants_full, name).toHaveLength(1);
      expect(p.variants_full![0]!.id).toMatch(/:default$/);
      expect(p.variants_full![0]!.supplier_sku, name).toBe('CJYD224754407GT');
      expect(p.supplier.sku).toBe('CJYD2247544'); // the card's record, never the supplier line
    }
    expect(built.story!.full.products.some((x) => x.card_id === FLOOR_LAMP)).toBe(true);
  });

  it('the travertine sconce (collapsed too): its default option’s SKU, by the rule rather than by chance', () => {
    const card = cards.get(TRAVERTINE)!;
    for (const b of Object.values(built)) {
      const p = b.full.products.find((x) => x.card_id === TRAVERTINE);
      if (!p) continue;
      expect(p.variants_full!.map((v) => v.supplier_sku)).toEqual([card.options!.default_sku]);
    }
  });

  it('a card without options whose SKU is CJ’s product-level code: the product’s one variant’s SKU (the cached CJ product)', () => {
    const want = { 'magazine-holder-cj-arch-iron-cane': 'CJJT161011001AZ', 'bowl-cj-glutinous-white-belly-bowl-21': 'CJYD238977901AZ' };
    for (const [id, sku] of Object.entries(want)) {
      const card = cards.get(id)!;
      expect(card.options ?? null).toBeNull();
      const cj = cjProductOf(REPO, card as Parameters<typeof cjProductOf>[1]);
      expect(cj?.productSku).toBe(card.supplier?.sku);
      expect(singleSku(card, cj)).toEqual({ sku, resolved: true });
      const sold = Object.values(built).flatMap((b) => b.full.products.filter((p) => p.card_id === id));
      expect(sold.length, id).toBeGreaterThan(0);
      for (const p of sold) expect(p.variants_full!.map((v) => v.supplier_sku)).toEqual([sku]);
    }
    // a card already carrying a variant's SKU keeps it; a product of several variants is not guessed
    expect(singleSku({ supplier: { sku: 'CJYD223337102BY' } }, { productSku: 'CJYD2233371', variants: [{ vid: '1', variantSku: 'X' }] })).toEqual({
      sku: 'CJYD223337102BY',
      resolved: false,
    });
    expect(
      singleSku(
        { supplier: { sku: 'CJP1' } },
        {
          productSku: 'CJP1',
          variants: [
            { vid: '1', variantSku: 'A' },
            { vid: '2', variantSku: 'B' },
          ],
        },
      ).resolved,
    ).toBe(false);
    // and the check refuses a product-level code it knows, on a card without options
    const bowl = built.story!.full.products.find((p) => p.card_id === 'bowl-cj-glutinous-white-belly-bowl-21')!;
    const old = { ...bowl, variants_full: bowl.variants_full!.map((v) => ({ ...v, supplier_sku: 'CJYD2389779' })) };
    expect(supplierSkuIssues([old], () => ({ ...cards.get(bowl.card_id!)!, product_level_sku: 'CJYD2389779' }))[0]?.why).toMatch(/product-level code/);
  });

  it('every product with options in both builds: no sold variant asks for a SKU outside its card’s options (sets too)', () => {
    for (const [name, b] of Object.entries(built)) {
      expect(
        supplierSkuIssues(b.full.products, (p) => {
          const c = cardOf(p);
          return c && { ...c, product_level_sku: cjProductOf(REPO, c as Parameters<typeof cjProductOf>[1])?.productSku ?? null };
        }),
        name,
      ).toEqual([]);
      // and the scan of QA's tool: a collapsed `:default` of a card with options is its one sold option
      for (const p of b.full.products) {
        const card = cardOf(p);
        if (!card?.options || p.options) continue;
        const v = p.variants_full!;
        expect(v, p.id).toHaveLength(1);
        expect(
          card.options.skus.map((s) => s.id),
          `${p.id} ${v[0]!.supplier_sku}`,
        ).toContain(v[0]!.supplier_sku);
      }
    }
  });

  it('the build check catches the old value (the card’s product SKU on a collapsed :default) and a set part outside the card', () => {
    const p = built.story!.full.products.find((x) => x.card_id === FLOOR_LAMP)!;
    const old = { ...p, variants_full: p.variants_full!.map((v) => ({ ...v, supplier_sku: 'CJYD2247544' })) };
    const issues = supplierSkuIssues([old], cardOf);
    expect(issues).toHaveLength(1);
    expect(issues[0]!.why).toMatch(/product-level SKU/);
    const set = { ...p, variants_full: p.variants_full!.map((v) => ({ ...v, set_skus: ['CJYD224754407GT', 'NOT-ON-THE-CARD'] })) };
    expect(supplierSkuIssues([set], cardOf).map((x) => x.why)).toEqual([expect.stringMatching(/NOT-ON-THE-CARD/)]);
    // a variant not sold (inactive) is not the supplier's business
    expect(supplierSkuIssues([{ ...old, variants_full: old.variants_full.map((v) => ({ ...v, active: false })) }], cardOf)).toEqual([]);
  });
});

describe('ת33: the customer reads the shop’s Hebrew, never the studio’s notes', () => {
  it('the Morandi triptych: a neutral Hebrew description from the card’s data, without the English sourcing remark', () => {
    const card = cards.get(MORANDI)!;
    expect(card.texture).toMatch(/bright crystal film/); // the card keeps its working note
    expect(publicTexture(card.texture)).toBeNull();
    for (const b of Object.values(built)) {
      const p = b.pub.products.find((x) => (b.full.products.find((f) => f.id === x.id)?.card_id ?? '') === MORANDI);
      if (!p) continue;
      expect(hasLatinText(p.description_he), p.description_he).toBe(false);
      expect(p.description_he).not.toMatch(/ליסטינג|בתמונות|texture|crystal/);
      expect(p.description_he).toMatch(/^חומרים: /);
      expect(p.description_he).toContain('מידות: 50 × 70 ס"מ');
    }
  });

  it('no public name, description or note in Latin, in either build; a card’s notes are in no public field', () => {
    for (const [name, b] of Object.entries(built)) {
      expect(latinPublicText(b.pub.products), name).toEqual([]);
      const text = JSON.stringify(b.pub.products);
      for (const f of b.full.products) {
        const notes = cardOf(f)?.notes;
        if (!notes || notes.length < 24) continue;
        expect(text.includes(notes.slice(0, 24)), `${f.id}: the card's notes in the public catalog`).toBe(false);
      }
    }
  });

  it('the rule: a texture is public only as a Hebrew sentence without a sourcing remark; the notes are never read', () => {
    expect(publicTexture('מרקם חול גס ומחוספס עם גלים לא סדירים, מראה עבודת יד')).toBe('מרקם חול גס ומחוספס עם גלים לא סדירים, מראה עבודת יד');
    expect(publicTexture("הדפס עם מרקם מובלט ('texture painting')")).toBeNull();
    expect(publicTexture('בתמונות נראה שטוח-מט')).toBeNull();
    expect(publicTexture('קיימת גרסה מבריקה באותו ליסטינג')).toBeNull();
    expect(publicTexture('textured cotton')).toBeNull();
    const d = publicDescription({ texture: null, notes: 'הערת ליקוט פנימית: vid מומלץ' } as { texture: null }, ['כותנה'], [50, 70], 'כרית.');
    expect(d).toBe('חומרים: כותנה. מידות: 50 × 70 ס"מ (לפי הספק, לא אומת).');
    expect(publicDescription({ texture: null }, [], [], 'כרית.')).toBe('כרית.');
  });

  it('the build check: Latin in a description or a name fails; a unit after a number and a standard’s mark pass (ת12)', () => {
    expect(hasLatinText('מנורת קיר, 90-260V, תקן CE, נורה 3000K, 5W')).toBe(false);
    expect(hasLatinText('אהיל 220mm')).toBe(false);
    expect(hasLatinText("קיימת גם גרסת 'bright crystal film'")).toBe(true);
    const issues = latinPublicText([
      { id: 'a', name_he: 'כרית', description_he: "הדפס ('texture painting')", notes_he: [] },
      { id: 'b', name_he: 'Pillow cover', description_he: 'כותנה.', notes_he: ['מתאים ל-CE'] },
    ]);
    expect(issues.map((x) => `${x.product}:${x.where}`)).toEqual(['a:description', 'b:name']);
  });
});
