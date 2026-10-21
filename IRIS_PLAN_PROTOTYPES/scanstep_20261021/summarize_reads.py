"""summarize_reads.py: medians over the scans of results/reads_*.jsonl, by cube, pattern and method."""
import glob, json, statistics
from collections import defaultdict
rows = defaultdict(list)
for path in sorted(glob.glob("results/reads_*.jsonl")):
    for line in open(path):
        d = json.loads(line)
        if "method" in d:
            rows[(d["cube"], d["pattern"], d["method"], d["values"])].append(d)
med = lambda xs: statistics.median(xs)
print(f"{'cube':5} {'pattern':6} {'method':22} {'n':>3} {'cold ms':>8} {'MB':>6} {'faults':>7} {'warm ms':>8} {'repeat ms':>9}"
      f" {'max load':>8}")
for (cube, pattern, method, values), ds in rows.items():
    c = lambda s, k: med([d[s][k] for d in ds])
    print(f"{cube:5} {pattern:6} {method:22} {len(ds):3} {c('cold','ms'):8.1f} {c('cold','read_mb'):6.0f} "
          f"{c('cold','majflt'):7.0f} {c('warm','ms'):8.2f} {c('repeat','ms'):9.2f} "
          f"{max(d.get('cold_load', 99) for d in ds):8.1f}   ({values} values)")
