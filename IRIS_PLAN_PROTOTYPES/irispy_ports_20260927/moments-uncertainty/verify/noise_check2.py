"""Does the per-sample model predict the variance of spectral SUMS (what moment errors use)? 4000255147 sit-and-stare."""
import numpy as np
from astropy.io import fits
F = "~/DATA/IRIS/2dd2d12db374b3466aa27a65bec235d3-iris_l2_20130902_163935_4000255147_raster/iris_l2_20130902_163935_4000255147_raster_t000_r00000.fits"
PH, RN = 4.0, 3.1
sig2 = lambda d: (np.clip(d * PH, 0, None) + (RN * PH) ** 2) / PH**2
with fits.open(F, memmap=True, do_not_scale_image_data=True) as h:
    for i, name in ((1, "C II 1336"), (6, "Si IV 1403")):
        hd = h[i].header
        sec = np.asarray(h[i].data[0:300], dtype=float) * hd["BSCALE"] + hd["BZERO"]
        sec[sec <= -199] = np.nan
        diff = sec[1:] - sec[:-1]
        pred = sig2(sec[1:]) + sig2(sec[:-1])
        mean = 0.5 * (sec[1:] + sec[:-1])
        noise = np.isfinite(diff) & (np.abs(mean) < 5)
        # lag-1 correlations of the temporal differences, noise regime only
        for ax, lab in ((2, "spectral"), (1, "spatial")):
            a = np.moveaxis(diff, ax, -1); m = np.moveaxis(noise, ax, -1)
            ok = m[..., 1:] & m[..., :-1]
            print(f"{name}: lag-1 {lab} corr = {np.corrcoef(a[..., 1:][ok], a[..., :-1][ok])[0, 1]:.3f}")
        for K in (1, 5, 15):
            nw = diff.shape[2] // K
            d = diff[..., : nw * K].reshape(*diff.shape[:2], nw, K)
            p = pred[..., : nw * K].reshape(*diff.shape[:2], nw, K)
            m = noise[..., : nw * K].reshape(*diff.shape[:2], nw, K).all(-1)
            print(f"{name}: K={K:2d} spectral sum  var/pred = {np.var(d.sum(-1)[m]) / np.mean(p.sum(-1)[m]):.2f}  (n={m.sum()})")
