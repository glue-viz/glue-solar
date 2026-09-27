"""Solar-main loader + stock viewers: Pixel clicks (threaded profile, layer > 1e7) while the GUI thread steps the spectrogram slice (WCSAxes reset)."""
import faulthandler
import os
import time

from glue.core import DataCollection
from glue_qt.app import GlueApplication
from glue_qt.utils import process_events
from glue_qt.viewers.image import ImageViewer
from glue_qt.viewers.profile import ProfileViewer
from matplotlib.backend_bases import MouseEvent

import glue_solar.sources.loaders.iris as L

RAS = "~/DATA/IRIS/2dd2d12db374b3466aa27a65bec235d3-iris_l2_20130902_163935_4000255147_raster/iris_l2_20130902_163935_4000255147_raster_t000_r00000.fits"


def mouse(viewer, name, x, y):
    px, py = viewer.axes.transData.transform((x, y))
    viewer.figure.canvas.callbacks.process(name, MouseEvent(name, viewer.figure.canvas, px, py, button=1))


def test_race(qtbot, monkeypatch):
    faulthandler.enable()
    if os.environ.get("FIX"):
        import fixes
        fixes.apply(os.environ["FIX"])
    monkeypatch.setattr(ProfileViewer, "large_data_size", None)
    d = L.raster_data([RAS], ["Si IV 1403"])[0]
    print("FIX", os.environ.get("FIX"), type(d.coords).__name__, flush=True)
    app = GlueApplication(DataCollection([d])); qtbot.addWidget(app)
    rmap = app.new_data_viewer(ImageViewer, data=d)
    rmap.state.x_att, rmap.state.y_att = d.pixel_component_ids[0], d.pixel_component_ids[1]
    spec = app.new_data_viewer(ImageViewer, data=d)
    prof = app.new_data_viewer(ProfileViewer, data=d)
    prof.state.x_att = d.world_component_ids[-1]
    rmap.toolbar.active_tool = "image:point_selection"
    for i in range(int(os.environ.get("CLICKS", "40"))):
        x, y = 50 + 37 * i, 100 + 5 * i
        mouse(rmap, "button_press_event", x, y); mouse(rmap, "button_release_event", x, y)
        t = time.perf_counter()
        k = 0
        while time.perf_counter() - t < 0.4:
            s = list(spec.state.slices); s[0] = (1500 - 30 * i + k) % 1600; spec.state.slices = tuple(s)
            spec.figure.canvas.draw(); rmap.figure.canvas.draw(); process_events(); k += 1
    print("SURVIVED", flush=True)
    app.close()
