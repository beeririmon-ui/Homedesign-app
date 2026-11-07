/**
 * QA's verdict and product rows for an editorial frame.
 *
 * Since 2026-11-07 the source is QA's register (registerReader): qa/reports/ged-register-<date>[-r<N>].json, a new file
 * per QA round with a rising `version`; the site reads the highest. `frames.<key>` has `state` (not_yet | almost |
 * final_test | approved_for_site; the designer's eye verdicts folded in) and one row per product, and per option when a
 * frame shows two options of one card: card_id, option (value ids, a text label, or null for the card's default),
 * verdict, note, dot (yes | no | closeup_only, G-ED.5). `superseded_by` maps older frame keys to the frame that replaces
 * them.
 *
 * Before the register (qaReader, kept for the records it was built on), the verdicts were read across QA's records
 * (listed oldest first; a newer record wins for a frame it lists). Two shapes:
 *  - qa/reports/2026-11-07-editorial-fin2-ed4-country.json: `final_test.<key>` is text ("ready…", "almost…", "not yet…")
 *    and `frames.<key>.rows` holds every product row
 *  - qa/reports/2026-11-07-ged-codefix-mc1-clay.json: `part1.frames.<key>` has `state` ("final_test" | "almost" |
 *    "not_yet"), `against` (the frame it was made from) and `rows_changed` (only the rows that changed): the rows are
 *    the base frame's rows with those changes
 * The key is the frame file's name without .png ("warm-modern-A-ed5").
 */
import { readFileSync, readdirSync } from 'node:fs';
import { basename, join } from 'node:path';
import { repoPath } from './paths';

export type QaState = 'final_test' | 'almost' | 'not_yet' | 'approved_for_site';
export type QaRow = {
  card: string;
  present: boolean;
  faithful: string;
  why?: string;
  /** the register's option (value ids, a text label, or null for the card's default) and its dot rule */
  option?: Record<string, string> | string | null;
  dot?: 'yes' | 'no' | 'closeup_only';
};
export type QaFrame = { state: QaState; rows: QaRow[]; record: string };

type OldShape = { final_test?: Record<string, string>; frames?: Record<string, { rows: QaRow[] }> };
type NewShape = {
  part1?: { frames?: Record<string, { state: QaState; against?: string; rows_changed?: { card: string; faithful: string; why?: string }[] }> };
};

/** "ready (unchanged; …)" → final_test, "almost: …" → almost, anything else → not_yet */
const stateOf = (text: string): QaState => (text.startsWith('ready') ? 'final_test' : text.startsWith('almost') ? 'almost' : 'not_yet');
/** a row's card is its first word ("cushions-cj-boucle-teddy (White, Milk tea)") */
export const cardOf = (row: { card: string }): string => row.card.split(' ')[0]!;

export function qaReader(records: string[]): (key: string) => QaFrame | null {
  const recs = records.map((path) => ({ path, d: JSON.parse(readFileSync(repoPath(path), 'utf8')) as OldShape & NewShape }));
  const find = (key: string, depth = 0): QaFrame | null => {
    if (depth > 8) return null;
    for (const r of [...recs].reverse()) {
      const f = r.d.part1?.frames?.[key];
      if (f) {
        if (!f.against) throw new Error(`${r.path}: part1.frames.${key} has no "against", so its rows cannot be read`);
        const base = find(basename(f.against, '.png'), depth + 1);
        if (!base) throw new Error(`${r.path}: part1.frames.${key} is against ${f.against}, which no record lists`);
        const rows = (base?.rows ?? []).map((row) => {
          const ch = f.rows_changed?.find((c) => cardOf(c) === cardOf(row));
          return ch ? { ...row, faithful: ch.faithful, ...(ch.why ? { why: ch.why } : {}) } : row;
        });
        return { state: f.state, rows, record: r.path };
      }
      const text = r.d.final_test?.[key];
      const rows = r.d.frames?.[key]?.rows;
      // a record that lists the frame in a shape without its rows (the flat codefix5 shape) is not read as no rows
      if (r.d.frames?.[key] && !Array.isArray(rows)) throw new Error(`${r.path}: frames.${key} has no rows, so its verdicts cannot be read`);
      if (text !== undefined && rows) return { state: stateOf(text), rows, record: r.path };
    }
    return null;
  };
  return (key) => find(key);
}

