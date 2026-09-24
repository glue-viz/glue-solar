"""Checker extras for WP4: OBSID guard types, data-only subset after add (data tree), closed viewer in registry,
QInputDialog flow, coords=None guard, test-1 assertion form."""
import os, sys, warnings, logging; warnings.simplefilter("ignore")
os.environ["QT_QPA_PLATFORM"] = "offscreen"; os.environ["MPLBACKEND"] = "agg"
import numpy as np
from irispy.io import read_files
from glue.core import Data
from glue_qt.app.application import GlueApplication
from glue_qt.viewers.image import ImageViewer
from qtpy import QtWidgets, QtCore
from irispy.data.test import get_test_data_filenames
from glue_solar.sources.loaders.iris import image_data, raster_data
from wp4_common import add_time, add_slit, slit_subset_state, link_hpc, link_time, sync_slices, whisker, quicklook
fs = [str(f) for f in get_test_data_filenames()]
sji_path = [f for f in fs if "sns" in f and "SJI_1400" in f][0]
cube = read_files(sji_path, memmap=False, uncertainty=False)
sji = image_data(sji_path); add_time(sji, cube); add_slit(sji, cube)
ras = raster_data([[f for f in fs if "sns" in f and "raster_t000" in f][0]], windows=["Si IV 1403"])[0]
stack = raster_data(sorted(f for f in fs if "20140329" in f and "raster_t000_r0000" in f)[:3], ["Mg II k 2796"], stack=True)[0]
# (a) OBSID guard
print("(a) OBSID:", repr(sji.meta.get("OBSID")), repr(ras.meta.get("OBSID")), repr(stack.meta.get("OBSID")), "| sns equal:", sji.meta.get("OBSID") == ras.meta.get("OBSID"), "| stack type", type(stack.meta).__name__)
# (b) data-only subset created AFTER the data is in the app (data tree gets SubsetCreateMessage with 0 subset_groups)
errors = []
class H(logging.Handler):
    def emit(self, r): errors.append(r.getMessage()[:120])
logging.getLogger().addHandler(H())
app = GlueApplication(); app.add_datasets([sji, ras]); dc = app.data_collection
try:
    s_after = sji.new_subset(slit_subset_state(sji), label="Slit-after"); app.app.processEvents()
    print("(b) data-only subset after add: created OK | logged errors:", errors[-2:] if errors else [])
except Exception as e:
    print("(b) data-only subset after add raised:", type(e).__name__, e)
sji.remove_subset(s_after) if hasattr(sji, "remove_subset") else None
# (c) closed viewer stays in the registry
dc.add_link(link_hpc(dc)); link_time(dc, sji, ras)
va = app.new_data_viewer(ImageViewer, data=sji); vb = app.new_data_viewer(ImageViewer, data=ras)
hooked = sync_slices(app)(None)
vb.close(warn=False); app.app.processEvents()
print("(c) after closing B: viewers", len(app.viewers[0]), "| hooked", len(hooked), end=" | ")
try:
    va.state.slices = (5, 0, 0); print("drive A after B closed: OK, B state now", vb.state.slices)
except Exception as e:
    print("drive A after B closed raised:", type(e).__name__, e)
# (d) whisker_plot menubar flow with QInputDialog auto-accepted
def whisker_plot(session, data_collection):
    app = session.application
    rasters = [d for d in data_collection if d.ndim >= 3 and "em.wl" in getattr(d.coords, "world_axis_physical_types", ())]
    if not rasters:
        return
    label, ok = QtWidgets.QInputDialog.getItem(app, "Whisker plot", "Raster window", [d.label for d in rasters], 0, False)
    if ok:
        return whisker(app, rasters[[d.label for d in rasters].index(label)])
def accept():
    w = app.app.activeModalWidget()
    if isinstance(w, QtWidgets.QInputDialog): w.accept()
    else: QtCore.QTimer.singleShot(50, accept)
QtCore.QTimer.singleShot(50, accept)
v = whisker_plot(app.session, dc)
print("(d) whisker_plot via QInputDialog:", type(v).__name__, "x", v.state.x_att, "y", v.state.y_att, "ref", v.state.reference_data.label[:12], "| hooked now", len(hooked))
# (e) quicklook with a coords=None dataset in the list
try:
    quicklook(app, [Data(label="table", x=np.arange(3))]); print("(e) coords=None dataset: OK")
except Exception as e:
    print("(e) coords=None dataset raises:", type(e).__name__, e)
# (f) test-1 assertion form
secs = sji[sji.world_component_ids[0]][:, 0, 0]
dt = (sji["Time"][:, 0, 0] - sji["Time"][0, 0, 0]) / np.timedelta64(1, "s")
print("(f) max |dT - dTimeUtc| =", np.abs(dt - (secs - secs[0])).max(), "s (< 1e-6)")
print("(g) Slit subset colour/label:", sji.subsets[0].label, sji.subsets[0].style.color)
app.close(); print("OK")
