#!/usr/bin/env python3
"""AliExpress importer: thin shim over scripts/ae/ds.py (the real client, wired 2026-10-10).

Same CLI shape as cj_source.py: search / image / product / freight / check / mark (plus card, specialinfo,
category from ds.py). `image <path-or-url>` maps to `ds.py image-search`. Keys only from the environment
(AE_DS_APP_KEY, AE_DS_APP_SECRET); without them ds.py prints "not configured" and calls nothing.
Registry keys: "aliexpress:<item id>" with the aliexpress.com id (1005...); .us ids (3256...) are stored as aliases
when the API returns the converter result. Docs: scripts/ae/README.md.
"""
import os
import sys

DS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ae", "ds.py")

if __name__ == "__main__":
    argv = ["image-search" if x == "image" else x for x in sys.argv[1:]]
    os.execv(sys.executable, [sys.executable, "-I", os.path.abspath(DS)] + argv)
