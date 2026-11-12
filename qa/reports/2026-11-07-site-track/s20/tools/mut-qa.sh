#!/usr/bin/env bash
# S20 (frontend-dev): QA S18's mutations of check:promises (qa/reports/2026-11-12-site-track-qa-s18/tools/mut-qa.sh), as QA
# wrote them, run against the S20 gate on the flag build. Changed from QA's: the paths (SITE, QA_TOOLS, MUT_TMP), and Q27
# gives the gate the mutated shared/src (--shared, new in S20: S18 had no input for it).
# Usage: SITE=<site> QA_TOOLS=<qa s18 tools> MUT_TMP=<scratch> bash mut-qa.sh
# (QA's header follows)
# QA S18, question 2: my own mutations of check:promises (site/tools/check-promises.ts at 3013d630), after the flag build.
# Every mutation is made on a copy (of web/dist without media, of api/src, of the copy file); the copy's tree is never
# touched. Each row: the mutation, whether a customer would read it, the gate's exit (1 = caught, 0 = passed), and its
# first line. "want 1" = a promise the customer reads, the gate should stop the build.
set -u
source "${QA_TOOLS:?QA S18 tools}/noNet.sh"
QA=$(cd "$(dirname "$0")/.." && pwd)
cd "${SITE:?the live site, or a copy}" || exit 2
OUT=$QA/data/mut-qa
mkdir -p "$OUT"
TSX="node $PWD/node_modules/tsx/dist/cli.mjs"
TMP=$(mktemp -d "${MUT_TMP:?a scratch dir}/mut-XXXX")
trap 'rm -rf "$TMP"' EXIT
copy_dist() { local d="$TMP/$1"; mkdir -p "$d" && (cd web/dist && tar cf - --exclude=./media .) | (cd "$d" && tar xf -); echo "$d"; }
# sub <file> <old> <new>: replace the first occurrence, exit 3 if the old text is not there
sub() { node -e 'const fs=require("fs");const [f,a,b]=process.argv.slice(1);const s=fs.readFileSync(f,"utf8");if(!s.includes(a)){console.error("not found in "+f+": "+a);process.exit(3)}fs.writeFileSync(f,s.replace(a,b))' "$@" || { echo "S20: the anchor of a mutation is missing; the run stops"; exit 3; }; }
PASS=0; FAIL=0
row() { # row <id> <want> <what> <command...>
  local id=$1 want=$2 what=$3; shift 3
  "$@" >"$OUT/$id.out" 2>&1; local got=$?
  local v; if [ "$got" = "$want" ]; then v=ok; PASS=$((PASS+1)); else v=GAP; FAIL=$((FAIL+1)); fi
  printf '%-4s %-4s want %s got %s  %s  | %s\n' "$v" "$id" "$want" "$got" "$what" "$(grep -m1 -E 'promises \(|refused|is not|built for|0 promises|problem' "$OUT/$id.out" | sed 's/^ *//' | cut -c1-150)"
}
CHK() { $TSX tools/check-promises.ts --dist="$1" "${@:2}"; }
PRIV='האתר לא שולח דיוור שיווקי.'
echo "QA S18 mutations of check:promises, $(date -u +%FT%TZ), S20 tree (flag build)"

D=$(copy_dist q0); row Q0 0 "clean dist" CHK "$D"

