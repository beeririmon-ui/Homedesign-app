#!/bin/bash
# ת46 on the live server: every row the copy's Worker wrote while the e2e, a11y and my browser checks ran (srv-8799.log),
# against the customer details those flows type (the e2e's own and mine). Counts per needle.
LOG=${1:-$(dirname "$0")/../s17-logs/srv-8799.log}
echo "server log: $(wc -l < "$LOG") lines, $(grep -cE "level: '(info|warn|error)'" "$LOG") structured rows ($(grep -c "level: 'error'" "$LOG") error, $(grep -c "level: 'warn'" "$LOG") warn); events: $(grep -oE "event: '[a-z_.]+'" "$LOG" | sort | uniq -c | sort -rn | head -12 | awk '{print $3"×"$1}' | tr '\n' ' ')"
for n in 'ישראלה ישראלי' 'ישראל ישראלי' 'נועה כהן' 'ישראלי' 'buyer@example.com' 'noa@example.com' 'noa.ops@example.com' '050-1234567' '0501234567' '03-1234567' 'תל אביב' 'הרצל' 'חיפה' 'הנמל' 'אורנה' 'בודקת' 'orna.delay17' 'orna.an17' '7716209' '7716207' 'Orna' 'מצפה' 'הבודקים'; do
  c=$(grep -cF -- "$n" "$LOG"); [ "$c" != 0 ] && echo "  LEAK? '$n': $c lines" ; done
c=$(grep -cP '(?<![0-9])1234567(?![0-9])' "$LOG"); [ "$c" != 0 ] && echo "  LEAK? the 7 digits 1234567 alone: $c lines"
echo "needles checked: 24; the lines above (if any) are hits"
