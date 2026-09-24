import warnings; warnings.simplefilter("ignore")
import numpy as np
from glue_qt.app import GlueApplication
from glue_qt.viewers.profile import ProfileViewer
from glue_qt.viewers.image import ImageViewer
from glue.viewers.image.state import AggregateSlice
from irispy.data.test import get_test_data_filenames
from glue_solar.sources.loaders.iris import raster_data
path = next(p for p in get_test_data_filenames() if p.name == "iris_l2_20210905_001833_3620258102_raster_t000_r00000.fits" and p.parent.name == "sns")
[ras] = raster_data([path], ["Mg II k 2796"])
app = GlueApplication(); app.data_collection.append(ras)
iv = app.new_data_viewer(ImageViewer, data=ras); iv.state.x_att, iv.state.y_att = ras.pixel_component_ids[1], ras.pixel_component_ids[0]
pv = app.new_data_viewer(ProfileViewer, data=ras); pv.state.x_att = ras.world_component_ids[2]; pv.state.function = "mean"
tools = pv.toolbar.tools["profile-analysis"]._profile_tools
print("ProfileTools:", type(tools).__name__, "| tabs:", [tools.ui.tabs.tabText(i) for i in range(tools.ui.tabs.count())])
tools.ui.tabs.setCurrentIndex(2); print("mode:", tools.mode, "| collapse_function default:", tools.collapse_function.__name__)
# simulate a drawn wavelength range (world values of the profile x axis: metres today, Angstrom after WP1)
wl = ras.coords.pixel_to_world_values(np.arange(ras.shape[2]), 0, 0)[0]
tools.rng_mode.state.x_min, tools.rng_mode.state.x_max = wl[10], wl[40]
print("x_range:", tools.rng_mode.state.x_range, "(units:", ras.coords.world_axis_units[0], ")")
tools.collapse_function = np.nansum; tools._on_collapse()
sl = iv.state.slices[2]; print("image slice after collapse:", type(sl).__name__, sl.slice, sl.function.__name__)
img = iv.layers[0].state.get_sliced_data(); ref = np.nansum(ras[ras.main_components[0]][:, :, 10:40], axis=2)
print("collapsed map == nansum over wl 10:40 (upper bound exclusive) ->", img.shape, np.allclose(img, ref, equal_nan=True))
