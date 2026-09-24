import os, glob, warnings
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen"); os.environ.setdefault("MPLBACKEND", "agg"); warnings.simplefilter("ignore")
import numpy as np, astropy.units as u, sunpy.map
from astropy.coordinates import SkyCoord
from sunpy.coordinates import frames
from irispy.data.test import get_test_data_filenames
from glue.core import Data, DataCollection
from glue.core.state import GlueSerializer, GlueUnSerializer, _save_wcs, _load_wcs
from glue_solar.sources.loaders.iris import image_data, raster_data
from glue_solar.sources.maps import read_sunpy_map
files = [str(f) for f in get_test_data_filenames()]
sji = [f for f in files if "sns/" in f and "SJI_1330" in f][0]
rdir = os.path.dirname([f for f in files if "3860258481_raster_t000_r00000" in f][0]); rfiles = sorted(glob.glob(rdir + "/*.fits"))[:3]
def save(label, ds):
    try:
        s = GlueSerializer(DataCollection(ds)).dumps(); print(f"[{label}] SAVE OK {len(s) // 1024} KB"); return s
    except Exception as e:
        print(f"[{label}] SAVE FAIL {type(e).__name__}: {str(e)[:110]}")
print("== as loaded (branch iris-observation-browser, stock glue-core 1.27.0) ==")
save("SJI", [image_data(sji)]); save("raster", raster_data(rfiles[:1])[:1]); save("stack", raster_data(rfiles, stack=True)[:1])
d = image_data(sji); d.coords = None; save("SJI coords=None", [d])
print("== stock @saver(WCS) applied to the bare irispy -TAB WCS ==")
w = raster_data(rfiles[:1])[0].coords._wcs
rec = _save_wcs(w, None); print("_save_wcs OK: header chars", len(rec["header"]), "| PS2_0 in header:", "PS2_0" in rec["header"])
try: _load_wcs(rec, None); print("_load_wcs OK?!")
except Exception as e: print("_load_wcs FAIL", type(e).__name__ + ":", str(e)[:100])
print("== Data whose coords is that bare -TAB WCS (no _GlueWCS, clean meta, no cmap) ==")
d0 = raster_data(rfiles[:1])[0]; d = Data(label="bare", coords=w); d.add_component(d0[d0.main_components[0]], "x")
s = save("bare -TAB Data", [d])
try: GlueUnSerializer.loads(s).object("__main__"); print("reload OK?!")
except Exception as e: print("reload FAIL", type(e).__name__ + ":", str(e)[:100])
print("== sunpy Map through glue_solar.sources.maps (main branch code, unrelated to IRIS) ==")
coord = SkyCoord(0 * u.arcsec, 0 * u.arcsec, obstime="2020-01-01", observer="earth", frame=frames.Helioprojective)
hdr = sunpy.map.make_fitswcs_header(np.zeros((16, 16)), coord, scale=[2, 2] * u.arcsec / u.pix, instrument="AIA", wavelength=171 * u.angstrom, telescope="SDO")
save("sunpy map", [read_sunpy_map(sunpy.map.Map(np.zeros((16, 16)), hdr))])
