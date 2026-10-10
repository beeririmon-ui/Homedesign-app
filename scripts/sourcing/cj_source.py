#!/usr/bin/env python3
"""CJ importer for the "do-once" pipeline. Wraps scripts/cj.py and adds the registry, the shared budget and
the raw cache. Every sourcing agent calls CJ through this script, never through cj.py directly.

Same CLI shape for every source (see aliexpress_source.py, google_vision_source.py):
  search  "<q>" [--page N] [--size N]                 # CJ listV2 (50 points). Hits are annotated with registry status
  list    "<word>" [--category ID] [--page N] [--size N]   # CJ /product/list (charged 50; cost not published)
  image   <image_url>                                  # not wired yet: 1,000 points and account level 3+
  product <pid> [<pid> ...] [--slot room/slot]         # 10 points each; SKIPS anything already seen
  freight <vid> [--to IL] [--qty 1]                    # 10 points; cached 14 days
  source  <image_url> --name "<n>" --approved "<decision>" [--slot room/slot] [--url U] [--price P] [--remark R]
          # CJ Sourcing request (charged 50). Sent only with --approved <decision id> (studio rules d.9, e.g. "AC1 2026-10-10").
          # The id comes back as cjSourcingId; it is registered as cj-sourcing:<id> and cached under data/sources/cj-sourcing/
  source-status <cjSourcingId> [...]                  # GET /product/sourcing/queryList (charged 50; up to 100 ids): 3 = succeeded, 5 = failed
  source-batch <file.json> --approved "<decision>" [--count 5]
          # sends the entries with status "pending" from a record file such as data/leads/cj/sourcing-requests-<date>.json
          # (fields slot, productName, productImage, remark, productUrl?, price?) and writes cjSourcingId/status back into it.
          # CJ allows 5 sourcing requests per day: the batch stops at the limit (code 1600000) and the rest stay "pending".
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


SRC_SOURCING = "cj-sourcing"
MAXLEN = 200  # CJ: productName, productImage, productUrl, remark are each <= 200 chars


def do_source(a):
    if not a.approved:
        sys.exit("CJ Sourcing requests need the user's approval first (studio rules d.9). "
                 "Pass --approved \"<decision id>\" (e.g. \"AC1 2026-10-10\"). Not sent.")
    for field in ("name", "image", "url", "remark"):
        v = getattr(a, field)
        if v and len(v) > MAXLEN:
            sys.exit("%s is %d chars; CJ allows %d. Not sent." % (field, len(v), MAXLEN))
    body = {"productName": a.name, "productImage": a.image, "productUrl": a.url, "price": a.price, "remark": a.remark}
    if a.dry_run:
        return out({"dry_run": True, "would_call": "sourcing_create", "slot": a.slot, "request": body,
                    "budget": spend(a, "sourcing_create")})
    out(_send_one(a, dict(body, slot=a.slot)))


LIMIT_WORDS = ("daily source limit", "exceeded", "limit", "quota")


def _send_one(a, req):
    """Shared by `source` and `source-batch`: charge, call, cache, register. Returns the response dict."""
    spend(a, "sourcing_create")
    r = cj().sourcing_create(req["productName"], req["productImage"], req.get("productUrl"), req.get("price"), req.get("remark"))
    res = dict(r, slot=req.get("slot"), approved=a.approved, request=req)
    sid = r.get("cjSourcingId")
    if r.get("ok") and sid:
        cache.put(SRC_SOURCING, sid, "create", res, endpoint="/product/sourcing/create", params={"slot": req.get("slot")})
        registry.add("%s:%s" % (SRC_SOURCING, sid), "seen",
                     "CJ sourcing request (%s) for %s: %s" % (a.approved, req.get("slot") or "?", req["productName"][:110]),
                     by=a.by, slot=req.get("slot"), opened=True, source=SRC_SOURCING, url=req.get("productUrl"))
    return res


def do_source_batch(a):
    import datetime as dt, time
    if not a.approved:
        sys.exit("CJ Sourcing requests need the user's approval first (studio rules d.9). Pass --approved. Not sent.")
    with open(a.file) as f:
        log = json.load(f)
    pending = [r for r in log.get("requests") or [] if r.get("status") == "pending"]
    if a.dry_run:
        return out({"dry_run": True, "pending": len(pending), "would_send": [r["slot"] for r in pending[:a.count]],
                    "budget": spend(a, "sourcing_create")})
    sent, stopped = 0, None
    for req in pending[:a.count]:
        for k in ("productName", "productImage", "remark", "productUrl"):
            if req.get(k) and len(req[k]) > MAXLEN:
                sys.exit("%s: %s is %d chars (max %d). Not sent." % (req["slot"], k, len(req[k]), MAXLEN))
        try:
            res = _send_one(a, req)
        except budget.BudgetExceeded as e:
            stopped = "budget: %s" % e; break
        now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
        req.update({"cjSourcingId": res.get("cjSourcingId"), "api_code": res.get("code"), "api_message": res.get("message"),
                    "requestId": res.get("requestId")})
        if res.get("ok") and res.get("cjSourcingId"):
            req["status"], req["created_at"] = "created", now; sent += 1
        else:
            msg = (res.get("message") or "").lower()
            if any(w in msg for w in LIMIT_WORDS):
                req["status"] = "pending"  # stays queued for tomorrow
                log.setdefault("limit_events", []).append({"at": now, "slot": req["slot"], "code": res.get("code"), "message": res.get("message")})
                stopped = "limit: %s" % res.get("message"); break
            req["status"], req["failed_at"] = "failed", now
            log.setdefault("failures", []).append({"at": now, "slot": req["slot"], "code": res.get("code"), "message": res.get("message")})
            stopped = "failed: %s" % res.get("message"); break
        print("[batch] created %s -> %s" % (req["slot"], req["cjSourcingId"]), file=sys.stderr)
        time.sleep(1.5)
    reqs = log.get("requests") or []
    log["summary"] = {"planned": len(reqs), "created": sum(r.get("status") == "created" for r in reqs),
                      "pending": sum(r.get("status") == "pending" for r in reqs), "failed": sum(r.get("status") == "failed" for r in reqs),
                      "cjSourcingIds": [r["cjSourcingId"] for r in reqs if r.get("status") == "created"],
                      "last_run": {"at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(), "sent": sent, "stopped": stopped}}
    with open(a.file, "w") as f:
        json.dump(log, f, ensure_ascii=False, indent=1); f.write("\n")
    out({"sent": sent, "stopped": stopped, "summary": log["summary"]})


def do_source_status(a):
    if a.dry_run:
        return out({"dry_run": True, "would_call": "sourcing_query", "ids": a.ids, "budget": spend(a, "sourcing_query")})
    spend(a, "sourcing_query")
    r = cj().sourcing_query(a.ids)
    for it in r.get("items") or []:
        sid = it.get("sourceId")
        if sid:
            cache.put(SRC_SOURCING, sid, "status", it, endpoint="/product/sourcing/queryList")
            note = "status %s (%s)%s" % (it.get("sourceStatus"), it.get("sourceStatusStr"),
                                         " cj:%s" % it["cjProductId"] if it.get("cjProductId") else "")
            registry.add("%s:%s" % (SRC_SOURCING, sid), "seen", note, by=a.by, opened=True, source=SRC_SOURCING)
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
    so.add_argument("--price"); so.add_argument("--remark"); so.add_argument("--slot"); so.add_argument("--approved")
    ss = sub.add_parser("source-status"); ss.add_argument("ids", nargs="+")
    sb = sub.add_parser("source-batch"); sb.add_argument("file"); sb.add_argument("--approved"); sb.add_argument("--count", type=int, default=5)
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
            do_source(a)
        elif a.cmd == "source-status":
            do_source_status(a)
        elif a.cmd == "source-batch":
            do_source_batch(a)
    except budget.BudgetExceeded as e:
        print("BUDGET STOP: %s" % e, file=sys.stderr)
        sys.exit(3)


if __name__ == "__main__":
    main()
