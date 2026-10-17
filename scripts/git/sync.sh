#!/bin/bash
# commit data/sources churn, merge the remote branch (auto-resolving seen.json, the board and derived coverage files), push. Usage: sync.sh "message"
cd /home/user/homedesign-app
S="$(cd "$(dirname "$0")" && pwd)"
for i in 1 2 3 4; do
  git add data/sources/ 2>/dev/null
  git diff --cached --quiet || git -c user.name="Beeri Rimon" -c user.email=beeririmon@gmail.com commit -q -m "${1:-CJ cache update}

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_012un7iEDRha5J5s2Ea72wCe"
  git fetch -q origin claude/agent-system-brand-launch-ax87dv
  if ! git -c user.name="Beeri Rimon" -c user.email=beeririmon@gmail.com merge -q --no-edit origin/claude/agent-system-brand-launch-ax87dv >/dev/null 2>&1; then
    U=$(git diff --name-only --diff-filter=U)
    # Auto-resolvable (2026-10-17): the registry (union), the board log (both sides kept, append-only),
    # and derived files that the scripts regenerate. Anything else stops for a human merge.
    REST=""
    for f in $U; do
      case "$f" in
        data/sources/seen.json) python3 $S/seen_union.py && git add "$f" ;;
        status/board.md) python3 -c "import sys;p=sys.argv[1];L=open(p).read().split('\n');open(p,'w').write('\n'.join(l for l in L if not (l.startswith('<<<<<<< ') or l=='=======' or l.startswith('>>>>>>> '))))" "$f" && git add "$f" ;;
        data/leads/final-2026-10-13/coverage.json|data/leads/final-2026-10-13/coverage.md|data/leads/final-2026-10-13/round5/targets.json)
          git checkout -q --theirs "$f" && git add "$f" ;;
        *) REST="$REST $f" ;;
      esac
    done
    if [ -n "$REST" ]; then echo "CONFLICT:$REST"; exit 1; fi
    if [ -n "$U" ]; then
      git -c user.name="Beeri Rimon" -c user.email=beeririmon@gmail.com commit -q --no-edit
      if echo "$U" | grep -q "coverage\|targets"; then
        python3 scripts/sourcing/final_round_coverage.py >/dev/null && python3 scripts/sourcing/round5_targets.py >/dev/null
        git add data/leads/final-2026-10-13/coverage.json data/leads/final-2026-10-13/coverage.md data/leads/final-2026-10-13/round5/targets.json
        git diff --cached --quiet || git -c user.name="Beeri Rimon" -c user.email=beeririmon@gmail.com commit -q -m "Coverage and targets regenerated after merge

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_012un7iEDRha5J5s2Ea72wCe"
      fi
    else continue; fi
  fi
  if git push -q -u origin claude/agent-system-brand-launch-ax87dv 2>/dev/null; then git log --oneline -1; exit 0; fi
  sleep 3
done
echo "push failed"; exit 1
