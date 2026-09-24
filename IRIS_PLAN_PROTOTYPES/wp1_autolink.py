"""WP1 proof: with the coherent _GlueWCS, glue ape14-wcs-autolink links every IRIS pair; stock 1.27.0 links none and does not crash."""
import warnings; warnings.simplefilter("ignore")
import glue; print("glue from", glue.__file__, "metadata version", glue.__version__)
from glue.core import DataCollection
from glue.plugins.wcs_autolinking.wcs_autolinking import wcs_autolink, WCSLink, IncompatibleWCS
from irispy.data.test import get_test_data_filenames
from irispy.io import read_files
from irispy.utils.moments import calculate_moments
from glue_solar.sources.loaders.iris import image_data, raster_data, _cube_data
files = list(get_test_data_filenames())
sns = lambda name: next(p for p in files if p.name.endswith(name) and p.parent.name == "sns")
def fresh(name):  # a Data can join one DataCollection only, so rebuild each pair
    if name == "SJI<->raster":
        return image_data(sns("SJI_1400_t000.fits")), raster_data([sns("raster_t000_r00000.fits")], ["Si IV 1403"])[0]
    scans = sorted(p for p in files if "3860258481_raster_t000_r0000" in p.name)[:2]
    scan0, scan1 = raster_data(scans, ["Mg II k 2796"])
    if name == "raster<->raster":
        return scan0, scan1
    cube = read_files(scans[:1], spectral_windows=["Mg II k 2796"], memmap=False, uncertainty=False)["Mg II k 2796"][0]
    maps = calculate_moments(cube)
    vel, inten = _cube_data(maps["velocity"], "velocity"), _cube_data(maps["intensity"], "intensity")
    return (scan0, vel) if name == "raster3D<->map2D" else (vel, inten)
for name in ("SJI<->raster", "raster<->raster", "raster3D<->map2D", "map2D<->map2D"):
    a, b = fresh(name)
    links = wcs_autolink(DataCollection([a, b]))
    try:
        WCSLink(a, b); direct = "WCSLink ok"
    except IncompatibleWCS as e: direct = "IncompatibleWCS"
    except Exception as e: direct = f"{type(e).__name__}: {str(e)[:50]}"
    cids = f" cids {[c.label for c in links[0].cids1]} <-> {[c.label for c in links[0].cids2]}" if links else ""
    print(f"  {name:18s} autolink={len(links)} direct={direct}{cids}")
