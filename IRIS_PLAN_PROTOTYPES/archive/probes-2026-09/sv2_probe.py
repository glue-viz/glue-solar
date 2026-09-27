import warnings, os, inspect; warnings.filterwarnings("ignore")
os.environ.setdefault("QT_QPA_PLATFORM","offscreen"); os.environ.setdefault("MPLBACKEND","agg")
import numpy as np, glue, irispy, astropy
print("glue", glue.__version__, glue.__file__); print("irispy", irispy.__version__, "astropy", astropy.__version__)
from irispy.data.test import get_test_data_filenames
from irispy.io import read_files
from glue.core import Data, DataCollection
from glue.plugins.wcs_autolinking.wcs_autolinking import wcs_autolink, WCSLink
from glue_solar.sources.loaders.iris import iris_data, raster_data, _cube_data
files = [str(f) for f in get_test_data_filenames()]
print("test files:", sorted({os.path.basename(f) for f in files}))
sji_f = [f for f in files if "3620258102_SJI_1400" in f][0]
ras_f = [f for f in files if "3620258102_raster" in f][0]
sji_cube = read_files(sji_f, memmap=False, uncertainty=False)
print("SJI wcs:", type(sji_cube.wcs), "names:", sji_cube.wcs.low_level_wcs.world_axis_names, "ptypes:", sji_cube.wcs.low_level_wcs.world_axis_physical_types)
print("SJI extra_coords:", list(sji_cube.extra_coords.keys()) if sji_cube.extra_coords else None, "mask None:", sji_cube.mask is None)
sji = iris_data(sji_f)
print("SJI Data comps:", [c.label for c in sji.components])
print("SJI coords names:", sji.coords.world_axis_names, sji.coords.world_axis_units)
ras_all = iris_data(ras_f); ras = [d for d in ras_all if d.label.startswith("Mg_II_k")][0]
print("raster labels:", [d.label for d in ras_all])
print("raster comps:", [c.label for c in ras.components])
print("raster coords names:", ras.coords.world_axis_names, ras.coords.world_axis_units, "ctype", ras.coords._wcs.wcs.ctype)
print("raster meta Quantity keys:", [k for k,v in dict(ras.meta).items() if hasattr(v,'unit')])
# autolink with installed glue
dc = DataCollection([sji, ras]); print("wcs_autolink (installed) links:", len(wcs_autolink(dc)))
try: WCSLink(sji, ras); print("WCSLink OK")
except Exception as e: print("WCSLink:", type(e).__name__, str(e)[:100])
# raw irispy WCS objects
a = Data(label="a"); a.coords = sji_cube.wcs; a.add_component(sji_cube.data, "v")
rc = read_files(ras_f, memmap=False, uncertainty=False)["Mg II k 2796"][0]
b = Data(label="b"); b.coords = rc.wcs; b.add_component(rc.data, "v")
for order,(x,y) in {"sji,ras":(a,b),"ras,sji":(b,a)}.items():
    try: print("raw autolink", order, "links:", len(wcs_autolink(DataCollection([x,y]))))
    except Exception as e: print("raw autolink", order, "RAISED", type(e).__name__, str(e)[:100])
print("raster has_celestial:", rc.wcs.has_celestial)
# sessions
from glue.core.state import GlueSerializer
for d in (sji, ras):
    try: GlueSerializer(DataCollection([d])).dumps(); print("serialize", d.label, "OK")
    except Exception as e: print("serialize", d.label, "FAIL", type(e).__name__, str(e)[:120])
d2 = _cube_data(rc, "r"); d2.meta = {k:v for k,v in dict(rc.meta).items() if not hasattr(v,'unit')}
try: GlueSerializer(DataCollection([d2])).dumps(); print("serialize raster w/o Quantity meta OK")
except Exception as e: print("serialize raster w/o Quantity meta FAIL", type(e).__name__, str(e)[:120])
# stack
sfiles = sorted(f for f in files if "3860258481_raster" in f)
coll = read_files(sfiles, memmap=False, uncertainty=False); w = list(coll.keys())[0]; s0 = coll[w][0]
print("stack input n:", len(sfiles), "dtype", s0.data.dtype, "mask cnt", int(s0.mask.sum()), "masked vals", np.unique(s0.data[np.asarray(s0.mask)])[:3])
st = raster_data(sfiles, [w], stack=True)[0]; arr = st.get_component(st.label).data
print("stack:", st.label, arr.dtype, type(arr).__name__, "nan in scan0:", int(np.isnan(arr[0]).sum()), "names:", st.coords.world_axis_names, "Time:", st.get_component("Time").data.dtype, st.get_component("Time").data.shape)
# moments
from irispy.utils.moments import calculate_moments
print("calculate_moments sig:", inspect.signature(calculate_moments))
print("rest_wavelength:", rc.meta.rest_wavelength)
out = calculate_moments(rc); print("keys:", list(out.keys()), type(out).__name__)
for k,c in out.items():
    d = _cube_data(c, k); print("  ", k, d.shape, d.get_component(k).units, d.coords.world_axis_names)
