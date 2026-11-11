"""Cost of the inverse against the table length, step size and jitter (synthetic)."""
import sys, time, warnings
import numpy as np
sys.path.insert(0, sys.argv[1])
import tab_inverse_repro as r
warnings.simplefilter("ignore")
rng = np.random.default_rng(1)

def inv_cost(x, y, n=300):
    w = r.raster_wcs(x, y)
    pix = [rng.uniform(0, s - 1, n) for s in (r.N_WAVE, r.N_SLIT, len(x))]
    world = w.pixel_to_world_values(*pix)
    t = time.perf_counter(); back = w.world_to_pixel_values(*world); t = time.perf_counter() - t
    d = back[2] - pix[2]
    return t / n * 1e6, np.nanmax(np.abs(d)), np.mean(d < -0.01), np.mean(d > 0.01)

print("scanning 0.35\" steps: us/pt against the number of exposures")
for N in (2, 4, 16, 100, 400, 1600, 6400):
    k = np.arange(N)
    print(f"  N={N:5d}: {inv_cost(r.X0 + 0.35 * k + rng.normal(0, 0.003, N), r.Y0 + rng.normal(0, 0.003, N))[0]:8.1f} us/pt")
print("sit-and-stare, 1600 exposures, 0.05\" every 6: us/pt, max |d exposure|, frac returned earlier / later than the true one, against the jitter")
k = np.arange(1600)
for s in (0.0, 0.0001, 0.0003, 0.001, 0.003):
    c = inv_cost(r.X0 + 0.05 * (k // 6) + rng.normal(0, s, 1600), r.Y0 + rng.normal(0, s, 1600))
    print(f"  jitter {s:.4f}\": {c[0]:8.1f} us/pt  max |d| {c[1]:.2f}  earlier {c[2]:.0%}  later {c[3]:.0%}")
print("sit-and-stare without the slit tilt (TILT=0), jitter 0.0003")
r.TILT = 0.0
c = inv_cost(r.X0 + 0.05 * (k // 6) + rng.normal(0, 0.0003, 1600), r.Y0 + rng.normal(0, 0.0003, 1600))
print(f"  {c[0]:8.1f} us/pt  max |d| {c[1]:.2f}  earlier {c[2]:.0%}  later {c[3]:.0%}")
