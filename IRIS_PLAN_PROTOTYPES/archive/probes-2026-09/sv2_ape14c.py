import warnings; warnings.filterwarnings("ignore")
import numpy as np
from irispy.data.test import get_test_data_filenames
from glue.core import DataCollection
from glue.plugins.wcs_autolinking.wcs_autolinking import wcs_autolink
from glue_solar.sources.loaders.iris import iris_data
files = [str(f) for f in get_test_data_filenames()]
sji = iris_data([f for f in files if "3620258102_SJI_1400" in f][0])
ras = [d for d in iris_data([f for f in files if "3620258102_raster" in f][0]) if d.label.startswith("Mg_II_k")][0]
dc = DataCollection([sji, ras]); dc.add_link(wcs_autolink(dc)[0])
rz = sji[ras.pixel_component_ids[0]][0]; ry = sji[ras.pixel_component_ids[1]][0]   # raster (step, slit) index for each SJI pixel at t=0
ok = np.isfinite(rz) & np.isfinite(ry); iy, ix = np.argwhere(ok)[len(np.argwhere(ok))//2]
lon_s, lat_s, _ = sji.coords.pixel_to_world_values(ix, iy, 0)
_, lat_r, lon_r = ras.coords.pixel_to_world_values(0, ry[iy, ix], rz[iy, ix])
print(f"SJI px (x={ix},y={iy}) -> raster (step={rz[iy,ix]:.2f}, slit={ry[iy,ix]:.2f}); world SJI=({lon_s:.3f},{lat_s:.3f}) raster=({lon_r:.3f},{lat_r:.3f}) arcsec; max diff {max(abs(lon_s-lon_r),abs(lat_s-lat_r)):.2e}")
sx = ras[sji.pixel_component_ids[2]]; sy = ras[sji.pixel_component_ids[1]]
print("reverse direction finite fraction:", float(np.isfinite(sx).mean()), "sample raster[90,20,0] -> sji (x,y)=", float(sx[90,20,0]), float(sy[90,20,0]))