# --- split across elements (prerendered HTML) ---
D=$(copy_dist q1); sub "$D/privacy/index.html" "$PRIV" 'חשבונית מס <span>נשלחת</span> במייל אחרי התשלום.'
row Q1 1 "HTML: verb in a <span>, object outside (privacy page)" CHK "$D"
D=$(copy_dist q2); sub "$D/privacy/index.html" "$PRIV" 'חשבונית מס <strong>נשלחת</strong> במייל אחרי התשלום.'
row Q2 1 "HTML: verb in a <strong> (privacy page)" CHK "$D"
D=$(copy_dist q3); sub "$D/privacy/index.html" "$PRIV" '<a href="/terms/">אישור</a> יישלח לאימייל.'
row Q3 1 "HTML: object in a link, verb after it" CHK "$D"
# --- attributes ---
P=$(grep -l 'waitlist-status' web/dist/p/*/index.html | head -1 | sed 's|web/dist/||')
D=$(copy_dist q4); sub "$D/$P" 'class="waitlist-status"' 'class="waitlist-status" aria-label="נעדכן אתכם במייל כשחוזר"'
row Q4 1 "attribute aria-label (product on hold)" CHK "$D"
D=$(copy_dist q5); sub "$D/$P" 'class="waitlist-status"' 'class="waitlist-status" title="נשלח לכם הודעה כשחוזר"'
row Q5 1 "attribute title" CHK "$D"
D=$(copy_dist q6); sub "$D/$P" 'המלאי אינו זמין כעת</p>' 'המלאי אינו זמין כעת</p><img src="/favicon.svg" alt="נעדכן אתכם כשהמוצר חוזר">'
row Q6 1 "attribute alt" CHK "$D"
D=$(copy_dist q7); sub "$D/$P" 'המלאי אינו זמין כעת</p>' 'המלאי אינו זמין כעת</p><input type="submit" value="עדכנו אותי כשחוזר">'
row Q7 1 "attribute value of a submit input (the button's text)" CHK "$D"
D=$(copy_dist q8); sub "$D/$P" 'class="waitlist-status"' "class=\"waitlist-status\" aria-label='נעדכן אתכם במייל כשחוזר'"
row Q8 1 "attribute aria-label in single quotes" CHK "$D"
D=$(copy_dist q9); sub "$D/$P" 'class="waitlist-status"' 'class="waitlist-status" aria-roledescription="נעדכן אתכם כשחוזר"'
row Q9 1 "attribute aria-roledescription" CHK "$D"
# --- JSON payloads ---
D=$(copy_dist q10); sub "$D/story/living-room/nordic/index.html" '"status":"unavailable"' '"status":"unavailable","note_he":"נשלח לכם הודעה כשהמוצר חוזר."'
F=$D/story/living-room/nordic/index.html; node -e 'const fs=require("fs");const f=process.argv[1];let s=fs.readFileSync(f,"utf8");s=s.replace(/("detail_he":")([^"]*)(")/,"$1נשלח לכם הודעה כשהמוצר חוזר. $2$3");fs.writeFileSync(f,s)' "$F"
row Q10 1 "JSON island type=application/json (story data, an item's detail_he that the sheet shows)" CHK "$D"
D=$(copy_dist q11); node -e 'const fs=require("fs");const f=process.argv[1];let s=fs.readFileSync(f,"utf8");const i=s.indexOf("application/ld+json");if(i<0)process.exit(3);s=s.replace(/("description":")/,"$1נשלח לכם אישור במייל. ");fs.writeFileSync(f,s)' "$D/$P"
row Q11 1 "JSON-LD description (product page)" CHK "$D"
D=$(copy_dist q12); mkdir -p "$D/data"; echo '{"notice_he":"נשלח לכם הודעה כשהמוצר חוזר למלאי."}' > "$D/data/notice.json"
row Q12 1 "a JSON file in dist (fetched at run time)" CHK "$D"
# --- chunks ---
D=$(copy_dist q13); f=$(ls "$D"/assets/Waitlist-*.js); printf '\nexport const __q13="נשלח לכם הודעה אחת כשהמוצר חוזר.";\n' >>"$f"
row Q13 1 "lazy chunk (Waitlist), a whole sentence" CHK "$D"
D=$(copy_dist q14); f=$(ls "$D"/assets/Order-*.js); printf '\nexport const __q14=(u)=>u("p",{children:["אישור ",u("b",{children:"יישלח"})," לאימייל שלכם."]});\n' >>"$f"
row Q14 1 "lazy chunk (Order), JSX split across <b>: \"אישור <b>יישלח</b> לאימייל\"" CHK "$D"
D=$(copy_dist q15); f=$(ls "$D"/assets/Order-*.js); printf '\nexport const __q15=(n)=>`האישור על ${n} פריטים יישלח אליכם`;\n' >>"$f"
row Q15 1 "lazy chunk (Order), template literal: object and verb split by \${n}" CHK "$D"
D=$(copy_dist q16); f=$(ls "$D"/assets/Order-*.js); printf '\nexport const __q16="אישור ההזמנה "+"יישלח בקרוב.";\n' >>"$f"
row Q16 1 "lazy chunk (Order), \"a\"+\"b\" concatenation" CHK "$D"
D=$(copy_dist q17); echo 'document.body.insertAdjacentText("beforeend","נשלח לכם אישור במייל.");' > "$D/notice.js"; sub "$D/privacy/index.html" '</body>' '<script src="/notice.js"></script></body>'
row Q17 1 "a script outside assets/ that a page loads (/notice.js)" CHK "$D"
D=$(copy_dist q18); f=$(ls "$D"/assets/Waitlist-*.js); b=$(basename "$f"); printf '\nexport const __q18="נשלח לכם הודעה אחת כשהמוצר חוזר.";\n' >>"$f"
for g in "$D"/assets/*.js; do [ "$g" = "$f" ] || sed -i "s#\"assets/$b\"#\"https://cdn.example/assets/$b\"#g; s#\"./$b\"#\"https://cdn.example/assets/$b\"#g; s#\"/assets/$b\"#\"https://cdn.example/assets/$b\"#g" "$g"; done
for g in $(grep -rl "$b" "$D" --include=*.html); do sed -i "s#/assets/$b#https://cdn.example/assets/$b#g" "$g"; done
row Q18 1 "the promise's chunk named by an absolute URL (a CDN base): skipped, listed, not scanned" CHK "$D"
D=$(copy_dist q19); c=$(ls "$D"/assets/main-*.css | head -1); printf '\n.waitlist-status::after{content:" נעדכן אתכם במייל כשחוזר"}\n' >>"$c"
row Q19 1 "CSS content: text drawn by a stylesheet" CHK "$D"
D=$(copy_dist q20); sub "$D/privacy/index.html" "$PRIV" 'We’ll email you when your order ships.'
row Q20 1 "English with a typographic apostrophe (We’ll email you)" CHK "$D"
D=$(copy_dist q21); sub "$D/privacy/index.html" "$PRIV" 'את האישור תמצאו בתיבת הדואר שלכם.'
row Q21 1 "indirect: \"את האישור תמצאו בתיבת הדואר שלכם\"" CHK "$D"
D=$(copy_dist q22); sub "$D/privacy/index.html" "$PRIV" 'עדכוני משלוח ב-SMS ובוואטסאפ.'
row Q22 1 "indirect: a feature line, \"עדכוני משלוח ב-SMS ובוואטסאפ\"" CHK "$D"
D=$(copy_dist q23); sub "$D/privacy/index.html" '<title>' '<title>נעדכן אתכם במייל · '
row Q23 1 "<title>" CHK "$D"
D=$(copy_dist q24); sub "$D/privacy/index.html" '</body>' '<noscript>נשלח לכם אישור במייל.</noscript></body>'
row Q24 1 "<noscript>" CHK "$D"
# --- the Worker and shared code ---
mkdir -p "$TMP/api1" && cp -r api/src/. "$TMP/api1/"
sub "$TMP/api1/lib/cancel.ts" "'ההזמנה לא נמצאה.'" "'ההזמנה לא נמצאה. נשלח לכם אישור במייל.'"
row Q25 1 "Worker: a customer message (lib/cancel.ts)" CHK "$(copy_dist q25)" --api="$TMP/api1"
mkdir -p "$TMP/api2" && cp -r api/src/. "$TMP/api2/" && printf '{"order_he":"נשלח לכם אישור במייל."}\n' > "$TMP/api2/lib/messages.json"
row Q26 1 "Worker: a .json of messages in api/src" CHK "$(copy_dist q26)" --api="$TMP/api2"
mkdir -p "$TMP/shared" && cp -r shared/src/. "$TMP/shared/" && sub "$TMP/shared/constants.ts" "paid: 'התקבלה'," "paid: 'התקבלה. אישור יישלח במייל',"
row Q27 1 "shared/src: ORDER_STATUS_HE.paid (served by the Worker as status_he; in no web chunk)" CHK "$(copy_dist q27)" --shared="$TMP/shared"
grep -c "אישור יישלח במייל" "$TMP/shared/constants.ts" > "$OUT/Q27.shared-mutated.txt"
# --- the copy file (master-designer's place) ---
node -e 'const fs=require("fs");const s=JSON.parse(fs.readFileSync("copy/promises.he.json","utf8"));s.strings["checkout.total_note"].no_email="כולל מע\"מ. תקבלו חשבונית מס.";fs.writeFileSync(process.argv[1],JSON.stringify(s))' "$TMP/c1.json"
row Q28 1 "copy file, no_email: \"כולל מע\\\"מ. תקבלו חשבונית מס.\"" $TSX tools/build-copy.ts --copy="$TMP/c1.json" --out="$TMP/never1.json"
node -e 'const fs=require("fs");const s=JSON.parse(fs.readFileSync("copy/promises.he.json","utf8"));s.strings["order.next.received"].no_email="אישור ההזמנה ומצבה מופיעים בדף הזה. המייל עם האישור כבר בדרך.";fs.writeFileSync(process.argv[1],JSON.stringify(s))' "$TMP/c2.json"
row Q29 1 "copy file, no_email: \"…המייל עם האישור כבר בדרך.\"" $TSX tools/build-copy.ts --copy="$TMP/c2.json" --out="$TMP/never2.json"
node -e 'const fs=require("fs");const s=JSON.parse(fs.readFileSync("copy/promises.he.json","utf8"));s.strings["order.next.shipped"].text="ההזמנה בדרך אליכם. נעדכן כשתגיע.";fs.writeFileSync(process.argv[1],JSON.stringify(s))' "$TMP/c3.json"
row Q30 1 "copy file, a text line (both modes) that promises" $TSX tools/build-copy.ts --copy="$TMP/c3.json" --out="$TMP/never3.json"
# --- false positives on honest lines (want 0) ---
D=$(copy_dist q31); sub "$D/returns/index.html" 'להודעת ביטול: פרטי הקשר' 'הודעת ביטול שנשלחת אלינו באימייל תטופל תוך 3 ימי עסקים. להודעת ביטול: פרטי הקשר' # S20: the line's new anchor
row Q31 0 "honest: the customer writes to us (\"הודעת ביטול שנשלחת אלינו באימייל…\")" CHK "$D"
D=$(copy_dist q32); sub "$D/privacy/index.html" "$PRIV" "$PRIV נעדכן את המדיניות מעת לעת, והנוסח המעודכן יופיע בדף הזה."
row Q32 0 "honest: legal boilerplate (\"נעדכן את המדיניות מעת לעת…\")" CHK "$D"
D=$(copy_dist q33); sub "$D/privacy/index.html" "$PRIV" "$PRIV שיניתם כתובת? עדכנו אותנו לפני המשלוח."
row Q33 0 "honest: the customer updates us (\"עדכנו אותנו\")" CHK "$D"
D=$(copy_dist q34); f=$(ls "$D"/assets/Order-*.js); printf '\nexport const __q34="קישור למעקב יופיע כאן כשהספק ישלח את החבילה.";\n' >>"$f"
row Q34 0 "honest: the page will show the link (\"קישור למעקב יופיע כאן כשהספק ישלח את החבילה\")" CHK "$D"
D=$(copy_dist q35); sub "$D/accessibility/index.html" 'שם, טלפון ואימייל של רכז/ת הנגישות' 'אנחנו מקבלים פניות במייל ובטלפון. שם, טלפון ואימייל של רכז/ת הנגישות' # S20: the line's new anchor
row Q35 0 "honest: we accept inquiries (\"אנחנו מקבלים פניות במייל ובטלפון\")" CHK "$D"
echo "rows as wanted: $PASS, gaps: $FAIL"
