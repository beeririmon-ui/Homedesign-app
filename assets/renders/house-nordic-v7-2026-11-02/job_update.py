#!/usr/bin/env python3
"""Update one job in jobs.json with key=value pairs (JSON values). usage: python3 job_update.py <id> key=json [key=json ...]"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
J = json.load(open(os.path.join(HERE, 'jobs.json')))
jid = sys.argv[1]
job = next(j for j in J['jobs'] if j['id'] == jid)
for kv in sys.argv[2:]:
    k, v = kv.split('=', 1)
    try:
        job[k] = json.loads(v)
    except Exception:
        job[k] = v
J['spent_tokens'] = sum(j.get('credits', 0) or 0 for j in J['jobs'])
json.dump(J, open(os.path.join(HERE, 'jobs.json'), 'w'), indent=1, ensure_ascii=False)
print(jid, {k: job.get(k) for k in ('status', 'placeholder_id', 'credits', 'attempt')}, 'spent', J['spent_tokens'])
