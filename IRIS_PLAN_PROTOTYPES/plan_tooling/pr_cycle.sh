#!/bin/bash
# pr_cycle.sh KEY TITLE BODYFILE CHANGELOG_TYPE CHANGELOG_TEXT
# Push branch KEY from ~/Git/glue-solar-KEY, open a draft PR, add changelog/<N>.<type>.rst, wait for CI,
# then mark ready and merge if every check passes. Exit 1 on CI failure, 2 on a stuck job, 3 on other errors.
set -u
KEY=$1; TITLE=$2; BODY=$3; CTYPE=$4; CTEXT=$5
W=~/Git/glue-solar-$KEY
cd "$W" || exit 3
push() { for i in 1 2 3 4 5 6; do git push -q --force-with-lease -u origin "$KEY" 2>/dev/null && return 0; sleep 30; done; return 1; }
git fetch -q origin && git rebase -q origin/main || { git rebase --abort; echo "REBASE CONFLICT on $KEY"; exit 3; }
push || { echo "push failed"; exit 3; }
N=$(gh pr list --head "$KEY" --state open --json number --jq '.[0].number // empty')
if [ -n "$N" ]; then echo "PR #$N (open already)"; else
URL=$(gh pr create --draft --base main --head "$KEY" --title "$TITLE" --body-file "$BODY") || { echo "pr create failed"; exit 3; }
N=${URL##*/}; echo "PR #$N $URL"; fi
if [ ! -e "changelog/$N.$CTYPE.rst" ]; then
printf '%s\n' "$CTEXT" > "changelog/$N.$CTYPE.rst"
git add "changelog/$N.$CTYPE.rst" && git commit -q -m "Add changelog entry for #$N" && push || { echo "changelog push failed"; exit 3; }
fi
HEAD=$(git rev-parse HEAD)
sleep 120
while true; do
  out=$(gh pr checks "$N" 2>/dev/null)
  if [ -n "$out" ] && ! echo "$out" | grep -qE "pending|queued|in_progress"; then break; fi
  for job in $(echo "$out" | grep -E "pending" | grep -o 'job/[0-9]*' | cut -d/ -f2); do
    st=$(gh api repos/glue-viz/glue-solar/actions/jobs/$job --jq '([.steps[]|select(.status=="in_progress")|.name][0] // "")+"|"+(.started_at // "")' 2>/dev/null)
    step=${st%%|*}; started=${st#*|}
    if [ "$step" = "Install dependencies" ] && [ -n "$started" ]; then
      age=$(( $(date -u +%s) - $(date -j -u -f "%Y-%m-%dT%H:%M:%SZ" "$started" +%s) ))
      [ $age -gt 900 ] && { echo "STUCK job $job for ${age}s"; echo "$out" | grep -v skipping; exit 2; }
    fi
  done
  sleep 60
done
echo "$out" | grep -v skipping
if echo "$out" | grep -v -E "codecov|readthedocs|skipping" | grep -qE "\sfail"; then echo "CI FAILED on #$N"; exit 1; fi
gh pr ready "$N" >/dev/null && gh pr merge "$N" --merge --match-head-commit "$HEAD" || { echo "merge failed"; exit 3; }
sleep 5; git fetch -q origin
git merge-base --is-ancestor "$HEAD" origin/main && echo "MERGED #$N into main at $(git rev-parse --short origin/main)"
