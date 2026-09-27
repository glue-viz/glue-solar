"""Checker: does the QProgressDialog created in start_fit survive the call (Python-owned, no parent)? Plus rejection paths."""
import sys, time, warnings; warnings.simplefilter("ignore")
sys.path.insert(0, "/private/tmp/claude-501/-Users-nabil-Git-glue-solar/72764293-8e82-4502-aeff-9f6c3d248202/scratchpad")
import numpy as np
from qtpy import QtWidgets
from glue_qt.utils import get_qapp
from glue_qt.utils.threading import Worker
from glue.core import Data, DataCollection
from astropy.wcs import WCS
from wp6_check_synth import synthetic_cube, synthetic_data
import wp6_fitting
from wp6_fitting import start_fit, gaussian_fit_data, add_fit_products, wavelength_angstrom


def dialogs():
    return [(p.labelText(), p.isVisible()) for p in QtWidgets.QApplication.topLevelWidgets() if isinstance(p, QtWidgets.QProgressDialog)]


def start_fit_fixed(data, data_collection, n_gaussians=1, rest=None, scheduler="processes"):
    progress = QtWidgets.QProgressDialog(f"Fitting {n_gaussians} Gaussian(s) to {data.label}…", None, 0, 0)
    progress.setWindowTitle("Gaussian fit")
    progress.show()
    worker = Worker(gaussian_fit_data, data, n_gaussians, rest, scheduler)
    worker.progress = progress  # keep the parentless dialog alive for as long as the fit runs
    worker.result.connect(lambda result: add_fit_products(data, data_collection, *result))
    worker.finished.connect(progress.close)
    worker.finished.connect(lambda: wp6_fitting._WORKERS.remove(worker))
    wp6_fitting._WORKERS.append(worker)
    worker.start()
    return worker


if __name__ == "__main__":
    app = get_qapp()
    cube, wl, truth = synthetic_cube(1, shape=(60, 50, 40))
    d = synthetic_data(cube, wl)
    dc = DataCollection([d])
    for label, fn in (("brief start_fit", start_fit), ("fixed start_fit", start_fit_fixed)):
        worker = fn(d, dc, 1, None, scheduler="processes")
        app.processEvents()
        print(f"{label}: progress dialogs right after return: {dialogs()}")
        visible_ticks = 0
        while wp6_fitting._WORKERS:
            app.processEvents(); time.sleep(0.05); visible_ticks += any(v for _, v in dialogs())
        app.processEvents()
        print(f"  visible ticks during the fit: {visible_ticks}; after finish: {dialogs()}; dc: {[x.label for x in dc]}")
        d = synthetic_data(cube, wl); dc = DataCollection([d])
    aia = Data(label="aia", x=np.zeros((4, 4)))
    w2 = WCS(naxis=2); w2.wcs.ctype = ["HPLN-TAN", "HPLT-TAN"]; w2.wcs.cunit = ["arcsec", "arcsec"]
    aia.coords = w2
    for name, obj in (("AIA-like astropy WCS", aia), ("no coords", Data(label="table", x=np.arange(5)))):
        try:
            wavelength_angstrom(obj)
        except ValueError as e:
            print(f"{name}: ValueError: {e}")
    print("PROGRESS CHECK DONE")
