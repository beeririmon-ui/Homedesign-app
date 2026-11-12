#!/usr/bin/env bash
# S18: the mutations of the email-promise checks. Run from site/, after `npm run build`:
#   bash ../qa/reports/2026-11-07-site-track/s18/tools/mut-promises.sh
# Every mutation is made on a copy (of web/dist without media, of api/src, of the copy, of wrangler.jsonc). The tree is
# never touched. With E2E=1 it also mutates web/dist itself (the privacy page and the copy chunk) for the rendered test,
# and puts the files back from a backup at the end, whatever happens.
set -u
cd "$(dirname "$0")/../../../../../site" || exit 2
OUT=../qa/reports/2026-11-07-site-track/s18/data
mkdir -p "$OUT"
TSX="node node_modules/tsx/dist/cli.mjs"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
OLD_ORDER='אישור וחשבונית מס יישלחו לאימייל. נעדכן כשההזמנה יוצאת למשלוח.'
NEW_ORDER=$(node -e 'console.log(JSON.parse(require("fs").readFileSync(".generated/copy.he.json","utf8")).strings["order.next.received"])')

copy_dist() { # a copy of the built site without its media (the check reads pages and scripts)
  local d="$TMP/$1"
  mkdir -p "$d" && (cd web/dist && tar cf - --exclude=./media .) | (cd "$d" && tar xf -)
  echo "$d"
}
expect() { # expect <name> <wanted exit> <command...>
  local name=$1 want=$2
  shift 2
  "$@" >"$OUT/$name.out" 2>&1
  local got=$?
  local verdict=$([ "$got" = "$want" ] && echo ok || echo WRONG)
  printf '%-6s %-4s exit %s (wanted %s)  %s\n' "$verdict" "$name" "$got" "$want" "$(grep -m1 -E 'promises \(|refused|is not|problem|built for|0 promises' "$OUT/$name.out" | sed 's/^ *//' | cut -c1-170)"
}

echo "S18 mutations, $(date -u +%FT%TZ)"
D=$(copy_dist m0)
expect M0 0 $TSX tools/check-promises.ts --dist="$D" --json="$OUT/mut-M0.json"

D=$(copy_dist m1) # the copy chunk shows the order page's old line
f=$(ls "$D"/assets/copy-*.js)
node -e 'const fs=require("fs");const [f,a,b]=process.argv.slice(1);const s=fs.readFileSync(f,"utf8");if(!s.includes(a))process.exit(3);fs.writeFileSync(f,s.replace(a,b))' "$f" "$NEW_ORDER" "$OLD_ORDER"
expect M1 1 $TSX tools/check-promises.ts --dist="$D" --json="$OUT/mut-M1.json"

D=$(copy_dist m2) # a promise written in the order page's code, past the copy
f=$(ls "$D"/assets/Order-*.js)
printf '\nexport const __s18="את פרטי ההזמנה שלחנו לאימייל שלכם.";\n' >>"$f"
expect M2 1 $TSX tools/check-promises.ts --dist="$D" --json="$OUT/mut-M2.json"

D=$(copy_dist m3) # the waiting-list button back in a prerendered product page
f=$(grep -l 'waitlist-status' "$D"/p/*/index.html | head -1)
node -e 'const fs=require("fs");const f=process.argv[1];const s=fs.readFileSync(f,"utf8");fs.writeFileSync(f,s.replace("המלאי אינו זמין כעת</p>","המלאי אינו זמין כעת</p><button type=\"button\" class=\"btn btn-ghost\">עדכנו אותי כשחוזר</button>"))' "$f"
expect M3 1 $TSX tools/check-promises.ts --dist="$D" --json="$OUT/mut-M3.json"

mkdir -p "$TMP/api" && cp -r api/src/. "$TMP/api/" # a customer message of the Worker that promises
printf "\nexport const __s18 = { message_he: 'ההזמנה התקבלה. נשלח אליכם אישור במייל.' };\n" >>"$TMP/api/routes/public.ts"
expect M4 1 $TSX tools/check-promises.ts --dist="$(copy_dist m4)" --api="$TMP/api" --json="$OUT/mut-M4.json"

node -e 'const fs=require("fs");const s=JSON.parse(fs.readFileSync("copy/promises.he.json","utf8"));s.strings["checkout.total_note"].no_email="כולל מע\"מ. חשבונית מס נשלחת במייל אחרי התשלום.";fs.writeFileSync(process.argv[1],JSON.stringify(s))' "$TMP/copy.json"
expect M5 1 $TSX tools/build-copy.ts --copy="$TMP/copy.json" --out="$TMP/never.json"

sed '/"production"/,$ s/"EMAIL_PROVIDER": "UNDECIDED"/"EMAIL_PROVIDER": "mock"/' api/wrangler.jsonc >"$TMP/wrangler.jsonc"
expect M6a 1 env HD_PUBLIC=1 $TSX tools/build-copy.ts --wrangler="$TMP/wrangler.jsonc" --out="$TMP/never.json"
expect M6b 1 sh -c "cd api && node ../node_modules/tsx/dist/cli.mjs scripts/check-config.ts '$TMP/wrangler.jsonc'"

echo '{"email_provider":"resend","sends":true,"strings":{}}' >"$TMP/stale.json"
expect M7 1 $TSX tools/check-promises.ts --dist="$(copy_dist m7)" --copy-out="$TMP/stale.json" --json="$OUT/mut-M7.json"

if [ "${E2E:-}" = "1" ]; then # the rendered page: the privacy policy's old line, in the page and in the copy chunk
  B="$TMP/backup"
  mkdir -p "$B"
  cp web/dist/privacy/index.html "$B/privacy.html"
  c=$(ls web/dist/assets/copy-*.js)
  cp "$c" "$B/copy.js"
  restore() { cp "$B/privacy.html" web/dist/privacy/index.html && cp "$B/copy.js" "$c"; }
  trap 'restore; rm -rf "$TMP"' EXIT
  for f in web/dist/privacy/index.html "$c"; do
    node -e 'const fs=require("fs");const f=process.argv[1];fs.writeFileSync(f,fs.readFileSync(f,"utf8").replace("האתר לא שולח דיוור שיווקי.","דיוור שיווקי נשלח רק אם סימנתם הסכמה, ואפשר להסיר בכל עת."))' "$f"
  done
  expect E1 1 npx --no-install playwright test --project=e2e e2e/s18.spec.ts -g "every page in the sitemap"
  grep -m2 -E "privacy|send" "$OUT/E1.out" | sed 's/^/         /'
  restore
  expect E0 0 npx --no-install playwright test --project=e2e e2e/s18.spec.ts -g "every page in the sitemap"
fi
