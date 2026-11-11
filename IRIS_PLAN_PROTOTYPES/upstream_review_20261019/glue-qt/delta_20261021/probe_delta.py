"""
Delta probes (2026-10-21) for the glue-qt register rows added since the D89 review (#360, #363, #364). Each check
prints FAULT / OK with the key numbers. ``--src DIR`` puts a glue-qt tree first on sys.path; ``--g7 FILE`` installs
glue's perf-g7-profile-vminmax ``_update_profile`` and ``_calculate_profile_postthread`` from that file.

Run: HOME=<scratch home> QT_QPA_PLATFORM=offscreen MPLBACKEND=agg python -I probe_delta.py [--src DIR] [--g7 F] [check ...]
"""
import argparse
import importlib.util
import os
import sys
import tempfile
import time
import traceback

parser = argparse.ArgumentParser()
parser.add_argument("--src")
parser.add_argument("--g7")
parser.add_argument("checks", nargs="*")
args = parser.parse_args()
if args.src:
    sys.path.insert(0, args.src)

cfg_dir = os.path.join(os.environ["HOME"], ".glue")  # keep glue-solar's plugin out
os.makedirs(cfg_dir, exist_ok=True)
with open(os.path.join(cfg_dir, "plugins.cfg"), "w") as f:
    f.write("[plugins]\nglue_solar = 0\n")

import numpy as np  # noqa: E402
import glue_qt  # noqa: E402
from glue.core import Data  # noqa: E402
from glue.core.subset import SliceSubsetState  # noqa: E402
from qtpy import QtCore, QtWidgets  # noqa: E402
from glue_qt.utils import get_qapp, process_events  # noqa: E402

print("glue_qt from", os.path.dirname(glue_qt.__file__), "| g7:", bool(args.g7))
qapp = get_qapp()

if args.g7:
    from glue.viewers.profile.layer_artist import ProfileLayerArtist
    spec = importlib.util.spec_from_file_location("g7_layer_artist", args.g7)
    g7 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(g7)
    for name in ("_update_profile", "_calculate_profile_postthread"):
        setattr(ProfileLayerArtist, name, getattr(g7.ProfileLayerArtist, name))

CHECKS = {}


def check(f):
    CHECKS[f.__name__] = f
    return f


def app():
    from glue_qt.app.application import GlueApplication
    a = GlueApplication()
    a.resize(1200, 800)
    a.show()
    process_events()
    assert "glue_solar" not in sys.modules
    return a


def spin(ms):
    loop = QtCore.QEventLoop()
    QtCore.QTimer.singleShot(ms, loop.quit)
    loop.exec_()


@check
def closebox_leaves_closed_unset():
    """#360: a viewer closed by its window's close box (QMdiSubWindow.close) emits window_closed, _closed stays False."""
    from glue_qt.viewers.image import ImageViewer
    a = app()
    d = Data(label="d", x=np.zeros((3, 5, 5)))
    a.data_collection.append(d)
    v = a.new_data_viewer(ImageViewer, data=d)
    process_events()
    emitted = []
    v.window_closed.connect(lambda: emitted.append(True))
    v._confirm_close = lambda: True  # the user's OK in 'Confirm Close'
    v._mdi_wrapper.close()  # what the title bar's close box does
    closed, listed = v._closed, any(v in tab for tab in a.viewers)
    QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)
    process_events()
    later = any(v in tab for tab in a.viewers)
    a.close()
    return ("FAULT" if emitted and not closed else "OK") + \
        f": window_closed={bool(emitted)}, _closed={closed}, still in app.viewers that turn={listed}, after events={later}"


