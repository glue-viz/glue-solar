"""
Regenerate the IRIS screenshots of the user guide in ``docs/user_guide/images``.

Usage (headless; glue rewrites ``~/.glue/settings.cfg``, so give it a scratch HOME)::

    HOME="$(mktemp -d)" QT_QPA_PLATFORM=offscreen python docs/make_screenshots.py <IRIS data folder>

The folder is searched for observations like the observation browser does. It must hold the extracted raster
archive of OBSID 3400109360 (``iris_l2_20250328_225628_3400109360_raster``), whose eight scans have the
``C II 1336`` and ``Mg II k 2796`` spectral windows.
"""

import faulthandler
import sys
import time
from pathlib import Path

import numpy as np
from glue.config import settings
from glue_qt.app import GlueApplication
from glue_qt.viewers.image import ImageViewer
from glue_qt.viewers.profile import ProfileViewer
from matplotlib import colormaps
from qtpy import QtWidgets
from qtpy.QtCore import QSettings, Qt
from scipy.ndimage import uniform_filter

from glue_solar.sources.loaders import iris
from glue_solar.sources.loaders.iris import QtIRISImporter, keep_hpc_linked
from glue_solar.tests.helpers import select_point

OBSID = "3400109360"
WINDOWS = ("C II 1336", "Mg II k 2796")
OUT = Path(__file__).parent / "user_guide" / "images"


def _print_box(self, *args):
    """Print a message box instead of blocking on it: offscreen there is nobody to press OK."""
    print("MSGBOX:", self.windowTitle(), "|", self.text(), "|", self.informativeText(), flush=True)
    return 0


def main(folder):
    faulthandler.dump_traceback_later(1800, exit=True)  # a stuck modal dialog would otherwise hang forever
    QtWidgets.QMessageBox.exec = QtWidgets.QMessageBox.exec_ = _print_box
    # the browser remembers its folder in QSettings, which on macOS ignore HOME: keep it in HOME too
    iris.QSettings = lambda org, app: QSettings(str(Path.home() / f"{org}-{app}.ini"), QSettings.IniFormat)
    settings.SHOW_LARGE_DATA_WARNING = False
    app = GlueApplication()
    app.resize(1800, 1200)
    app.show()

    def wait(done=lambda: True, viewers=()):
        """Process events until ``done()`` and every profile worker of ``viewers`` is idle, then draw."""
        deadline = time.time() + 300
        while time.time() < deadline:
            app.app.processEvents()
            workers = [getattr(layer, "_worker", None) for viewer in viewers for layer in viewer.layers]
            if done() and not any(w is not None and (w.running or not w.work_queue.empty()) for w in workers):
                break
            time.sleep(0.1)
        for viewer in viewers:
            viewer.axes.figure.canvas.draw()
        app._log._set_console_button(attention=False)
        for _ in range(10):
            app.app.processEvents()

    def shot(name, widget=app, viewers=()):
        wait(viewers=viewers)
        widget.grab().save(str(OUT / name))
        print("saved", name, flush=True)

    def observation(dialog):
        root = dialog.obs_tree.invisibleRootItem()
        row = next(root.child(i) for i in range(root.childCount()) if root.child(i).text(1) == OBSID)
        dialog.obs_tree.expandItem(row)
        return [row.child(i) for i in range(row.childCount()) if row.child(i).text(0).split(" — ")[0] in WINDOWS]

    # 1. the browser listing every observation of the folder
    dialog = QtIRISImporter(folder)
    wait(lambda: dialog.ok.isEnabled() and not iris._RUNNING)  # the folder is scanned in the background
    observation(dialog)[-1].setCheckState(0, Qt.Checked)
    dialog.resize(1400, 640)
    dialog.show()
    shot("loading-iris-data-2.png", dialog)
    dialog.close()

    # 2. two spectral windows of one observation, stacked
    dialog = QtIRISImporter(next(Path(folder).glob(f"*_{OBSID}_raster")))
    wait(lambda: dialog.ok.isEnabled() and not iris._RUNNING)
    for item in observation(dialog):
        item.setCheckState(0, Qt.Checked)
    dialog.stack.setChecked(True)
    dialog.quicklook.setChecked(False)
    dialog.resize(1400, 340)
    dialog.show()
    shot("choosing-iris-level-2-data-cubes-and-stacking-raster-cubes.png", dialog)
    dialog.ok.click()
    wait(lambda: dialog.ok.isEnabled() and not iris._RUNNING)
    app.data_collection.extend(dialog.datasets)
    keep_hpc_linked(app.data_collection)

    # 3. a pixel of the Mg II k map at its line core, and its spectrum
    data = next(d for d in app.data_collection if d.label.startswith("Mg_II_k_2796"))
    v = app.new_data_viewer(ImageViewer, data=data)
    v.viewer_size = (1000, 560)
    v.layers[0].state.percentile = 99
    v.layers[0].state.cmap = colormaps["viridis"]
    scan0 = np.asarray(data[data.main_components[0]][0])  # (raster step, slit, wavelength)
    core = int(np.nanargmax(np.nanmean(scan0, axis=(0, 1))))
    v.state.x_att, v.state.y_att = data.pixel_component_ids[1], data.pixel_component_ids[2]
    v.state.slices = (0, 0, 0, core)
    v.state.aspect = "auto"
    v.state.reset_limits()
    # a bright region, not a hot pixel or saturated plage, off the masked slit ends and the frame edges
    image = uniform_filter(np.nan_to_num(scan0[:, :, core], nan=0.0), size=5)
    image[image > np.percentile(image, 99)] = 0
    image[np.isfinite(scan0).mean(axis=2) < 0.9] = 0
    image[:3] = image[-3:] = 0
    image[:, :40] = image[:, -40:] = 0
    step, slit = np.unravel_index(np.argmax(image), image.shape)
    wait(viewers=[v])
    select_point(v, step, slit)

    pv = app.new_data_viewer(ProfileViewer, data=data)
    pv.viewer_size = (1000, 460)
    pv.position = (0, 575)
    pv.state.function = "mean"
    pv.state.x_att = next(c for c in pv.state.x_att_helper.choices if getattr(c, "label", None) == "Wavelength")
    wait(viewers=[pv])
    for layer in pv.layers:  # recompute: a layer drawn while the settings changed can keep a stale line
        layer.state.reset_cache()
        layer._calculate_profile(reset=True)
    wait(viewers=[pv])
    pv.state.reset_limits()
    shot("spectrum-at-the-selected-pixel.png", app, [v, pv])
    app.close()


if __name__ == "__main__":
    main(sys.argv[1])
