"""
Regenerate the IRIS screenshots of the user guide in ``docs/user_guide/images``.

Usage (headless; glue rewrites ``~/.glue/settings.cfg``, so give it a scratch HOME)::

    HOME="$(mktemp -d)" QT_QPA_PLATFORM=offscreen python docs/make_screenshots.py <IRIS data folder>

The folder is searched for observations like the observation browser does. It must hold the extracted raster
archive of OBSID 3400109360 (``iris_l2_20250328_225628_3400109360_raster``), whose eight scans have the
``C II 1336`` and ``Mg II k 2796`` spectral windows, and OBSID 4000255147's extracted raster archive and SJI 1400 file.
"""

import faulthandler
import sys
import time
from pathlib import Path

from glue.config import settings
from glue.main import load_plugins
from glue_qt.app import GlueApplication
from PIL import Image
from qtpy import QtWidgets
from qtpy.QtCore import QSettings, Qt

from astropy.io import fits

from glue_solar.quicklook import quicklook
from glue_solar.sources.loaders import iris
from glue_solar.sources.loaders.iris import QtIRISImporter
from glue_solar.tests.helpers import select_point

OBSID = "3400109360"
WINDOWS = ("C II 1336", "Mg II k 2796")
QUICKLOOK, POINT = "4000255147", (800, 200)  # an exposure and slit pixel of its Mg II k map
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
    load_plugins(require_qt_plugins=True)  # before the application, as glue starts: glue-solar's icon wraps its init
    app = GlueApplication()
    app.resize(1600, 1000)
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
    dialog.resize(1400, 400)
    dialog.show()
    shot("choosing-iris-level-2-data-cubes-and-stacking-raster-cubes.png", dialog)
    dialog.close()

    # 3. the default quicklook of OBSID 4000255147 (Mg II k 2796 and SJI 1400), with a point placed
    raster = next(Path(folder).glob(f"*_{QUICKLOOK}_raster/*_r00000.fits"))
    sji = next(Path(folder).glob(f"*_{QUICKLOOK}_SJI_1400_t000.fits*"))
    header = fits.getheader(raster)  # every window, as ticking the observation in the browser passes them
    windows = [header[f"TDESC{i}"] for i in range(1, header["NWIN"] + 1)]
    viewers = quicklook(app, [*iris.iris_data(str(raster)), iris.iris_data(str(sji))], window=windows)
    panels = [viewers["map"], viewers["spectrogram"], viewers["wavelength"], viewers["spectrum"], *viewers["sji"]]
    wait(viewers=panels)
    select_point(viewers["map"], *POINT)
    shot("quicklook.png", app, panels)
    shot_file = OUT / "quicklook.png"
    Image.open(shot_file).convert("RGB").quantize(256).save(shot_file, optimize=True)  # a palette keeps it < 300 kB
    app.close()


if __name__ == "__main__":
    main(sys.argv[1])
