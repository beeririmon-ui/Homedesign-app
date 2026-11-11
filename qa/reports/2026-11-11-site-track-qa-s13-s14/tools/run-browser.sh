#!/bin/bash
# my checks in a row, against the copy's Worker on 8799 (S13–S14 round)
cd "$(dirname "$0")/.."
export PATH=/opt/node22/bin:$PATH QA_BASE=http://127.0.0.1:8799 QA_COPY=$PWD/build-s1314/site QA_REPO=$PWD/build-s1314 QA_OUT=/home/user/homedesign-app/qa/reports/2026-11-11-site-track-qa-s13-s14
export QA_SRVLOG=$PWD/s1314-logs/srv-8799.log QA_TOKEN=qa-dummy-admin-token-not-a-key-0123456789 QA_D1_EXEC=$PWD/s1314-tools/d1-exec.sh QA_DE_ALL=1
for t in "$@"; do
  echo "=== $t $(date -u +%H:%M:%S)"
  case $t in
    ops) node s1314-tools/ops-live.mjs ;;
    screens) node s1314-tools/ops-screens.mjs ;;
    room) node s1314-tools/your-room.mjs ;;
    paint) node s1314-tools/first-paint.mjs ;;
    enc-poster) QA_RESFILE=data/encoding-qa.json node s1314-tools/encoding-qa.mjs poster ;;
    enc-fallback) QA_RESFILE=data/encoding-qa.json node s1314-tools/encoding-qa.mjs fallback ;;
    enc-handoff) QA_RESFILE=data/encoding-qa.json node s1314-tools/encoding-qa.mjs handoff ;;
  esac
  echo "=== $t exit $? $(date -u +%H:%M:%S)"
done
