"""Which warnings do the WP7 recipes emit? (pytest.ini turns warnings into errors)"""
import warnings, os
warnings.simplefilter("always")
import numpy as np, astropy.units as u
from astropy.coordinates import SkyCoord
import sunpy.map, sunpy.data.test
from sunpy.map.header_helper import make_fitswcs_header
from sunpy.coordinates import Helioprojective, propagate_with_solar_surface
from sunpy.timeseries import TimeSeries
from irispy.data.test import get_test_data_filenames
from glue_solar.sources.loaders.iris import image_data, _GlueWCS
from glue_solar.sources.maps import _parse_sunpy_map
seen = []
def show(message, category, filename, lineno, file=None, line=None):
    seen.append(f"{category.__name__}: {str(message)[:110]}  [{os.path.basename(filename)}:{lineno}]")
warnings.showwarning = show
print("== TimeSeries ==")
ts = TimeSeries(sunpy.data.test.get_test_filepath("sci_xrsf-l2-avg1m_g16_d20210101_truncated.nc"), source="xrs").truncate("2021-01-01T22:30:00", "2021-01-01T23:10:00")
df = ts.to_dataframe()
print("\n".join(sorted(set(seen))) or "(none)"); seen.clear()
print("== synthetic AIA map + save/load ==")
t0 = "2021-09-05T00:18:33.640"
ref = SkyCoord(-53 * u.arcsec, -400 * u.arcsec, frame=Helioprojective(obstime=t0, observer="earth"))
hdr = make_fitswcs_header(np.zeros((800, 800)), ref, scale=[0.6, 0.6] * u.arcsec / u.pix, instrument="AIA", telescope="SDO/AIA", observatory="SDO", wavelength=171 * u.AA, exposure=2 * u.s)
aia = sunpy.map.Map(np.random.default_rng(0).random((800, 800)), hdr)
p = os.path.join(os.environ["HOME"], "warn_aia.fits"); aia.save(p, overwrite=True); aia = sunpy.map.Map(p)
print("\n".join(sorted(set(seen))) or "(none)"); seen.clear()
print("== IRIS load + corners + transform + submap + Data ==")
f = [f for f in get_test_data_filenames() if f.name.endswith("3620258102_SJI_1400_t000.fits")][0]
sji = image_data(str(f))
print("\n".join(sorted(set(seen))) or "(none)"); seen.clear()
corners = SkyCoord([-56.4, -50.4, -50.4, -56.3] * u.arcsec, [-403, -403, -396.5, -396.5] * u.arcsec, frame=Helioprojective(obstime=t0, observer="earth"))
with propagate_with_solar_surface():
    c = corners.transform_to(aia.coordinate_frame)
bl = SkyCoord(c.Tx.min() - 100 * u.arcsec, c.Ty.min() - 100 * u.arcsec, frame=aia.coordinate_frame)
tr = SkyCoord(c.Tx.max() + 100 * u.arcsec, c.Ty.max() + 100 * u.arcsec, frame=aia.coordinate_frame)
ctx = aia.submap(bl, top_right=tr)
gd = _parse_sunpy_map(ctx, "ctx"); gd.coords = _GlueWCS(ctx.wcs)
px, py = ctx.wcs.world_to_pixel(c)
print("\n".join(sorted(set(seen))) or "(none)"); seen.clear()
