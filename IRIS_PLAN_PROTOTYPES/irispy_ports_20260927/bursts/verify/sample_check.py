import sys, glob, numpy as np
sys.path.insert(0, ".")
import idlfaithful as I
import irispy.utils.response as R
from astropy.time import Time
from astropy.io import fits
def a(t):
    r = R.get_latest_response(Time(t)); lam = r["LAMBDA"].to_value("nm"); return r["AREA_SG"][0, np.argmin(abs(lam - 140.277))]
f = "~/Library/Application Support/sunpy/iris_l2_20211001_060925_3683602040_raster_t000_r00000.fits"
h0 = fits.getheader(f)
print(h0["OBS_DESC"], "SUMSPAT", h0["SUMSPAT"], "SUMSPTRF", h0["SUMSPTRF"], "STEPS_AV", h0["STEPS_AV"], [(h0[f"TDESC{i}"], h0[f"TWMIN{i}"], h0[f"TWMAX{i}"]) for i in range(1, h0["NWIN"]+1)])
d, exp, t, ybin, nb, iw, h0 = I.load(f)
thr = 500 * a(h0["DATE_OBS"]) / a("2013-10-22T21:00")
mean, med, hit, lab, ng = I.idl_check(d, exp, thr, ybin)
good = mean > -200
print("nbins", nb, "thr", thr * ybin, "npix", int(hit.sum()), "groups", ng, "max mean", mean[good].max())
