#!/usr/bin/env python3
"""Shared daily API budget per source. Lives in scratch, never in the repo:
    ~/.cache/sourcing/budget-<UTC date>.json      (CJ points reset at 00:00 UTC)

Every agent and every process charges the same file (flock), so parallel agents share one budget.

CJ points model (developers.cjdropshipping.com/en/api/api2/standard/points.html, checked 2026-10-09):
  50,000 points/day; listV2 (search) 50, product/query 10, freightCalculate 10, image search 1,000.
  Also 1,000 calls/day per endpoint. /product/list and /product/sourcing/* costs are not published:
  we charge them 50 (conservative) until CJ says otherwise. Sourcing requests: 5 per day (endpoint_caps).
Soft stop at 80% of the daily cap (doc 2.3), hard stop at 100%. Per-run caps on top (default
5,000 points and 150 calls per run; env SOURCING_RUN_MAX_POINTS / SOURCING_RUN_MAX_CALLS,
or --max-points / --max-calls in the source CLIs). A run is named by --run-id or SOURCING_RUN_ID.

CLI:
  python3 scripts/sourcing/budget.py status
  python3 scripts/sourcing/budget.py can cj product
  python3 scripts/sourcing/budget.py record cj 2870 "rounds 6-8 before the pipeline"   # usage made outside it
"""
import contextlib, datetime as dt, fcntl, json, os, sys

DIR = os.path.expanduser("~/.cache/sourcing")

SOURCES = {
    "cj": {
        "unit": "points", "daily_cap": 50000, "soft_ratio": 0.8, "endpoint_daily_calls": 1000,
        "cost": {"search": 50, "list": 50, "product": 10, "freight": 10, "image": 1000,
                 "variant": 10, "sourcing_create": 50, "sourcing_query": 50},
        # Verified 2026-10-10: the 6th POST /product/sourcing/create of the day is refused (code 1600000,
        # "Exceeded the daily source limit"), the same 5/day as the website's free tier.
        "endpoint_caps": {"sourcing_create": 5},
    },
    # AliExpress DS API (scripts/ae/ds.py): the per-app quota is not published for Test apps (it is shown in the
    # App Console, doc 1361 "API traffic control policy"); 5,000 calls/day is our own conservative cap until
    # the console value is copied here. Unit = calls, every endpoint costs 1.
    "aliexpress": {"unit": "calls", "daily_cap": 5000, "soft_ratio": 0.8, "endpoint_daily_calls": None,
                   "cost": {"search": 1, "image": 1, "product": 1, "freight": 1, "specialinfo": 1, "category": 1}},
    "google_vision": {"unit": "units", "daily_cap": 33, "soft_ratio": 0.8, "endpoint_daily_calls": None,
                      "cost": {"image": 1}},  # 1,000 free units/month ~ 33/day
}


class BudgetExceeded(Exception):
    pass


def today():
    return dt.datetime.now(dt.timezone.utc).date().isoformat()


def path(date=None):
    return os.path.join(DIR, "budget-%s.json" % (date or today()))


@contextlib.contextmanager
def _locked_state(date=None):
    os.makedirs(DIR, mode=0o700, exist_ok=True)
    p = path(date)
    with open(p + ".lock", "w") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        try:
            st = json.load(open(p)) if os.path.exists(p) else {"date": date or today(), "sources": {}}
            yield st
            tmp = p + ".tmp"
            with open(tmp, "w") as f:
                json.dump(st, f, indent=1, sort_keys=True)
            os.replace(tmp, p)
        finally:
            fcntl.flock(lk, fcntl.LOCK_UN)


def run_caps(max_points=None, max_calls=None):
    return (int(max_points or os.environ.get("SOURCING_RUN_MAX_POINTS", 5000)),
            int(max_calls or os.environ.get("SOURCING_RUN_MAX_CALLS", 150)))


def run_id(rid=None):
    return rid or os.environ.get("SOURCING_RUN_ID") or "default"


