"""Q3: glue-core AggregateSlice + glue-qt Profile 'collapse' tool == zeroth-moment map with zero plugin code?"""
import os, warnings, numpy as np; warnings.simplefilter("ignore")
from glue_qt.app import GlueApplication
from glue_qt.viewers.image import ImageViewer
from glue_qt.viewers.profile import ProfileViewer
from glue.viewers.image.state import AggregateSlice
from irispy.data.test import get_test_data_filenames
from glue_solar.sources.loaders.iris import raster_data
fs = [str(f) for f in get_test_data_filenames() if str(f).endswith(".fits")]
[ras] = raster_data([f for f in fs if "20140329" in f and "r00000" in f], ["Mg II k 2796"])
app = GlueApplication(); app.data_collection.append(ras)
iv = app.new_data_viewer(ImageViewer, data=ras)
iv.state.x_att = ras.pixel_component_ids[1]; iv.state.y_att = ras.pixel_component_ids[0]   # slit x step map
iv.state.slices = (0, 0, AggregateSlice(slice(10, 40), 20, np.nansum))
img = iv.layers[0].state.get_sliced_data()
ref = np.nansum(ras[ras.main_components[0]][:, :, 10:40], axis=2)
print("map shape", img.shape, "== nansum over wl 10:40:", np.allclose(img, ref, equal_nan=True))
iv.figure.canvas.draw(); print("draw OK; slices:", [type(s).__name__ for s in iv.state.slices])
pv = app.new_data_viewer(ProfileViewer, data=ras); pv.state.x_att = ras.world_component_ids[2]
pv.figure.canvas.draw()
print("ProfileTools modes:", [pv.options_widget().profile_tools.tabs.tabText(i) for i in range(3)] if hasattr(pv.options_widget(), "profile_tools") else "see grep")
from glue_qt.viewers.profile.profile_tools import COLLAPSE_FUNCS; print("collapse funcs:", list(COLLAPSE_FUNCS))
