"""SJI slider cost vs frame index (gwcs SJI, irispy 0.9.0)."""
import os
import time

from glue.core import DataCollection
from glue_qt.app import GlueApplication
from glue_qt.viewers.image import ImageViewer

import glue_solar.sources.loaders.iris as L

SJI = os.environ.get("SJI", "~/DATA/IRIS/534d789bb0a2821fb2b78eb36d1d6753-iris_l2_20130902_163935_4000255147_SJI_1400_t000.fits.gz")


def test_sji(qtbot):
    t = time.perf_counter(); d = L.image_data(SJI); print("LOAD", round(time.perf_counter() - t, 2), d.shape, d.coords._wcs.__class__.__name__, flush=True)
    app = GlueApplication(DataCollection([d])); qtbot.addWidget(app)
    v = app.new_data_viewer(ImageViewer, data=d)
    v.figure.canvas.draw()
    n = d.shape[0]
    out = []
    for step in (1, 2, n // 2, n // 2 + 1, n - 2, n - 1, 3):
        sl = list(v.state.slices); sl[0] = step
        t = time.perf_counter(); v.state.slices = tuple(sl); t1 = time.perf_counter(); v.figure.canvas.draw(); t2 = time.perf_counter()
        out.append(f"{step}:{t1 - t:.3f}+{t2 - t1:.3f}")
    print("SJISLIDER", " ".join(out), flush=True)
    app.close()
