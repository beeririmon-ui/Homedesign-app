// qa-agent: the deploy check (configIssues) on NOTIFY_PROVIDER in a production block, and the run-time choice (S13)
import { configIssues, providerOf } from '../build-s1314/site/api/src/lib/config';
import { notifier } from '../build-s1314/site/api/src/lib/notify';
const base = { ENVIRONMENT: 'production', PAYMENT_PROVIDER: 'UNDECIDED', INVOICE_PROVIDER: 'UNDECIDED', SUPPLIER_PROVIDER: 'cj' };
for (const v of [undefined, '', 'mock', 'Mock', 'UNDECIDED', 'telegram', 'email']) {
  const vars: Record<string, unknown> = { ...base, ...(v === undefined ? {} : { NOTIFY_PROVIDER: v }) };
  const n = notifier(vars as { ENVIRONMENT: string; NOTIFY_PROVIDER?: string });
  console.log(`production NOTIFY_PROVIDER=${JSON.stringify(v)}: deploy check ${configIssues(vars).filter((x) => x.includes('NOTIFY')).join(' | ') || 'passes'}; at run time ${n.ok ? `runs ${n.notifier.id}` : 'skipped'}`);
}
for (const E of ['development', 'preview', 'preview-local', 'test']) console.log(`${E} NOTIFY_PROVIDER="mock": ${providerOf({ ENVIRONMENT: E, NOTIFY_PROVIDER: 'mock' }, 'NOTIFY_PROVIDER').ok ? 'mock runs' : 'refused'}`);
