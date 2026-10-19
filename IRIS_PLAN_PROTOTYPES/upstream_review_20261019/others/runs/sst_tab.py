import sys, subprocess, threading, warnings, numpy as np, astropy
from astropy.io import fits
from astropy.wcs import WCS
warnings.simplefilter("ignore"); path = sys.argv[1]
with fits.open(path) as hdul:
    h = hdul[0].header; w = WCS(h, hdul)
print(f"astropy {astropy.__version__}: ctype {list(w.wcs.ctype)} SPECSYS={h.get('SPECSYS')!r} OBSGEO-X in header: {'OBSGEO-X' in h}")
(tab,) = w.wcs.tab
print(" table map", list(tab.map), "K", list(tab.K), "coord shape", tab.coord.shape)
print(" astropy axis_correlation_matrix (world rows x pixel cols):\n", w.axis_correlation_matrix.astype(int))
varies = {}
for m, world in enumerate(tab.map):
    varies[world] = [int(tab.map[k]) for k in range(tab.M) if np.ptp(tab.coord[..., m], axis=tab.M - 1 - k).any()]
print(" table: world axis -> pixel axes it varies along:", varies)
# thread race on the forward transform
pix = np.column_stack([np.random.rand(500) * (n - 1) for n in w.pixel_shape])
ref = w.all_pix2world(pix, 0); bad = []
def worker():
    for _ in range(100):
        if not np.allclose(w.all_pix2world(pix, 0), ref, equal_nan=True): bad.append(1)
ts = [threading.Thread(target=worker) for _ in range(8)]
[t.start() for t in ts]; [t.join() for t in ts]
print(f" 8 threads x 100 all_pix2world: wrong in {len(bad)} of 800")
code = f"""
import warnings; warnings.simplefilter('ignore')
from astropy.io import fits
from astropy.wcs import WCS
with fits.open({path!r}) as hdul: w = WCS(hdul[0].header, hdul)
c = w.celestial; print('celestial sub ok', c.naxis, c.pixel_to_world_values(10, 10))
"""
r = subprocess.run([sys.executable, "-I", "-c", code], capture_output=True, text=True)
print(f" w.celestial in a subprocess: exit {r.returncode} {r.stdout.strip()[:80]} {r.stderr.strip()[-100:]}")
