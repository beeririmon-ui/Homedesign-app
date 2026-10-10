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

export type SellQtyDefault = { qty: number; sure: boolean; set_of: number | null; reason: string | null };

/**
 * Units per sale when the studio has not set `sell_qty`. The slot's set_of counts only when the card says its cost is
 * per piece; when that is unclear the default is 1 and sure = false (the studio shows a "not sure" chip). Same rules
 * as studio/build.py (a test keeps them aligned on the real cards).
 */
export function sellQtyDefault(card: { name?: string | null; notes?: string | null }, slotSetOf: number | null | undefined): SellQtyDefault {
  const home = typeof slotSetOf === 'number' && slotSetOf > 1 ? slotSetOf : null;
  const name = card.name ?? '';
  const notes = card.notes ?? '';
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
    const n = m ? Number(m[1] ?? m[2]) : null;
    if (n && n > 1) return { qty: n, sure: true, set_of: n, reason: `ההערות אומרות שהעלות ליחידה ושהמוצר נמכר כסט של ${n}` };
  }
  return { qty: 1, sure: true, set_of: null, reason: null };
}
