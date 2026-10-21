#!/bin/bash
# run.sh SCRIPT ARGS...: a script of this folder with glue-solar main, an isolated HOME and offscreen Qt, from this folder
set -u
S=$(cd "$(dirname "$0")" && pwd)
home=$(mktemp -d "$S/home.XXXXXX")
mkdir -p "$home/config" "$home/cache"
cd "$S" && env HOME="$home" XDG_CONFIG_HOME="$home/config" XDG_CACHE_HOME="$home/cache" QT_QPA_PLATFORM=offscreen \
  MPLBACKEND=agg PYTHONPATH=/home/nabil/Git/glue-solar-main OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  /home/nabil/.local/share/mamba/envs/iris-plan-qt6-802-f058/bin/python "$S/$@"
status=$?
rm -rf "$home"
exit $status
