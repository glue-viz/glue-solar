"""
irispy-v34-flip: V34 rasters (STEPS_AV < -0.01) flip their data and times but not their mask or
per-step metadata (irispy <= 0.9.0; fix: LM-SAL/irispy#176).

Run with any irispy env; needs ~/DATA/IRIS (20250328_225628 OBSID 3400109360):

    env HOME="$(mktemp -d)" ~/mamba/envs/iris-plan/bin/python IRIS_PLAN_PROTOTYPES/upstream/irispy-v34-flip.py

On 0.9.0 every scan reports mask mismatches and a meta/time offset of about the raster duration (587 s);
with the fix the mismatch count is 0 and the offset is half an exposure (4.0 s).
"""

import os
import pwd
from pathlib import Path

import numpy as np

import irispy
from irispy.io import read_files

DATA = Path(pwd.getpwuid(os.getuid()).pw_dir) / "DATA" / "IRIS"
files = sorted(DATA.glob("*_3400109360_raster/*_raster_t000_r*.fits"))
print("irispy", irispy.__version__, "from", Path(irispy.__file__).parent)
for path in files:
    cube = read_files(path, spectral_windows=["Si IV 1403"], memmap=False, uncertainty=False)["Si IV 1403"][0]
    mismatch = int((cube.mask != (cube.data == -200)).sum())
    times = cube.axis_world_coords("time", wcs=cube.extra_coords)[0]
    offset = abs((times[0] - cube.meta["auxiliary times"][0]).to_value("s"))
    print(f"{path.name}: STEPS_AV {cube.meta['STEPS_AV']:.3f}  mask != (data == -200) at {mismatch:,d} samples;"
          f"  |time[0] - meta 'auxiliary times'[0]| = {offset:.1f} s")
