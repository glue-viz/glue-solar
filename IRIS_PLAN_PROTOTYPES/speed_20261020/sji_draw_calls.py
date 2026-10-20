"""
gWCS calls per slit-jaw frame step and draw in glue-solar (R36): python sji_draw_calls.py SJI_FILE GLUE_SOLAR_TREE, with
an isolated HOME and offscreen Qt. Counts the calls that reach irispy's gWCS, past glue-solar's _GlueWCS memo.
"""
import sys
import time

sys.path.insert(0, sys.argv[2])
from glue_qt.app import GlueApplication  # noqa: E402
from glue_qt.viewers.image import ImageViewer  # noqa: E402
from qtpy.QtWidgets import QApplication  # noqa: E402

import glue_solar  # noqa: E402
from glue_solar.sources.loaders.iris import image_data  # noqa: E402

glue_solar.setup()
app = GlueApplication()
app.resize(1600, 1000)
app.show()
data = image_data(sys.argv[1])
app.data_collection.append(data)
viewer = app.new_data_viewer(ImageViewer, data=data)
viewer.state.show_axes = True
for _ in range(10):
    QApplication.processEvents()
gwcs = data.coords._wcs
calls = {"pixel_to_world_values": [], "world_to_pixel_values": []}
for name in calls:
    def counted(*args, _original=getattr(gwcs, name), _name=name):
        start = time.perf_counter()
        result = _original(*args)
        calls[_name].append(time.perf_counter() - start)
        return result
    setattr(gwcs, name, counted)
for frame in (5, 6, 7, 50):
    for record in calls.values():
        record.clear()
    slices = list(viewer.state.slices)
    slices[0] = frame
    start = time.perf_counter()
    viewer.state.slices = tuple(slices)
    viewer.figure.canvas.draw()
    total = time.perf_counter() - start
    print(f"frame {frame}: step and draw {total * 1e3:.0f} ms; gWCS calls {({k: len(v) for k, v in calls.items()})},"
          f" {sum(map(sum, calls.values())) * 1e3:.1f} ms in them")
