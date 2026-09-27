"""Checker e2e (offscreen): registered layer action -> dialog OK -> Worker -> maps in the app; ImageViewer on the maps,
ProfileViewer with the residual, subset propagation, SJI rejection path, and a session save attempt."""
import sys, time, warnings; warnings.simplefilter("ignore")
sys.path.insert(0, "/private/tmp/claude-501/-Users-nabil-Git-glue-solar/72764293-8e82-4502-aeff-9f6c3d248202/scratchpad")
import numpy as np
from qtpy import QtCore, QtWidgets
from glue_qt.app import GlueApplication
from glue_qt.config import layer_action
from glue_qt.viewers.image import ImageViewer
from glue_qt.viewers.profile import ProfileViewer
from glue.core.roi import RectangularROI
from glue.core.subset import RoiSubsetState
from irispy.data.test import get_test_data_filenames
from glue_solar.sources.loaders.iris import image_data
from wp6_check_synth import synthetic_cube, synthetic_data
import wp6_fitting
from wp6_fitting import _WORKERS

if __name__ == "__main__":
    app = GlueApplication()
    qapp = QtWidgets.QApplication.instance()
    cube, wl, truth = synthetic_cube(1, shape=(30, 20, 40))
    d = synthetic_data(cube, wl)
    app.data_collection.append(d)
    action = next(a for a in layer_action if "Gaussian" in a.label)
    print("registry item:", type(action).__name__, action._fields, "callback:", action.callback.__name__)

    def press_ok():
        dlg = next(w for w in qapp.topLevelWidgets() if isinstance(w, QtWidgets.QDialog) and w.isVisible())
        print("dialog:", dlg.windowTitle(), "| combo:", dlg.findChild(QtWidgets.QComboBox).currentText())
        dlg.findChild(QtWidgets.QDialogButtonBox).accepted.emit()

    QtCore.QTimer.singleShot(0, press_ok)
    t0 = time.time()
    action.callback(d, app.data_collection)  # exactly what UserAction._do_action does for single=True
    worker = _WORKERS[0]
    progress = [w for w in qapp.topLevelWidgets() if isinstance(w, QtWidgets.QProgressDialog)]
    print("progress dialogs visible while running:", [p.labelText() for p in progress if p.isVisible()])
    while _WORKERS:
        qapp.processEvents(); time.sleep(0.05)
    print(f"fit done in {time.time()-t0:.1f}s; dc:", [x.label for x in app.data_collection],
          "progress visible after:", [p.isVisible() for p in progress])
    maps = app.data_collection[1]
    np.testing.assert_allclose(maps["centroid"], truth["centroid"], rtol=1e-5)
    iv = app.new_data_viewer(ImageViewer, data=maps)
    iv.state.layers[0].attribute = maps.id["centroid"]
    qapp.processEvents()
    print("ImageViewer x/y:", iv.state.x_att, iv.state.y_att, "| format_coord(3,2):", iv.axes.format_coord(3, 2))
    print("ImageViewer axis labels:", iv.axes.get_xlabel(), "/", iv.axes.get_ylabel())
    pv = app.new_data_viewer(ProfileViewer, data=d)
    pv.add_data(d)
    pv.state.layers[0].attribute = d.id["synthetic-gauss1 residual"]
    qapp.processEvents()
    print("ProfileViewer layers:", [(l.layer.label, l.state.attribute.label) for l in pv.layers], "x_att:", pv.state.x_att)
    box = RoiSubsetState(maps.pixel_component_ids[1], maps.pixel_component_ids[0], RectangularROI(0.5, 4.5, 0.5, 3.5))
    app.data_collection.new_subset_group("box", box)
    n_map = maps.subsets[0].to_mask().sum(); n_src = d.subsets[0].to_mask().sum()
    print(f"subset on maps {n_map} px -> source {n_src} px (= {n_map} x 40)")
    # SJI rejection path: the warning is a modal QMessageBox, close it from a timer
    sji = image_data(next(p for p in get_test_data_filenames() if p.name.endswith("SJI_1400_t000.fits")))
    seen = []
    def close_box():
        box = next(w for w in qapp.topLevelWidgets() if isinstance(w, QtWidgets.QMessageBox) and w.isVisible())
        seen.append(box.text()); box.reject()
    QtCore.QTimer.singleShot(0, close_box)
    action.callback(sji, app.data_collection)
    print("SJI right-click ->", seen, "| workers:", len(_WORKERS), "| dc:", len(app.data_collection))
    # session save with SlicedLowLevelWCS coords on the maps
    try:
        app.save_session("/private/tmp/claude-501/-Users-nabil-Git-glue-solar/72764293-8e82-4502-aeff-9f6c3d248202/scratchpad/wp6_chk_e2e.glu")
        print("session save: OK")
    except Exception as e:
        print("session save FAILED:", type(e).__name__, str(e)[:200])
    print("E2E OK")
