#!/bin/bash
# QA S18, question 4: the EMAIL_PROVIDER gate. Each case is a temp copy of api/wrangler.jsonc (3013d630) with one value
# changed; check-config (the deploy check, runs before every API build) and build-copy (the copy build, first in
# prepare:data; HD_PUBLIC=1 reads production) run on it. The tree is never touched.
source "$(dirname "$0")/noNet.sh"
QA=$(cd "$(dirname "$0")/.." && pwd)
cd "$QA/build-s18/site"
T=$(mktemp -d "$QA/tmp-gate-XXXX"); trap 'rm -rf "$T"' EXIT
TSX="node $PWD/node_modules/tsx/dist/cli.mjs"
W=$PWD/api/wrangler.jsonc
mk() { # mk <name> <section: top|preview|production> <sed expression on the EMAIL_PROVIDER line of that section>
  local f="$T/$1.jsonc"
  case $2 in
    top) node -e 'const fs=require("fs");const [w,o,e]=process.argv.slice(1);const s=fs.readFileSync(w,"utf8");const i=s.indexOf("\"EMAIL_PROVIDER\"");fs.writeFileSync(o,s.slice(0,i)+eval(e)(s.slice(i,s.indexOf("\n",i)))+s.slice(s.indexOf("\n",i)))' $W "$f" "$3";;
    preview|production) node -e 'const fs=require("fs");const [w,o,sec,e]=process.argv.slice(1);const s=fs.readFileSync(w,"utf8");const j=s.indexOf("\""+sec+"\": {");const i=s.indexOf("\"EMAIL_PROVIDER\"",j);fs.writeFileSync(o,s.slice(0,i)+eval(e)(s.slice(i,s.indexOf("\n",i)))+s.slice(s.indexOf("\n",i)))' $W "$f" "$2" "$3";;
  esac
  echo "$f"
}
row() { # row <case> <file> <public 0|1>
  local cc bc
  (cd api && $TSX scripts/check-config.ts "$2") > "$T/cc.out" 2>&1; cc=$?
  HD_PUBLIC=$3 $TSX tools/build-copy.ts --wrangler="$2" --out="$T/never.json" > "$T/bc.out" 2>&1; bc=$?
  printf '%-34s check-config exit %s | build-copy(HD_PUBLIC=%s) exit %s | %s\n' "$1" "$cc" "$3" "$bc" "$(grep -h -m1 -E 'EMAIL_PROVIDER|refused|not set|not a provider|no vars|customer email' "$T/cc.out" "$T/bc.out" | sed 's/^ *//' | cut -c1-150)"
}
echo "EMAIL_PROVIDER gate, $(date -u +%FT%TZ), commit 3013d630"
row "G0 as committed (UNDECIDED)" $W 1
row "G0b as committed, flag build" $W 0
row "G1 production mock" "$(mk g1 production 's=>s.replace(/"UNDECIDED"/,"\"mock\"")')" 1
row "G2 production Resend (not built)" "$(mk g2 production 's=>s.replace(/"UNDECIDED"/,"\"resend\"")')" 1
row "G3 production missing (line out)" "$(mk g3 production 's=>"// removed"')" 1
row "G4 production empty string" "$(mk g4 production 's=>s.replace(/"UNDECIDED"/,"\"\"")')" 1
row "G5 production lowercase undecided" "$(mk g5 production 's=>s.replace(/"UNDECIDED"/,"\"undecided\"")')" 1
row "G6 production ' UNDECIDED'" "$(mk g6 production 's=>s.replace(/"UNDECIDED"/,"\" UNDECIDED\"")')" 1
row "G7 production null" "$(mk g7 production 's=>s.replace(/"UNDECIDED"/,"null")')" 1
row "G8 production true" "$(mk g8 production 's=>s.replace(/"UNDECIDED"/,"true")')" 1
row "G9 production MOCK" "$(mk g9 production 's=>s.replace(/"UNDECIDED"/,"\"MOCK\"")')" 1
row "G10 top level mock, flag build" "$(mk g10 top 's=>s.replace(/"UNDECIDED"/,"\"mock\"")')" 0
row "G11 preview mock" "$(mk g11 preview 's=>s.replace(/"UNDECIDED"/,"\"mock\"")')" 0
row "G12 top level missing, flag build" "$(mk g12 top 's=>"// removed"')" 0
