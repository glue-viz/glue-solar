import glob, warnings, traceback, io, contextlib
import numpy as np
import astropy.units as u
import matplotlib.pyplot as plt
import irispy
from irispy.io import read_files, fits_info
from irispy.io.sji import read_sji_lvl2
print(irispy.__file__)
B = "<scratch>/features/itn32-sot/"
fg = B + "small/x/sot_l2_20150830_070953_3603259402_20150830100400_Gband4305_FG.fits"
mg = B + "small/x/sot_l2_20160108_191211_3680100932_20160108181400_TFNaI5896_MG.fits"
sp = B + "small/x/sotsp_l2_20160108_191211_3680100932_20160108_185006_blapp_index.fits"
sp2 = B + "sotsp/sotsp_l2_20150805_110921_3860109380_20150805_105734_blapp_index.fits"
def tryit(label, fn):
    try:
        r = fn(); print(f"OK   {label}: {str(r)[:160]!s}")
    except Exception as e:
        print(f"FAIL {label}: {type(e).__name__}: {str(e)[:200]}")
allx = sorted(glob.glob(B + "small/x/*.fits"))
coll = read_files(allx)
print("keys", list(coll.keys()))
print({k: (type(v).__name__, str(v.unit)) for k, v in coll.items()})
for name, f in (("fg", fg), ("mg", mg), ("sp", sp)):
    c = read_sji_lvl2(f)
    print("==", name, c.shape, c.unit)
    tryit("str(cube)", lambda: str(c).replace("\n", " | "))
    tryit("str(meta)", lambda: str(c.meta).replace("\n", " | "))
    for p in ["observing_mode_id", "spectral_range", "temporal_cadence", "date_reference", "date_end", "observing_campaign_start",
              "rest_wavelength", "distance_to_sun", "sun_angular_radius", "observer_radial_velocity", "detector_band", "spectral_band", "exposure_time", "satellite_rotation", "processing_level"]:
        tryit(f"meta.{p}", lambda p=p: getattr(c.meta, p))
    tryit("p2w last", lambda: c.wcs.pixel_to_world(0, 0, c.shape[0]-1))
    w = c.wcs.pixel_to_world(10, 10, 0)
    tryit("w2p frame0", lambda: c.wcs.world_to_pixel(*w))
    tryit("cube[0]", lambda: c[0].shape)
    tryit("cube[0].plot", lambda: (c[0].plot(), plt.close("all")))
    tryit("cube.plot", lambda: (c.plot(), plt.close("all")))
    tryit("to_maps(0).plot", lambda: (c.to_maps(0).plot(), plt.close("all")))
    tryit("to_maps(0) unit/wave/instr", lambda: (c.to_maps(0).unit, c.to_maps(0).wavelength, c.to_maps(0).meta.get("bunit"), c.to_maps(0).instrument, c.to_maps(0).observatory))
    tryit("cube[0].to_maps()", lambda: c[0].to_maps())
    tryit("crop world", lambda: c.crop(c.wcs.pixel_to_world(5, 5, 0), c.wcs.pixel_to_world(30, 30, c.shape[0]-1)).shape)
    tryit("nan frac", lambda: float(np.isnan(c.data).mean()))
    tryit("memmap unit", lambda: read_sji_lvl2(f, memmap=True).unit)
    tryit("uncertainty", lambda: read_sji_lvl2(f, uncertainty=True).uncertainty)
    buf = io.StringIO()
    def fi():
        with contextlib.redirect_stdout(buf):
            fits_info(f)
        return buf.getvalue()[:100]
    tryit("fits_info", fi)
# collisions across OBS
c2 = read_files([sp, sp2])
print("SP two-OBS keys", list(c2.keys()) if hasattr(c2, "keys") else type(c2))
# mixed IRIS + SOT
irisfiles = sorted(glob.glob("irispy/data/test/*SJI*.fits*")) + sorted(glob.glob("irispy/data/test/**/*SJI*.fits*", recursive=True))
print("iris test sji", irisfiles[:4])
if irisfiles:
    c3 = read_files(irisfiles[:2] + [fg, mg])
    print("mixed keys", list(c3.keys()))
