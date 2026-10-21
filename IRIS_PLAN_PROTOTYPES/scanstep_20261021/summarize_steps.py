"""summarize_steps.py: medians over the scans of results/step_*.jsonl, by cube, run and pass."""
import glob
import json
import statistics
from collections import defaultdict

steps, summaries = defaultdict(list), {}
for path in sorted(glob.glob("results/step_*.jsonl")):
    for line in open(path):
        d = json.loads(line)
        if "summary" in d:
            summaries[(d["cube"], d["run"])] = d
        else:
            steps[(d["cube"], d["run"], d["pass_"])].append(d)
med = statistics.median
print(f"{'cube':5} {'run':32} {'pass':6} {'n':>3} {'step ms':>8} {'p90':>6} {'slit frb':>8} {'slit draw':>9} {'read MB':>7}"
      f" {'majflt':>6} {'prefetched':>10} {'rss GB':>6} {'anon GB':>7} {'max load':>8} {'prefetch ms':>11}")
for (cube, run, label), ds in steps.items():
    ms = sorted(d["step_ms"] for d in ds)
    print(f"{cube:5} {run:32} {label:6} {len(ds):3} {med(ms):8.1f} {ms[int(0.9 * (len(ms) - 1))]:6.0f} "
          f"{med(d['slit_frb_ms'] for d in ds):8.1f} {med(d['slit_draw_ms'] for d in ds):9.1f} "
          f"{med(d['read_mb'] for d in ds):7.0f} {med(d['majflt'] for d in ds):6.0f} "
          f"{sum(d['prefetched'] for d in ds):4}/{len(ds):<5} {ds[-1]['rss_gb']:6.2f} {ds[-1]['anon_gb']:7.3f} "
          f"{max(d.get('step_load', [99])[0] for d in ds):8.1f} {med(summaries[(cube, run)]['prefetch_ms_all'] or [0]):11.1f}")
