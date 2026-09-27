"""Spectrogram slider cost vs exposure index (sit-and-stare Si IV 1403, 1600 exposures) and how much is spent in the WCS."""
import os
import time

import numpy as np
from glue.core import DataCollection
from glue_qt.app import GlueApplication
from glue_qt.viewers.image import ImageViewer

import glue_solar.sources.loaders.iris as L

RAS = "~/DATA/IRIS/2dd2d12db374b3466aa27a65bec235d3-iris_l2_20130902_163935_4000255147_raster/iris_l2_20130902_163935_4000255147_raster_t000_r00000.fits"
STATS = {"p2w": [0, 0.0, 0], "w2p": [0, 0.0, 0]}


def _timed(name, fn):
    def wrapper(self, *arrays):
        t = time.perf_counter()
        try:
            return fn(self, *arrays)
        finally:
            s = STATS[name]; s[0] += 1; s[1] += time.perf_counter() - t; s[2] += np.size(np.broadcast(*arrays))
    return wrapper


def test_slider(qtbot, monkeypatch):
    if os.environ.get("FIX"):
        import fixes
        fixes.apply(os.environ["FIX"])
    monkeypatch.setattr(L._GlueWCS, "pixel_to_world_values", _timed("p2w", L._GlueWCS.pixel_to_world_values))
    monkeypatch.setattr(L._GlueWCS, "world_to_pixel_values", _timed("w2p", L._GlueWCS.world_to_pixel_values))
    d = L.raster_data([RAS], ["Si IV 1403"])[0]
    app = GlueApplication(DataCollection([d])); qtbot.addWidget(app)
    spec = app.new_data_viewer(ImageViewer, data=d)  # displays wavelength x slit, slices exposures
    spec.figure.canvas.draw()
    print("DISPLAY x", spec.state.x_att, "y", spec.state.y_att, "slices", spec.state.slices, flush=True)
    for step in (1, 2, 400, 401, 800, 801, 1200, 1201, 1598, 1599, 5, 6):
        for s in STATS.values(): s[:] = [0, 0.0, 0]
        sl = list(spec.state.slices); sl[0] = step
        t = time.perf_counter(); spec.state.slices = tuple(sl); t1 = time.perf_counter(); spec.figure.canvas.draw(); t2 = time.perf_counter()
        print(f"STEP {step} total={t2 - t:.3f} set={t1 - t:.3f} draw={t2 - t1:.3f} "
              f"p2w={STATS['p2w'][1]:.3f}s/{STATS['p2w'][0]}calls/{STATS['p2w'][2]}pts "
              f"w2p={STATS['w2p'][1]:.3f}s/{STATS['w2p'][0]}calls/{STATS['w2p'][2]}pts", flush=True)
    app.close()