@check
def gluestate_lists_closed():
    """#364: data removed and session saved in one turn: the closed Image viewer is saved and the restore fails."""
    from glue_qt.app.application import GlueApplication
    from glue_qt.viewers.image import ImageViewer
    a = app()
    d = Data(label="gone", x=np.zeros((3, 5, 5)))
    keep = Data(label="kept", y=np.zeros(4))
    a.data_collection.append(d)
    a.data_collection.append(keep)
    v = a.new_data_viewer(ImageViewer, data=d)
    process_events()
    a.data_collection.remove(d)  # closes v (its last layer)
    closed = v._closed
    saved = [len(tab) for tab in a.viewers]
    path = os.path.join(tempfile.mkdtemp(dir=os.environ["HOME"]), "s.glu")
    a.save_session(path)  # same turn: v not yet deleted
    a.close()
    process_events()
    try:
        b = GlueApplication.restore_session(path)
        process_events()
        result = f"restored, {sum(len(t) for t in b.viewers)} viewers"
        b.close()
        fault = False
    except Exception as e:  # noqa: BLE001
        result, fault = f"restore raised {type(e).__name__}: {str(e).splitlines()[0][:90]}", True
    return ("FAULT" if fault else "OK") + f": viewer _closed={closed}, saved viewers per tab={saved}; {result}"


def _profile_moves(workaround, moves=6):
    from glue_qt.viewers.profile import ProfileViewer
    from glue_qt.viewers.profile.layer_artist import QThreadedProfileLayerArtist as Q
    from glue.core import Subset
    from glue.core.message import ComputationEndedMessage
    runs, ends = [], []
    original = Q._calculate_profile_thread

    def counting(self, reset=False):
        if isinstance(self.state.layer, Subset):
            runs.append(time.perf_counter())
        return original(self, reset=reset)

    Q._calculate_profile_thread = counting  # before the viewer: the worker binds it at setup
    a = app()
    rng = np.random.default_rng(1)
    d = Data(label="big", x=rng.random((41, 500, 500), dtype=np.float32))  # 1.025e7 > glue-qt's 1e7
    a.data_collection.append(d)

    def point(i):
        return SliceSubsetState(d, [slice(None), slice(i, i + 1), slice(i, i + 1)])

    group = a.data_collection.new_subset_group("pt", point(0))
    pv = a.new_data_viewer(ProfileViewer, data=d)
    a.session.hub.subscribe(pv, ComputationEndedMessage,
                            handler=lambda m: ends.append(time.perf_counter())
                            if isinstance(m.sender.state.layer, Subset) else None)
    spin(1500)
    counts, waits = [], []
    for i in range(1, moves + 1):
        runs.clear()
        ends.clear()
        t0 = time.perf_counter()
        group.subset_state = point(i)
        if workaround:  # glue-solar's `_Refit._limits` (#363)
            def limits():
                for layer in pv.layers:
                    if isinstance(layer.state.layer, Subset):
                        layer.state.update_limits()
            QtCore.QTimer.singleShot(0, limits)
        spin(700)
        counts.append(len(runs))
        waits.append((ends[-1] - t0) * 1e3 if ends else float("nan"))
    a.close()
    Q._calculate_profile_thread = original
    return counts, waits


@check
def profile_limits_requeue():
    """#363: a subset move on a threaded profile runs the worker twice (v_min/v_max set as it ends)."""
    counts, waits = _profile_moves(False)
    return ("FAULT" if max(counts) > 1 else "OK") + \
        f": worker runs per move {counts}; move to last ComputationEnded median {np.nanmedian(waits):.0f} ms"


@check
def profile_limits_requeue_with_refit():
    """#363 with glue-solar's workaround: limits set on the GUI thread first."""
    counts, waits = _profile_moves(True)
    return ("FAULT" if max(counts) > 1 else "OK") + \
        f": worker runs per move {counts}; move to last ComputationEnded median {np.nanmedian(waits):.0f} ms"


def _watchdog():
    for w in qapp.topLevelWidgets():
        if isinstance(w, QtWidgets.QDialog) and w.isVisible():
            print(f"  (watchdog rejected dialog {w.windowTitle()!r})")
            w.reject()


_wd = QtCore.QTimer()
_wd.setInterval(1000)
_wd.timeout.connect(_watchdog)
_wd.start()

for name in args.checks or list(CHECKS):
    try:
        print(f"[{name}] {CHECKS[name]()}")
    except Exception:  # noqa: BLE001
        print(f"[{name}] ERROR {traceback.format_exc().strip().splitlines()[-1]}")
        traceback.print_exc()
    sys.stdout.flush()
