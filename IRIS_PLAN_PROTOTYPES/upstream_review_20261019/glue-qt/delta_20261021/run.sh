#!/bin/sh
# run.sh SCRIPT ARGS...: a probe with the iris-plan env, a scratch HOME, offscreen Qt, Agg (python -I, cwd the scratch HOME)
F=$(cd "$(dirname "$0")" && pwd)
H=$F/home
mkdir -p $H/xdg/config $H/xdg/cache $H/xdg/data $H/xdg/runtime && chmod 700 $H/xdg/runtime
cd $H && exec env HOME=$H XDG_CONFIG_HOME=$H/xdg/config XDG_CACHE_HOME=$H/xdg/cache XDG_DATA_HOME=$H/xdg/data \
  XDG_RUNTIME_DIR=$H/xdg/runtime QT_QPA_PLATFORM=offscreen MPLBACKEND=agg timeout 300 \
  /home/nabil/.local/share/mamba/envs/iris-plan-qt6-802-f058/bin/python -I "$@"
