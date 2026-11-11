import time, warnings, numpy as np, matplotlib; matplotlib.use("agg")
import matplotlib.pyplot as plt, astropy
from astropy.wcs import WCS
from astropy.wcs.wcsapi import BaseLowLevelWCS, HighLevelWCSWrapper
warnings.simplefilter("ignore")
class Counting(BaseLowLevelWCS):
    def __init__(self, wcs): self._w = wcs; self.n = 0; self.pts = 0
    pixel_n_dim = property(lambda s: s._w.pixel_n_dim); world_n_dim = property(lambda s: s._w.world_n_dim)
    world_axis_physical_types = property(lambda s: s._w.world_axis_physical_types); world_axis_units = property(lambda s: s._w.world_axis_units)
    world_axis_object_components = property(lambda s: s._w.world_axis_object_components); world_axis_object_classes = property(lambda s: s._w.world_axis_object_classes)
    axis_correlation_matrix = property(lambda s: s._w.axis_correlation_matrix); pixel_shape = property(lambda s: s._w.pixel_shape)
    pixel_bounds = property(lambda s: s._w.pixel_bounds); world_axis_names = property(lambda s: s._w.world_axis_names)
    def pixel_to_world_values(self, *a): self.n += 1; self.pts += np.size(a[0]); return self._w.pixel_to_world_values(*a)
    def world_to_pixel_values(self, *a): return self._w.world_to_pixel_values(*a)
w = WCS(naxis=2); w.wcs.ctype = ["HPLN-TAN", "HPLT-TAN"]; w.wcs.cdelt = [1/3600, 1/3600]; w.wcs.crpix = [400, 400]; w.wcs.cunit = ["deg", "deg"]
c = Counting(w); fig = plt.figure(figsize=(6, 6)); ax = fig.add_subplot(111, projection=HighLevelWCSWrapper(c))
ax.imshow(np.zeros((800, 800))); fig.canvas.draw(); c.n = c.pts = 0
fig.canvas.draw(); n1, p1 = c.n, c.pts; c.n = c.pts = 0
ax.set_xlabel("x"); n2 = c.n; c.n = 0
t0 = time.perf_counter()
for _ in range(20): fig.canvas.draw()
dt = (time.perf_counter() - t0) / 20
print(f"astropy {astropy.__version__}: pixel_to_world_values calls per redraw {n1} ({p1} points), per set_xlabel {n2}; unchanged redraw {dt*1e3:.1f} ms")
