#!/usr/bin/env python3
"""Google Cloud Vision (Web Detection) reverse image search: STUB. Same CLI shape; only `image` applies.

Needs GOOGLE_VISION_API_KEY (doc task 4). Budget: 1,000 free units per month (budget.py: ~33 per day).
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stub_source import run_stub  # noqa: E402

if __name__ == "__main__":
    run_stub("google_vision", ["GOOGLE_VISION_API_KEY"], supported=("image", "check"),
             doc_task="docs/suppliers/access-and-pipeline-2026-10.md, task 4")
