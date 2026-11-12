#!/bin/bash
# S20 (frontend-dev): QA S18's source mutations SM1–SM6 (qa/reports/2026-11-12-site-track-qa-s18/tools/setup-srcmut.sh),
# written in the source the way a developer or the designer would, built by the real build (build-copy, vite, esbuild,
# prerender) in an isolated copy of site/, then the S20 gate. QA S18: the gate stopped only on SM3.
# The copy: the sources copied, node_modules and the media hard-linked (only read by the build). The live tree is not touched.
# Usage: SITE=<live site> QA_TOOLS=<qa s18 tools> MUT_TMP=<scratch> OUT=<data dir> bash srcmut.sh
set -o pipefail
source "${QA_TOOLS:?}/noNet.sh"
SC="${MUT_TMP:?}/srcmut/site"
rm -rf "${MUT_TMP}/srcmut" && mkdir -p "$SC"
(cd "${SITE:?}" && tar cf - --exclude=node_modules --exclude=./web/dist --exclude=./api/dist --exclude=./web/public/media --exclude=./.wrangler-state \
  --exclude=./test-results --exclude=./screens --exclude=./dist-artifact --exclude=./web/.ssr .) | (cd "$SC" && tar xf -)
for d in node_modules web/node_modules api/node_modules shared/node_modules tools/node_modules web/public/media; do
  [ -e "$SITE/$d" ] && cp -al "$SITE/$d" "$SC/$d"
done
# QA's setup, as QA wrote it, from the copy (its "build-s18-email/site" is this copy)
mkdir -p "${MUT_TMP}/srcmut/qa/build-s18-email" && ln -s "$SC" "${MUT_TMP}/srcmut/qa/build-s18-email/site"
mkdir -p "${MUT_TMP}/srcmut/qa/tools" && cp "$QA_TOOLS/setup-srcmut.sh" "${MUT_TMP}/srcmut/qa/tools/"
bash "${MUT_TMP}/srcmut/qa/tools/setup-srcmut.sh" || exit 1
cd "$SC"
date -u +"=== build-copy %H:%M:%S"; npm run copy || exit 1
date -u +"=== web build %H:%M:%S"; npm run build -w @hd/web > "${OUT:?}/srcmut-webbuild.log" 2>&1 || { echo "web build FAILED"; tail -20 "$OUT/srcmut-webbuild.log"; exit 2; }
date -u +"=== check-promises %H:%M:%S"; node node_modules/tsx/dist/cli.mjs tools/check-promises.ts --json="$OUT/check-promises-srcmut.json"; echo "check-promises exit $?"
date -u +"=== which marker each finding carries %H:%M:%S"
for m in סמ1 סמ2 סמ3 סמ4 סמ5 סמ6; do
  n=$(node -e 'const r=require(process.argv[1]);console.log(r.findings.filter(f=>f.sentence.includes(process.argv[2])).map(f=>f.file+" "+f.rule).join("; ")||"MISSED")' "$OUT/check-promises-srcmut.json" "$m")
  echo "$m: $n"
done
date -u +"=== done %H:%M:%S"
