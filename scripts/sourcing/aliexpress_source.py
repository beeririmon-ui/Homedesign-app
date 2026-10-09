#!/usr/bin/env python3
"""AliExpress importer: STUB. Same CLI as cj_source.py (search / image / product / freight / check / mark).

Needs the AliExpress Open Platform Dropshipping app (doc task 2): AE_DS_APP_KEY, AE_DS_APP_SECRET.
The Affiliates app (task 3: AE_AFF_APP_KEY, AE_AFF_APP_SECRET, AE_AFF_TRACKING_ID) is optional, read-only.
Registry keys: "aliexpress:<item id>" with the aliexpress.com id (1005...); .us ids (3256...) map to it.
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stub_source import run_stub  # noqa: E402

if __name__ == "__main__":
    run_stub("aliexpress", ["AE_DS_APP_KEY", "AE_DS_APP_SECRET"],
             supported=("search", "image", "product", "freight", "check", "mark"),
             doc_task="docs/suppliers/access-and-pipeline-2026-10.md, tasks 2-3")
