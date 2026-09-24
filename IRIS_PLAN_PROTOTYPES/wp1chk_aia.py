import warnings; warnings.simplefilter("ignore")
import glue; print("glue from", glue.__file__)
import sunpy.data.test, sunpy.map
from glue.core import DataCollection
from glue.plugins.wcs_autolinking.wcs_autolinking import wcs_autolink, WCSLink
from irispy.data.test import get_test_data_filenames
from glue_solar.sources.loaders.iris import raster_data, image_data
from glue_solar.sources.maps import _parse_sunpy_map
files = list(get_test_data_filenames())
sns = lambda n: next(p for p in files if p.name.endswith(n) and p.parent.name == "sns")
for name in ("raster", "sji"):
    aia = _parse_sunpy_map(sunpy.map.Map(sunpy.data.test.get_test_filepath("aia_171_level1.fits")), "aia")
    d = raster_data([sns("raster_t000_r00000.fits")], ["Si IV 1403"])[0] if name == "raster" else image_data(sns("SJI_1400_t000.fits"))
    links = wcs_autolink(DataCollection([d, aia]))
    try:
        WCSLink(d, aia); direct = "ok"
    except Exception as e:
        direct = f"{type(e).__name__}: {str(e)[:80]}"
    print(f"{name}<->AIA(astropy WCS, deg): autolink={len(links)} direct={direct}", f"cids {[c.label for c in links[0].cids1]} <-> {[c.label for c in links[0].cids2]}" if links else "")
