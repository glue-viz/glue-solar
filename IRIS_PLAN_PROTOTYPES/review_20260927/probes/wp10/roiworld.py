"""Raster ROI propagated to a full-res SJI frame: pixel-cid ROI (needs the -TAB inverse) vs the same ROI as a world-cid polygon (link_hpc, no inverse)."""
import sys, time, warnings
sys.path[:0] = ["~/Git/glue-solar/IRIS_PLAN_PROTOTYPES/wp1", "<session-scratch>/tools"]
import qs_isolate  # noqa
import numpy as np
warnings.simplefilter("ignore")
from glob import glob
from glue.core import DataCollection
from glue.core.roi import PolygonalROI, RectangularROI
from glue.core.subset import RoiSubsetState
import glue_solar.sources.loaders.iris as L
print("LOADER", L.__file__)
sji = L.image_data("~/DATA/IRIS/c844c41797b93a28fbad181337864edd-iris_l2_20130902_182935_4000005156_SJI_2796_t000_deconvolved.fits.gz")
ras = L.raster_data(sorted(glob("~/DATA/IRIS/0598beef2a051b4f371a4b09e439c4e4-iris_l2_20130902_182935_4000005156_raster/*r00000.fits")), ["Si IV 1403"])[0]
dc = DataCollection([sji, ras]); dc.add_link(L.link_hpc(dc))
pt = list(ras.coords.world_axis_physical_types)[::-1]
lon = ras.world_component_ids[pt.index("custom:pos.helioprojective.lon")]
lat = ras.world_component_ids[pt.index("custom:pos.helioprojective.lat")]
x0, x1, y0, y1 = 10, 40, 200, 500  # raster step and slit pixel ranges
pix = RoiSubsetState(ras.pixel_component_ids[0], ras.pixel_component_ids[1], RectangularROI(x0, x1, y0, y1))
# same rectangle as a world polygon: walk its edges in raster pixels, 20 points per edge
e = np.linspace(0, 1, 20)
sx = np.concatenate([x0 + (x1 - x0) * e, np.full(20, x1), x1 - (x1 - x0) * e, np.full(20, x0)])
sy = np.concatenate([np.full(20, y0), y0 + (y1 - y0) * e, np.full(20, y1), y1 - (y1 - y0) * e])
w = ras.coords.pixel_to_world_values(np.zeros_like(sx), sy, sx)  # pixel order: wave, slit, step
wpt = list(ras.coords.world_axis_physical_types)
world = RoiSubsetState(lon, lat, PolygonalROI(w[wpt.index("custom:pos.helioprojective.lon")], w[wpt.index("custom:pos.helioprojective.lat")]))
view = (5, slice(None), slice(None))
for name, st in (("world-cid polygon", world), ("pixel-cid rectangle", pix)):
    t = time.perf_counter(); m = sji.get_mask(st, view=view); dt = time.perf_counter() - t
    print(f"{name}: {dt:.2f}s per {m.size}-px SJI frame, {m.sum()} px selected", flush=True)
    if name.startswith("world"):
        mw = m
print("agreement", (mw == m).mean(), "differing px", int((mw != m).sum()))
