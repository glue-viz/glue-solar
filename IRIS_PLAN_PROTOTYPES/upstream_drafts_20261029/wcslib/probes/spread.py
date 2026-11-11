"""Per-point inverse time on the reproducer's sit-and-stare: the spread behind the mean."""
import sys, time, warnings
import numpy as np
sys.path.insert(0, sys.argv[1])
import tab_inverse_repro as r
warnings.simplefilter("ignore")
rng = np.random.default_rng(0)
k = np.arange(r.N_EXPOSURES)
jitter = lambda s: rng.normal(0, s, r.N_EXPOSURES)
w = r.raster_wcs(r.X0 + 0.05 * (k // 6) + jitter(0.001), r.Y0 + jitter(0.001))
pix = [rng.uniform(0, s - 1, 400) for s in w.pixel_shape]
world = np.array(w.pixel_to_world_values(*pix))
ts = []
for j in range(world.shape[1]):
    t = time.perf_counter(); w.world_to_pixel_values(*world[:, j:j + 1]); ts.append((time.perf_counter() - t) * 1e3)
ts = np.array(ts)
print(f"sit-and-stare, 400 random points one at a time (ms): mean {ts.mean():.2f}  median {np.median(ts):.2f}  p90 {np.percentile(ts, 90):.2f}  p99 {np.percentile(ts, 99):.1f}  max {ts.max():.1f}")
