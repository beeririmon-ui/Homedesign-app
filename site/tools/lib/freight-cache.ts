/**
 * The cached supplier answers (data/sources/<supplier>/<id>.json, written by the sourcing scripts): the freight lines of
 * the room SKU to Israel for one piece, the way scripts/economics/no_loss.py reads them (source_quotes). The no-loss
 * prices of 2026-10-20 were computed from these for products the studio has no freight file for, so the site reads
 * them too, after the studio's own sources and before the final-round record. Read-only; no supplier is contacted.
 */
import { existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import type { ShippingLine } from '@hd/shared';

type Section = { payload?: { options?: Record<string, unknown>[]; variants?: Record<string, unknown>[] } };
type Cached = { sections?: Record<string, Section> };

function readCached(repo: string, kind: 'aliexpress' | 'cj', id: string): Cached | null {
  const f = join(repo, 'data/sources', kind, `${id}.json`);
  if (!existsSync(f)) return null;
  try {
    return JSON.parse(readFileSync(f, 'utf8')) as Cached;
  } catch {
    return null;
  }
}

const num = (v: unknown): number | null => (typeof v === 'number' && Number.isFinite(v) ? v : null);

/** The one-piece lines of a SKU (or a CJ vid) from the cached answer, or null when there is none. */
function linesOf(d: Cached | null, kind: 'aliexpress' | 'cj', key: string): ShippingLine[] | null {
  const sec = d?.sections?.[`freight:${key}:IL:1`];
  const opts = sec?.payload?.options;
  if (!Array.isArray(opts)) return null;
  const out: ShippingLine[] = [];
  for (const o of opts) {
    if (kind === 'aliexpress') {
      const fee = num(o.fee);
      if (fee === null || String(o.currency ?? 'USD').toUpperCase() !== 'USD') continue;
      const dmax = num(o.days_max);
      out.push({ usd: fee, name: (o.company as string) ?? (o.code as string) ?? null, days: dmax !== null ? `${num(o.days_min) ?? dmax}-${dmax}` : null });
    } else {
      const usd = num(o.usd);
      if (usd === null) continue;
      out.push({ usd, name: (o.name as string) ?? null, days: (o.days as string) ?? null });
    }
  }
  return out.length ? out : null;
}

export type CachedFreight = { lines: ShippingLine[]; label: string };

/**
 * The cached lines of a card's room SKU: AliExpress by item id (the card's product_url) and SKU (options.default_sku,
 * else supplier.sku); CJ by the product id in the url and the vid of the room SKU (the cached product answer).
 */
export function cachedFreight(
  repo: string,
  card: { supplier: { product_url: string; sku?: string | null }; options?: { default_sku: string } | null },
  cj?: { pid?: string; vid?: string } | null,
): CachedFreight | null {
  const url = card.supplier.product_url;
  const roomSku = String(card.options?.default_sku ?? card.supplier.sku ?? '');
  const ae = /aliexpress\.[a-z.]+\/item\/(\d+)\.html/i.exec(url)?.[1];
  if (ae && roomSku) {
    const lines = linesOf(readCached(repo, 'aliexpress', ae), 'aliexpress', roomSku);
    if (lines) return { lines, label: `מטמון AliExpress ${ae} sku ${roomSku}` };
  }
  const pid = cj?.pid ?? /-p-([^./?#]+)\.html/.exec(url)?.[1];
  if (pid) {
    const d = readCached(repo, 'cj', pid);
    let vid = cj?.vid ?? null;
    if (!vid && roomSku) {
      const v = d?.sections?.product?.payload?.variants?.find((x) => String(x.variantSku ?? '') === roomSku && x.vid);
      vid = v ? String(v.vid) : null;
    }
    if (vid) {
      const lines = linesOf(d, 'cj', vid);
      if (lines) return { lines, label: `מטמון CJ vid ${vid}` };
    }
  }
  return null;
}
