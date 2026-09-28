"""Empirical check of irispy's per-sample noise model on sit-and-stare 4000255147 (small section read)."""
import numpy as np
from astropy.io import fits
F = "~/DATA/IRIS/2dd2d12db374b3466aa27a65bec235d3-iris_l2_20130902_163935_4000255147_raster/iris_l2_20130902_163935_4000255147_raster_t000_r00000.fits"
PH, RN = 4.0, 3.1
with fits.open(F, memmap=True, do_not_scale_image_data=True) as h:
    p = h[0].header
    names = {p[f"TDESC{i}"]: i for i in range(1, p["NWIN"] + 1)}
    print(names, p.get("STEPT_AV"), p.get("SUMSPTRF"), p.get("SUMSPAT"))
    for name in [n for n in names if n.startswith("Si IV") or n.startswith("C II")]:
        i = names[name]; hd = h[i].header
        sec = np.asarray(h[i].data[0:300], dtype=float) * hd.get("BSCALE", 1) + hd.get("BZERO", 0)
        sec[sec <= -199] = np.nan
        wv = hd["CRVAL1"] + hd["CDELT1"] * (np.arange(hd["NAXIS1"]) + 1 - hd["CRPIX1"])
        diff = sec[1:] - sec[:-1]
        sig2 = lambda d: (np.clip(d * PH, 0, None) + (RN * PH) ** 2) / PH**2
        pred = sig2(sec[1:]) + sig2(sec[:-1])
        mean = 0.5 * (sec[1:] + sec[:-1])
        for lo, hi in ((-5, 1), (1, 5), (5, 20), (20, 100), (100, 1e9)):
            sel = np.isfinite(diff) & (mean >= lo) & (mean < hi)
            if sel.sum() > 1000:
                r = np.var(diff[sel]) / np.mean(pred[sel])
                print(f"{name:12s} mean DN [{lo},{hi}) n={sel.sum():8d}  var(dt diff)/predicted = {r:.2f}")
