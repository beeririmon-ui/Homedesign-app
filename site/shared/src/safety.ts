/**
 * Standards and safety on the product page (decision D9, docs/studio-rules.md ד.4): the card's optional `safety` block
 * (data/product-card.schema.json) becomes a "תקנים ובטיחות" row. Only claims that have a value in the card are shown;
 * a missing block, a null and an empty list show nothing. `source` (where the supplier said it) stays internal, and a
 * certificate link is public only once it is verified.
 */
import { z } from 'zod';

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
  certificates: z.array(z.object({ name: z.string(), url: z.string().nullable(), verified: z.boolean() })),
});
export type PublicSafety = z.infer<typeof PublicSafetySchema>;

type CardSafety = {
  ce?: boolean | null;
  ip_rating?: string | null;
  toy_standard?: (typeof TOY_STANDARDS)[number][];
  power?: (typeof POWER_KINDS)[number] | null;
  plug_type?: string | null;
  voltage?: string | null;
  certificates?: { name: string; url: string; verified: boolean }[];
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
      .map((c) => ({ name: c.name.trim(), url: c.verified ? c.url : null, verified: c.verified === true })),
  };
  return safetyLinesHe(out).length ? out : null;
}

const STANDARD_HE: Record<(typeof TOY_STANDARDS)[number], string> = { EN71: 'EN 71', 'SI-562': 'ת"י 562', EN13613: 'EN 13613' };

/** IP code → whether it is splash-proof (second digit ≥ 4: IP44, IPX4, IP65…), the bathroom requirement (ד.5). */
function splashProof(ip: string): boolean {
  const m = /^IP([0-9X])([0-9X])$/.exec(ip);
  return !!m && m[2] !== 'X' && Number(m[2]) >= 4;
}

export type SafetyLine = { text: string; href?: string };

/** The Hebrew lines of the row, in a fixed order. Never a claim the card does not make. */
export function safetyLinesHe(s: PublicSafety | null | undefined): SafetyLine[] {
  if (!s) return [];
  const lines: SafetyLine[] = [];
  const toys = s.toy_standard.filter((t) => t === 'EN71' || t === 'SI-562');
  if (toys.length) lines.push({ text: `תקן צעצועים ${toys.map((t) => STANDARD_HE[t]).join(' / ')}` });
  if (s.toy_standard.includes('EN13613')) lines.push({ text: `תקן סקייטבורד ${STANDARD_HE.EN13613}` });
  if (s.ip_rating) lines.push({ text: splashProof(s.ip_rating) ? `${s.ip_rating}, מתאים לחדר רחצה` : `דרגת אטימות ${s.ip_rating}` });
  if (s.ce === true) lines.push({ text: 'CE' });
  if (s.power === 'wired') lines.push({ text: 'דורשת התקנה על ידי חשמלאי' });
  else if (s.power === 'plug') lines.push({ text: s.plug_type ? `מתחברת לשקע, תקע ${s.plug_type}` : 'מתחברת לשקע' });
  else if (s.power === 'battery') lines.push({ text: 'פועלת על סוללות' });
  else if (s.power === 'usb') lines.push({ text: 'הזנה בחיבור USB' });
  if (s.voltage) lines.push({ text: `מתח ${s.voltage}` });
  for (const c of s.certificates) lines.push({ text: c.verified ? `תעודה: ${c.name}` : `תעודה: ${c.name} (לפי הספק, לא אומתה)`, href: c.url ?? undefined });
  return lines;
}
