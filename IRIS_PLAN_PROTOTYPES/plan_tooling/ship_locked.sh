#!/bin/bash
# ship_locked.sh ARGS...: ship.sh ARGS, one at a time (a mkdir lock, released on exit).
D=${PLAN_SCRATCH:?set PLAN_SCRATCH to the session scratchpad}; T=$(cd "$(dirname "$0")" && pwd)
until mkdir "$D/ship.lock" 2>/dev/null; do sleep 20; done
trap 'rmdir "$D/ship.lock"' EXIT
# a ship.sh started outside the lock (before this wrapper existed) may still run
while pgrep -f 'ship[.]sh wp|ship[.]sh pv|ship[.]sh measure' | grep -v $$ >/dev/null; do sleep 20; done
"$T/ship.sh" "$@"
