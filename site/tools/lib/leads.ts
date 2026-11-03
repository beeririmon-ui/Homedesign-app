/**
 * The final round's records per card (data/leads/final-2026-10-13/results/*.json), read the way the studio reads them
 * (scripts/boards/room_boards.py Context.records_any, studio/build.py lead_records): the repriced record (an Israeli-value
 * price) first, then the newest file; the card's record is the first one with a plain price. The Israeli-shop files (il-*)
 * are skipped, as in the studio.
 */
import { readdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import type { LeadRecord } from '@hd/shared';

export const RESULTS_DIR = 'data/leads/final-2026-10-13/results';

type Rec = Record<string, unknown>;
type Entry = [flag: number, date: string, file: string, rec: Rec];

export function loadLeadRecords(repo: string): Map<string, LeadRecord> {
  const dir = join(repo, RESULTS_DIR);
  const all = new Map<string, Entry[]>();
  let files: string[] = [];
  try {
    files = readdirSync(dir).filter((f) => f.endsWith('.json') && !f.startsWith('il-'));
  } catch {
    return new Map();
  }
  for (const f of files) {
    let d: { date?: unknown; slots?: Record<string, { candidates?: unknown }> };
    try {
      d = JSON.parse(readFileSync(join(dir, f), 'utf8')) as typeof d;
    } catch {
      continue;
    }
    const date = String(d.date ?? '');
    for (const s of Object.values(d.slots ?? {})) {
      const cands = Array.isArray(s?.candidates) ? (s.candidates as Rec[]) : [];
      for (const c of cands) {
        if (!c || typeof c !== 'object' || !c.card_id) continue;
        const p = c.price_ils;
        const flag = p === null || p === undefined || p === '' || (typeof p === 'object' && Object.keys(p as object).length === 0) ? 0 : 1;
        const id = String(c.card_id);
        if (!all.has(id)) all.set(id, []);
        all.get(id)!.push([flag, date, f, c]);
      }
    }
  }
  const out = new Map<string, LeadRecord>();
  for (const [id, list] of all) {
    list.sort((a, b) => b[0] - a[0] || b[1].localeCompare(a[1]) || b[2].localeCompare(a[2]));
    const hit = list.find(([, , , c]) => typeof c.price_ils === 'number' && c.price_ils > 0);
    if (hit) out.set(id, { rec: hit[3], file: hit[2], date: hit[1] });
  }
  return out;
}
