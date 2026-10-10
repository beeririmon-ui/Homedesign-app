import type { CartLine } from '@hd/shared';
import { packLabelHe } from '@hd/shared/packs';

/** What a cart or order line holds (P1): "סט של N" or "יחידה אחת"; empty for a product sold only as itself. */
export function lineLabelHe(l: Pick<CartLine, 'pack' | 'pack_qty'>): string {
  if (l.pack === 'unit') return packLabelHe('unit', 1);
  return l.pack_qty > 1 ? packLabelHe('set', l.pack_qty) : '';
}
