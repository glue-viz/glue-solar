#!/bin/bash
# run_survey.sh OUT CUBE...: every part of sst_perf_survey.py, each cube in a fresh process, then the linked pair of the
# first two cubes; the SURVEY lines go to OUT/survey.jsonl, the rest of the output to OUT/<part>-<n>.log. Paste
# OUT/survey.jsonl back. Uses the python on PATH, with glue-solar main installed.
set -u
OUT=$1; shift
mkdir -p "$OUT"; OUT=$(cd "$OUT" && pwd)
HERE=$(cd "$(dirname "$0")" && pwd)
run() {  # part, log name, cubes
  local part=$1 name=$2; shift 2
  local home; home=$(mktemp -d)
  (cd "$home" && env HOME="$home" QT_QPA_PLATFORM=offscreen MPLBACKEND=agg python "$HERE/sst_perf_survey.py" "$part" "$@") \
    > "$OUT/$name.log" 2>&1
  echo "$part $name exit $?"
  grep '^SURVEY ' "$OUT/$name.log" | sed 's/^SURVEY //' >> "$OUT/survey.jsonl"
  rm -rf "$home"
}
n=0
for cube in "$@"; do
  n=$((n + 1))
  run file "file-$n" "$cube"
  run quicklook "quicklook-$n" "$cube"
done
[ $# -ge 2 ] && run link link "$1" "$2"
echo "done: $OUT/survey.jsonl"
