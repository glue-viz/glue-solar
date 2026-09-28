"""
irispy-crpix: the SJI/AIA gWCS applies the 1-based FITS CRPIX to 0-based pixels, so it is one pixel off
a FITS WCS built from the header and each frame's pointing (irispy <= 0.9.0; fix: LM-SAL/irispy#178).

    env HOME="$(mktemp -d)" ~/mamba/envs/iris-plan/bin/python IRIS_PLAN_PROTOTYPES/upstream/irispy-crpix.py

Needs ~/DATA/IRIS: the 4000255147 SJI 1400, the 3860608353 rolled SJI 2832 and a 3640107442 AIA 171 cutout.
"""

import os
import pwd
from pathlib import Path

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS

import irispy
from irispy.io import read_files

DATA = Path(pwd.getpwuid(os.getuid()).pw_dir) / "DATA" / "IRIS"
print("irispy", irispy.__version__, "from", Path(irispy.__file__).parent)
for pattern in ("*4000255147_SJI_1400*", "*3860608353_SJI_2832*", "*3640107442_SDO/aia_l2_*_171.fits"):
    path = next(DATA.glob(pattern))
    cube = read_files(path, memmap=False, uncertainty=False)
    with fits.open(path) as hdulist:
        header, aux, columns = hdulist[0].header, hdulist[1].data, hdulist[1].header
    ny, nx = cube.data.shape[1:]
    x, y = np.array([0, nx - 1, (nx - 1) / 2]), np.array([0, ny - 1, (ny - 1) / 2])
    worst = 0.0
    for frame in (0, cube.data.shape[0] - 1):
        wcs = WCS(naxis=2)
        wcs.wcs.ctype, wcs.wcs.cunit = ["HPLN-TAN", "HPLT-TAN"], ["arcsec", "arcsec"]
        wcs.wcs.crpix, wcs.wcs.cdelt = [header["CRPIX1"], header["CRPIX2"]], [header["CDELT1"], header["CDELT2"]]
        wcs.wcs.crval = [aux[frame, columns["XCENIX"]], aux[frame, columns["YCENIX"]]]
        wcs.wcs.pc = [[aux[frame, columns[f"PC{i}_{j}IX"]] for j in (1, 2)] for i in (1, 2)]
        lon, lat = (v * 3600 for v in wcs.pixel_to_world_values(x, y))
        world = cube.wcs.pixel_to_world_values(x, y, np.full_like(x, frame))
        dlon = (world[0] - lon + 648000) % 1296000 - 648000
        worst = max(worst, float(np.max(np.hypot(dlon, world[1] - lat))))
    print(f"{path.name}: gWCS vs FITS pointing, worst of corners and centre: {worst:.4f} arcsec "
          f"({worst / abs(header['CDELT1']):.2f} px)")
