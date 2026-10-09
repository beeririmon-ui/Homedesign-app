#!/usr/bin/env python3
"""CJ importer for the "do-once" pipeline. Wraps scripts/cj.py and adds the registry, the shared budget and
the raw cache. Every sourcing agent calls CJ through this script, never through cj.py directly.

Same CLI shape for every source (see aliexpress_source.py, google_vision_source.py):
  search  "<q>" [--page N] [--size N]                 # CJ listV2 (50 points). Hits are annotated with registry status
  list    "<word>" [--category ID] [--page N] [--size N]   # CJ /product/list (charged 50; cost not published)
  image   <image_url>                                  # not wired yet: 1,000 points and account level 3+
  product <pid> [<pid> ...] [--slot room/slot]         # 10 points each; SKIPS anything already seen
  freight <vid> [--to IL] [--qty 1]                    # 10 points; cached 14 days
  source  <image_url> --name "<n>" [--url U]           # CJ Sourcing request: needs the user's OK (doc task 1)
  check   <pid|vid|sku> [...]                          # registry only, no call
  mark    <pid> --status rejected|seen|card --reason "..." [--slot room/slot] [--card-id ID]

Global flags (before the command):
  --dry-run     no network, no writes: prints what would be skipped / read from cache / called, and the cost
  --force       open even if the registry says skip (say why in the round summary)
  --by NAME     who is working (default: sourcing-agent); stored in the registry
  --run-id ID   names the run for per-run caps (or env SOURCING_RUN_ID)
  --max-points N / --max-calls N   per-run caps (defaults 5,000 points / 150 calls)
  --hide-seen   drop search hits that the registry says to skip
  --raw         print the stored payload as-is
Exit code 3 = budget stop.

The token is handled only inside scripts/cj.py (~/.cache/cj/token.json); this script never reads it.
"""
import argparse, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))  # scripts/ -> cj.py
import budget, cache, registry  # noqa: E402

SRC = "cj"
_cj = None


def cj():
    global _cj
    if _cj is None:
        import cj as m  # scripts/cj.py; imported lazily so --dry-run never touches it
        _cj = m
    return _cj


def out(o):
    json.dump(o, sys.stdout, ensure_ascii=False, indent=1)
    print()


def spend(a, endpoint):
    """Check (dry run) or charge the budget. Returns a dict for the log, raises BudgetExceeded on a stop."""
    if a.dry_run:
        ok, cost, problems, used = budget.can(SRC, endpoint, a.run_id, a.max_points, a.max_calls)
        return {"would_cost": cost, "used_today": used, "ok": ok, "problems": problems}
    cost, used = budget.charge(SRC, endpoint, a.run_id, a.max_points, a.max_calls)
    print("[budget] %s %s: -%d points, %d used today" % (SRC, endpoint, cost, used), file=sys.stderr)
    return {"cost": cost, "used_today": used}


def annotate(products, reg, hide):
    res = []
    for p in products:
        pid = p.get("id")
        c = registry.check(pid, reg) if pid else {"action": "open", "why": ""}
        if hide and c["action"] == "skip":
            continue
        p = dict(p, registry=c["action"], registry_why=c["why"])
        res.append(p)
    return res


def do_query(a, kind):
    params = {"q": a.q, "page": a.page, "size": a.size}
    if kind == "list":
        params["category"] = a.category
    hit = cache.get_query(SRC, kind, params)
    reg = registry.load()
    if hit:
        res = dict(hit["payload"], cached_at=hit["fetched_at"])
    elif a.dry_run:
        return out({"dry_run": True, "would_call": kind, "params": params, "budget": spend(a, kind)})
    else:
        spend(a, kind)
        res = cj().search(a.q, a.page, a.size) if kind == "search" else cj().listing(a.q, a.page, a.size, a.category)
        cache.put_query(SRC, kind, params, res, endpoint="/product/listV2" if kind == "search" else "/product/list")
    if a.raw:
        return out(res)
    prods = annotate(res.get("products") or [], reg, a.hide_seen)
    out(dict(res, products=prods, skipped_by_registry=len(res.get("products") or []) - len(prods)))


