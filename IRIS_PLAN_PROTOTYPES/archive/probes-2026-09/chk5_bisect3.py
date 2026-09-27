import sys, warnings; warnings.simplefilter("ignore")
order = sys.argv[1]
if order == "fits-first":
    from astropy.io import fits
from irispy.data.test import get_test_data_filenames
from glue_solar.sources.loaders.iris import raster_data
import irispy.io.spectrograph as sg
orig = sg._nuv_t_obs_from_source_filenames
def probe(source_data, exposure_times, auxiliary_times, *, filename):
    print("  source_data:", type(source_data).__name__, getattr(source_data, "shape", None), "dtype:", getattr(source_data, "dtype", None) if not hasattr(source_data, "names") else source_data.names, "| n exp:", len(exposure_times), flush=True)
    return orig(source_data, exposure_times, auxiliary_times, filename=filename)
sg._nuv_t_obs_from_source_filenames = probe
files = {p.name: str(p) for p in get_test_data_filenames()}
f21 = files["iris_l2_20210905_001833_3620258102_raster_t000_r00000.fits"]
try:
    d = raster_data([f21], ["Mg II k 2796"])[0]; print(order, "OK", d.shape)
except Exception as e:
    print(order, "FAIL", str(e)[:70])
