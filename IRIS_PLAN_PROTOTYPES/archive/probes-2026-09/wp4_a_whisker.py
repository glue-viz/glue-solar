"""(a) whisker preset on glue 1.27: 3D sit-and-stare raster and 4D stack."""
import os, warnings; warnings.simplefilter("ignore")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen"); os.environ.setdefault("MPLBACKEND", "agg")
import glue, numpy as np
from glue.core import DataCollection
from glue_qt.app.application import GlueApplication
from glue_qt.viewers.image import ImageViewer
from irispy.data.test import get_test_data_filenames
from glue_solar.sources.loaders.iris import raster_data
from wp4_common import whisker
fs = [str(f) for f in get_test_data_filenames()]
raster = raster_data([[f for f in fs if "sns" in f and "raster_t000" in f][0]], windows=["Si IV 1403"])[0]
stack = raster_data(sorted(f for f in fs if "20140329" in f and "raster_t000_r0000" in f)[:3], ["Mg II k 2796"], stack=True)[0]
print("glue", glue.__version__, "| raster", raster.shape, "| stack", stack.shape)
app = GlueApplication(DataCollection([raster, stack]))
def sliders(v):
    lay = v.options_widget().slice_helper.layout
    return [(w.state.label, w.state.slice_center) for w in (lay.itemAt(i).widget() for i in range(lay.count())) if w is not None and hasattr(w, "state")]
d = app.new_data_viewer(ImageViewer, data=raster)
print("default 3D view: x", d.state.x_att, "y", d.state.y_att, "slices", d.state.slices, "sliders", sliders(d), "(== spectroheliogram)")
w = whisker(app, raster, slit_index=20)
print("whisker 3D: x", w.state.x_att, "y", w.state.y_att, "slices", w.state.slices, "| x_att_world", w.state.x_att_world, "| y_att_world", w.state.y_att_world, "| sliders", sliders(w))
w4 = whisker(app, stack, slit_index=50)
print("whisker 4D: x", w4.state.x_att, "y", w4.state.y_att, "slices", w4.state.slices, "| x_att_world", w4.state.x_att_world, "| y_att_world", w4.state.y_att_world, "| sliders", sliders(w4))
for v in (d, w, w4): v.figure.canvas.draw()
print("image shapes drawn:", w.layers[0].get_image_shape(), w4.layers[0].get_image_shape(), "| OK")
app.close()
