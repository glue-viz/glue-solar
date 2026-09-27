"""A14/C: default Image Viewer axes for a 3-D raster window and for a 4-D stack."""
import warnings; warnings.filterwarnings("ignore")
from irispy.data.test import get_test_data_filenames
from glue_solar.sources.loaders.iris import raster_data
from glue_qt.app import GlueApplication
from glue_qt.viewers.image import ImageViewer
fs = sorted(str(f) for f in get_test_data_filenames() if "20140329" in str(f) and str(f).endswith(".fits"))
[ras] = raster_data(fs[:1], ["Mg II k 2796"])
[stack] = raster_data(fs[:3], ["Mg II k 2796"], stack=True)
app = GlueApplication()
for d in (ras, stack):
    app.data_collection.append(d)
    v = app.new_data_viewer(ImageViewer, data=d)
    s = v.state
    sliders = [d.world_component_ids[i].label for i in range(d.ndim) if i not in (s.x_att.axis, s.y_att.axis)]
    print(f"{d.label} shape={d.shape}: x={s.x_att_world.label!r} y={s.y_att_world.label!r} sliders={sliders}")
app.close()
