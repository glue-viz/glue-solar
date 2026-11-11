import sys, threading, warnings, numpy as np, astropy
from astropy.io import fits
from astropy.wcs import WCS
warnings.simplefilter("ignore")
path, nthreads, lock = sys.argv[1], int(sys.argv[2]), sys.argv[3] == "lock"
with fits.open(path) as hdul:
    w = WCS(hdul[0].header, hdul)
print("ctype", list(w.wcs.ctype), "naxis", w.naxis)
pix = np.random.rand(2000, w.naxis) * 10
ref = w.all_pix2world(pix, 0)
print("finite fraction of reference", np.isfinite(ref).mean())
L = threading.Lock(); bad = []
def worker():
    for _ in range(300):
        if lock:
            with L: out = w.all_pix2world(pix, 0)
        else:
            out = w.all_pix2world(pix, 0)
        if not np.allclose(out, ref, equal_nan=True): bad.append(1)
threads = [threading.Thread(target=worker) for _ in range(nthreads)]
for t in threads: t.start()
for t in threads: t.join()
print(f"astropy {astropy.__version__} threads={nthreads} lock={lock}: wrong in {len(bad)} of {300*nthreads}")
