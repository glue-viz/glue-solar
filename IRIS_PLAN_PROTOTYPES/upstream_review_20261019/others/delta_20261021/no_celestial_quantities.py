"""Row 5 (#359): with `has_celestial = False`, as sst.py's _TabularWCS sets it, astropy gives a WCS's angles as
Quantities, not a SkyCoord, so tools._sky builds the SkyCoord from the physical types.

Run: python -I no_celestial_quantities.py
"""

import astropy
import sunpy.coordinates  # noqa: F401  registers the helioprojective frame, as glue-solar has it
from astropy.wcs import WCS
from astropy.wcs.wcsapi import HighLevelWCSWrapper

header = {"CTYPE1": "HPLN-TAN", "CTYPE2": "HPLT-TAN", "CUNIT1": "arcsec", "CUNIT2": "arcsec",
          "CDELT1": 0.06, "CDELT2": 0.06, "CRPIX1": 50, "CRPIX2": 50, "CRVAL1": -300, "CRVAL2": 200, "DATE-OBS": "2024-07-05T08:00:00", "DSUN_OBS": 1.5e11, "HGLN_OBS": 0, "HGLT_OBS": 0}


class NoCelestial(WCS):
    has_celestial = False


print("astropy", astropy.__version__)
for cls in (WCS, NoCelestial):
    world = HighLevelWCSWrapper(cls(header)).pixel_to_world(10, 20)
    print(cls.__name__, [type(w).__name__ for w in (world if isinstance(world, list) else [world])],
          list(cls(header).world_axis_physical_types))
