// qa-agent scratch test of site/tools/lib/qa-frames.ts (register reader) and of the close-up gate of make-story.ts 412-423
import { relative } from 'node:path';
import { registerReader, rowOf, qaReader, type QaFrame } from '/home/user/homedesign-app/site/tools/lib/qa-frames.ts';
const REPO = '/home/user/homedesign-app';
const S = process.argv[2]!;
const rel = (p: string) => relative(REPO, p);
const out: Record<string, unknown> = {};
const reg = registerReader(rel(`${S}/regs-ok`));
out.highest = { path: reg.path, version: reg.version };
const FINAL = new Set(['final_test', 'approved_for_site']);
const isFaithful = (v: string) => /^yes\b/.test(v);
const faithfulOf = (q: QaFrame, p: string, v: Record<string, string> | null) => rowOf(q, p, v)?.faithful ?? 'not checked';
const product = 'rug-cj-braided-wool-natural';
const values = { size: '200x300', other: 'square' };
const frameRow = rowOf(reg.read('nordic-A-ed4')!, product, values)!;
out.frame_row = frameRow;
for (const [key, option] of [['cu-final-same', undefined], ['cu-almost', undefined], ['cu-final-other', { size: '160x230' }], ['cu-final-partly', undefined]] as const) {
  const c = { product, option, qa_key: key };
  const sameOption = Object.entries(c.option ?? {}).every(([k, v]) => (values as Record<string, string>)[k] === v) && (!!c.option || true);
  const cq = sameOption ? reg.read(c.qa_key) : null;
  const closeupYes = !!cq && FINAL.has(cq.state) && isFaithful(faithfulOf(cq, product, values));
  const dot = frameRow.dot ? frameRow.dot === 'yes' || (frameRow.dot === 'closeup_only' && closeupYes) : false;
  out[key] = { state: cq?.state ?? null, sameOption, closeupYes, dot };
}
for (const bad of ['regs-bad1', 'regs-bad2', 'regs-bad3'])
  try {
    registerReader(rel(`${S}/${bad}`));
    out[bad] = 'READ (no error)';
  } catch (e) {
    out[bad] = `throws: ${(e as Error).message.slice(0, 160)}`;
  }
for (const legacy of ['part1-noagainst.json', 'flat.json'])
  try {
    out[legacy] = qaReader([rel(`${S}/legacy/${legacy}`)])('k') ? 'read' : 'null';
  } catch (e) {
    out[legacy] = `throws: ${(e as Error).message.slice(0, 160)}`;
  }
console.log(JSON.stringify(out, null, 1));
