/**
 * Standards and safety on the product page (decision D9, docs/studio-rules.md ד.4): the card's optional `safety` block
 * (data/product-card.schema.json) becomes a "תקנים ובטיחות" row. Only claims that have a value in the card are shown;
 * a missing block, a null and an empty list show nothing. `source` (where the supplier said it) stays internal, and a
 * certificate link is public only once it is verified. A certificate without a document (schema 1.2, source:
 * seller-claim; decision SCH1, 2026-11-03) is shown as the seller's claim, never as a verified certificate.
 */
import { z } from 'zod';
import { safetyLinesHe } from './safety-lines';

export const TOY_STANDARDS = ['EN71', 'SI-562', 'EN13613'] as const;
export const POWER_KINDS = ['plug', 'wired', 'battery', 'usb', 'none'] as const;

/** What the browser gets (no source; unverified certificates without their link). */
export const PublicSafetySchema = z.object({
  ce: z.boolean().nullable(),
  ip_rating: z.string().nullable(),
  toy_standard: z.array(z.enum(TOY_STANDARDS)),
  power: z.enum(POWER_KINDS).nullable(),
  plug_type: z.string().nullable(),
  voltage: z.string().nullable(),
  certificates: z.array(
    z.object({
      name: z.string(),
      url: z.string().nullable(),
      verified: z.boolean(),
      /** the seller's claim, no document (card schema 1.2, source: seller-claim; decision SCH1) */
      seller_claim: z.boolean(),
    }),
  ),
});
export type PublicSafety = z.infer<typeof PublicSafetySchema>;

type CardSafety = {
  ce?: boolean | null;
  ip_rating?: string | null;
  toy_standard?: (typeof TOY_STANDARDS)[number][];
  power?: (typeof POWER_KINDS)[number] | null;
  plug_type?: string | null;
  voltage?: string | null;
  certificates?: { name: string; url?: string; verified: boolean; source?: 'seller-claim' }[];
  source?: string;
};

const clean = (s: string | null | undefined): string | null => (typeof s === 'string' && s.trim() ? s.trim() : null);

/** Card block → public block; null when nothing in it would be shown. */
export function publicSafety(s: CardSafety | null | undefined): PublicSafety | null {
  if (!s) return null;
  const out: PublicSafety = {
    ce: typeof s.ce === 'boolean' ? s.ce : null,
    ip_rating: clean(s.ip_rating)?.toUpperCase().replace(/\s+/g, '') ?? null,
    toy_standard: [...new Set(s.toy_standard ?? [])],
    power: s.power ?? null,
    plug_type: clean(s.plug_type),
    voltage: clean(s.voltage),
    certificates: (s.certificates ?? [])
      .filter((c) => clean(c.name))
      .map((c) => ({
        name: c.name.trim(),
        url: c.verified && c.url ? c.url : null,
        // a certificate without a document is never "verified", whatever the flag says
        verified: c.verified === true && !!c.url,
        seller_claim: !c.url || c.source === 'seller-claim',
      })),
  };
  return safetyLinesHe(out).length ? out : null;
}

// S13: the Hebrew lines are the browser's half, zod-free, in ./safety-lines (the room's JS budget)
export { safetyLinesHe, type SafetyLine } from './safety-lines';
