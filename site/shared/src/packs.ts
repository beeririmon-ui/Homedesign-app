/**
 * Set or single (decision P1, docs/studio-rules.md ה.6): a product that appears in the room as a pair or a set is sold
 * as that set by default, and can also be bought as one piece.
 *
 *   N (set_qty)  supplier units in one set = sell_qty: data/economics/products.json `sell_qty` when the studio set it,
 *                else the studio's sell_qty_default (studio/build.py, ported below). N = 1: sold singly, no choice.
 *   set price    retail_ils as set in the studio: the price of the whole sale unit (the set).
 *   unit price   `unit_retail_ils` when the studio sets one; else an ESTIMATE until it does:
 *                ceil(set / N × 1.15), rounded down to a price ending in 9 (one piece ships alone, so it costs more
 *                per piece), never below the set's own per-piece price.
 */
export const PACKS = ['set', 'unit'] as const;
export type Pack = (typeof PACKS)[number];

/** Per-piece premium of a single unit over the set's per-piece price (shipping one piece costs more). */
export const UNIT_PREMIUM = 1.15;

/** Rounds a whole shekel amount down to the nearest price ending in 9 (e.g. 115 → 109, 189 → 189). */
export function charmRoundDownIls(ils: number): number {
  const n = Math.floor(ils);
  const r = (((n - 9) % 10) + 10) % 10;
  return n - r;
}

/**
 * ESTIMATED single-unit price (shekels) for a set of `n` sold at `setIls`. Provisional until the studio defines
 * `unit_retail_ils` per product; the site marks it as an estimate.
 */
export function unitPriceEstimateIls(setIls: number, n: number): number {
  if (!(n > 1) || !(setIls > 0)) throw new Error(`unit price needs a set of 2 or more (n=${n}, set=${setIls})`);
  const perPiece = Math.ceil(setIls / n);
  const est = charmRoundDownIls(Math.ceil((setIls / n) * UNIT_PREMIUM));
  // rounding down to …9 can fall under the set's own per-piece price (small prices): then round that up to …9
  if (est >= perPiece) return est;
  const r = perPiece % 10;
  return r === 9 ? perPiece : perPiece + ((9 - r + 10) % 10);
}

export const packLabelHe = (pack: Pack, setQty: number): string => (pack === 'set' ? `סט של ${setQty}` : 'יחידה אחת');

// ---------- the studio's default sell quantity (studio/build.py, sell_qty_default) ----------
const QTY_PER_PIECE = [
  /price\s+(?:is\s+)?per\s+(?:lamp|light|unit|piece|pc|item|cup|mug|plate|bowl|cover|cushion|frame|print)/i,
  /(?:pair|set)\s*=\s*\d+\s*x\s*\$/i,
  /set of \d+\s*=\s*\d+\s*units/i,
  /=\s*order\s+qty\s*\d/i,
  /sell\s+\d+\s+units/i,
  /sell as a set of [\d\sor]+=\s*qty/i,
  /sold\s+(?:as\s+1\s*pc|singly|individually|per\s+piece)/i,
  /(?:מחיר|cost)[^.;\n]{0,25}ליחידה/,
  /ליחידה[^.;\n]{0,15}(?:מחיר|cost)/,
];
const QTY_WHOLE_SET_NOTES = [/price\s+(?:is\s+)?for\s+(?:\d+|two|three|four|the\s+(?:set|pair))\b/i, /המחיר\s+(?:הוא\s+)?ל(?:סט|זוג)/];
const QTY_WHOLE_SET_NAME = [/\bset of \d\b/i, /\bpair\b/i, /\b(?:two|three|four|five|six)-piece\b|\b\d+\s*-?\s*(?:pcs|pieces)\s*\/\s*set/i];
const QTY_COUNT = /set of (\d+)\s*=\s*\d+\s*units|כסט של (\d+) יחידות/i;
// "2 x $1.48", "(2 x 1.48 + 8.26)", "3 x 9.98 USD", "2 × $20.01 =": the notes price a sale of N units of the card's cost
// (QA 2026-10-17, M5). Only a money reading counts, never "15 x 15 x 30 cm".
const TIMES_COST = /(?<![\d.,])([2-9])\s*[x×]\s*(\$\s*)?(\d+(?:\.\d+)?)(\s*(?:USD|\+|=))?/g;
// How many pieces the room SKU's price covers, from the supplier's labels of its option values ("1 PC W100cmxH275cm",
// "2PC W225cm", "4 pcs", "set of 2", "pair"). A SKU that is already a pair or a set is never multiplied by the slot's set.
const SKU_PIECES: [RegExp, number | null][] = [
  [/(?<![\d.])(\d{1,2})\s*-?\s*(?:pcs?|pieces?|panels?)\b(?!\s*(?:\/|per)\s*(?:colou?r))/i, null],
  [/\bset\s*of\s*(\d{1,2})\b/i, null],
  [/\bpairs?\b|זוג/, 2],
  [/\bper\s+piece\b|\bsingle\b|פאנל אחד|יחידה אחת/, 1],
];
/** the final round priced at the conservative rate of FR-C (2026-10-10) */
const LEAD_FX = 3.3;
const ALT_TOL_CM = 3;

