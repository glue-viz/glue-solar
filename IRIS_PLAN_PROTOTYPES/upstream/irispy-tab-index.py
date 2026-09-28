"""
irispy-tab-index: the raster -TAB WCS has a 1..N step index vector (PS3_2 = 'RASTER'), which wcslib
searches linearly, so pixel_to_world costs O(step) (irispy <= 0.9.0; fix: LM-SAL/irispy#177).

    env HOME="$(mktemp -d)" ~/mamba/envs/iris-plan/bin/python IRIS_PLAN_PROTOTYPES/upstream/irispy-tab-index.py

Needs ~/DATA/IRIS 20130902_163935 OBSID 4000255147 (1600-exposure sit-and-stare).
"""

import os
import pwd
import time
from pathlib import Path

import numpy as np

import irispy
from irispy.io import read_files

DATA = Path(pwd.getpwuid(os.getuid()).pw_dir) / "DATA" / "IRIS"
path = next(DATA.glob("*_4000255147_raster/*_raster_t000_r00000.fits"))
cube = read_files(path, spectral_windows=["Si IV 1403"], memmap=True)["Si IV 1403"][0]
steps = cube.data.shape[0]
print("irispy", irispy.__version__, "from", Path(irispy.__file__).parent, "| PS3_2 in header:", "PS3_2" in cube._fits_wcs.to_header())
wavelength, slit = np.linspace(0, cube.data.shape[2] - 1, 1000), np.full(1000, 200.0)
for step in (0, 400, 800, steps - 1):
    start = time.perf_counter()
    for _ in range(20):
        cube.wcs.pixel_to_world_values(wavelength, slit, np.full(1000, float(step)))
    print(f"step {step:5d}: {(time.perf_counter() - start) / 20 * 1e3:.3f} ms per 1000 points")
