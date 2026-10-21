"""
Profile glue-solar's observation-browser load of an IRIS observation, and its session restore, as sst_perf_survey.py's
part_iris runs them (every raster window and slit-jaw image ticked, scans stacked).

    python prof.py FOLDER OBSID OUT [--files N] [--restore] [--cprofile] [--patch NAME ...]

--files N keeps the first N raster files; --cprofile writes OUT-load.prof (and OUT-restore.prof); --patch applies a
prototype fix from patches.py. Prints one ``PROF {json}`` line per timing, with the load average before and after.
"""

import argparse
import cProfile
import json
import os
import tempfile
import threading
import time
from functools import partial
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("folder")
parser.add_argument("obsid")
parser.add_argument("out")
parser.add_argument("--files", type=int)
parser.add_argument("--restore", action="store_true")
parser.add_argument("--cprofile", action="store_true")
parser.add_argument("--patch", nargs="*", default=())
args = parser.parse_args()


def report(step, **values):
    print("PROF " + json.dumps({"step": step, "obsid": args.obsid, "patch": list(args.patch), **values}), flush=True)


def timed(name, action, **extra):
    load0 = os.getloadavg()
    profile = cProfile.Profile() if args.cprofile else None
    start = time.perf_counter()
    if profile:
        profile.enable()
    result = action()
    if profile:
        profile.disable()
        profile.dump_stats(f"{args.out}-{name}.prof")
    seconds = round(time.perf_counter() - start, 2)
    report(name, seconds=seconds, cprofile=bool(profile), loadavg_start=load0, loadavg_end=os.getloadavg(), **extra)
    return result


from glue_qt.app import GlueApplication  # noqa: E402
from qtpy.QtWidgets import QApplication  # noqa: E402

import glue_solar  # noqa: E402

glue_solar.setup()
import patches  # noqa: E402

for name in args.patch:
    getattr(patches, name)()

from glue_qt.dialogs.autolinker import autolinker  # noqa: E402
from qtpy import QtWidgets  # noqa: E402

autolinker.AutoLinkPreview.exec = autolinker.AutoLinkPreview.exec_ = lambda self: (self.accept(), 1)[1]
QtWidgets.QMessageBox.exec = QtWidgets.QMessageBox.exec_ = lambda box: QtWidgets.QMessageBox.StandardButton.Ok
QtWidgets.QDialog.exec = QtWidgets.QDialog.exec_ = lambda box: 0

from glue_solar.quicklook import coordinator, quicklook  # noqa: E402
from glue_solar.sources import iris  # noqa: E402
from glue_solar.sources.loaders import iris as loaders  # noqa: E402
from glue_solar.sources.loaders.scan import scan_directory  # noqa: E402

app = GlueApplication()
app.resize(1600, 1000)
app.show()

obs = next(o for o in scan_directory(args.folder) if o.obsid == args.obsid and (o.rasters or o.sji))
if args.files:
    obs.rasters = obs.rasters[: args.files]
picks = [(0, "raster", window) for window in obs.windows] + [(0, "sji", name) for name in sorted(obs.sji)]


def load():
    _, loaded, error = loaders._load(0, [obs], picks, len(obs.rasters) > 1, partial(iris._shown, quicklooks=True),
                                     threading.Event(), lambda *_: None)
    if error:
        raise RuntimeError(error)
    return loaded


loaded = timed("load", load, raster_files=len(obs.rasters), windows=len(obs.windows), sji=len(obs.sji))
if args.restore:
    (shown, window), = iris._quicklooks(loaded)
    coord = coordinator(app.data_collection)
    quicklook(app, shown, window=window)
    for _ in range(50):
        QApplication.instance().processEvents()
    session = Path(tempfile.mkdtemp()) / "prof.glu"
    app.save_session(str(session), include_data=False, absolute_paths=True)
    report("saved", datasets=len(app.data_collection), kb=round(session.stat().st_size / 1e3))

    def restore():
        restored = app.restore_session(str(session), show=False)
        for _ in range(50):
            QApplication.instance().processEvents()
        return restored

    restored = timed("restore", restore)
    report("restored", datasets=len(restored.data_collection), viewers=sum(map(len, restored.viewers)))
