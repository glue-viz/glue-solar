import warnings, sys, time; warnings.simplefilter("ignore")
import numpy as np
from astropy.modeling import models as m
from astropy.modeling.fitting import LMLSQFitter, parallel_fit_dask
from glue_qt.utils import get_qapp
from glue_qt.utils.threading import Worker
from qtpy import QtCore
def fit():
    x = np.linspace(-1, 1, 20); data = np.exp(-x**2/0.1)[None, None, :].repeat(60, 0).repeat(50, 1)
    return parallel_fit_dask(data=data, fitting_axes=2, world=(x,), model=m.Gaussian1D(1, 0, 0.3), fitter=LMLSQFitter(), scheduler="processes")
if __name__ == "__main__":
    app = get_qapp()
    out = {}
    w = Worker(fit)
    w.result.connect(lambda r: (out.__setitem__("r", r), app.quit()))
    w.error.connect(lambda e: (out.__setitem__("e", e), app.quit()))
    ticks = []
    timer = QtCore.QTimer(); timer.timeout.connect(lambda: ticks.append(time.time())); timer.start(50)
    t0 = time.time(); w.start(); app.exec()
    print("Worker+processes:", "OK" if "r" in out else out.get("e"), "shape", out["r"].amplitude.shape if "r" in out else None, "elapsed %.1fs" % (time.time()-t0), "GUI timer ticks while fitting:", len(ticks))
