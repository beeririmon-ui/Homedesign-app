#!/usr/bin/env python3
"""Astra: a second-opinion agent on the OpenAI API.

The key is read from the OPENAI_API_KEY environment variable (set it in the cloud
environment settings). Never put keys in the repo or in chat.

Usage:
  python3 scripts/astra.py models                       # list models this key can use
  python3 scripts/astra.py ask --model <id> --brief <file.md> [--file <path> ...] [--image <path> ...] --out <file.md>

--brief  : the task (markdown). Write it like any agent brief: task, inputs, expected output, acceptance criteria.
--file   : text files whose content is appended as context (e.g. the Design Bible).
--image  : local images (jpg/png/webp) sent to the model for visual review.
--out    : where the answer is written (inside the repo, e.g. briefs/astra/<name>.md).
The model can also be set with OPENAI_MODEL.
"""
import argparse, base64, json, mimetypes, os, sys, urllib.request

API = "https://api.openai.com/v1"


def call(method, path, body=None):
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        sys.exit("OPENAI_API_KEY is not set in this environment.")
    req = urllib.request.Request(API + path, method=method,
                                 data=json.dumps(body).encode() if body is not None else None)
    req.add_header("Authorization", "Bearer " + key)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit("OpenAI API error %s: %s" % (e.code, e.read().decode()[:500]))


def ask(model, brief, files, images, out):
    text = open(brief, encoding="utf-8").read()
    for f in files:
        text += "\n\n--- %s ---\n%s" % (f, open(f, encoding="utf-8").read())
    content = [{"type": "input_text", "text": text}]
    for p in images:
        mime = mimetypes.guess_type(p)[0] or "image/jpeg"
        b64 = base64.b64encode(open(p, "rb").read()).decode()
        content.append({"type": "input_image", "image_url": "data:%s;base64,%s" % (mime, b64)})
    d = call("POST", "/responses", {"model": model, "input": [{"role": "user", "content": content}]})
    answer = d.get("output_text") or "".join(
        c.get("text", "") for o in d.get("output", []) for c in (o.get("content") or []) if c.get("type") == "output_text")
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("<!-- Astra (%s) · brief: %s -->\n\n%s\n" % (model, brief, answer))
    print("written:", out, "| tokens:", (d.get("usage") or {}).get("total_tokens"))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("models")
    a = sub.add_parser("ask")
    a.add_argument("--model", default=os.environ.get("OPENAI_MODEL"))
    a.add_argument("--brief", required=True)
    a.add_argument("--file", action="append", default=[])
    a.add_argument("--image", action="append", default=[])
    a.add_argument("--out", required=True)
    args = ap.parse_args()
    if args.cmd == "models":
        print("\n".join(sorted(m["id"] for m in call("GET", "/models").get("data", []))))
    else:
        if not args.model:
            sys.exit("Pick a model: --model <id> or OPENAI_MODEL (see: astra.py models).")
        ask(args.model, args.brief, args.file, args.image, args.out)
