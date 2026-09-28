import sys, numpy as np
from astropy.io import fits
from astropy.time import Time, TimeDelta
import proto
f = "tian2016/iris_l2_20150502_023447_3820109196_raster_t000_r00000.fits"
h0 = fits.getheader(f, 0); aux = fits.open(f)[-2]
t = Time(h0["STARTOBS"]) + TimeDelta(aux.data[:, aux.header["TIME"]], format="sec")
print("SUMSPAT", h0["SUMSPAT"], "SUMSPTRF", h0["SUMSPTRF"], "STEPS_AV", h0.get("STEPS_AV"), "DATE_OBS", h0["DATE_OBS"], "L2 version", h0.get("VER_RF2"), h0.get("DATE_RF2"))
for thr in (None, 465.1 / 2):
    r = proto.burst_check(f, threshold=thr)
    lab = r["labels"]
    print(f"threshold used {r['thr']:.1f} DN/s, npix {r['npix']}, groups {r['ngroups']}")
    # recompute intensity to find brightest pixel per group
    with fits.open(f, memmap=True, do_not_scale_image_data=True) as h:
        iw = [i for i in range(1, h0["NWIN"] + 1) if h0[f"TWMIN{i}"] <= 1402.77 <= h0[f"TWMAX{i}"]][0]
        hw = h[iw].header
        lam = hw["CRVAL1"] + (np.arange(hw["NAXIS1"]) + 1 - hw["CRPIX1"]) * hw["CDELT1"]
        v = proto.C_KMS * (lam - 1402.77) / 1402.77; k = np.flatnonzero(abs(v) <= 50)
        c = proto._scaled(h[iw], np.s_[:, :, k[0]:k[-1] + 1]); c[c <= -10] = np.nan
        c /= h[-2].data[:, h[-2].header["EXPTIMEF"]][:, None, None]
        inten = np.nanmean(c, axis=-1)
    rows = []
    for g in range(1, r["ngroups"] + 1):
        idx = np.argwhere(lab == g); vals = inten[lab == g]; x, y = idx[np.argmax(vals)]
        rows.append((g, t[x].isot[11:19], x, y, vals.max(), len(vals)))
    rows.sort(key=lambda q: -q[4])
    for row in rows[:12]:
        print("   event %3d  %s  x=%4d y=%4d  I=%7.1f  npix=%d" % row)
