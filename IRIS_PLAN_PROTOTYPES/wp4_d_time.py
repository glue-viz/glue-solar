"""(d) datetime64 'Time' component for SJI cubes from the gWCS time axis."""
import warnings; warnings.simplefilter("ignore")
import numpy as np
from irispy.io import read_files
from irispy.data.test import get_test_data_filenames
from glue_solar.sources.loaders.iris import image_data, raster_data
from wp4_common import add_time, cube_times
fs = [str(f) for f in get_test_data_filenames()]
sji_path = [f for f in fs if "sns" in f and "SJI_1400" in f][0]
cube = read_files(sji_path, memmap=False, uncertainty=False)
print("SJI extra_coords has 'time':", "time" in cube.extra_coords.keys(), "| wcs physical types:", cube.wcs.world_axis_physical_types)
t = cube.axis_world_coords("time")[0]
print("axis_world_coords('time') ->", type(t).__name__, t.shape, "| datetime64:", cube_times(cube)[:2], cube_times(cube).dtype)
sji = image_data(sji_path); print("main_components before:", len(sji.main_components)); add_time(sji, cube)
print("main_components after:", len(sji.main_components), "| Time shape", sji["Time"].shape, sji["Time"].dtype, "| Time[:, 0, 0] == Time[:, -1, -1]:", np.array_equal(sji["Time"][:, 0, 0], sji["Time"][:, -1, -1]))
# cross-check with the world axis 'Time (Utc)' (seconds since the gWCS reference epoch)
secs = sji[sji.world_component_ids[0]][:, 0, 0]
ref = sji["Time"][0, 0, 0] - np.timedelta64(int(round(secs[0] * 1e9)), "ns")
print("reference epoch:", ref, "| max |Time - (epoch + Time (Utc))| =", np.abs((sji["Time"][:, 0, 0] - ref) / np.timedelta64(1, "s") - secs).max(), "s")
# raster path unchanged
ras = raster_data([[f for f in fs if "sns" in f and "raster_t000" in f][0]], windows=["Si IV 1403"])[0]
print("raster Time still from extra coords:", ras["Time"][:2, 0, 0], "| span SJI", sji["Time"][0,0,0], "->", sji["Time"][-1,0,0], "| raster", ras["Time"][0,0,0], "->", ras["Time"][-1,0,0])
