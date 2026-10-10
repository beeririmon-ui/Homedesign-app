#!/usr/bin/env python3
"""AliExpress Open Platform client (Dropshipping app) for the sourcing pipeline. Python 3 stdlib only.

Protocol ("IOP", the gateway shared with Lazada), verified 2026-10-10 against the official docs and the
official Java SDK source (the SDK zip linked from every API page; com.global.iop.util.IopUtils):
  * Endpoints (doc 1369 "API endpoint URLs"):
      business APIs  https://api-sg.aliexpress.com/sync?method={api_path}&{query}   (aliexpress.ds.* etc.)
      system APIs    https://api-sg.aliexpress.com/rest{api_path}?{query}           (/auth/token/create, /auth/token/refresh)
    https://openservice.aliexpress.com/doc/doc.htm#/?docId=1369
  * Signature (doc 1386/1367 "Signature algorithm", doc 1385/1366 "HTTP request sample"):
      1. take every request parameter (system + business) except "sign" and byte[] parameters; for a
         business API the "method" parameter takes part like any other parameter;
      2. sort by parameter name (ASCII), concatenate name+value with no separators; empty values are
         skipped (SDK IopUtils.areNotEmpty);
      3. system API only: prefix the api path (e.g. "/auth/token/create"); business API: no prefix
         (SDK TopExecutor signs with apiName "" and GopExecutor with the path);
      4. HMAC-SHA256 with the App Secret as key, over the UTF-8 string; 5. uppercase hex.
      sign_method = "sha256". Worked example with App Secret "helloworld" in doc 1385 (used in test_sign.py).
    https://openservice.aliexpress.com/doc/doc.htm#/?docId=1386   https://openservice.aliexpress.com/doc/doc.htm#/?docId=1385
  * System parameters (each API page, "common parameters"; SDK Constants): app_key, timestamp (ms since
    epoch, within 7200 s of UTC), sign_method, sign, access_token (business calls). The SDK's TOP executor
    also sends format=json, v=2.0, simplify=true, partner_id and names the token "session"; the HTTP doc
    sample names it "access_token". We send "access_token" (AE_DS_TOKEN_PARAM=session switches it).
  * Authorization (doc 1364 "Seller authorization introduction", doc 1590 "Authorize your APP"):
      https://api-sg.aliexpress.com/oauth/authorize?response_type=code&force_auth=true&redirect_uri=<callback>&client_id=<app_key>
      then POST /auth/token/create {code}, later POST /auth/token/refresh {refresh_token}.
      Test-status app: access_token 1 day, refresh_token 2 days; after "Apply Online": 30 / 60 days.
      Refresh is recommended 30 minutes before expiry; refresh_expires_in = 0 means it cannot be refreshed.
    https://openservice.aliexpress.com/doc/doc.htm#/?docId=1364   https://openservice.aliexpress.com/doc/doc.htm#/?docId=1590
  * Errors (doc 1372, SDK IopResponse): gateway errors come as {"type": SYSTEM|ISV|ISP, "code", "message"|"msg",
    "sub_code", "sub_msg", "request_id"}, sometimes under "error_response". Business payloads may be wrapped in
    {"<method with _>_response": {...}} and/or {"resp_result": {...}}; unwrap() handles both.
  * Flow control (doc 1790, FAQ): "Api access frequency exceeds the limit" -> sleep 1-2 s and retry.

Security (docs/studio-rules.md ch. 8): App Key and App Secret come only from the environment variables
AE_DS_APP_KEY and AE_DS_APP_SECRET. Tokens live only in ~/.cache/ae/token.json (chmod 600). Nothing here
prints a key, a secret, a token or a signature. Plain User-Agent, no scraping of aliexpress.com pages.
"""
import datetime as dt
import hashlib
import hmac
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