def _evaluate(st, source, endpoint, rid, max_points, max_calls):
    cfg = SOURCES[source]
    cost = cfg["cost"].get(endpoint)
    if cost is None:
        raise BudgetExceeded("unknown endpoint %s for %s" % (endpoint, source))
    s = st["sources"].setdefault(source, {"used": 0, "calls": {}, "runs": {}})
    r = s["runs"].setdefault(rid, {"used": 0, "calls": 0})
    rp, rc = run_caps(max_points, max_calls)
    cap, soft = cfg["daily_cap"], int(cfg["daily_cap"] * cfg["soft_ratio"])
    problems = []
    if s["used"] + cost > soft:
        problems.append("daily soft stop: %d + %d > %d (80%% of %d %s)" % (s["used"], cost, soft, cap, cfg["unit"]))
    epc = cfg.get("endpoint_caps", {}).get(endpoint) or cfg.get("endpoint_daily_calls")
    if epc and s["calls"].get(endpoint, 0) + 1 > epc:
        problems.append("endpoint cap: %s already %d calls today (max %d)" % (endpoint, s["calls"][endpoint], epc))
    if r["used"] + cost > rp:
        problems.append("run cap: run '%s' %d + %d > %d %s" % (rid, r["used"], cost, rp, cfg["unit"]))
    if r["calls"] + 1 > rc:
        problems.append("run cap: run '%s' already %d calls (max %d)" % (rid, r["calls"], rc))
    return cost, s, r, problems


def can(source, endpoint, rid=None, max_points=None, max_calls=None):
    """Read-only check. -> (ok, cost, problems, used_today)."""
    p = path()
    st = json.load(open(p)) if os.path.exists(p) else {"sources": {}}
    cost, s, r, problems = _evaluate(st, source, endpoint, run_id(rid), max_points, max_calls)
    return not problems, cost, problems, s["used"]


def charge(source, endpoint, rid=None, max_points=None, max_calls=None, n=1):
    """Reserve the cost BEFORE the call. Raises BudgetExceeded and charges nothing if over a cap."""
    rid = run_id(rid)
    with _locked_state() as st:
        total = 0
        for _ in range(n):
            cost, s, r, problems = _evaluate(st, source, endpoint, rid, max_points, max_calls)
            if problems:
                raise BudgetExceeded("; ".join(problems))
            s["used"] += cost; r["used"] += cost; r["calls"] += 1
            s["calls"][endpoint] = s["calls"].get(endpoint, 0) + 1
            total += cost
        return total, s["used"]


def record(source, amount, note=""):
    """Add usage that happened outside this pipeline (another tool, the CJ site), so the caps stay honest."""
    with _locked_state() as st:
        s = st["sources"].setdefault(source, {"used": 0, "calls": {}, "runs": {}})
        s["used"] += int(amount)
        s.setdefault("external", []).append({"amount": int(amount), "note": note})
        return s["used"]


def status(date=None):
    p = path(date)
    st = json.load(open(p)) if os.path.exists(p) else {"date": date or today(), "sources": {}}
    out = {"date": st.get("date"), "file": p, "sources": {}}
    for src, cfg in SOURCES.items():
        s = st["sources"].get(src, {"used": 0, "calls": {}, "runs": {}})
        out["sources"][src] = {"used": s["used"], "unit": cfg["unit"], "daily_cap": cfg["daily_cap"],
                               "soft_stop": int(cfg["daily_cap"] * cfg["soft_ratio"]),
                               "left_before_soft_stop": int(cfg["daily_cap"] * cfg["soft_ratio"]) - s["used"],
                               "calls": s["calls"], "runs": s["runs"]}
    return out


if __name__ == "__main__":
    a = sys.argv[1:] or ["status"]
    if a[0] == "status":
        json.dump(status(a[1] if len(a) > 1 else None), sys.stdout, indent=1); print()
    elif a[0] == "can" and len(a) >= 3:
        ok, cost, problems, used = can(a[1], a[2])
        print(json.dumps({"ok": ok, "cost": cost, "used_today": used, "problems": problems}, indent=1))
        sys.exit(0 if ok else 1)
    elif a[0] == "record" and len(a) >= 3:
        print(json.dumps({"used_today": record(a[1], a[2], " ".join(a[3:]))}))
    else:
        sys.exit(__doc__)
