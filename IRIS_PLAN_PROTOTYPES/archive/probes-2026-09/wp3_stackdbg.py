import os, sys, glob, warnings
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen"); os.environ.setdefault("MPLBACKEND", "agg"); warnings.simplefilter("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, wp3_impl
from irispy.data.test import get_test_data_filenames
from glue.core import DataCollection
from glue.core.state import GlueSerializer, GlueUnSerializer
from glue_solar.sources.loaders.iris import raster_data
files = [str(f) for f in get_test_data_filenames()]
rdir = os.path.dirname([f for f in files if "3860258481_raster_t000_r00000" in f][0]); rfiles = sorted(glob.glob(rdir + "/*.fits"))[:3]
stk = raster_data(rfiles, stack=True)[0]; dc = DataCollection([stk])
s = GlueSerializer(dc).dumps(); d2 = GlueUnSerializer.loads(s).object("__main__")[0]
print("names", stk.coords.world_axis_names, "->", d2.coords.world_axis_names)
print("units", stk.coords.world_axis_units, "->", d2.coords.world_axis_units)
print("comps", [c.label for c in stk.world_component_ids], "->", [c.label for c in d2.world_component_ids])
grid = np.meshgrid(*[np.arange(n) for n in stk.shape[::-1]], indexing="ij")
a = stk.coords.pixel_to_world_values(*grid); b = d2.coords.pixel_to_world_values(*grid)
print("p2w maxdiff per axis", [float(np.nanmax(np.abs(x - y))) for x, y in zip(a, b)], "nans", [int(np.isnan(x).sum()) for x in a], [int(np.isnan(y).sum()) for y in b])
g2 = [x + 0.37 for x in grid]; a = stk.coords.pixel_to_world_values(*g2); b = d2.coords.pixel_to_world_values(*g2)
print("offset p2w maxdiff per axis", [float(np.nanmax(np.abs(x - y))) for x, y in zip(a, b)], "nans", [int(np.isnan(x).sum()) for x in a], [int(np.isnan(y).sum()) for y in b])
world = stk.coords.pixel_to_world_values(*grid)
print("w2p orig-vs-restored per axis", [float(np.nanmax(np.abs(x - y))) for x, y in zip(stk.coords.world_to_pixel_values(*world), d2.coords.world_to_pixel_values(*world))])
print("closure per axis", [float(np.nanmax(np.abs(x - y))) for x, y in zip(grid, d2.coords.world_to_pixel_values(*world))])
print("inner", type(d2.coords._wcs).__name__, [type(p).__name__ for p in d2.coords._wcs._wcs], "scan wcs pixel_shape", d2.coords._wcs._wcs[1]._wcs.pixel_shape, "orig", stk.coords._wcs._wcs[1]._wcs.pixel_shape)
