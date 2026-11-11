import sys, numpy as np
from astropy.io import fits
for f in sys.argv[1:]:
    with fits.open(f, memmap=True) as h:
        aux = h[-2]; x = aux.data[:, aux.header["XCENIX"]]; y = aux.data[:, aux.header["YCENIX"]]
        dx = np.abs(np.diff(x))
        print(f.split("/")[-1][8:60], "n", len(x), "STEPS_AV", h[0].header.get("STEPS_AV"), "OBS_DESC", h[0].header.get("OBS_DESC"),
              f"x span {np.ptp(x):.2f} med|dx| {np.median(dx) if len(dx) else 0:.4f} y span {np.ptp(y):.2f} jumps>0.03 {(dx > 0.03).sum()}")
