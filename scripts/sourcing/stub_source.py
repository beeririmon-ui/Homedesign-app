#!/usr/bin/env python3
"""Shared stub for sources that are not connected yet. Same CLI shape as cj_source.py.

A stub only checks whether the needed environment variables exist (it never prints their values and never
asks for keys) and says "not configured". Keys are set by the user in the Claude environment settings
(doc: docs/suppliers/access-and-pipeline-2026-10.md, task list). When a source is wired, its module
replaces run_stub() with real calls through registry / budget / cache, exactly like cj_source.py.
"""
import argparse, os, sys

COMMANDS = ("search", "list", "image", "product", "freight", "source", "check", "mark")


def parser(name):
    ap = argparse.ArgumentParser(description="%s importer (stub)" % name)
    ap.add_argument("--dry-run", action="store_true"); ap.add_argument("--force", action="store_true")
    ap.add_argument("--by", default="sourcing-agent"); ap.add_argument("--run-id")
    ap.add_argument("--max-points", type=int); ap.add_argument("--max-calls", type=int)
    ap.add_argument("--hide-seen", action="store_true"); ap.add_argument("--raw", action="store_true")
    ap.add_argument("cmd", choices=COMMANDS); ap.add_argument("args", nargs=argparse.REMAINDER)
    return ap


def run_stub(name, env_vars, supported, doc_task):
    a = parser(name).parse_args()
    missing = [v for v in env_vars if not os.environ.get(v)]
    if a.cmd not in supported:
        sys.exit("%s: '%s' is not offered by this source." % (name, a.cmd))
    if missing:
        print("%s: not configured (missing env: %s). See %s. Nothing was called." % (name, ", ".join(missing), doc_task))
    else:
        print("%s: env vars are present, but the importer is not implemented yet. Nothing was called." % name)
    sys.exit(2)
