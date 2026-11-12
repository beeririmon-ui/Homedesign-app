// QA S22: kept as written for the run (the output files it names live in the scratchpad, never in the repo).
// QA S22: a test contact for the public build, made at run time: not in the repo, not a sample (contact-samples), well
// formed (@hd/shared/contact). Writes a wrangler config for HD_WRANGLER and the two values for my server's --var.
import { readFileSync, writeFileSync } from 'node:fs';
import { pathToFileURL } from 'node:url';
const [site, outCfg, outEnv] = process.argv.slice(2);
const S = await import(pathToFileURL(`${site}/shared/src/contact-samples.ts`).href);
const C = await import(pathToFileURL(`${site}/shared/src/contact.ts`).href);
const r = (n: number) => Math.random().toString(36).slice(2, 2 + n).replace(/\d/g, 'k');
for (;;) {
  const email = `studio@beit-${r(5)}-${r(4)}.co.il`;
  const phone = `03-6${String(100000 + Math.floor(Math.random() * 899999))}`;
  if (S.sampleEmailReason(email) || S.samplePhoneReason(phone)) continue;
  const issues = C.contactIssues({ CONTACT_EMAIL: email, CONTACT_PHONE: phone });
  if (issues.length) { console.log('issue', issues); process.exit(1); }
  const cfg = readFileSync(`${site}/api/wrangler.jsonc`, 'utf8').replaceAll('"CONTACT_EMAIL": "UNDECIDED"', `"CONTACT_EMAIL": "${email}"`).replaceAll('"CONTACT_PHONE": "UNDECIDED"', `"CONTACT_PHONE": "${phone}"`);
  writeFileSync(outCfg, cfg);
  writeFileSync(outEnv, `QA_CONTACT_EMAIL=${email}\nQA_CONTACT_PHONE=${phone}\n`);
  console.log('made a test contact (not printed), replaced', (cfg.match(new RegExp(email.replace(/[.]/g, '\\.'), 'g')) ?? []).length, 'emails');
  break;
}
