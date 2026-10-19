import sys, threading, warnings, numpy as np, astropy
from astropy.io import fits
from astropy.wcs import WCS
warnings.simplefilter("ignore")
kind = sys.argv[1]
if kind == "tan":
    w = WCS(naxis=2); w.wcs.crpix = [256, 256]; w.wcs.cdelt = [-0.066667, 0.066667]; w.wcs.crval = [0, 0]; w.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    world = np.random.rand(1000, 2) * 10
    def worker():
        for _ in range(300):
            pix = w.all_world2pix(world, 0); w.all_pix2world(pix, 0)
else:
    path = sys.argv[2]
    with fits.open(path) as hdul:
        w = WCS(hdul[0].header, hdul)
    n = w.naxis
    pix = np.random.rand(2000, n) * 10
    ref = w.all_pix2world(pix, 0)
    bad = []
    def worker():
        for _ in range(300):
            out = w.all_pix2world(pix, 0)
            if not np.allclose(out, ref, equal_nan=True): bad.append(1)
            w.all_world2pix(out, 0)
threads = [threading.Thread(target=worker) for _ in range(8)]
for t in threads: t.start()
for t in threads: t.join()
print(kind, "astropy", astropy.__version__, "ok", "" if kind == "tan" else f"wrong results in {len(bad)} iterations")
