#!/bin/bash
# my browser checks in a row, against the copy's Worker on 8799
cd "$(dirname "$0")/.."
export PATH=/opt/node22/bin:$PATH QA_BASE=http://127.0.0.1:8799 QA_COPY=$PWD/build-s1112/site QA_REPO=$PWD/build-s1112 QA_OUT=/home/user/homedesign-app/qa/reports/2026-11-11-site-track-qa-s11-s12
for t in "$@"; do
  echo "=== $t $(date -u +%H:%M:%S)"
  case $t in
    switch) node s1112-tools/switch-mid.mjs ;;
    room) node s1112-tools/your-room.mjs ;;
    enc-file) node s1112-tools/encoding-qa.mjs file ;;
    enc-poster) node s1112-tools/encoding-qa.mjs poster ;;
    enc-engine) node s1112-tools/encoding-qa.mjs engine ;;
  esac
  echo "=== $t exit $? $(date -u +%H:%M:%S)"
done
