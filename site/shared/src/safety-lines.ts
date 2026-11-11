/**
 * S13: the "תקנים ובטיחות" row's Hebrew lines, zod-free, so the product page loads them without the schemas of
 * ./safety (which re-exports this). Never a claim the card does not make.
 */
import type { PublicSafety, TOY_STANDARDS } from './safety';

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
  for (const c of s.certificates)
    lines.push({
      text: c.seller_claim ? `${c.name}: טענת המוכר, אין מסמך` : c.verified ? `תעודה: ${c.name}` : `תעודה: ${c.name} (לפי הספק, לא אומתה)`,
      href: c.url ?? undefined,
    });
  return lines;
}
