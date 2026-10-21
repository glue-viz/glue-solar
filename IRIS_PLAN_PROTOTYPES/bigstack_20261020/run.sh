#!/bin/bash
# run.sh LOGNAME ARGS...: prof.py ARGS in the iris-plan-qt6-802-f058 env, glue-solar main, offscreen, isolated HOME.
W=/tmp/claude-1000/-home-nabil-Git-glue-solar/b6e23444-55cd-4e14-8c5a-719e6cf98359/scratchpad/bigstack
name=$1; shift
mkdir -p "$W/home" "$W/xdg_config" "$W/xdg_cache"  # remove them after: rm -r home xdg_config xdg_cache
cd "$W" && uptime > "$W/$name.log" && env PYTHONPATH=/home/nabil/Git/glue-solar-main:$W QT_QPA_PLATFORM=offscreen MPLBACKEND=agg \
  HOME=$W/home XDG_CONFIG_HOME=$W/xdg_config XDG_CACHE_HOME=$W/xdg_cache \
  ${PYSPY:+$W/wheels/py_spy-0.4.2.data/scripts/py-spy record $PYSPY --} \
  /home/nabil/.local/share/mamba/envs/iris-plan-qt6-802-f058/bin/python "$W/prof.py" "$@" >> "$W/$name.log" 2>&1
echo "exit $?" >> "$W/$name.log"; uptime >> "$W/$name.log"
grep -E '^PROF|^TIMER|^exit|load average|Error' "$W/$name.log"