GATEWAY = "https://api-sg.aliexpress.com"
SYNC_URL = GATEWAY + "/sync"
REST_URL = GATEWAY + "/rest"
AUTHORIZE_URL = GATEWAY + "/oauth/authorize"
DEFAULT_CALLBACK = "https://127.0.0.1/callback"  # the callback registered on the app; AE_DS_CALLBACK_URL overrides
USER_AGENT = "homedesign-ae-client/1.0"
TOKEN_CACHE = os.path.expanduser("~/.cache/ae/token.json")
SIGN_METHOD = "sha256"
PARTNER_ID = "homedesign-ae-client-1.0"
MIN_INTERVAL = 0.5          # seconds between calls (polite; AE flow control is per app, not published for Test apps)
RETRIES_5XX = 3             # retries on HTTP 5xx / network errors, backoff 1, 2, 4 s
REFRESH_MARGIN = 30 * 60    # refresh the access token this many seconds before it expires (doc 1590)
TIMEOUT = 60

ENV_KEY, ENV_SECRET = "AE_DS_APP_KEY", "AE_DS_APP_SECRET"


class AeError(Exception):
    """Any failure. .code/.type/.message/.sub_code/.sub_msg/.request_id are set for gateway errors."""

    def __init__(self, message, code=None, type_=None, sub_code=None, sub_msg=None, request_id=None, http=None):
        super().__init__(message)
        self.message, self.code, self.type, self.sub_code, self.sub_msg, self.request_id, self.http = \
            message, code, type_, sub_code, sub_msg, request_id, http

    def __str__(self):
        parts = []
        if self.http: parts.append("HTTP %s" % self.http)
        if self.type: parts.append("type=%s" % self.type)
        if self.code: parts.append("code=%s" % self.code)
        parts.append("message=%s" % self.message)
        if self.sub_code: parts.append("sub_code=%s" % self.sub_code)
        if self.sub_msg: parts.append("sub_msg=%s" % self.sub_msg)
        if self.request_id: parts.append("request_id=%s" % self.request_id)
        return "AliExpress error: " + " | ".join(parts)


class AeConfigError(AeError):
    pass


class AeAuthRequired(AeError):
    pass


# ----------------------------------------------------------------------------- credentials

def app_key():
    v = os.environ.get(ENV_KEY)
    if not v:
        raise AeConfigError("חסר משתנה הסביבה %s. מגדירים אותו בהגדרות הסביבה של Claude (לא בצ'אט), ופותחים סשן חדש." % ENV_KEY)
    return v


def app_secret():
    v = os.environ.get(ENV_SECRET)
    if not v:
        raise AeConfigError("חסר משתנה הסביבה %s. מגדירים אותו בהגדרות הסביבה של Claude (לא בצ'אט), ופותחים סשן חדש." % ENV_SECRET)
    return v


def configured():
    return bool(os.environ.get(ENV_KEY)) and bool(os.environ.get(ENV_SECRET))


def callback_url():
    return os.environ.get("AE_DS_CALLBACK_URL") or DEFAULT_CALLBACK


def token_param_name():
    return os.environ.get("AE_DS_TOKEN_PARAM") or "access_token"


# ----------------------------------------------------------------------------- signing

def to_param_str(v):
    """Values as the gateway expects them: objects/arrays as compact JSON, booleans as true/false."""
    if v is None:
        return None
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (dict, list, tuple)):
        return json.dumps(v, ensure_ascii=False, separators=(",", ":"))
    return str(v)


def normalize_params(params):
    out = {}
    for k, v in (params or {}).items():
        s = to_param_str(v)
        if s is None or s == "":
            continue
        out[str(k)] = s
    return out


def sign(secret, api_path, params):
    """Official algorithm (doc 1386; SDK IopUtils.signApiRequest).

    api_path: "/auth/token/create" for a system API (prefixed), "" for a business API (no prefix).
    params: every parameter that will be sent, except "sign". Empty values are skipped, like the SDK does.
    Returns uppercase hex of HMAC-SHA256(secret, api_path + concat(sorted key+value)).
    """
    pieces = [api_path or ""]
    for k in sorted(params):
        v = params[k]
        if k == "sign" or v is None or v == "":
            continue
        pieces.append("%s%s" % (k, v))
    data = "".join(pieces).encode("utf-8")
    return hmac.new(secret.encode("utf-8"), data, hashlib.sha256).hexdigest().upper()


