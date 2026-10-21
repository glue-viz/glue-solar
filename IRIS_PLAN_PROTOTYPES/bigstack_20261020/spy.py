"""
Inclusive shares of a py-spy raw (collapsed) profile, split by prof.py's ``load`` and ``restore`` phases, and its threads.

    python spy.py RAW
"""

import re
import sys
from collections import Counter

# (label, frame pattern): a sample counts toward each label whose pattern is in one of its frames
TARGETS = [
    ("read_files (irispy, per file)", r"^read_files \(irispy/io/utils"),
    ("  _create_tabular_wcs", r"^_create_tabular_wcs "),
    ("  SGMeta", r"^__init__ \(irispy/meta.py"),
    ("  fits.open", r"^fitsopen "),
    ("  _memmap_fill_mask (dask)", r"^_memmap_fill_mask "),
    ("  SpectrogramCube", r"^__init__ \(irispy/spectrograph.py"),
    ("  get_body_heliographic_stonyhurst", r"^get_body_heliographic_stonyhurst "),
    ("  _primary_header", r"^_primary_header "),
    ("  astropy Time", r"^__(init|new)__ \(astropy/time/core.py"),
    ("  SkyCoord", r"^__init__ \(astropy/coordinates/sky_coordinate.py"),
    ("_window_scaling (glue-solar, per file)", r"^_window_scaling "),
    ("stack_times (glue-solar)", r"^stack_times "),
    ("stack_wcs / _dataset / exposure / time", r"^(stack_wcs|_dataset|_add_exposure|_add_time) "),
    ("RawComponent._sample (color limits)", r"^_sample \(glue_solar"),
    ("image_data (SJI)", r"^image_data "),
    ("restore: viewers", r"^new_data_viewer "),
    ("restore: draws", r"^draw \(glue_qt/viewers/matplotlib/widget"),
    ("astropy config reads", r"^(__get__|__call__) \(astropy/config/configuration"),
    ("gc", r"^<gc>|^gc_collect"),
]


def main(path):
    phases = {"load": Counter(), "restore": Counter()}
    totals, threads = Counter(), Counter()
    for line in open(path, errors="replace"):
        stack, _, count = line.rstrip().rpartition(" ")
        frames = [re.sub(r"/home/nabil/[^ ]*?site-packages/|/home/nabil/Git/glue-solar-main/", "", frame)
                  for frame in stack.split(";")]
        count = int(count)
        threads[frames[0]] += count
        phase = next((p for p in phases if any(f.startswith(f"{p} (") and "prof.py" in f for f in frames)), None)
        if phase is None:
            continue
        totals[phase] += count
        for label, pattern in TARGETS:
            if any(re.search(pattern, frame) for frame in frames):
                phases[phase][label] += count
    print("threads:", dict(threads.most_common(5)))
    for phase, counter in phases.items():
        if totals[phase]:
            print(f"\n{phase}: {totals[phase]} samples")
            for label, _ in TARGETS:
                if counter[label]:
                    print(f"  {100 * counter[label] / totals[phase]:5.1f}%  {label}")


if __name__ == "__main__":
    main(sys.argv[1])
