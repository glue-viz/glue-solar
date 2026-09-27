"""F035 on the 1600-exposure sit-and-stare: lambda-t image step along the slit, and Pixel click -> spectrum at the point."""
import os
import time

import numpy as np
from glue.core import DataCollection
from glue_qt.app import GlueApplication
from glue_qt.viewers.image import ImageViewer
from glue_qt.viewers.profile import ProfileViewer
from matplotlib.backend_bases import MouseEvent

import glue_solar.sources.loaders.iris as L

RAS = "~/DATA/IRIS/2dd2d12db374b3466aa27a65bec235d3-iris_l2_20130902_163935_4000255147_raster/iris_l2_20130902_163935_4000255147_raster_t000_r00000.fits"


def mouse(viewer, name, x, y):
    px, py = viewer.axes.transData.transform((x, y))
    viewer.figure.canvas.callbacks.process(name, MouseEvent(name, viewer.figure.canvas, px, py, button=1))


def test_f035(qtbot):
    if os.environ.get("FIX"):
        import fixes
        fixes.apply(os.environ["FIX"])
    d = L.raster_data([RAS], ["Si IV 1403"])[0]
    app = GlueApplication(DataCollection([d])); qtbot.addWidget(app)
    lt = app.new_data_viewer(ImageViewer, data=d)
    lt.state.x_att, lt.state.y_att = d.pixel_component_ids[2], d.pixel_component_ids[0]  # wavelength x exposure at one slit row
    lt.figure.canvas.draw()
    out = []
    for y in (10, 11, 200, 201, 400, 401):
        sl = list(lt.state.slices); sl[1] = y
        t = time.perf_counter(); lt.state.slices = tuple(sl); lt.figure.canvas.draw(); out.append(f"{y}:{time.perf_counter() - t:.3f}")
    print("LAMBDA_T slit-step", " ".join(out), flush=True)
    rmap = app.new_data_viewer(ImageViewer, data=d)
    rmap.state.x_att, rmap.state.y_att = d.pixel_component_ids[0], d.pixel_component_ids[1]  # exposure x slit at one wavelength
    prof = app.new_data_viewer(ProfileViewer)
    prof.large_data_size = None
    prof.add_data(d)
    prof.state.x_att = d.pixel_component_ids[2]
    rmap.toolbar.active_tool = "image:point_selection"
    qtbot.wait(200)
    qtbot.waitUntil(lambda: not prof.layers[0].is_computing, timeout=60000)
    print("INITIAL profile ready", flush=True)
    out = []
    for i, (x, y) in enumerate([(100, 50), (800, 200), (1500, 380), (400, 100)]):
        t = time.perf_counter()
        mouse(rmap, "button_press_event", x, y); mouse(rmap, "button_release_event", x, y)
        t_click = time.perf_counter() - t
        before = prof.layers[-1].state._profile_cache if len(prof.layers) > 1 else None
        qtbot.waitUntil(lambda: len(prof.layers) > 1 and prof.layers[-1].state._profile_cache is not None
                        and prof.layers[-1].state._profile_cache is not before and not prof.layers[-1].is_computing, timeout=60000)
        prof.figure.canvas.draw()
        t_spec = time.perf_counter() - t
        cache = prof.layers[-1].state._profile_cache
        qtbot.wait(60)
        qtbot.waitUntil(lambda: not prof.layers[0].is_computing, timeout=60000)
        out.append(f"({x},{y}):click={t_click:.3f} spectrum_drawn={t_spec:.3f} n={None if cache is None else len(cache[1])} full-cube data-layer rework in worker={time.perf_counter() - t:.2f}")
    print("PIXEL->PROFILE", " ".join(out), "layers", len(prof.layers), flush=True)
    app.close()
