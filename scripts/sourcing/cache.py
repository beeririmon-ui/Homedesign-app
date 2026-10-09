#!/usr/bin/env python3
"""Raw payload cache, in the repo: data/sources/<source>/<id>.json

One file per supplier item, one section per kind, each with its own timestamp:
    {"source": "cj", "id": "<pid>", "sections": {
        "product":    {"fetched_at": "...", "endpoint": "/product/query", "params": {...}, "payload": {...}},
        "freight:<vid>:IL": {"fetched_at": "...", ...}}}
Query results (search/list) go to data/sources/<source>/queries/<slug>.json in the same shape.

TTL (doc 2.2): product 30 days, freight 14 days, queries 7 days. A fresh section is read from the cache
with no supplier call.

CLI:
  python3 scripts/sourcing/cache.py show cj <pid>
  python3 scripts/sourcing/cache.py ls cj
"""
import datetime as dt, hashlib, json, os, re, sys, tempfile

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ROOT = os.path.join(REPO, "data", "sources")
TTL_DAYS = {"product": 30, "freight": 14, "query": 7, "image": 7}


def now():
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def _safe(s):
    return re.sub(r"[^A-Za-z0-9._-]+", "-", str(s)).strip("-")[:120] or "x"


def item_path(source, item_id):
    return os.path.join(ROOT, _safe(source), _safe(item_id) + ".json")


def query_path(source, kind, params):
    blob = json.dumps(params, sort_keys=True, ensure_ascii=False)
    slug = _safe("%s-%s" % (kind, "-".join(str(v) for v in params.values())))[:80]
    return os.path.join(ROOT, _safe(source), "queries",
                        "%s-%s.json" % (slug, hashlib.sha1(blob.encode()).hexdigest()[:8]))


def _read(p):
    if not os.path.exists(p):
        return None
    with open(p) as f:
        return json.load(f)


def _write(p, d):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(p), prefix=".tmp-")
    with os.fdopen(fd, "w") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
        f.write("\n")
    os.replace(tmp, p)


def fresh(section, kind):
    if not section:
        return False
    t = dt.datetime.fromisoformat(section["fetched_at"])
    return dt.datetime.now(dt.timezone.utc) - t < dt.timedelta(days=TTL_DAYS.get(kind, 7))


def get(source, item_id, section, kind=None, allow_stale=False):
    d = _read(item_path(source, item_id))
    s = (d or {}).get("sections", {}).get(section)
    if s and (allow_stale or fresh(s, kind or section.split(":")[0])):
        return s
    return None


def put(source, item_id, section, payload, endpoint=None, params=None):
    p = item_path(source, item_id)
    d = _read(p) or {"source": source, "id": str(item_id), "sections": {}}
    d["sections"][section] = {"fetched_at": now(), "endpoint": endpoint, "params": params or {}, "payload": payload}
    _write(p, d)
    return p


def get_query(source, kind, params):
    d = _read(query_path(source, kind, params))
    return d if d and fresh(d, "query") else None


def put_query(source, kind, params, payload, endpoint=None):
    p = query_path(source, kind, params)
    _write(p, {"source": source, "kind": kind, "fetched_at": now(), "endpoint": endpoint,
               "params": params, "payload": payload})
    return p


if __name__ == "__main__":
    a = sys.argv[1:]
    if len(a) == 3 and a[0] == "show":
        d = _read(item_path(a[1], a[2]))
        if d is None:
            sys.exit("not cached")
        for k, s in d["sections"].items():
            print("%-24s fetched %s  fresh=%s" % (k, s["fetched_at"], fresh(s, k.split(":")[0])))
    elif len(a) == 2 and a[0] == "ls":
        d = os.path.join(ROOT, _safe(a[1]))
        for f in sorted(os.listdir(d)) if os.path.isdir(d) else []:
            if f.endswith(".json"):
                print(f[:-5])
    else:
        sys.exit(__doc__)
