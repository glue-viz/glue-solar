import warnings; warnings.simplefilter("ignore")
import numpy as np, astropy.units as u
from irispy.data.test import get_test_data_filenames
from irispy.io import read_files
from irispy.utils.moments import calculate_moments
from glue_solar.sources.loaders.iris import image_data, raster_data, _cube_data
fs = [str(f) for f in get_test_data_filenames() if str(f).endswith(".fits")]
sji = image_data([f for f in fs if "sns" in f and "SJI_1400" in f][0])
r14 = sorted(f for f in fs if "20140329" in f and "raster" in f)
[ras] = raster_data(r14[:1], ["C II 1336"])
[stack] = raster_data(r14[:2], ["C II 1336"], stack=True)
cube = read_files(r14[:1], spectral_windows=["Mg II k 2796"], uncertainty=False, memmap=False)["Mg II k 2796"][0]
mom = _cube_data(calculate_moments(cube)["velocity"], "vel")
for name, d in (("SJI gwcs", sji), ("raster -TAB", ras), ("stack compound", stack), ("moment map 2D", mom)):
    w = d.coords._wcs
    print(f"== {name}: inner {type(w).__module__}.{type(w).__name__}")
    print("  names", w.world_axis_names, "| types", w.world_axis_physical_types, "| units", w.world_axis_units)
    print("  glue labels", [c.label for c in d.world_component_ids])
    print("  components", [(k, i, g if isinstance(g, str) else f"<callable {type(g).__name__}>") for k, i, g in w.world_axis_object_components])
    for k, v in w.world_axis_object_classes.items():
        cls, args, kwargs, *rest = v
        print("  class", k, cls.__name__, args, {kk: (vv if kk == "unit" else type(vv).__name__) for kk, vv in kwargs.items()}, "rest", len(rest))
