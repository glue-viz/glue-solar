"""WP1: derived SJI pixel x for world (lon,lat,t) links, with glue-core 1.27.0's world2pixel_single_axis vs glue_solar.glue_patches."""
import warnings; warnings.simplefilter("ignore")
import importlib.util, numpy as np
import glue.core.coordinate_helpers as ch, glue.core.component_link as cl
import glue_solar  # applies glue_patches
from glue.core import Data, DataCollection
from glue.core.link_helpers import LinkSame
from irispy.data.test import get_test_data_filenames
from glue_solar.sources.loaders.iris import image_data
spec = importlib.util.spec_from_file_location("ch_orig", ch.__file__); orig = importlib.util.module_from_spec(spec); spec.loader.exec_module(orig)
load = lambda: image_data(next(p for p in get_test_data_filenames() if p.name.endswith("SJI_1400_t000.fits") and p.parent.name == "sns"))
sji = load()
frames = np.arange(sji.shape[0], dtype=float)
lon, lat, t = sji.coords.pixel_to_world_values(10.0, 10.0, frames)  # the same SJI pixel (10, 10) at every exposure
cid = lambda label: next(c for c in sji.world_component_ids if c.label == label)
for label, fn in (("glue-core 1.27.0 original", orig.world2pixel_single_axis), ("glue_solar.glue_patches", glue_solar.glue_patches.world2pixel_single_axis)):
    ch.world2pixel_single_axis = cl.world2pixel_single_axis = fn
    sji = load(); points = Data(label="points", lon=lon, lat=lat, t=t); dc = DataCollection([sji, points])
    dc.add_link([LinkSame(points.id["lon"], cid("Helioprojective Longitude")), LinkSame(points.id["lat"], cid("Helioprojective Latitude")), LinkSame(points.id["t"], cid("Time (Utc)"))])
    x = points[sji.pixel_component_ids[2]]
    print(f"{label:28s} derived SJI x at frames 0/30/61: {np.round(x[[0, 30, 61]], 2).tolist()}  (truth: 10.0 everywhere) | max |x-10| = {np.abs(x - 10).max():.2e}")
print("axis_correlation_matrix untouched:", sji.coords.axis_correlation_matrix.astype(int).tolist())
