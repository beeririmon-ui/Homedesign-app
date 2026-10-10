#!/usr/bin/env python3
"""One-time authorization of the AliExpress Dropshipping app with the user's own AliExpress buyer account.

Flow (doc 1364 "Seller authorization introduction", doc 1590 "Authorize your APP", both at
https://openservice.aliexpress.com/doc/doc.htm#/?docId=1364 and ...docId=1590):
  1. python3 scripts/ae/auth.py url        -> prints the authorize URL (client_id = AE_DS_APP_KEY, redirect_uri = the
                                              callback registered on the app, https://127.0.0.1/callback by default)
  2. open it in a browser, log in with the AliExpress buyer account, click "Access Now / Authorize"
  3. the browser is sent to https://127.0.0.1/callback?code=...  (the page does not load; copy the code from the
     address bar; the code expires within minutes)
  4. python3 scripts/ae/auth.py code <code or the whole redirect URL>   -> POST /rest/auth/token/create, token stored
     in ~/.cache/ae/token.json (chmod 600). Prints only: stored, expiry, masked account.
  5. python3 scripts/ae/auth.py status | refresh | forget

Run steps 1 and 4 in a session where AE_DS_APP_KEY / AE_DS_APP_SECRET exist (the desktop session), so the code never
goes through a chat. Nothing here prints a key, a secret or a token.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import client  # noqa: E402

USAGE = """שימוש:
  python3 scripts/ae/auth.py url            # כתובת ההרשאה לפתיחה בדפדפן
  python3 scripts/ae/auth.py code <code>    # החלפת ה-code בטוקן ושמירה ב-~/.cache/ae/token.json
  python3 scripts/ae/auth.py status         # האם יש טוקן תקף ומתי הוא פג
  python3 scripts/ae/auth.py refresh        # רענון הטוקן עכשיו
  python3 scripts/ae/auth.py forget         # מחיקת הטוקן השמור"""


def cmd_url():
    url = client.authorize_url()
    print(url)
    print()
    print("מה לעשות:")
    print("1. לפתוח את הכתובת למעלה בדפדפן ולהתחבר עם חשבון הקונה של AliExpress (לא חשבון מוכר).")
    print("2. ללחוץ על האישור (Access Now / Authorize).")
    print("3. הדפדפן יופנה אל %s?code=...  הדף לא ייטען, וזה בסדר: מעתיקים את הערך של code משורת הכתובת"
          " (אפשר להעתיק את כל הכתובת)." % client.callback_url())
    print("4. באותו טרמינל, תוך כמה דקות: python3 scripts/ae/auth.py code <code>")
    print("הערה: ה-code הוא חד-פעמי וקצר-חיים. לא מדביקים אותו בצ'אט.")
    return 0


def cmd_code(arg):
    if not arg:
        sys.exit("חסר ה-code. שימוש: python3 scripts/ae/auth.py code <code>")
    st = client.exchange_code(arg)
    print("stored, expires %s, account %s (%s)" % (st["expires"], st["account"], st.get("account_platform") or "?"))
    print("refresh_token בתוקף עד %s" % st["refresh_expires"])
    return 0


def cmd_status():
    st = client.token_status()
    if not st["exists"]:
        print("אין טוקן שמור (%s). הרשאה: python3 scripts/ae/auth.py url" % client.TOKEN_CACHE)
        return 1
    print("token: %s | expires %s (%s h) | refreshable until %s: %s | account %s (%s) | obtained %s" % (
        "valid" if st["valid"] else "EXPIRED", st["expires"], st["expires_in_h"], st["refresh_expires"],
        "yes" if st["refreshable"] else "no", st["account"], st.get("account_platform") or "?", st["obtained"]))
    if not st["valid"] and not st["refreshable"]:
        print("צריך הרשאה מחדש: python3 scripts/ae/auth.py url")
        return 1
    return 0


def cmd_refresh():
    st = client.refresh_token()
    print("refreshed, expires %s, account %s" % (st["expires"], st["account"]))
    return 0


def cmd_forget():
    client.delete_token()
    print("deleted %s (if it existed)" % client.TOKEN_CACHE)
    return 0


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(USAGE)
        return 0
    cmd, rest = argv[0], argv[1:]
    try:
        if cmd == "url":
            return cmd_url()
        if cmd == "code":
            return cmd_code(" ".join(rest))
        if cmd == "status":
            return cmd_status()
        if cmd == "refresh":
            return cmd_refresh()
        if cmd == "forget":
            return cmd_forget()
        print(USAGE)
        return 2
    except client.AeConfigError as e:
        print("לא מוגדר: %s" % e.message, file=sys.stderr)
        return 2
    except client.AeAuthRequired as e:
        print(e.message, file=sys.stderr)
        return 1
    except client.AeError as e:
        print(str(e), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
