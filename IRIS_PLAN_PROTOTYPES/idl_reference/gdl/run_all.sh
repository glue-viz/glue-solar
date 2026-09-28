#!/bin/sh
# Run the four IRIS IDL routines under GDL. Usage: run_all.sh <gdl-binary> <outdir-tag>
set -u
R=$(cd "$(dirname "$0")" && pwd)
G=$1; TAG=$2
mkdir -p "$R/run_$TAG/out" && cd "$R/run_$TAG" || exit 1
export SSW=$R/sswfull HARNESS=$R/harness IRIS_DATA_LOCAL=$R/iris_data HOME=$(mktemp -d)
for cmd in drv_mg drv_wavecorr drv_burst "drv_sjiburst, '2013-09-02 17:00', 'obs4000255147'"; do
  echo "== $cmd"
  perl -e 'alarm 1500; exec @ARGV' "$G" -quiet -e "!path='$R/harness:'+!path & $cmd" < /dev/null 2>&1 | grep -E 'elapsed|^%|Array\[|images with' | grep -v 'Compiled module'
done
ls -la out