def timestamp_ms():
    return str(int(time.time() * 1000))


# ----------------------------------------------------------------------------- HTTP

_last_call = [0.0]


def _throttle():
    wait = MIN_INTERVAL - (time.monotonic() - _last_call[0])
    if wait > 0:
        time.sleep(wait)
    _last_call[0] = time.monotonic()


def _debug(msg):
    if os.environ.get("AE_DS_DEBUG"):
        print("[ae] " + msg, file=sys.stderr)


def _post(url, form):
    """POST application/x-www-form-urlencoded (doc 1385: every API accepts POST). Returns (status, text)."""
    body = urllib.parse.urlencode(form).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded;charset=utf-8")
    req.add_header("Accept", "application/json")
    req.add_header("User-Agent", USER_AGENT)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return resp.status, resp.read().decode("utf-8", "replace")


def _request(url, form, label):
    """Throttled POST with backoff on 5xx / network errors only. Never logs values, only parameter names."""
    delay = 1.0
    for attempt in range(RETRIES_5XX + 1):
        _throttle()
        _debug("%s params=%s attempt=%d" % (label, ",".join(sorted(form)), attempt + 1))
        try:
            status, text = _post(url, form)
        except urllib.error.HTTPError as e:
            text = e.read().decode("utf-8", "replace") if e.fp else ""
            if 500 <= e.code < 600 and attempt < RETRIES_5XX:
                _debug("HTTP %d, retry in %.0fs" % (e.code, delay)); time.sleep(delay); delay *= 2; continue
            raise AeError(_safe_excerpt(text) or e.reason, http=e.code)
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            if attempt < RETRIES_5XX:
                _debug("network error, retry in %.0fs" % delay); time.sleep(delay); delay *= 2; continue
            raise AeError("network error: %s" % getattr(e, "reason", e))
        try:
            return json.loads(text)
        except ValueError:
            raise AeError("non-JSON response (HTTP %s): %s" % (status, _safe_excerpt(text)), http=status)
    raise AeError("unreachable")  # pragma: no cover


def _safe_excerpt(text, n=300):
    return (text or "").replace("\n", " ").strip()[:n]


# ----------------------------------------------------------------------------- envelopes and errors

def gateway_error(d):
    """Return an AeError if d is a gateway-level error (SDK IopResponse fields), else None."""
    if not isinstance(d, dict):
        return None
    root = d.get("error_response") if isinstance(d.get("error_response"), dict) else d
    code = root.get("code")
    msg = root.get("message") or root.get("msg")
    if root is not d or (code is not None and "request_id" in root and (root.get("type") or msg) and str(code) not in ("0", "00", "200")):
        return AeError(msg or "error", code=code, type_=root.get("type"), sub_code=root.get("sub_code"),
                       sub_msg=root.get("sub_msg"), request_id=root.get("request_id"))
    return None


def unwrap(d):
    """Strip {"<x>_response": {...}} and {"resp_result": {...}} wrappers (the DS family is inconsistent)."""
    if isinstance(d, dict) and len(d) == 1:
        (k, v), = d.items()
        if k.endswith("_response") and isinstance(v, dict):
            d = v
    if isinstance(d, dict) and isinstance(d.get("resp_result"), dict):
        d = d["resp_result"]
    return d


def business_status(d):
    """-> (ok, code, message) from the business-level fields: rsp_code/rsp_msg, resp_code/resp_msg, code/msg,
    result.success / result.code / result.ret (doc pages of ds.product.get, ds.freight.query, ds.category.get)."""
    if not isinstance(d, dict):
        return False, None, "unexpected payload"
    for cf, mf in (("rsp_code", "rsp_msg"), ("resp_code", "resp_msg"), ("code", "msg")):
        if cf in d:
            c = d.get(cf)
            ok = c is None or str(c).strip() in ("", "0", "00", "200")
            return ok, c, d.get(mf) or d.get("message") or d.get("sub_msg")
    r = d.get("result")
    if isinstance(r, dict):
        if "success" in r:
            return bool(r["success"]), r.get("code"), r.get("msg") or r.get("error_desc") or r.get("messages")
        if "ret" in r:
            return bool(r["ret"]), r.get("code"), r.get("err_message") or r.get("messages")
        if "code" in r:
            return str(r["code"]) in ("0", "00", "200"), r.get("code"), r.get("msg")
    return True, None, None


