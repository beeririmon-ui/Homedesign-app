#!/bin/bash
# commit data/sources churn, merge the remote branch (union-resolving seen.json), push. Usage: sync.sh "message"
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
    if [ "$U" = "data/sources/seen.json" ]; then
      python3 $S/seen_union.py && git add data/sources/seen.json && git -c user.name="Beeri Rimon" -c user.email=beeririmon@gmail.com commit -q --no-edit
    elif [ -n "$U" ]; then echo "CONFLICT: $U"; exit 1
    else continue; fi
  fi
  if git push -q -u origin claude/agent-system-brand-launch-ax87dv 2>/dev/null; then git log --oneline -1; exit 0; fi
  sleep 3
done
echo "push failed"; exit 1
