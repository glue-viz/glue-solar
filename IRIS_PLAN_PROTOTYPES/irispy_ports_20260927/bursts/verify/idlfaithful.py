"""IDL-faithful re-implementation of iris_burst_check numerics (quirks kept) to compare against the report's prototype."""
import sys, numpy as np
from astropy.io import fits
from astropy.time import Time, TimeDelta
from scipy import ndimage
C = 2.997924580e5
def load(f, lref=1402.77, vmax=50.0):
    with fits.open(f, memmap=True, do_not_scale_image_data=True) as h:
        h0 = h[0].header
        iw = [i for i in range(1, h0["NWIN"] + 1) if h0[f"TWMIN{i}"] <= lref <= h0[f"TWMAX{i}"]]
        hw = h[iw[0]].header
        lam = hw["CRVAL1"] + (np.arange(hw["NAXIS1"]) + 1 - hw["CRPIX1"]) * hw["CDELT1"]
        v = (lam - lref) / lref * C
        k = np.flatnonzero((v >= -vmax) & (v <= vmax))
        raw = h[iw[0]].section[:, :, k[0]:k[-1] + 1]
        d = (raw * hw["BSCALE"] + hw["BZERO"]).astype(np.float32)
        aux = h[-2]
        exp = aux.data[:, aux.header["EXPTIMEF"]]
        t = Time(h0["STARTOBS"]) + TimeDelta(aux.data[:, aux.header["TIME"]], format="sec")
        ybin = round(hw["CDELT2"] / 0.166)
    return d, exp, t, ybin, k.size, iw, h0
def idl_check(d, exp, thr, ybin, med_factor=10.0):
    d = d.copy()
    d[(d > -200) & (d < -10)] = -200.0
    miss = d == -200.0
    d = np.where(miss, d, d / exp[:, None, None])
    n = (~miss).sum(-1)
    mean = np.where(n > 0, np.where(miss, 0, d).sum(-1) / np.maximum(n, 1), -200.0)
    s = np.sort(d, axis=-1); med = s[..., s.shape[-1] // 2]  # IDL MEDIAN, no /EVEN, -200 included
    hit = (mean >= thr * ybin) & (mean < med_factor * med)
    lab, ng = ndimage.label(hit, structure=np.ones((3, 3), bool))
    return mean, med, hit, lab, ng
def table(mean, lab, ng, t):
    rows = []
    for g in range(1, ng + 1):
        idx = np.argwhere(lab == g); vals = mean[lab == g]; x, y = idx[np.argmax(vals)]
        rows.append((t[x].isot[11:19], int(x), int(y), float(vals.max()), len(vals)))
    return sorted(rows, key=lambda r: -r[3])
if __name__ == "__main__":
    f = sys.argv[1]; thr = float(sys.argv[2]) if len(sys.argv) > 2 else None
    d, exp, t, ybin, nb, iw, h0 = load(f)
    print("windows containing 1402.77:", [h0[f"TDESC{i}"] for i in iw], "nbins", nb, "ybin", ybin, "SUMSPTRF", h0["SUMSPTRF"])
    mean, med, hit, lab, ng = idl_check(d, exp, thr, ybin)
    print("thr", thr * ybin, "npix", int(hit.sum()), "groups", ng)
    for r in table(mean, lab, ng, t): print("  %s x=%4d y=%4d I=%7.1f npix=%d" % r)
    # guard sensitivity: median via np.nanmedian excluding missing
    dd = d.copy(); dd[dd <= -10] = np.nan; dd /= exp[:, None, None]
    m2 = np.nanmean(dd, -1); md2 = np.nanmedian(dd, -1)
    hit2 = (m2 >= thr * ybin) & (m2 < 10 * md2)
    print("prototype-style (nanmedian): npix", int(hit2.sum()), "diff pixels vs IDL-faithful", int((hit2 ^ hit).sum()))
    print("count of -200 in +-50 km/s bins:", int((d == -200).sum()), "of", d.size, "; (-200,-10):", int(((d > -200) & (d < -10)).sum()), "; saturated 16183:", int((d >= 16183).sum()))
