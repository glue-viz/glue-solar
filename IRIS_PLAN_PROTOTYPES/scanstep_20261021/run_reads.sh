#!/bin/bash
# run_reads.sh CUBE...: reads.py on 12 scans of each cube, each after the load average is under 8 (gate.sh)
set -u
cd "$(dirname "$0")"
. ./gate.sh
for cube in "$@"; do
  gate "reads $cube"
  ./run.sh reads.py "$cube" 12 > "results/reads_$cube.log" 2>&1
  echo "reads $cube exit $?"
done
