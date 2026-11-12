#!/usr/bin/env bash
# S23 (frontend-dev): QA S20's tool as S22 ran it, copied to s23/tools so its output lands in s23/data/mut-s20.
# QA S20, ת58–ת60, my new mutations of check:promises (site/tools/check-promises.ts at 8828cab9), after the flag build.
# Every mutation is made on a copy of web/dist (without media); the copy's tree is never touched. Each row: the
# mutation, whether the gate should stop (want 1) or pass (want 0), the gate's exit and its first line.
#   X: a promise where the task asks (SVG <title>, <noscript>, meta description, OG, a WebP's XMP, manifest.json) and
#      a few of my own (an SVG <desc>, an array .join(" "), String.concat);
#   Y: honest lines that must pass (the S20 contact wording, a heading "X: Y" with a negation).
#   SITE=<copy>/site MUT_TMP=<scratch> bash mut-s20.sh
set -u
source "$(dirname "$0")/noNet.sh"
QA=$(cd "$(dirname "$0")/.." && pwd)
cd "${SITE:?}" || exit 2
OUT=$QA/data/mut-s20
mkdir -p "$OUT"
TSX="node $PWD/node_modules/tsx/dist/cli.mjs"
TMP=$(mktemp -d "${MUT_TMP:?}/mut20-XXXX")
trap 'rm -rf "$TMP"' EXIT
copy_dist() { local d="$TMP/$1"; mkdir -p "$d" && (cd web/dist && tar cf - --exclude=./media .) | (cd "$d" && tar xf -); echo "$d"; }
sub() { node -e 'const fs=require("fs");const [f,a,b]=process.argv.slice(1);const s=fs.readFileSync(f,"utf8");if(!s.includes(a)){console.error("not found in "+f+": "+a);process.exit(3)}fs.writeFileSync(f,s.replace(a,b))' "$@" || { echo "the anchor of a mutation is missing; the run stops"; exit 3; }; }
PASS=0; FAIL=0
row() { local id=$1 want=$2 what=$3; shift 3
  "$@" >"$OUT/$id.out" 2>&1; local got=$?
  local v; if [ "$got" = "$want" ]; then v=ok; PASS=$((PASS+1)); else v=GAP; FAIL=$((FAIL+1)); fi
  printf '%-4s %-4s want %s got %s  %s  | %s\n' "$v" "$id" "$want" "$got" "$what" "$(grep -m1 -E 'promises \(|0 promises|problem' "$OUT/$id.out" | sed 's/^ *//' | cut -c1-170)"
}
CHK() { $TSX tools/check-promises.ts --dist="$1" "${@:2}"; }
PRIV='האתר לא שולח דיוור שיווקי.'
DESC='סיור בבית מעוצב: נוגעים בכל פריט בחדר'
echo "QA S20 new mutations of check:promises, $(date -u +%FT%TZ), commit 8828cab9 (flag build)"
D=$(copy_dist x0); row X0 0 "clean dist" CHK "$D"
# --- SVG ---
D=$(copy_dist x1); node -e 'const fs=require("fs");const f=process.argv[1];let s=fs.readFileSync(f,"utf8");s=s.replace(/(<svg\b[^>]*>)/,"$1<title>נשלח לכם אישור במייל</title>");fs.writeFileSync(f,s)' "$D/favicon.svg"; grep -c 'נשלח לכם' "$D/favicon.svg" > "$OUT/X1.check"
row X1 1 "an SVG file in dist (favicon.svg): <title>" CHK "$D"
D=$(copy_dist x2); sub "$D/privacy/index.html" "$PRIV" "$PRIV<svg role=\"img\" aria-labelledby=\"qa-t\" width=\"1\" height=\"1\"><title id=\"qa-t\">נעדכן אתכם במייל כשההזמנה יוצאת</title></svg>"
row X2 1 "an inline SVG in a page: <title>" CHK "$D"
D=$(copy_dist x3); sub "$D/privacy/index.html" "$PRIV" "$PRIV<svg role=\"img\" width=\"1\" height=\"1\"><desc>תקבלו התראה בוואטסאפ כשהחבילה יוצאת</desc></svg>"
row X3 1 "an inline SVG in a page: <desc>" CHK "$D"
# --- noscript ---
D=$(copy_dist x4); sub "$D/order/index.html" '</head>' '<noscript>&#1488;&#1497;&#1513;&#1493;&#1512; &#1497;&#1497;&#1513;&#1500;&#1495; &#1500;&#1488;&#1497;&#1502;&#1497;&#1497;&#1500; &#1513;&#1500;&#1499;&#1501;.</noscript></head>'
row X4 1 "<noscript> in the <head> of the order shell (a client-only page), numeric entities (\"אישור יישלח לאימייל שלכם.\")" CHK "$D"
D=$(copy_dist x5); sub "$D/404.html" '</body>' '<noscript><p>אישור ההזמנה <b>יישלח</b> במייל.</p></noscript></body>'
row X5 1 "<noscript> in 404, split across <b>" CHK "$D"
# --- meta and OG ---
D=$(copy_dist x6); sub "$D/index.html" "content=\"$DESC" "content=\"נעדכן אתכם במייל על כל מוצר חדש. $DESC"
row X6 1 "meta description (home)" CHK "$D"
D=$(copy_dist x7); node -e 'const fs=require("fs");const f=process.argv[1];let s=fs.readFileSync(f,"utf8");const a="<meta property=\"og:description\" content=\"";if(!s.includes(a))process.exit(3);s=s.replace(a,a+"הירשמו לניוזלטר ותקבלו 10% הנחה. ");fs.writeFileSync(f,s)' "$D/index.html"
row X7 1 "og:description (home)" CHK "$D"
D=$(copy_dist x8); sub "$D/index.html" '<meta property="og:title" content="' '<meta property="og:title" content="תקבלו עדכונים ב-SMS · '
row X8 1 "og:title (home)" CHK "$D"
D=$(copy_dist x9); sub "$D/index.html" '</head>' '<meta name="twitter:description" content="נשלח לכם קופון במייל &quot;מיד&quot; אחרי ההרשמה"></head>'
row X9 1 "twitter:description with &quot; entities (home)" CHK "$D"
D=$(copy_dist x10); sub "$D/index.html" '</head>' "<meta property='og:description' content='נעדכן אתכם כשהמוצר חוזר'></head>"
row X10 1 "a second og:description, single quotes" CHK "$D"
# --- a WebP with an XMP packet (dc:description); referenced by a page ---
D=$(copy_dist x11); node -e '
const sharp=require(process.argv[2]);
const xmp="<?xpacket begin=\"\" id=\"W5M0MpCehiHzreSzNTczkc9d\"?><x:xmpmeta xmlns:x=\"adobe:ns:meta/\"><rdf:RDF xmlns:rdf=\"http://www.w3.org/1999/02/22-rdf-syntax-ns#\"><rdf:Description xmlns:dc=\"http://purl.org/dc/elements/1.1/\"><dc:description><rdf:Alt><rdf:li xml:lang=\"x-default\">נשלח לכם אישור במייל כשהמוצר חוזר</rdf:li></rdf:Alt></dc:description></rdf:Description></rdf:RDF></x:xmpmeta><?xpacket end=\"w\"?>";
sharp({create:{width:8,height:8,channels:3,background:{r:240,g:236,b:230}}}).webp().withXmp(xmp).toFile(process.argv[1]).then(()=>{const d=require("fs").readFileSync(process.argv[1]);console.log("XMP chunk:",d.includes(Buffer.from("XMP ")),"promise in the file:",d.includes(Buffer.from("נשלח לכם אישור")),"bytes",d.length)})' "$D/qa-x11.webp" "$PWD/node_modules/sharp" > "$OUT/X11.check" 2>&1
sub "$D/privacy/index.html" "$PRIV" "$PRIV<img src=\"/qa-x11.webp\" alt=\"\" width=\"8\" height=\"8\">"
row X11 0 "a WebP with XMP (dc:description) in dist, shown by a page: binary, never read by a customer (want 0: info only)" CHK "$D"
# --- manifests ---
D=$(copy_dist x12); printf '{"name":"הבית","short_name":"הבית","description":"נשלח לכם הודעה כשהמוצר חוזר למלאי.","start_url":"/","display":"standalone"}\n' > "$D/manifest.json"; sub "$D/index.html" '</head>' '<link rel="manifest" href="/manifest.json"></head>'
row X12 1 "manifest.json in dist, linked from home: description" CHK "$D"
D=$(copy_dist x13); printf '{"name":"הבית","short_name":"עדכונים ב-SMS","start_url":"/"}\n' > "$D/site.webmanifest"
row X13 1 "site.webmanifest, not linked: short_name \"עדכונים ב-SMS\" (two words: the definition's label exemption)" CHK "$D"
D=$(copy_dist x13b); printf '{"name":"הבית","short_name":"נעדכן אתכם במייל","start_url":"/"}\n' > "$D/site.webmanifest"
row X13b 1 "site.webmanifest, not linked: short_name \"נעדכן אתכם במייל\" (the file is scanned)" CHK "$D"
D=$(copy_dist x14); printf '{"name":"הבית","shortcuts":[{"name":"עדכנו אותי כשחוזר","url":"/"}]}\n' > "$D/manifest.webmanifest"
row X14 1 "manifest.webmanifest: a shortcut's name" CHK "$D"
# --- code: joins the scanner does not read ---
D=$(copy_dist x15); f=$(ls "$D"/assets/Order-*.js); printf '\nexport const __x15=["אישור ההזמנה","יישלח","במייל"].join(" ");\n' >>"$f"
row X15 1 "lazy chunk (Order): [\"אישור ההזמנה\",\"יישלח\",\"במייל\"].join(\" \")" CHK "$D"
D=$(copy_dist x16); f=$(ls "$D"/assets/Order-*.js); printf '\nexport const __x16="האישור ".concat("יגיע ","לתיבת הדואר");\n' >>"$f"
row X16 1 "lazy chunk (Order): \"האישור \".concat(\"יגיע \",\"לתיבת הדואר\")" CHK "$D"
D=$(copy_dist x17); sub "$D/privacy/index.html" "$PRIV" "$PRIV<label><input type=\"checkbox\"> חשבונית במייל</label><label><input type=\"checkbox\"> עדכונים ב-SMS</label>"
row X17 1 "two checkbox labels, two words each: \"חשבונית במייל\", \"עדכונים ב-SMS\"" CHK "$D"
# --- honest lines (want 0) ---
D=$(copy_dist y1); sub "$D/returns/index.html" 'להודעת ביטול: פרטי הקשר' 'להודעת ביטול: פנו אלינו באחת הדרכים שלמטה, וציינו את מספר ההזמנה. אפשר לכתוב לנו עם מספר ההזמנה, ונבדוק אותה. להודעת ביטול: פרטי הקשר'
row Y1 0 "honest: the S20 contact wording (returns, no_access_contact)" CHK "$D"
D=$(copy_dist y2); sub "$D/accessibility/index.html" 'שם, טלפון ואימייל של רכז/ת הנגישות' 'נשמח לשמוע על כל קושי. פניות לרכז/ת הנגישות נענות תוך 5 ימי עסקים. <span class="contact-label">אימייל: </span><a href="mailto:info@hd-qa.co.il">info@hd-qa.co.il</a> שם, טלפון ואימייל של רכז/ת הנגישות'
row Y2 0 "honest: the S20 accessibility wording and the contact block (\"אימייל: info@…\")" CHK "$D"
D=$(copy_dist y3); sub "$D/privacy/index.html" "$PRIV" "דיוור שיווקי: האתר לא שולח דיוור."
row Y3 0 "honest: a heading \"X: Y\" then a negation (\"דיוור שיווקי: האתר לא שולח דיוור.\")" CHK "$D"
D=$(copy_dist y4); sub "$D/privacy/index.html" "$PRIV" "$PRIV שינוי בכתובת? שלחו לנו מייל לפני שההזמנה יוצאת."
row Y4 0 "honest: the customer writes to us (\"שלחו לנו מייל\")" CHK "$D"
echo "rows as wanted: $PASS, gaps: $FAIL"
