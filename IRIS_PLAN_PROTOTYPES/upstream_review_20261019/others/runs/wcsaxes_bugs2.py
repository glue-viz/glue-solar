import warnings, numpy as np, matplotlib; matplotlib.use("agg")
import matplotlib.pyplot as plt, astropy, astropy.units as u
from astropy.wcs import WCS
warnings.simplefilter("ignore"); print("astropy", astropy.__version__)
def case(name, fn):
    try: out = fn(); print(f"{name}: OK {out or ''}")
    except Exception as e: print(f"{name}: {type(e).__name__}: {str(e)[:120]}")
def coupled():  # pixel axis 3 (step) moves lon and lat: 3 world coords survive a slice, as a raster window's view
    w = WCS(naxis=3); w.wcs.ctype = ["WAVE", "HPLT-TAN", "HPLN-TAN"]; w.wcs.crval = [1400, 0, 0]
    w.wcs.cdelt = [0.01, 1/3600, 1/3600]; w.wcs.crpix = [10, 50, 5]; w.wcs.cunit = ["Angstrom", "deg", "deg"]
    w.wcs.pc = [[1, 0, 0], [0, 1, 0.1], [0, 0.1, 1]]; return w
def c_grid_lines_3coord():
    fig = plt.figure(); ax = fig.add_subplot(111, projection=coupled(), slices=("x", "y", 2)); ax.imshow(np.zeros((100, 100)))
    print("  world_n_dim of view:", ax.wcs.world_n_dim)
    ax.coords.grid(draw_grid=True, grid_type="lines"); fig.canvas.draw(); return "drew"
def c_world_transform_3coord():
    fig = plt.figure(); ax = fig.add_subplot(111, projection=coupled(), slices=("x", "y", 2)); ax.imshow(np.zeros((100, 100)))
    ax.get_transform("world").transform(np.array([[1400.0, 0.0]])); return "ok"
def c_tickable_outside():
    w = WCS(naxis=2); w.wcs.ctype = ["HPLN-TAN", "HPLT-TAN"]; w.wcs.cdelt = [1/3600, 1/3600]; w.wcs.crpix = [50, 50]; w.wcs.cunit = ["deg", "deg"]
    fig = plt.figure(); ax = fig.add_subplot(111, projection=w); ax.imshow(np.zeros((100, 100)))
    ax.coords[0].add_tickable_gridline("far", 5 * u.deg); fig.canvas.draw(); return "drew"
for n, f in list(globals().items()):
    if n.startswith("c_"): case(n[2:], f)
