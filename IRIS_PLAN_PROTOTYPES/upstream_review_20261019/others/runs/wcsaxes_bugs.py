import pickle, sys, traceback, warnings
import numpy as np, matplotlib; matplotlib.use("agg")
import matplotlib.pyplot as plt
import astropy
from astropy.wcs import WCS
from astropy.visualization.wcsaxes import WCSAxes
warnings.simplefilter("ignore")
print("astropy", astropy.__version__)

def case(name, fn):
    try:
        out = fn(); print(f"{name}: OK {out if out is not None else ''}")
    except Exception as e:
        print(f"{name}: {type(e).__name__}: {str(e)[:110]}")

def wcs3():  # raster-like: wavelength, lat-TAB? no: a plain 3-D cube lon, lat, wave
    w = WCS(naxis=3); w.wcs.ctype = ["HPLN-TAN", "HPLT-TAN", "WAVE"]
    w.wcs.crval = [0, 0, 1400]; w.wcs.cdelt = [1/3600, 1/3600, 0.01]; w.wcs.crpix = [50, 50, 10]
    w.wcs.cunit = ["deg", "deg", "Angstrom"]; return w

def wcs2():
    w = WCS(naxis=2); w.wcs.ctype = ["HPLN-TAN", "HPLT-TAN"]; w.wcs.crval = [0, 0]
    w.wcs.cdelt = [1/3600, 1/3600]; w.wcs.crpix = [50, 50]; w.wcs.cunit = ["deg", "deg"]; return w

def c_format_coord_1d():
    w = WCS(naxis=1); w.wcs.ctype = ["WAVE"]; w.wcs.cunit = ["Angstrom"]; w.wcs.crval = [1400]; w.wcs.cdelt = [0.01]; w.wcs.crpix = [1]
    fig = plt.figure(); ax = fig.add_subplot(111, projection=w); fig.canvas.draw()
    return ax.format_coord(3.0, 0.5)[:40]

def c_three_coord_grid_lines():
    fig = plt.figure(); ax = fig.add_subplot(111, projection=wcs3(), slices=("x", "y", 5))
    ax.imshow(np.zeros((100, 100))); ax.coords.grid(draw_grid=True, grid_type="lines"); fig.canvas.draw(); return "drew"

def c_three_coord_plot_coord():
    from astropy.coordinates import SkyCoord
    fig = plt.figure(); ax = fig.add_subplot(111, projection=wcs3(), slices=("x", "y", 5))
    ax.imshow(np.zeros((100, 100)))
    ax.plot_coord(SkyCoord(0, 0, unit="deg", frame="helioprojective") if False else None) if False else None
    tr = ax.get_transform("world"); tr.transform(np.array([[0.0, 0.0]])); return "world transform of 2 coords ok"

def c_sliced_out_hash_invert():
    w = WCS(naxis=3); w.wcs.ctype = ["HPLN-TAN", "HPLT-TAN", "TIME"]; w.wcs.crval = [0, 0, 0]
    w.wcs.cdelt = [1/3600, 1/3600, 1]; w.wcs.crpix = [50, 50, 1]; w.wcs.cunit = ["deg", "deg", "s"]
    fig = plt.figure(); ax = fig.add_subplot(111, projection=w, slices=("x", "y", 0)); ax.imshow(np.zeros((100, 100)))
    for c in ax.coords: c.set_ticklabel_position("#"); c.set_ticks_position("all")
    fig.canvas.draw(); ax.invert_xaxis(); fig.canvas.draw(); ax.invert_xaxis(); fig.canvas.draw(); return "3 draws"

def c_swapped_cube_simplify():
    fig = plt.figure(); ax = fig.add_subplot(111, projection=wcs3(), slices=("y", "x", 7)); ax.imshow(np.zeros((100, 100)))
    ax.coords[2].set_ticklabel_position("t"); ax.coords[2].set_ticks_position("t"); ax.tick_params(labelsize=6); fig.canvas.draw(); return "drew"

def c_tickable_gridline_outside():
    fig = plt.figure(); ax = fig.add_subplot(111, projection=wcs2()); ax.imshow(np.zeros((100, 100)))
    ax.coords[0].add_tickable_gridline("far", 10 * 3600 * (1/3600) * 100)  # 1000 deg, off the view
    fig.canvas.draw(); return "drew"

def c_zero_size_axes():
    fig = plt.figure(); ax = fig.add_axes([0.1, 0.1, 0.0, 0.5], projection=wcs2()); ax.imshow(np.zeros((100, 100))); fig.canvas.draw(); return "drew"

def c_pickle():
    fig = plt.figure(); ax = fig.add_subplot(111, projection=wcs2()); ax.imshow(np.zeros((100, 100))); fig.canvas.draw()
    pickle.loads(pickle.dumps(fig)); return "round trip"

def c_grid_minor():
    fig = plt.figure(); ax = fig.add_subplot(111, projection=wcs2()); ax.imshow(np.zeros((100, 100)))
    ax.grid(which="minor"); fig.canvas.draw(); return "minor grid"

def c_grid_toggle_key():  # matplotlib's g key: ax.grid() toggling
    fig = plt.figure(); ax = fig.add_subplot(111, projection=wcs2()); ax.imshow(np.zeros((100, 100)))
    from matplotlib.backend_bases import KeyEvent, key_press_handler
    fig.canvas.draw(); ev = KeyEvent("key_press_event", fig.canvas, "g", 50, 50); ev.inaxes = ax
    key_press_handler(ev, fig.canvas); return "g handled"

for n, f in list(globals().items()):
    if n.startswith("c_"): case(n[2:], f)
