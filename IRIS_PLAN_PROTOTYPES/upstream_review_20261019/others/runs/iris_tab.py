import sys, subprocess, threading, time, warnings, numpy as np, astropy
warnings.simplefilter("ignore")
from irispy.io import read_files
path = sys.argv[1]
coll = read_files(path, memmap=True, uncertainty=False)
cube = coll[list(coll.keys())[0]]; cube = cube[0] if not hasattr(cube, "wcs") else cube
w = cube.wcs
print(f"astropy {astropy.__version__}: raster {cube.data.shape} ctype {list(getattr(w.wcs, 'ctype', []))}")
# inverse timing: random pixels inside the window, world -> pixel per point
rng = np.random.default_rng(0); n = 40
pix = [rng.uniform(0, s - 1, n) for s in w.pixel_shape]
world = w.pixel_to_world_values(*pix)
t0 = time.perf_counter(); back = w.world_to_pixel_values(*world); dt = (time.perf_counter() - t0) / n
err = np.nanmax([np.abs(np.asarray(b) - p) for b, p in zip(back, pix)])
print(f" -TAB inverse: {dt*1e3:.2f} ms per point, max round-trip error {err:.2e} px")
code = f"""
import threading, warnings, numpy as np; warnings.simplefilter('ignore')
from irispy.io import read_files
coll = read_files({path!r}, memmap=True, uncertainty=False); cube = coll[list(coll.keys())[0]]; cube = cube[0] if not hasattr(cube, 'wcs') else cube; w = cube.wcs
pix = [np.random.rand(300) * (s - 1) for s in w.pixel_shape]; ref = w.pixel_to_world_values(*pix); bad = []
def worker():
    for _ in range(100):
        if not np.allclose(w.pixel_to_world_values(*pix), ref, equal_nan=True): bad.append(1)
ts = [threading.Thread(target=worker) for _ in range(8)]; [t.start() for t in ts]; [t.join() for t in ts]
print('wrong in', len(bad), 'of 800')
"""
r = subprocess.run([sys.executable, "-I", "-u", "-c", code], capture_output=True, text=True)
print(f" IRIS raster -TAB WCS, 8 threads x 100 pixel_to_world: exit {r.returncode} {r.stdout.strip()[-40:]} {r.stderr.strip()[-80:]}")
