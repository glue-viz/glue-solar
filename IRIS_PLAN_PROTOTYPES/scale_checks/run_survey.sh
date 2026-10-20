#!/bin/bash
# run_survey.sh OUT CUBE...: every part of sst_perf_survey.py, each cube in a fresh process, then the linked pair of the
# first two cubes; the SURVEY lines go to OUT/survey.jsonl, the rest of the output to OUT/<part>-<n>.log. Paste
# OUT/survey.jsonl back. Uses the python on PATH, with glue-solar main installed.
# run_survey.sh OUT iris FOLDER OBSID...: the iris part for each IRIS observation in FOLDER instead.
set -u
if [ $# -lt 2 ]; then
  echo "usage: run_survey.sh OUT CUBE.fits [CUBE.fits ...]   (OUT: a new folder for the results)" >&2
  echo "       run_survey.sh OUT iris FOLDER OBSID [OBSID ...]" >&2
  exit 2
fi
command -v python >/dev/null || { echo "no python on PATH: activate the env with glue-solar main first" >&2; exit 2; }
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
if [ "$1" = iris ]; then
  folder=$2; shift 2
  for obsid in "$@"; do run iris "iris-$obsid" "$folder" "$obsid"; done
  echo "done: $OUT/survey.jsonl"
  exit 0
fi
n=0
for cube in "$@"; do
  n=$((n + 1))
  run file "file-$n" "$cube"
  run quicklook "quicklook-$n" "$cube"
done
[ $# -ge 2 ] && run link link "$1" "$2"
echo "done: $OUT/survey.jsonl"
