import type { CartLine } from '@hd/shared';
import { packLabelHe } from '@hd/shared/packs';

/**
 * What a cart or order line holds: the supplier option chosen on the product page ("בז', 45×45 ס"מ", 2026-10-11) and
 * the pack (P1: "סט של N" or "יחידה אחת"); empty for a product sold only as itself.
 */
export function lineLabelHe(l: Pick<CartLine, 'pack' | 'pack_qty'> & { option_he?: string | null }): string {
  const pack = l.pack === 'unit' ? packLabelHe('unit', 1) : l.pack_qty > 1 ? packLabelHe('set', l.pack_qty) : '';
  return [l.option_he, pack].filter(Boolean).join(', ');
}
