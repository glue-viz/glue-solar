"""Slit subset created in the loader (before the Data joins a DataCollection), then quicklook edge cases."""
import os, warnings; warnings.simplefilter("ignore")
os.environ["QT_QPA_PLATFORM"] = "offscreen"; os.environ["MPLBACKEND"] = "agg"
import numpy as np
from irispy.io import read_files
from glue_qt.app.application import GlueApplication
from glue_qt.viewers.image import ImageViewer
from irispy.data.test import get_test_data_filenames
from glue_solar.sources.loaders.iris import image_data, raster_data
from wp4_common import add_slit, add_time, slit_subset_state, quicklook
fs = [str(f) for f in get_test_data_filenames()]
sji_path = [f for f in fs if "sns" in f and "SJI_1400" in f][0]
cube = read_files(sji_path, memmap=False, uncertainty=False)
sji = image_data(sji_path); add_time(sji, cube); add_slit(sji, cube)
subset = sji.new_subset(slit_subset_state(sji), label="Slit")            # in the loader: no DataCollection yet
print("subset before dc:", subset.label, "| sji.subsets", [s.label for s in sji.subsets])
app = GlueApplication(); app.add_datasets([sji])
v = app.new_data_viewer(ImageViewer, data=sji); v.figure.canvas.draw()
layer = [l for l in v.layers if l.layer is subset][0]
bounds = [(0, sji.shape[1] - 1, sji.shape[1]), (0, sji.shape[2] - 1, sji.shape[2])]
v.state.slices = (30, 0, 0); v.figure.canvas.draw()
print("viewer layers:", [(type(l).__name__, l.enabled) for l in v.layers], "| flagged column at slice 30:", np.unique(np.where(np.asarray(layer.subset_array(bounds)) > 0)[1]), "| subset_groups", len(app.data_collection.subset_groups), "| edit subset", app.session.edit_subset_mode.edit_subset)
# quicklook with only an SJI, then only rasters
print("quicklook(SJI only):", [type(x).__name__ for x in quicklook(app, [sji])])
ras = raster_data([[f for f in fs if "sns" in f and "raster_t000" in f][0]], windows=["Si IV 1403"]); app.add_datasets(ras)
print("quicklook(rasters only):", [type(x).__name__ for x in quicklook(app, ras)], "| viewers open:", len(app.viewers[0]))
app.close(); print("OK")
