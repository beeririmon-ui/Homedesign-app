/**
 * QA's verdict and product rows for an editorial frame, read across QA's records (listed oldest first; a newer record
 * wins for a frame it lists). Two shapes so far:
 *  - qa/reports/2026-11-07-editorial-fin2-ed4-country.json: `final_test.<key>` is text ("ready…", "almost…", "not yet…")
 *    and `frames.<key>.rows` holds every product row
 *  - qa/reports/2026-11-07-ged-codefix-mc1-clay.json: `part1.frames.<key>` has `state` ("final_test" | "almost" |
 *    "not_yet"), `against` (the frame it was made from) and `rows_changed` (only the rows that changed): the rows are
 *    the base frame's rows with those changes
 * The key is the frame file's name without .png ("warm-modern-A-ed5").
 */
import { readFileSync } from 'node:fs';
import { basename } from 'node:path';
import { repoPath } from './paths';

export type QaState = 'final_test' | 'almost' | 'not_yet';
export type QaRow = { card: string; present: boolean; faithful: string; why?: string };
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
        const base = f.against ? find(basename(f.against, '.png'), depth + 1) : null;
        const rows = (base?.rows ?? []).map((row) => {
          const ch = f.rows_changed?.find((c) => cardOf(c) === cardOf(row));
          return ch ? { ...row, faithful: ch.faithful, ...(ch.why ? { why: ch.why } : {}) } : row;
        });
        return { state: f.state, rows, record: r.path };
      }
      const text = r.d.final_test?.[key];
      const rows = r.d.frames?.[key]?.rows;
      if (text !== undefined && rows) return { state: stateOf(text), rows, record: r.path };
    }
    return null;
  };
  return (key) => find(key);
}
