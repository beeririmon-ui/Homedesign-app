// qa-agent scratch test: how site/tools/lib/qa-frames.ts reads close-up records, and what make-story.ts lines 367-372 do with them
import { relative } from 'node:path';
import { qaReader, cardOf, type QaFrame } from '/home/user/homedesign-app/site/tools/lib/qa-frames.ts';
const REPO = '/home/user/homedesign-app';
const S = process.argv[2]!;
const base = ['qa/reports/2026-11-07-editorial-fin2-ed4-country.json', 'qa/reports/2026-11-07-ged-codefix-mc1-clay.json'];
const recs = ['rec-old.json', 'rec-new-noagainst.json', 'rec-new-against.json', 'rec-almost.json', 'rec-flat.json'].map((f) => relative(REPO, `${S}/${f}`));
const qaOf = qaReader([...base, ...recs]);
const allowed = ['final_test', 'almost'];
const faithfulOf = (q: QaFrame, product: string): string => q.rows.find((r) => cardOf(r) === product)?.faithful ?? 'not checked';
const isFaithful = (v: string) => /^yes\b/.test(v);
const product = 'rug-cj-braided-wool-natural';
const frameVerdict = faithfulOf(qaOf('nordic-A-ed4')!, product);
for (const key of ['nordic-A-rug-cu1', 'nordic-A-rug-cu2', 'nordic-A-rug-cu3', 'nordic-A-rug-cu4', 'nordic-A-rug-cu5']) {
  const cq = qaOf(key);
  const closeupYes = !!cq && allowed.includes(cq.state) && isFaithful(faithfulOf(cq, product));
  const dot = isFaithful(frameVerdict) || (/^partly\b/.test(frameVerdict) && closeupYes);
  console.log(JSON.stringify({ key, read: !!cq, state: cq?.state ?? null, rows: cq?.rows.length ?? 0, verdict_in_closeup: cq ? faithfulOf(cq, product) : null, frame_verdict: frameVerdict, dot }));
}