type RegisterFrame = { state: QaState; rows: { card_id: string; option: QaRow['option']; verdict: string; note?: string; dot: QaRow['dot'] }[] };
type Register = {
  version: number;
  frames: Record<string, RegisterFrame>;
  /** layer 2's close-ups, keyed by their qa_key, with the same four states and full rows */
  closeups?: Record<string, RegisterFrame>;
  superseded_by?: Record<string, string>;
};
const STATES = new Set<QaState>(['not_yet', 'almost', 'final_test', 'approved_for_site']);
const DOTS = new Set(['yes', 'no', 'closeup_only']);
/** QA on S2: a record the site cannot read fails loudly, never as a frame with no rows */
function checkRegister(path: string, d: Register): void {
  const bad: string[] = [];
  if (!Number.isInteger(d.version)) bad.push('version');
  for (const [part, frames] of [
    ['frames', d.frames],
    ['closeups', d.closeups ?? {}],
  ] as const) {
    if (!frames || typeof frames !== 'object') {
      bad.push(part);
      continue;
    }
    for (const [key, f] of Object.entries(frames)) {
      if (!STATES.has(f?.state)) bad.push(`${part}.${key}.state`);
      if (!Array.isArray(f?.rows) || (f.state !== 'not_yet' && !f.rows.length)) bad.push(`${part}.${key}.rows`);
      for (const [i, r] of (f?.rows ?? []).entries())
        if (typeof r?.card_id !== 'string' || typeof r?.verdict !== 'string' || !DOTS.has(r?.dot as string)) bad.push(`${part}.${key}.rows[${i}]`);
    }
  }
  if (bad.length) throw new Error(`${path}: QA's register cannot be read (${bad.slice(0, 8).join(', ')}${bad.length > 8 ? ', …' : ''})`);
}
export type RegisterReader = {
  path: string;
  version: number;
  read: (key: string) => QaFrame | null;
  /** the frame that replaces an older key, or null */
  supersededBy: (key: string) => string | null;
};
/** QA's register with the highest version among qa/reports/ged-register-*.json */
export function registerReader(dir = 'qa/reports'): RegisterReader {
  const files = readdirSync(repoPath(dir)).filter((n) => /^ged-register-.*\.json$/.test(n));
  const all = files.map((n) => ({ path: join(dir, n), d: JSON.parse(readFileSync(repoPath(dir, n), 'utf8')) as Register }));
  const top = all.sort((a, b) => b.d.version - a.d.version)[0];
  if (!top) throw new Error(`no QA register (${dir}/ged-register-*.json)`);
  checkRegister(top.path, top.d);
  return {
    path: top.path,
    version: top.d.version,
    read: (key) => {
      const f = top.d.frames[key] ?? top.d.closeups?.[key];
      if (!f) return null;
      const rows = f.rows.map((r) => ({ card: r.card_id, present: true, faithful: r.verdict, why: r.note, option: r.option, dot: r.dot }));
      return { state: f.state, rows, record: top.path };
    },
    supersededBy: (key) => top.d.superseded_by?.[key] ?? null,
  };
}
/**
 * The row of one product in a frame, for the option the frame shows: a row whose option names value ids matches when
 * every one of them is the point's; a row without an option (or a text label) is the product's row otherwise.
 */
export function rowOf(q: QaFrame, card: string, values: Record<string, string> | null): QaRow | null {
  const rows = q.rows.filter((r) => cardOf(r) === card);
  const exact = rows.find((r) => r.option && typeof r.option === 'object' && Object.entries(r.option).every(([k, v]) => values?.[k] === v));
  return exact ?? rows.find((r) => !r.option || typeof r.option !== 'object') ?? rows[0] ?? null;
}
