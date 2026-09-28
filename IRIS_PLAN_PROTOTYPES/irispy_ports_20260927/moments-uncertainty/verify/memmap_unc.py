import glob, numpy as np
from irispy.io.utils import read_files
f = sorted(glob.glob("irispy-main/irispy/data/test/sns/*raster*"))[0]
print(f)
for mm in (False, True):
    rc = read_files(f, spectral_windows=["C II 1336"], uncertainty=True, memmap=mm)
    c = rc["C II 1336"][0]
    unc = c.uncertainty
    print("memmap", mm, type(unc).__name__, None if unc is None else (np.nanmedian(unc.array), np.nanmedian(np.asarray(c.data, float))), c.data.dtype)
