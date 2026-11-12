#!/bin/bash
# QA S18, question 2 (source level): promises written the way a developer or the designer would, in the source, then
# built by the real build (vite, esbuild, prerender) in the scratchpad copy that served the email-mode test (its flag
# restored to 3013d630: EMAIL_PROVIDERS = [], every EMAIL_PROVIDER UNDECIDED). Each mutation has a marker word so it can
# be found in the bundle and on the page:
#   SM1 Order.tsx (client-only page), JSX split across <b>:      <p>אישור <b>יישלח</b> לאימייל שלכם (סמ1).</p>
#   SM2 Order.tsx, a template literal split by ${}:              `האישור על ${n} פריטים יישלח אליכם (סמ2).`
#   SM3 Checkout.tsx, "a" + "b":                                 {'אישור ההזמנה ' + 'יישלח בקרוב (סמ3).'}
#   SM4 shared/src/constants.ts ORDER_STATUS_HE.paid (the Worker serves it as status_he; in no web chunk)
#   SM5 Legal.tsx, privacy (prerendered), a <span> split:        <li>חשבונית מס <span>נשלחת</span> במייל (סמ5).</li>
#   SM6 Legal.tsx, privacy, an indirect form:                    <li>את האישור תמצאו בתיבת הדואר שלכם (סמ6).</li>
set -euo pipefail
QA=$(cd "$(dirname "$0")/.." && pwd)
cd "$QA/build-s18-email/site"
sub() { node -e 'const fs=require("fs");const [f,a,b]=process.argv.slice(1);const s=fs.readFileSync(f,"utf8");if(!s.includes(a)){console.error("not found in "+f+": "+a);process.exit(3)}fs.writeFileSync(f,s.replace(a,b))' "$@"; }
sub web/src/pages/Order.tsx "                  : copyHe('order.next.received')}
            </p>" "                  : copyHe('order.next.received')}
            </p>
          ) : null}
          {paid && !closed ? (
            <>
              <p class=\"qa-sm1\">
                אישור <b>יישלח</b> לאימייל שלכם (סמ1).
              </p>
              <p class=\"qa-sm2\">{\`האישור על \${order.lines.length} פריטים יישלח אליכם (סמ2).\`}</p>
            </>"
sub web/src/pages/Checkout.tsx "<p class=\"small muted\">{copyHe('checkout.total_note')}</p>" "<p class=\"small muted\">{copyHe('checkout.total_note')}</p>
            <p class=\"qa-sm3\">{'אישור ההזמנה ' + 'יישלח בקרוב (סמ3).'}</p>"
sub ../site/shared/src/constants.ts "  paid: 'התקבלה'," "  paid: 'התקבלה. אישור יישלח במייל (סמ4)',"
sub web/src/pages/Legal.tsx "            <li>{copyHe('privacy.marketing')}</li>" "            <li>{copyHe('privacy.marketing')}</li>
            <li class=\"qa-sm5\">
              חשבונית מס <span>נשלחת</span> במייל (סמ5).
            </li>
            <li class=\"qa-sm6\">את האישור תמצאו בתיבת הדואר שלכם (סמ6).</li>"
grep -c "סמ" web/src/pages/Order.tsx web/src/pages/Checkout.tsx shared/src/constants.ts web/src/pages/Legal.tsx