export type SellQtyDefault = { qty: number; sure: boolean; set_of: number | null; reason: string | null; sku_pieces?: number; alt_form?: string | null };

/** What the rule reads from a card: the studio reads the same fields (build.py sell_qty_default). */
export type SellQtyCard = {
  name?: string | null;
  notes?: string | null;
  /** the card's own `sell_qty` (rare: a card that states its sale) */
  sell_qty?: unknown;
  price?: { cost?: unknown } | null;
  dimensions_cm?: { width?: unknown } | null;
  options?: {
    default_sku: string;
    axes: { id: string; values: { id: string; label_he: string; label_src?: string }[] }[];
    skus: { id: string; values: Record<string, string | undefined>; shipping_il?: { amount: number; currency: string } | null }[];
  } | null;
};
export type SellQtySlot = {
  set_of?: number | null;
  /** data/slots alternative_form: one object or a list */
  alternative_form?: unknown;
};
export type SellQtyLead = { rec: Record<string, unknown>; file: string } | null;

const isNum = (v: unknown): v is number => typeof v === 'number' && Number.isFinite(v);
const setOf = (v: unknown): number | null => (isNum(v) && v > 1 ? Math.round(v) : null);

type AltForm = { id: string | null; name_he: string | null; set_of: number | null; envelope_cm: Record<string, unknown> | null };
function altForms(v: unknown): AltForm[] {
  const list = Array.isArray(v) ? v : v && typeof v === 'object' ? [v] : [];
  return list
    .filter((a): a is Record<string, unknown> => !!a && typeof a === 'object')
    .map((a) => ({
      id: a.id ? String(a.id) : null,
      name_he: typeof a.name_he === 'string' ? a.name_he : null,
      set_of: isNum(a.set_of) && Number.isInteger(a.set_of) && a.set_of >= 1 ? a.set_of : null,
      envelope_cm: a.envelope_cm && typeof a.envelope_cm === 'object' ? (a.envelope_cm as Record<string, unknown>) : null,
    }));
}

/** The slot's alternative form this card is (build.py alt_form_of): named in the card, or its width in the form's range. */
export function altFormOf(card: SellQtyCard, slot: SellQtySlot | null | undefined): (AltForm & { why: string }) | null {
  const forms = altForms(slot?.alternative_form);
  if (!forms.length) return null;
  const text = `${card.name ?? ''}\n${card.notes ?? ''}`.toLowerCase();
  const width = isNum(card.dimensions_cm?.width) ? card.dimensions_cm.width : null;
  for (const a of forms) {
    const words = [a.id, (a.id ?? '').replace(/-/g, ' '), a.name_he].filter((w): w is string => !!w);
    const hit = words.find((w) => text.includes(w.toLowerCase()));
    if (hit) return { ...a, why: `הכרטיס מציין "${hit}"` };
    const rng = a.envelope_cm?.w;
    if (width !== null && Array.isArray(rng) && rng.length === 2 && rng.every(isNum)) {
      const [lo, hi] = [Math.min(...(rng as number[])), Math.max(...(rng as number[]))];
      if (lo - ALT_TOL_CM <= width && width <= hi + ALT_TOL_CM) return { ...a, why: `רוחב ${width} ס"מ בטווח של הצורה החלופית (${lo}–${hi})` };
    }
  }
  return null;
}

