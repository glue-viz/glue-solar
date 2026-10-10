"""
A check of the built app, which runs it in place of glue with the files of an IRIS observation, and with
``QT_QPA_PLATFORM=offscreen`` to keep it off the screen; from the checkout::

    GLUE_SOLAR_APP_CHECK=packaging/macos/smoke.py "packaging/macos/dist/app/Glue Solar.app/Contents/MacOS/glue-solar" \
        raster.fits sji.fits

It starts glue as ``glue`` does, checks that glue-solar's menu entries are there on PyQt6 and that glue's IPython
terminal starts, loads the files and opens their quicklook as ``glue --startup=iris_quicklook`` does, adds irispy's
radiometric calibration of the raster, which needs irispy's response files, and prints when the window showed and the
seconds each step took. It exits 1 at the first failure.
"""

import os
import sys
import time
import traceback

import numpy as np
import qtpy
from glue.main import list_loaded_plugins
from glue_qt.app import GlueApplication
from glue_qt.main import load_data_files, start_glue
from qtpy import QtCore, QtGui


def check(app):
    from glue_solar.quicklook import QuicklookImageViewer, _role
    from glue_solar.sources.calibration import radiometric_calibration

    try:
        print(f"window shown at {time.time():.3f}", flush=True)
        entries = {action.text() for action in app.findChildren(QtGui.QAction)}
        assert qtpy.API_NAME == "PyQt6", qtpy.API_NAME
        assert "glue_solar" in list_loaded_plugins(), list_loaded_plugins()
        assert {"IRIS: browse observations…", "IRIS: quicklook…"} <= entries, entries
        assert app.has_terminal()
        began = time.perf_counter()
        app.add_datasets(load_data_files(sys.argv[1:]))
        app.run_startup_action("iris_quicklook")
        app.app.processEvents()
        assert any(isinstance(viewer, QuicklookImageViewer) for tab in app.viewers for viewer in tab)
        print(f"quicklook {time.perf_counter() - began:.2f} s", flush=True)
        began = time.perf_counter()
        raster = next(data for data in app.data_collection if _role(data) == "raster")
        assert np.isfinite(raster[radiometric_calibration(raster)]).any()
        print(f"radiometric calibration {time.perf_counter() - began:.2f} s", flush=True)
    except BaseException:
        traceback.print_exc()
        os._exit(1)
    app.close()  # as glue quits


def start(app, *args, **kwargs):
    QtCore.QTimer.singleShot(0, lambda: check(app))  # once glue shows its window
    return glue_start(app, *args, **kwargs)


if __name__ == "__main__":
    glue_start, GlueApplication.start = GlueApplication.start, start
    start_glue()
