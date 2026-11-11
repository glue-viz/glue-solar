"""One-cell and 1600-exposure cost of the inverse against the slit's tilt (synthetic)."""
import sys, time, warnings
import numpy as np
sys.path.insert(0, sys.argv[1])
import tab_inverse_repro as r
warnings.simplefilter("ignore")
rng = np.random.default_rng(2)
def cost(x, y, n=300):
    w = r.raster_wcs(x, y)
    pix = [rng.uniform(0, s - 1, n) for s in w.pixel_shape]
    world = w.pixel_to_world_values(*pix)
    t = time.perf_counter(); w.world_to_pixel_values(*world); return (time.perf_counter() - t) / n * 1e6
for tilt in (0.0, 0.0112, 0.05):
    r.TILT = tilt
    k2, k = np.arange(2), np.arange(1600)
    one = cost(r.X0 + 0.35 * k2, r.Y0 + 0 * k2)
    sas = cost(r.X0 + 0.05 * (k // 6) + rng.normal(0, 0.001, 1600), r.Y0 + rng.normal(0, 0.001, 1600), 100)
    print(f"TILT {tilt:6.4f}: one 0.35\" cell {one:7.1f} us/pt;  1600-exposure sit-and-stare {sas:8.1f} us/pt")
