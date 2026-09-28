import glob, sys, numpy as np
sys.path.insert(0, ".")
import idlfaithful as I
import irispy.utils.response as R
from astropy.time import Time
def a(t):
    r = R.get_latest_response(Time(t)); lam = r["LAMBDA"].to_value("nm"); return r["AREA_SG"][0, np.argmin(abs(lam - 140.277))]
for obs in sys.argv[1:]:
    f = sorted(glob.glob(f"~/DATA/IRIS/*{obs}_raster/*_r00000.fits"))[0]
    d, exp, t, ybin, nb, iw, h0 = I.load(f)
    thr = 500 * a(h0["DATE_OBS"]) / a("2013-10-22T21:00")
    mean, med, hit, lab, ng = I.idl_check(d, exp, thr, ybin)
    good = mean > -200
    print(obs, "win", [h0[f"TDESC{i}"] for i in iw], "SUMSPTRF", h0["SUMSPTRF"], "nbins", nb, "ybin", ybin, "thr %.1f" % (thr * ybin),
          "npix", int(hit.sum()), "groups", ng, "median mean %.2f p99 %.1f max %.1f" % (np.median(mean[good]), np.percentile(mean[good], 99), mean[good].max()))
