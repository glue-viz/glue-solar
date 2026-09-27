"""Qt checks for WP6: start_fit (Worker + QProgressDialog) with scheduler='processes' keeps the event loop live."""
import sys, time, warnings
warnings.simplefilter("ignore")
sys.path.insert(0, "/private/tmp/claude-501/-Users-nabil-Git-glue-solar/72764293-8e82-4502-aeff-9f6c3d248202/scratchpad")
import numpy as np
from qtpy import QtCore
from glue.core import DataCollection
from glue_qt.utils import get_qapp
from glue_qt.config import layer_action
from wp6_check_synth import synthetic_cube, synthetic_data
import wp6_fitting
from wp6_fitting import start_fit, _WORKERS

if __name__ == "__main__":
    app = get_qapp()
    print("layer_action registered:", [a.label for a in layer_action if "Gaussian" in a.label], "single/data:",
          [(a.single, a.data) for a in layer_action if "Gaussian" in a.label])
    cube, wl, truth = synthetic_cube(1, shape=(60, 50, 40))
    d = synthetic_data(cube, wl)
    dc = DataCollection([d])
    ticks = []
    timer = QtCore.QTimer(); timer.timeout.connect(lambda: ticks.append(time.time())); timer.start(50)
    t0 = time.time()
    worker = start_fit(d, dc, 1, None, scheduler="processes")
    print("workers alive:", len(_WORKERS))
    worker.finished.connect(app.quit)
    app.exec()
    app.processEvents()
    print(f"elapsed {time.time()-t0:.1f}s, GUI timer ticks while fitting: {len(ticks)}, workers alive after: {len(_WORKERS)}")
    print("dc:", [x.label for x in dc], "links:", len(dc.links), "source comps:", [c.label for c in d.main_components])
    np.testing.assert_allclose(dc[1]["centroid"], truth["centroid"], rtol=1e-5)
    # test idiom: synchronous wait instead of app.exec()
    worker = start_fit(d, dc, 2, None, scheduler="single-threaded")
    worker.wait(); app.processEvents()
    print("sync idiom:", [x.label for x in dc], "links:", len(dc.links))
    print("QT OK")
