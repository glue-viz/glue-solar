import warnings; warnings.filterwarnings("ignore")
import numpy as np, astropy.units as u
from irispy.io import read_files
from irispy.data.test import get_test_data_filenames
from glue_solar.sources.loaders.iris import image_data
import importlib.util, sys
spec = importlib.util.spec_from_file_location("wp7_sdo2_defs", "/private/tmp/claude-501/-Users-nabil-Git-glue-solar/72764293-8e82-4502-aeff-9f6c3d248202/scratchpad/wp7_sdo2.py")
# reuse fov_polygon without executing the script body: copy the function source
src = open(spec.origin).read(); start = src.index("def fov_polygon"); end = src.index("fs = get_test_data_filenames()")
ns = {}; exec("import numpy as np\nHPC = 'custom:pos.helioprojective.'\n" + src[start:end], ns)
f = [f for f in get_test_data_filenames() if f.name.endswith("3620258102_SJI_1400_t000.fits")][0]
data = image_data(str(f)); lon, lat, _ = ns["fov_polygon"](data)
m0 = read_files(f, memmap=False, uncertainty=False).to_maps(0)
ny, nx = m0.data.shape
c = m0.wcs.pixel_to_world([0, nx - 1, nx - 1, 0], [0, 0, ny - 1, ny - 1])
print("fov_polygon lon:", np.round(lon, 3), "| to_maps(0) Tx:", np.round(c.Tx.to_value(u.arcsec), 3))
print("fov_polygon lat:", np.round(lat, 3), "| to_maps(0) Ty:", np.round(c.Ty.to_value(u.arcsec), 3))
print("match:", np.allclose(lon, c.Tx.to_value(u.arcsec), atol=1e-6), np.allclose(lat, c.Ty.to_value(u.arcsec), atol=1e-6))
