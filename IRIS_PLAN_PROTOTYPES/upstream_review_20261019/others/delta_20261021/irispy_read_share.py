"""wp10-l-big-stack-load: where irispy's read_files spends a raster file's read (one tabular WCS and one SGMeta per
window), on the installed irispy or a source tree.

Run: python -I irispy_read_share.py RASTER_DIR N [IRISPY_SOURCE_DIR]
"""

import cProfile
import pstats
import sys
import time
import warnings
from pathlib import Path

if len(sys.argv) > 3:
    sys.path.insert(0, sys.argv[3])
warnings.simplefilter("ignore")

import irispy
from irispy.io import read_files

files = sorted(Path(sys.argv[1]).glob("*raster*.fits"))[: int(sys.argv[2])]
print("irispy", irispy.__file__.rsplit("/", 3)[-3], irispy.__version__, "| files:", len(files))
read_files([files[0]], memmap=True, uncertainty=False)  # warm: imports, ephemeris
profile = cProfile.Profile()
t = time.perf_counter()
profile.enable()
for path in files[1:]:
    read_files([path], memmap=True, uncertainty=False)
profile.disable()
per_file = (time.perf_counter() - t) / (len(files) - 1) * 1e3
stats = pstats.Stats(profile)
cum = {name: ct for (_, _, name), (_, _, _, ct, _) in stats.stats.items()}
own = {}
for (path, _, name), (_, _, _, ct, _) in stats.stats.items():
    if name in ("_create_tabular_wcs", "__init__") and ("spectrograph.py" in path or "meta.py" in path):
        own[(Path(path).name, name)] = max(own.get((Path(path).name, name), 0), ct)
total = sum(tt for (*_,), (_, _, tt, _, _) in stats.stats.items())
print(f"{per_file:.0f} ms a file under cProfile;"
      f" _create_tabular_wcs {cum.get('_create_tabular_wcs', 0) / total:.0%},"
      f" SGMeta/BaseMeta __init__ {own.get(('meta.py', '__init__'), 0) / total:.0%},"
      f" astropy config __get__ {max(ct for (p, _, n), (_, _, _, ct, _) in stats.stats.items() if 'astropy/config' in p and n == '__get__') / total:.0%}")
