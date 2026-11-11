import sys, numpy as np
from astropy.io import fits
for f in sys.argv[1:]:
    with fits.open(f, memmap=True) as h:
        aux = h[-2]; a = aux.data; ah = aux.header; hd = h[1].header
        x = a[:, ah["XCENIX"]]; y = a[:, ah["YCENIX"]]
        print(f.split("/")[-1][8:35], "NAXIS2", hd["NAXIS2"], "CDELT2", hd["CDELT2"], "CDELT3", hd["CDELT3"], "CRPIX2", hd["CRPIX2"],
              "PC3_2 range", a[:, ah["PC3_2IX"]].min(), a[:, ah["PC3_2IX"]].max(), "PC2_2", a[:, ah["PC2_2IX"]].min(), a[:, ah["PC2_2IX"]].max(),
              "NAXIS1", hd["NAXIS1"], "CDELT1", hd["CDELT1"], hd["CUNIT1"], "nwin", h[0].header["NWIN"], "T step med", np.median(np.diff(a[:, ah["TIME"]])))
        dx = np.diff(x)
        j = np.flatnonzero(np.abs(dx) > 0.02)
        print("  x first 30 (arcsec, rel):", np.round(x[:30] - x[0], 4).tolist())
        print("  dx at jumps (first 15):", np.round(dx[j[:15]], 3).tolist(), "gaps:", np.diff(j[:16]).tolist())
        print("  |dx| percentiles 50/90/99:", np.percentile(np.abs(dx), [50, 90, 99]).round(4).tolist(), "sign changes of dx (jumps):", int((np.diff(np.sign(dx[j])) != 0).sum()))
        print("  x monotone?", bool(np.all(dx >= -1e-3)) or bool(np.all(dx <= 1e-3)), " y span", np.ptp(y).round(3), "y |dy| med", np.median(np.abs(np.diff(y))).round(4))
