import warnings, numpy as np, matplotlib; matplotlib.use("agg")
import matplotlib.pyplot as plt, astropy
from astropy.wcs import WCS
warnings.simplefilter("ignore")
w = WCS(naxis=2); w.wcs.ctype = ["HPLN-TAN", "HPLT-TAN"]; w.wcs.cdelt = [1/3600, 1/3600]; w.wcs.crpix = [50, 50]; w.wcs.cunit = ["deg", "deg"]
fig = plt.figure(); ax = fig.add_subplot(111, projection=w); ax.imshow(np.zeros((100, 100)))
before = ax.format_coord(10.0, 20.0)
fig.canvas.draw(); after = ax.format_coord(10.0, 20.0)
ax.coords.frame.set_visible(False) if hasattr(ax.coords.frame, "set_visible") else None
ax.reset_wcs(w); reset = ax.format_coord(10.0, 20.0)
print(f"astropy {astropy.__version__}: before any draw: {before!r}; after a draw: {after!r}; after reset_wcs: {reset!r}")
