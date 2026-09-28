"""
irispy-slit-units: the SJI "slit x/y position" extra coordinates hold SLTPX1IX/SLTPX2IX pixel values but are
tagged arcsec, as is "ophaseix" (orbital phase) (irispy <= 0.9.0; fix: LM-SAL/irispy#178).

    env HOME="$(mktemp -d)" ~/mamba/envs/iris-plan/bin/python IRIS_PLAN_PROTOTYPES/upstream/irispy-slit-units.py
"""

from pathlib import Path

from astropy.io import fits

import irispy
from irispy.data.test import get_test_data_filenames
from irispy.io import read_files

path = next(p for p in get_test_data_filenames() if "sns" in str(p) and "SJI_1400" in p.name)
cube = read_files(path, memmap=False, uncertainty=False)
with fits.open(path) as hdulist:
    aux, columns, nx = hdulist[1].data, hdulist[1].header, hdulist[0].header["NAXIS1"]
print("irispy", irispy.__version__, "from", Path(irispy.__file__).parent, "|", path.name, "NAXIS1", nx)
units = dict(zip(cube.extra_coords.wcs.world_axis_names, cube.extra_coords.wcs.world_axis_units, strict=True))
for name, column in (("slit x position", "SLTPX1IX"), ("slit y position", "SLTPX2IX"), ("ophaseix", "OPHASEIX")):
    values = aux[:, columns[column]]
    print(f"{name:>16}: {column} from {values.min():.4g} to {values.max():.4g}, tagged {units[name]!r}")
