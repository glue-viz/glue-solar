#!/bin/bash
# run_steps.sh CUBE...: step.py's matrix, one fresh process a run, each after the load average is under 8 (gate.sh);
# logs to results/logs/, uptime before each run to results/uptime.log (each result line has the load averages too)
set -u
cd "$(dirname "$0")"
. ./gate.sh
mkdir -p results/logs
for cube in "$@"; do
  while read -r variant state wait; do
    name="$cube-$variant-$state-$wait"
    for try in 1 2 3; do  # step.py exits 3 when a cold step saw a load average of 8 or more: again
      gate "$name"
      ./run.sh step.py "$cube" "$variant" "$state" "$wait" > "results/logs/$name.log" 2>&1
      status=$?
      echo "$name try $try exit $status"
      [ $status -ne 3 ] && break
    done
  done <<'RUNS'
today cold 300
today warm 300
today cold 0
pread cold 300
pread warm 300
hints cold 300
hints warm 300
hints cold 0
pread+hints cold 300
pread+hints warm 300
prefetch cold done
prefetch cold 300
prefetch cold 0
prefetch+band cold done
prefetch+band cold 300
prefetch+band cold 100
prefetch+band cold 0
readahead cold 300
prefetch+band+hints cold 0
RUNS
done
