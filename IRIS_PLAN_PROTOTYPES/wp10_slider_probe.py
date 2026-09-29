"""
On-screen slider latency probe (wp10-m0-acceptance data tier; run by hand, not a glue-solar test).

Opens one IRIS raster window or SJI in a real Glue window and steps its leading slider, timing:

- set: assigning the viewer's slice, as Glue recomputes the displayed image;
- draw: rendering the figure (Agg);
- paint: pushing the rendered figure to the screen (Qt repaint);
- tick: one QSlider value change with its events, which is what each tick of a drag costs;

and the share of each step spent in glue-solar's WCS conversions. ``--profile`` adds a cProfile
of the ticks. Run it in the environment you use Glue from; it prints the versions it imported.

Usage: python wp10_slider_probe.py FILE [--window "Si IV 1403"] [--steps 40] [--profile]
"""

import argparse
import cProfile
import platform
import pstats
import sys
import time
from importlib.metadata import version

import numpy as np
from glue_qt.app import GlueApplication
from glue_qt.utils import get_qapp
from glue_qt.viewers.image import ImageViewer
from qtpy import QT_VERSION, QtWidgets

from astropy.io import fits

import glue_solar
from glue_solar.sources.loaders import iris

parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
parser.add_argument("file")
parser.add_argument("--window", help="raster spectral window (default: Si IV 1403, else the first)")
parser.add_argument("--steps", type=int, default=40)
parser.add_argument("--profile", action="store_true")
args = parser.parse_args()

# Time spent in glue-solar's coordinate conversions
WCS_SECONDS = [0.0]
for name in ("pixel_to_world_values", "world_to_pixel_values"):
    original = getattr(iris._GlueWCS, name)

    def timed(self, *arrays, _original=original):
        start = time.perf_counter()
        try:
            return _original(self, *arrays)
        finally:
            WCS_SECONDS[0] += time.perf_counter() - start

    setattr(iris._GlueWCS, name, timed)

header = fits.getheader(args.file)
if header["INSTRUME"] == "SPEC":
    windows = [header[f"TDESC{i}"] for i in range(1, header["NWIN"] + 1)]
    window = args.window or ("Si IV 1403" if "Si IV 1403" in windows else windows[0])
    [data] = iris.raster_data([args.file], [window])
else:
    data = iris.image_data(args.file)

glue_solar.setup()
qapp = get_qapp()
app = GlueApplication()
app.data_collection.append(data)
viewer = app.new_data_viewer(ImageViewer, data=data)
app.show()
for _ in range(5):
    qapp.processEvents()
    time.sleep(0.1)
canvas = viewer.figure.canvas
slider = viewer.options_widget().findChildren(QtWidgets.QSlider)[0]  # the first slice slider
n = data.shape[0]

print(f"Python {sys.version.split()[0]} on {platform.platform()}; Qt {QT_VERSION} ({qapp.platformName()})")
print("  " + ", ".join(f"{p} {version(p)}" for p in ("glue-core", "glue-qt", "glue-solar", "irispy-lmsal", "astropy", "numpy", "matplotlib")))
print(f"  glue_solar from {glue_solar.__file__}")
print(f"  screen devicePixelRatio {qapp.primaryScreen().devicePixelRatio()}, canvas {canvas.width()}x{canvas.height()} px")
print(f"{data.label}: shape {data.shape}, {data[data.main_components[0]].dtype}; slider over axis 0 ({n} positions)")


def step_by_state(index):
    WCS_SECONDS[0] = 0.0
    start = time.perf_counter()
    viewer.state.slices = (index, *viewer.state.slices[1:])
    set_done = time.perf_counter()
    canvas.draw()
    draw_done = time.perf_counter()
    canvas.repaint()
    qapp.processEvents()
    return set_done - start, draw_done - set_done, time.perf_counter() - draw_done, WCS_SECONDS[0]


def tick(value):
    WCS_SECONDS[0] = 0.0
    start = time.perf_counter()
    slider.setValue(value)
    qapp.processEvents()  # the slice change and glue's queued redraw
    qapp.processEvents()
    return time.perf_counter() - start, WCS_SECONDS[0]


def report(label, rows, names):
    rows = np.array(rows)
    parts = ", ".join(f"{name} median {np.median(rows[:, i]):.3f} s (max {rows[:, i].max():.3f})" for i, name in enumerate(names))
    print(f"{label}: {parts}")


report("Jumps across the axis", [step_by_state(i) for i in np.linspace(0, n - 1, args.steps).astype(int)], ("set", "draw", "paint", "WCS"))
report("Neighbouring steps", [step_by_state(i % n) for i in range(n // 2, n // 2 + args.steps)], ("set", "draw", "paint", "WCS"))
start_value = slider.value()
profiler = cProfile.Profile() if args.profile else None
if profiler:
    profiler.enable()
ticks = [tick(start_value + i + 1) for i in range(min(args.steps, slider.maximum() - start_value))]
if profiler:
    profiler.disable()
report("Slider ticks (a drag)", ticks, ("tick", "WCS"))
if profiler:
    pstats.Stats(profiler).sort_stats("cumulative").print_stats(25)
app.close()
