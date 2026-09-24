"""Q4/Q5: can calculate_moments run from the glue Data alone (no cube handle prerequisite)?"""
import warnings, numpy as np, astropy.units as u; warnings.simplefilter("ignore")
from irispy.data.test import get_test_data_filenames
from irispy.spectrograph import SpectrogramCube
from irispy.utils.moments import calculate_moments
from irispy.utils.constants import DN_UNIT
from glue_solar.sources.loaders.iris import raster_data, _cube_data
fs = [str(f) for f in get_test_data_filenames() if str(f).endswith(".fits")]
[d] = raster_data([f for f in fs if "20140329" in f and "r00000" in f], ["Mg II k 2796"])
cid = d.main_components[0]; print("components:", [c.label for c in d.main_components], "units:", d.get_component(cid).units)
with u.add_enabled_units([DN_UNIT["FUV"], DN_UNIT["NUV"]]):
    unit = u.Unit(d.get_component(cid).units)
    cube = SpectrogramCube(d[cid], d.coords._wcs, None, unit, d.meta, mask=d[f"{cid.label} mask"].astype(bool))
    print("rewrapped:", cube.dimensions if hasattr(cube, "dimensions") else cube.data.shape, "wavelength_axis", cube.wavelength_axis, "rest", cube.meta.rest_wavelength)
    out = calculate_moments(cube, rest_wavelength=2791.3 * u.AA, wings=0.5 * u.AA, min_intensity=50)
print("moments keys:", list(out.keys()))
v = _cube_data(out["velocity"], "vel"); print("ingest:", v.shape, [c.label for c in v.world_component_ids], "median v", np.nanmedian(v["vel"]))