def do_product(a):
    reg = registry.load()
    results = []
    for pid in a.pids:
        c = registry.check(pid, reg, a.force)
        key = c["key"]
        native = key.split(":", 1)[1]
        if c["action"] == "skip":
            stale = cache.get(SRC, native, "product", allow_stale=True)
            results.append({"pid": native, "action": "SKIP", "why": c["why"],
                            "cached": bool(stale), "cached_at": stale and stale["fetched_at"]})
            continue
        hit = cache.get(SRC, native, "product")
        if hit:
            results.append({"pid": native, "action": "CACHE", "why": c["why"], "cached_at": hit["fetched_at"],
                            "payload": None if a.dry_run else hit["payload"]})
            continue
        if a.dry_run:
            results.append({"pid": native, "action": "WOULD_CALL", "why": c["why"], "budget": spend(a, "product")})
            continue
        spend(a, "product")
        p = cj().product(native)
        cache.put(SRC, native, "product", p, endpoint="/product/query", params={"pid": native})
        vids = [v.get("vid") for v in p.get("variants") or []]
        registry.add(key, "seen", "opened via cj_source: %s" % (p.get("productNameEn") or "")[:120], by=a.by,
                     slot=a.slot, opened=True, vids=vids, skus=[p.get("productSku")], url=p.get("url"))
        results.append({"pid": native, "action": "CALLED", "why": c["why"], "payload": p})
    if a.dry_run:
        out({"dry_run": True, "results": results,
             "summary": {k: sum(r["action"] == k for r in results) for k in ("SKIP", "CACHE", "WOULD_CALL")}})
    else:
        out(results if len(results) > 1 else results[0])


def do_freight(a):
    reg = registry.load()
    key, entry = registry.resolve(reg, "%s:vid:%s" % (SRC, a.vid))
    owner = key.split(":", 1)[1] if entry else "vid-%s" % a.vid
    section = "freight:%s:%s:%d" % (a.vid, a.to, a.qty)
    hit = cache.get(SRC, owner, section, kind="freight")
    if hit:
        return out(dict(hit["payload"], cached_at=hit["fetched_at"], registry=entry and entry["status"]))
    if a.dry_run:
        return out({"dry_run": True, "would_call": "freight", "vid": a.vid, "pid": entry and key,
                    "registry": entry and entry["status"], "budget": spend(a, "freight")})
    spend(a, "freight")
    r = cj().freight(a.vid, a.to, a.qty)
    cache.put(SRC, owner, section, r, endpoint="/logistic/freightCalculate",
              params={"vid": a.vid, "to": a.to, "qty": a.qty})
    if entry:
        registry.add(key, "seen", None, by=a.by, opened=True)  # bumps last_seen only
    out(r)


def main(argv=None):
    ap = argparse.ArgumentParser(description="CJ importer (registry + budget + cache)")
    ap.add_argument("--dry-run", action="store_true"); ap.add_argument("--force", action="store_true")
    ap.add_argument("--by", default="sourcing-agent"); ap.add_argument("--run-id")
    ap.add_argument("--max-points", type=int); ap.add_argument("--max-calls", type=int)
    ap.add_argument("--hide-seen", action="store_true"); ap.add_argument("--raw", action="store_true")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search"); s.add_argument("q"); s.add_argument("--page", type=int, default=1); s.add_argument("--size", type=int, default=20)
    l = sub.add_parser("list"); l.add_argument("q", nargs="?", default=""); l.add_argument("--category"); l.add_argument("--page", type=int, default=1); l.add_argument("--size", type=int, default=50)
    i = sub.add_parser("image"); i.add_argument("image")
    p = sub.add_parser("product"); p.add_argument("pids", nargs="+"); p.add_argument("--slot")
    f = sub.add_parser("freight"); f.add_argument("vid"); f.add_argument("--to", default="IL"); f.add_argument("--qty", type=int, default=1)
    so = sub.add_parser("source"); so.add_argument("image"); so.add_argument("--name", required=True); so.add_argument("--url")
    c = sub.add_parser("check"); c.add_argument("ids", nargs="+")
    m = sub.add_parser("mark"); m.add_argument("pid"); m.add_argument("--status", required=True, choices=registry.STATUSES)
    m.add_argument("--reason", required=True); m.add_argument("--slot"); m.add_argument("--card-id")
    a = ap.parse_args(argv)
    try:
        if a.cmd in ("search", "list"):
            do_query(a, a.cmd)
        elif a.cmd == "product":
            do_product(a)
        elif a.cmd == "freight":
            do_freight(a)
        elif a.cmd == "check":
            reg = registry.load()
            out([{k: v for k, v in registry.check(x, reg, a.force).items() if k != "entry"} for x in a.ids])
        elif a.cmd == "mark":
            if a.dry_run:
                return out({"dry_run": True, "would_mark": a.pid, "status": a.status})
            out(registry.add(a.pid, a.status, a.reason, by=a.by, slot=a.slot, card_id=a.card_id, opened=True))
        elif a.cmd == "image":
            sys.exit("image search is not wired: it costs 1,000 points and needs CJ account level 3+ "
                     "(doc 1.1). Ask the coordinator before adding it.")
        elif a.cmd == "source":
            sys.exit("CJ Sourcing requests need the user's approval first (doc task 1). Not sent.")
    except budget.BudgetExceeded as e:
        print("BUDGET STOP: %s" % e, file=sys.stderr)
        sys.exit(3)


if __name__ == "__main__":
    main()