/** (pieces the room SKU's price covers, the label that says so) from the SKU's value labels; the largest count wins. */
export function skuPieces(card: SellQtyCard): [number, string] | null {
  const o = card.options;
  if (!o) return null;
  const sku = o.skus.find((x) => x.id === o.default_sku);
  if (!sku) return null;
  const labels: string[] = [];
  for (const a of o.axes) {
    const v = a.values.find((x) => x.id === sku.values[a.id]);
    if (v) for (const k of ['label_src', 'label_he'] as const) if (v[k]) labels.push(String(v[k]));
  }
  for (const k of ['label', 'name', 'label_src']) {
    const v = (sku as Record<string, unknown>)[k];
    if (typeof v === 'string') labels.push(v);
  }
  const found: [number, string][] = [];
  for (const lab of labels) {
    for (const [rx, n] of SKU_PIECES) {
      const m = rx.exec(lab);
      if (m) {
        const k = n ?? Number(m[1]);
        if (k >= 1) found.push([k, lab]);
        break;
      }
    }
  }
  if (!found.length) return null;
  return found.reduce((a, b) => (b[0] > a[0] ? b : a));
}

/** (N, the words) when the card's notes price the sale as N x the card's own cost (build.py notes_times_cost). */
export function notesTimesCost(card: SellQtyCard): [number, string] | null {
  const cost = card.price?.cost;
  if (!isNum(cost) || cost <= 0) return null;
  for (const m of (card.notes ?? '').matchAll(TIMES_COST)) {
    if (!(m[2] || m[4])) continue;
    if (Math.abs(Number(m[3]) - cost) <= 0.011) return [Number(m[1]), m[0].trim()];
  }
  return null;
}

/**
 * (units in the sale, where it says so) from the card's final-round record (build.py lead_qty): its qty_in_sale / qty,
 * else what its landed cost implies (landed = (units x the card's cost + shipping) x 3.3).
 */
export function leadQtyOf(card: SellQtyCard, lead: SellQtyLead): [number, string] | null {
  if (!lead) return null;
  const c = lead.rec;
  for (const k of ['qty_in_sale', 'qty']) {
    const q = c[k];
    if (isNum(q) && Number.isInteger(q) && q > 1) return [q, lead.file];
  }
  const cost = card.price?.cost;
  if (['qty_in_sale', 'qty'].some((k) => isNum(c[k])) || !(isNum(c.landed_ils) && isNum(cost) && cost > 0)) return null;
  let ship = 0;
  if (isNum(c.ship_usd)) ship = c.ship_usd;
  else {
    const sku = card.options?.skus.find((x) => x.id === card.options?.default_sku);
    const si = sku?.shipping_il;
    if (si && isNum(si.amount) && si.currency.toUpperCase() === 'USD') ship = si.amount;
  }
  const q = (c.landed_ils / LEAD_FX - ship) / cost;
  const n = Math.round(q);
  if (n >= 2 && n <= 12 && Math.abs(q - n) <= 0.05 * n) return [n, `${lead.file}, לפי עלות הנחיתה ₪${c.landed_ils}`];
  return null;
}

function sellQtyNotes(name: string, notes: string, home: number | null, shared: [number, string][]): SellQtyDefault {
  const pp = QTY_PER_PIECE.some((r) => r.test(name) || r.test(notes));
  const wsStrong = QTY_WHOLE_SET_NOTES.some((r) => r.test(notes));
  const ws = wsStrong || QTY_WHOLE_SET_NAME.some((r) => r.test(name));
  if (home) {
    if (pp && !wsStrong) return { qty: home, sure: true, set_of: home, reason: `העמדה דורשת סט של ${home}, וההערות אומרות שהעלות ליחידה` };
    if (ws && !pp) return { qty: 1, sure: true, set_of: home, reason: `העמדה דורשת סט של ${home}, והעלות בכרטיס כבר לסט או לזוג` };
    return { qty: 1, sure: false, set_of: home, reason: `העמדה דורשת סט של ${home}, ולא ברור מהכרטיס אם העלות ליחידה או לסט` };
  }
  if (pp) {
    const m = QTY_COUNT.exec(name) ?? QTY_COUNT.exec(notes);
    let n: number | null = null;
    let why: string | null = null;
    if (m) {
      n = Number(m[1] ?? m[2]);
      why = `ההערות אומרות שהעלות ליחידה ושהמוצר נמכר כסט של ${n}`;
    } else if (shared.length) {
      const [sn, k] = shared.reduce((a, b) => (b[0] > a[0] ? b : a));
      n = sn;
      why = `ההערות אומרות שהעלות ליחידה, והעמדה המשותפת ${k} דורשת סט של ${n}`;
    }
    if (n && n > 1) return { qty: n, sure: true, set_of: n, reason: why };
  }
  return { qty: 1, sure: true, set_of: null, reason: null };
}

