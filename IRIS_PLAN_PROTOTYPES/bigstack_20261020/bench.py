"""
Per-unit costs of the pieces of a raster file's read, without a profiler: the first N files of FOLDER/raster.

    python bench.py FOLDER [N]
"""

import os
import sys
import time
from pathlib import Path

import numpy as np

from astropy.io import fits
from astropy.time import Time
from sunpy.coordinates.ephemeris import get_body_heliographic_stonyhurst

from irispy.io import read_files
from irispy.io.spectrograph import _create_tabular_wcs
from irispy.meta import SGMeta

from glue_solar.sources.loaders.iris import _window_scaling
from glue_solar.sources.loaders.stack_spectrograms import stack_times

files = sorted(Path(sys.argv[1], "raster").glob("*raster*.fits"))[: int(sys.argv[2]) if len(sys.argv) > 2 else 50]
print("loadavg", os.getloadavg(), "files", len(files))


def per(label, function, items, unit="file"):
    start = time.perf_counter()
    out = [function(item) for item in items]
    ms = 1e3 * (time.perf_counter() - start) / len(items)
    print(f"{label:58s} {ms:7.2f} ms a {unit}")
    return out


per("fits.open + every header (memmap, unscaled)", lambda p: [h.header for h in fits.open(p, memmap=True, do_not_scale_image_data=True)], files)
per("glue-solar _window_scaling (its own fits.open)", _window_scaling, files)
reads = per("irispy read_files([path], memmap=True), 9 windows", lambda p: read_files([p], memmap=True, uncertainty=False), files)
opened = [fits.open(p, memmap=True, do_not_scale_image_data=True) for p in files]
for h in opened:
    [x.header for x in h]
windows = [opened[0][0].header[f"TDESC{i}"] for i in range(1, 10)]
per("SGMeta(primary header, window) x9", lambda h: [SGMeta(h[0].header, w, data_shape=h[i + 1].data.shape) for i, w in enumerate(windows)], opened)
per("SGMeta x9 from one dict of the header", lambda h: (lambda d: [SGMeta(d, w) for w in windows])(dict(h[0].header)), opened)
per("dict(primary header) once", lambda h: dict(h[0].header), opened)
per("_create_tabular_wcs x9", lambda h: [_create_tabular_wcs(h[i].header, h[-2], date_obs=h[0].header["DATE_OBS"]) for i in range(1, 10)], opened)
per("get_body_heliographic_stonyhurst('Earth', DATE_OBS)", lambda h: get_body_heliographic_stonyhurst("Earth", Time(h[0].header["DATE_OBS"])), opened)
cubes = [read["Si IV 1403"][0] for read in reads]
per("stack_times of one window's scans", lambda c: stack_times([c]), cubes, unit="scan")
per("cube.axis_world_coords('time', wcs=extra_coords)", lambda c: c.axis_world_coords("time", wcs=c.extra_coords), cubes, unit="scan")
per("time straight from the table coordinate", lambda c: c.extra_coords["time"].table.utc.to_value("datetime64"), cubes, unit="scan")
assert all((stack_times([c]) == c.extra_coords["time"].table.utc.to_value("datetime64")[None]).all() for c in cubes[:5])
