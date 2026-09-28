import sys, numpy as np
sys.argv = ["x"]
import proto
from astropy.io import fits
for f in ["~/DATA/IRIS/2dd2d12db374b3466aa27a65bec235d3-iris_l2_20130902_163935_4000255147_raster/iris_l2_20130902_163935_4000255147_raster_t000_r00000.fits",
          "~/DATA/IRIS/0598beef2a051b4f371a4b09e439c4e4-iris_l2_20130902_182935_4000005156_raster/iris_l2_20130902_182935_4000005156_raster_t000_r00000.fits"]:
    with fits.open(f, memmap=True, do_not_scale_image_data=True) as h:
        hw = h[6].header
        lam = hw["CRVAL1"] + (np.arange(hw["NAXIS1"]) + 1 - hw["CRPIX1"]) * hw["CDELT1"]
        # continuum-ish/quiet: take median over whole window of per-pixel mean DN/s in +-50 km/s
        r = proto.burst_check(f)
    # recompute intensity median quickly
    with fits.open(f, memmap=True, do_not_scale_image_data=True) as h:
        hw = h[6].header
        lam = hw["CRVAL1"] + (np.arange(hw["NAXIS1"]) + 1 - hw["CRPIX1"]) * hw["CDELT1"]
        v = proto.C_KMS*(lam-1402.77)/1402.77; k = np.flatnonzero(abs(v) <= 50)
        c = proto._scaled(h[6], np.s_[:, :, k[0]:k[-1]+1]); c[c <= -10] = np.nan
        c /= h[-2].data[:, h[-2].header["EXPTIMEF"]][:, None, None]
        m = np.nanmean(c, axis=-1); s = np.nansum(c, axis=-1) * hw["CDELT1"]
    print(f[-45:], "CDELT1", hw["CDELT1"], "nbins", k.size, "median mean-per-bin DN/s %.2f" % np.nanmedian(m), "median sum*dlam DN/s*A %.3f" % np.nanmedian(s), "p99 mean %.1f" % np.nanpercentile(m, 99))
