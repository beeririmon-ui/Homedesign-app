#!/bin/bash
# QA S23: my existing tools (S21, S22) against the flag build on 127.0.0.1:8850, one after the other (no two browsers at once).
source "$(dirname "$0")/noNet.sh"
QA=$(cd "$(dirname "$0")/.." && pwd)
export QA_COPY=$QA/build-s23/site
B=http://127.0.0.1:8850
T=$QA/tools
st() { echo "=== $1 $(date -u +%H:%M:%S)"; }
st cart-flash; node $T/cart-flash.mjs $B $QA/data/cart-flash-s23qa.json "" $QA/screens > $QA/data/cart-flash-s23qa.log 2>&1; echo "exit $?"
st bfcache; node $T/bfcache.mjs $B $QA/data/bfcache-s23qa.json > $QA/data/bfcache-s23qa.log 2>&1; echo "exit $?"
for m in refused kept; do
  st history-$m; rm -rf $QA/tmp/profile-$m; node $T/history-db.mjs $B $QA/tmp/profile-$m $m > $QA/data/history-db-$m.log 2>&1; echo "exit $?"
  python3 -I $T/read-history.py $QA/tmp/profile-$m $QA/tmp/history-$m.sqlite >> $QA/data/history-db-$m.log 2>&1
done
st wname; node $T/wname-s23qa.mjs $B $QA/data/wname-s23qa.json > $QA/data/wname-s23qa.log 2>&1; echo "exit $?"
st h30; node $T/h30-s23qa.mjs $B $QA/data/h30-s23qa.json $QA/screens > $QA/data/h30-s23qa.log 2>&1; echo "exit $?"
cd $QA_COPY
for v in desktop phone; do
  st early-$v; node node_modules/tsx/dist/cli.mjs $T/options-early-click-s22qa.mts --base=$B --site=$QA_COPY --runs=20 --out=$QA/data/options-early-click-$v.json --view=$v > $QA/data/options-early-click-$v.log 2>&1; echo "exit $?"
done
st done
