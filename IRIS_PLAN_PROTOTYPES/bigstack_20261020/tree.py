"""
Print a cProfile's call tree under a function, each child's time as called from its parent (a deeper level scaled by
the parent's share of that function's calls, as gprof2dot does), and its share of the root.

    python tree.py PROF ROOT_SUBSTRING [DEPTH] [MIN_SHARE]
"""

import pstats
import sys

SITE = "/home/nabil/.local/share/mamba/envs/iris-plan-qt6-802-f058/lib/python3.13/site-packages/"


def name(key):
    file, line, func = key
    return f"{file.replace(SITE, '').replace('/home/nabil/Git/glue-solar-main/', '')}:{line}({func})"


def main(path, root, depth=4, minimum=0.01):
    stats = pstats.Stats(path).stats
    children = {}
    for key, (*_, callers) in stats.items():
        for caller, (cc, nc, tt, ct) in callers.items():
            children.setdefault(caller, []).append((key, nc, ct))
    top = max((key for key in stats if root in name(key)), key=lambda key: stats[key][3])
    total = stats[top][3]
    print(f"{total:8.2f} s  100.0%  {name(top)}")

    def walk(key, scale, level, seen):
        if level >= depth:
            return
        rows = sorted(children.get(key, ()), key=lambda row: -row[2])
        for child, calls, ct in rows:
            seconds = ct * scale
            if seconds / total < minimum or child in seen:
                continue
            print(f"{seconds:8.2f} s {100 * seconds / total:6.1f}%  {'  ' * level}{name(child)}  [{calls} calls]")
            own = stats[child][3]
            walk(child, seconds / own if own else 0, level + 1, seen | {child})

    walk(top, 1.0, 1, {top})


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], *(int(sys.argv[3]),) if len(sys.argv) > 3 else (),
         *(float(sys.argv[4]),) if len(sys.argv) > 4 else ())
