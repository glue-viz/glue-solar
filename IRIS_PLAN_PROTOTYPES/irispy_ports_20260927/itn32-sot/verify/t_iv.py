import glob, warnings
import numpy as np
from astropy.io import fits
from irispy.io import read_files
from irispy.io.sji import read_sji_lvl2
D = "<scratch>/features/verify-itn32-sot/dl/copy/"
tars = sorted(glob.glob(D + "*.tar.gz"))
c = read_files(tars)
print("keys from 2 tarballs:", list(c.keys()) if hasattr(c, "keys") else type(c))
for f in sorted(glob.glob(D + "*/*.fits")):
    h = fits.getheader(f)
    d = fits.getdata(f)
    print(f.split("/")[-1], {k: h.get(k) for k in ("INSTRUME", "TDESC1", "BTYPE", "BUNIT", "NAXIS3", "OBSID")}, "nanfrac", float(np.isnan(d).mean()), "finite range", np.nanmin(d) if np.isfinite(d).any() else None, np.nanmax(d) if np.isfinite(d).any() else None)
    try:
        cube = read_sji_lvl2(f); print("   ->", type(cube).__name__, cube.unit, cube.shape)
    except Exception as e:
        print("   -> FAIL", type(e).__name__, e)
