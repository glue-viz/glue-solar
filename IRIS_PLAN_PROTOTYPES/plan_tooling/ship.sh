#!/bin/bash
# ship.sh KEY TITLE BODYFILE CTYPE CTEXT SUMMARY: pr_cycle, then, only if merged, record in the plan and remove the worktree.
set -u
KEY=$1; TITLE=$2; BODY=$3; CTYPE=$4; CTEXT=$5; SUMMARY=$6
D=${PLAN_SCRATCH:?set PLAN_SCRATCH to the session scratchpad}; T=$(cd "$(dirname "$0")" && pwd)
R=/Users/nabil/Git/glue-solar
L=$D/items/$KEY/cycle.log; mkdir -p "$D/items/$KEY"
C=pr_cycle.sh; [ "$CTYPE" = none ] && C=pr_cycle_nocl.sh  # CTYPE none: no changelog entry (tooling)
"$T/$C" "$KEY" "$TITLE" "$BODY" "$CTYPE" "$CTEXT" > "$L" 2>&1
code=$?
grep -v "	pass	" "$L"
if [ $code -ne 0 ] || ! grep -q "^MERGED" "$L"; then echo "NOT MERGED ($code): nothing recorded or removed"; exit 1; fi
[ "$(git -C $R branch --show-current)" = plan ] || { echo "plan checkout not on plan"; exit 1; }
git -C $R fetch -q origin
N=$(grep -o "PR #[0-9]*" "$L" | head -1 | tr -dc 0-9)
python3 "$T/plan_record.py" "$KEY" "$N" "$(git -C $R rev-parse --short origin/main)" "$SUMMARY" || exit 1
git -C $R add IRIS_GLUE_GAP_PLAN.md && git -C $R commit -q -m "Record #$N and drop $KEY" || exit 1
for i in 1 2 3 4 5 6; do git -C $R push -q origin plan 2>/dev/null && break; sleep 30; done
git -C $R fetch -q origin
[ "$(git -C $R rev-parse origin/plan)" = "$(git -C $R rev-parse plan)" ] || { echo "plan push failed"; exit 1; }
git -C $R worktree remove "$R-$KEY" && git -C $R branch -D "$KEY" >/dev/null && echo "RECORDED #$N, worktree removed"