def is_flow_control(err):
    s = ("%s %s" % (err.code or "", err.message or "")).lower()
    return ("frequency" in s) or ("limit" in s and "call" in s) or ("current limiting" in s) or ("throttl" in s)


# ----------------------------------------------------------------------------- calls

def system_call(path, params):
    """System API (GOP protocol): POST https://api-sg.aliexpress.com/rest{path}. No access token."""
    form = normalize_params(params)
    form.update({"app_key": app_key(), "timestamp": timestamp_ms(), "sign_method": SIGN_METHOD})
    form["sign"] = sign(app_secret(), path, form)
    d = _request(REST_URL + path, form, "system " + path)
    err = gateway_error(d)
    if err:
        raise err
    return d


def business_call(method, params, access_token=None, retry_flow_control=True):
    """Business API (TOP protocol): POST https://api-sg.aliexpress.com/sync?method=... Returns the unwrapped payload."""
    token = access_token if access_token is not None else get_access_token()
    form = normalize_params(params)
    form.update({"app_key": app_key(), "timestamp": timestamp_ms(), "sign_method": SIGN_METHOD, "method": method,
                 "format": "json", "v": "2.0", "simplify": "true", "partner_id": PARTNER_ID, token_param_name(): token})
    form["sign"] = sign(app_secret(), "", form)
    url = SYNC_URL + "?" + urllib.parse.urlencode({"method": method})
    d = _request(url, form, "business " + method)
    err = gateway_error(d)
    if err:
        if retry_flow_control and is_flow_control(err):
            _debug("flow control (%s); sleeping 2 s and retrying once" % err.code); time.sleep(2.0)
            return business_call(method, params, token, retry_flow_control=False)
        raise err
    return unwrap(d)


def call_ok(method, params, access_token=None):
    """business_call + business-level status check. Raises AeError with the full AE message on failure."""
    d = business_call(method, params, access_token)
    ok, code, msg = business_status(d)
    if not ok:
        raise AeError(msg or "business error", code=code, request_id=d.get("request_id") if isinstance(d, dict) else None)
    return d


# ----------------------------------------------------------------------------- tokens

def authorize_url(redirect_uri=None, key=None):
    """Doc 1364/1590: response_type=code&force_auth=true&redirect_uri=...&client_id=<app_key>."""
    q = [("response_type", "code"), ("force_auth", "true"), ("redirect_uri", redirect_uri or callback_url()),
         ("client_id", key or app_key())]
    return AUTHORIZE_URL + "?" + urllib.parse.urlencode(q)


def _now():
    return int(time.time())


def token_record(resp, previous=None):
    """Normalize a /auth/token/create or /refresh response into the cache record (never printed)."""
    now = _now()
    exp_in = int(resp.get("expires_in") or 0)
    rexp_in = int(resp.get("refresh_expires_in") or 0)
    expires_at = int(resp["expire_time"]) // 1000 if resp.get("expire_time") else now + exp_in
    refresh_at = int(resp["refresh_token_valid_time"]) // 1000 if resp.get("refresh_token_valid_time") else (now + rexp_in if rexp_in else 0)
    rec = {
        "access_token": resp.get("access_token"),
        "refresh_token": resp.get("refresh_token") or (previous or {}).get("refresh_token"),
        "expires_at": expires_at,
        "refresh_expires_at": refresh_at if (rexp_in or resp.get("refresh_token_valid_time")) else (previous or {}).get("refresh_expires_at", 0),
        "obtained_at": now,
        "account": {k: resp.get(k) for k in ("account", "account_id", "user_id", "seller_id", "account_platform", "sp", "locale")},
        "app_key_hint": (os.environ.get(ENV_KEY) or "")[-3:],  # last 3 chars only, to notice a key change
    }
    if not rec["access_token"]:
        raise AeError("token response without access_token", request_id=resp.get("request_id"))
    return rec