/**
 * Units per sale when the studio has not set `sell_qty` (units of the card's cost). Same rules, in the same order, as
 * studio/build.py sell_qty_default (a test keeps them aligned on the real cards): the card's own sell_qty; the slot's
 * alternative form; a room SKU whose label is already a pair or a set is never multiplied; then the notes rule (the slot's
 * set_of counts only when the card says its cost is per piece; unclear = 1 and sure: false), and when that gives 1, the
 * final-round record's units or "N x cost" in the notes.
 *   slot    the slot (set_of, alternative_form), or just its set_of as before
 *   lead    the card's final-round record (tools/lib/leads.ts), when there is one
 *   shared  other slots this card is shared in, with their set_of (the studio's _shared_in)
 */
export function sellQtyDefault(
  card: SellQtyCard,
  slot: SellQtySlot | number | null | undefined,
  lead: SellQtyLead = null,
  shared: [number, string][] = [],
): SellQtyDefault {
  const slotObj: SellQtySlot | null = typeof slot === 'number' ? { set_of: slot } : (slot ?? null);
  const home = setOf(slotObj?.set_of);
  const name = card.name ?? '';
  const notes = card.notes ?? '';
  const own = card.sell_qty;
  if (isNum(own) && Number.isInteger(own) && own >= 1) return { qty: own, sure: true, set_of: home, reason: `הכרטיס קובע ${own} יח' למכירה (sell_qty)` };
  const alt = altFormOf(card, slotObj);
  if (alt) {
    const n = alt.set_of ?? 1;
    return { qty: n, sure: true, set_of: n, alt_form: alt.id, reason: `הצורה החלופית של העמדה (${alt.name_he ?? alt.id}): ${n} יח' במכירה, ${alt.why}` };
  }
  const pcs = skuPieces(card);
  if (pcs && pcs[0] > 1) {
    const m = QTY_COUNT.exec(name) ?? QTY_COUNT.exec(notes);
    let need: number | null = null;
    let why: string | null = null;
    if (home) [need, why] = [home, `העמדה דורשת סט של ${home}`];
    else if (m) {
      need = Number(m[1] ?? m[2]);
      why = `ההערות אומרות שהמוצר נמכר כסט של ${need}`;
    } else if (shared.length) {
      const [sn, k] = shared.reduce((a, b) => (b[0] > a[0] ? b : a));
      [need, why] = [sn, `העמדה המשותפת ${k} דורשת סט של ${sn}`];
    }
    if (!need || pcs[0] >= need)
      return { qty: 1, sure: true, set_of: need, sku_pieces: pcs[0], reason: need ? `${why}, והמק"ט שבחדר כבר כולל ${pcs[0]} יח' (${pcs[1]})` : null };
    return {
      qty: 1,
      sure: false,
      set_of: need,
      sku_pieces: pcs[0],
      reason: `${why}, והמק"ט שבחדר הוא כבר סט של ${pcs[0]} (${pcs[1]}). לא ברור אם צריך עוד סט`,
    };
  }
  let out = sellQtyNotes(name, notes, home, shared);
  if (out.qty === 1) {
    const lq = leadQtyOf(card, lead);
    const tc = lq ? null : notesTimesCost(card);
    if (lq) out = { qty: lq[0], sure: true, set_of: home ?? lq[0], reason: `הליקוט האחרון מתמחר ${lq[0]} יח' במכירה (${lq[1]}), והעלות בכרטיס ליחידה` };
    else if (tc)
      out = { qty: tc[0], sure: true, set_of: home ?? tc[0], reason: `ההערות מחשבות את המכירה כ-${tc[0]} × העלות שבכרטיס ("${tc[1].slice(0, 40)}")` };
  }
  if (pcs && pcs[0] === 1) {
    out.sku_pieces = 1;
    if (out.qty > 1 && out.reason) out.reason += `; המק"ט שבחדר הוא יחידה אחת (${pcs[1]})`;
    else if (!out.sure && out.set_of)
      out.reason = `העמדה דורשת סט של ${out.set_of}, והמק"ט שבחדר הוא יחידה אחת (${pcs[1]}). לא ברור אם הסט הוא ${out.set_of} מאותו מוצר`;
  }
  return out;
}