def save_token(rec):
    d = os.path.dirname(TOKEN_CACHE)
    os.makedirs(d, mode=0o700, exist_ok=True)
    tmp = TOKEN_CACHE + ".tmp"
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(rec, f)
    os.chmod(tmp, 0o600)
    os.replace(tmp, TOKEN_CACHE)
    os.chmod(TOKEN_CACHE, 0o600)


def load_token():
    if not os.path.exists(TOKEN_CACHE):
        return None
    with open(TOKEN_CACHE) as f:
        return json.load(f)


def delete_token():
    if os.path.exists(TOKEN_CACHE):
        os.remove(TOKEN_CACHE)


def exchange_code(code):
    """POST /rest/auth/token/create {code}. Stores the token; returns the (secret-free) status dict."""
    code = extract_code(code)
    resp = system_call("/auth/token/create", {"code": code})
    rec = token_record(resp)
    save_token(rec)
    return token_status(rec)


def refresh_token(rec=None):
    rec = rec or load_token()
    if not rec or not rec.get("refresh_token"):
        raise AeAuthRequired("אין refresh_token שמור. צריך הרשאה מחדש: python3 scripts/ae/auth.py url")
    if rec.get("refresh_expires_at") and rec["refresh_expires_at"] <= _now():
        raise AeAuthRequired("ה-refresh_token פג (%s). צריך הרשאה מחדש: python3 scripts/ae/auth.py url" % _fmt(rec["refresh_expires_at"]))
    resp = system_call("/auth/token/refresh", {"refresh_token": rec["refresh_token"]})
    new = token_record(resp, previous=rec)
    save_token(new)
    return token_status(new)


def get_access_token():
    """Valid access token from the cache, refreshing when it is within REFRESH_MARGIN of expiry."""
    rec = load_token()
    if not rec:
        raise AeAuthRequired("אין טוקן של AliExpress. הרשאה חד-פעמית: python3 scripts/ae/auth.py url  (ראו scripts/ae/README.md)")
    if rec.get("expires_at", 0) - REFRESH_MARGIN <= _now():
        refresh_token(rec)
        rec = load_token()
    return rec["access_token"]


def _fmt(ts):
    if not ts:
        return "?"
    return dt.datetime.fromtimestamp(int(ts), dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def mask(s):
    """'someone@example.com' -> 'so…ne@example.com'; '2637908814' -> '26…14'; short values -> '…'."""
    if not s:
        return "?"
    s = str(s)
    if "@" in s:
        local, _, domain = s.partition("@")
        return (local[:2] + "…" + local[-2:] if len(local) > 4 else "…") + "@" + domain
    return s[:2] + "…" + s[-2:] if len(s) > 4 else "…"


def token_status(rec=None):
    """Secret-free summary for the CLI."""
    rec = rec if rec is not None else load_token()
    if not rec:
        return {"exists": False}
    now = _now()
    acc = rec.get("account") or {}
    return {
        "exists": True,
        "valid": rec.get("expires_at", 0) > now,
        "expires": _fmt(rec.get("expires_at")),
        "expires_in_h": round((rec.get("expires_at", 0) - now) / 3600, 1),
        "refresh_expires": _fmt(rec.get("refresh_expires_at")),
        "refreshable": bool(rec.get("refresh_token")) and (rec.get("refresh_expires_at", 0) > now),
        "account": mask(acc.get("account") or acc.get("account_id") or acc.get("user_id")),
        "account_platform": acc.get("account_platform"),
        "obtained": _fmt(rec.get("obtained_at")),
        "file": TOKEN_CACHE,
    }


def extract_code(s):
    """Accept a bare code or the whole redirect URL (https://127.0.0.1/callback?code=...&...)."""
    s = (s or "").strip()
    if "code=" in s:
        q = urllib.parse.urlparse(s).query if "?" in s else s
        vals = urllib.parse.parse_qs(q).get("code")
        if vals:
            return vals[0]
    return s
