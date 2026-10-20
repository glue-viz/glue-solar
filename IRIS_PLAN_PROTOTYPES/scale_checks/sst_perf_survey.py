"""
The second SST performance survey (D100, `wp10-perf-survey-2`): glue-solar main on large SSTRED cubes, measured as the
2026-10-10 survey measured them (GLUE_SPEED.md), plus the quicklook-era parts. Linux and macOS.

    python sst_perf_survey.py PART CUBE [CUBE2]
    python sst_perf_survey.py iris FOLDER OBSID

PART is ``file`` (glue's File > Open, a new Image viewer, slider steps, the Profile button, a Pixel click and drag with
the Profile open, session save and restore), ``quicklook`` (an SST quicklook: open, a point click and drag, a scan step,
a path diagram), ``link`` (two cubes of one observation: their quicklooks linked, the point moved) or ``iris`` (an
IRIS observation in FOLDER through the observation browser and its quicklook, as the 2026-10-10 survey's IRIS rows:
open, each panel's slider steps, a point click and drag on the map, session save and restore). Run each part in a
fresh process, from an empty folder, with an isolated HOME and offscreen Qt; ``run_survey.sh`` does that for a list of
cubes. Each measurement prints one line ``SURVEY {json}``; times are seconds to idle (no pending draw, profile or
coordinator timer), memory in GB.
"""

import json
import os
import platform
import resource
import statistics
import sys
import tempfile
import threading
import time
from importlib.metadata import version
from pathlib import Path

GB = 1e9


def _rusage_macos():
    import ctypes

    class RU(ctypes.Structure):
        _fields_ = [("uuid", ctypes.c_uint8 * 16)] + [(n, ctypes.c_uint64) for n in (
            "user_time", "system_time", "pkg_idle_wkups", "interrupt_wkups", "pageins", "wired_size", "resident_size",
            "phys_footprint", "proc_start_abstime", "proc_exit_abstime", "child_user_time", "child_system_time",
            "child_pkg_idle_wkups", "child_interrupt_wkups", "child_pageins", "child_elapsed_abstime",
            "diskio_bytesread", "diskio_byteswritten")]

    libc, ru = ctypes.CDLL("/usr/lib/libSystem.B.dylib"), RU()
    libc.proc_pid_rusage(os.getpid(), 2, ctypes.byref(ru))
    return ru.resident_size, ru.diskio_bytesread


def memory_and_reads():
    """The resident memory and the bytes read from disk so far, of this process."""
    if sys.platform == "darwin":
        return _rusage_macos()
    rss = int(Path("/proc/self/statm").read_text().split()[1]) * resource.getpagesize()
    io = dict(line.split(": ") for line in Path("/proc/self/io").read_text().splitlines())
    return rss, int(io["read_bytes"])


def physical_memory():
    return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")


class Sampler(threading.Thread):
    """The peak resident memory every 20 ms since `mark`; stops the run before the machine runs out (85% of RAM)."""

    def __init__(self):
        super().__init__(daemon=True)
        self.peak, self.limit = 0, 0.85 * physical_memory()

    def mark(self):
        self.peak = memory_and_reads()[0]

    def run(self):
        while True:
            rss = memory_and_reads()[0]
            self.peak = max(self.peak, rss)
            if rss > self.limit:
                print(f"SURVEY {json.dumps({'abort': f'resident memory {rss / GB:.1f} GB past 85% of RAM'})}", flush=True)
                os._exit(3)
            time.sleep(0.02)


SAMPLER = Sampler()


def report(name, **values):
    rss, read = memory_and_reads()
    values.update(memory_gb=round(rss / GB, 2), peak_gb=round(SAMPLER.peak / GB, 2), read_gb=round(read / GB, 2))
    print(f"SURVEY {json.dumps({'part': PART, 'step': name, **values}, default=str)}", flush=True)


def answer_dialogs():
    """
    Answer glue's modal dialogs as a user clicking through them would, and report each: message boxes OK, such as glue's
    on adding large data to a Profile viewer, the autolinker's Apply, any other dialog cancelled.
    """
    from glue_qt.dialogs.autolinker import autolinker
    from qtpy import QtWidgets

    def message(box):
        report("dialog", text=f"{box.text()} {box.informativeText()}"[:300])
        return QtWidgets.QMessageBox.StandardButton.Ok

    def dialog(box):
        report("dialog", text=f"{type(box).__name__} {box.windowTitle()} (cancelled)")
        return 0

    autolinker.AutoLinkPreview.exec = autolinker.AutoLinkPreview.exec_ = lambda self: (self.accept(), 1)[1]
    QtWidgets.QMessageBox.exec = QtWidgets.QMessageBox.exec_ = message
    QtWidgets.QDialog.exec = QtWidgets.QDialog.exec_ = dialog


def busy(app, coord):
    for tab in app.viewers:
        for viewer in tab:
            canvas = viewer.figure.canvas  # a canvas out of sight draws only once shown (glue-solar's quicklook panels)
            if getattr(canvas, "_draw_pending", False) and canvas.isVisible() and not canvas.visibleRegion().isEmpty():
                return True
            for layer in viewer.layers:
                if getattr(layer, "is_computing", False):
                    return True
                worker = getattr(layer, "_worker", None)
                if worker is not None and not worker.work_queue.empty():
                    return True
    return coord is not None and coord._timer.isActive()


def to_idle(app, coord, start, quiet=0.05, timeout=900):
    """Seconds from ``start`` until the app went idle, the quiet window that confirms it not counted."""
    qt = QApplication.instance()
    calm = None
    while time.perf_counter() - start < timeout:
        qt.processEvents()
        if busy(app, coord):
            calm = None
        else:
            calm = calm or time.perf_counter()
            if time.perf_counter() - calm > quiet:
                return round(calm - start, 3)
        time.sleep(0.001)
    return None


def timed(app, coord, action):
    start = time.perf_counter()
    action()
    return to_idle(app, coord, start)


def median_ms(values):
    values = [value for value in values if value is not None]
    return round(statistics.median(values) * 1e3, 1) if values else None


def point(cube, y, x, scan=0):
    """A Pixel point of ``cube`` at ``y, x``, its scan and Stokes fixed, its tuning free, as a quicklook click is."""
    slices = [slice(scan, scan + 1)] + [slice(0, 1)] * (cube.ndim - 4) + [slice(None), slice(y, y + 1), slice(x, x + 1)]
    return PixelSubsetState(cube, slices)


def save_and_restore(app):
    session = Path(tempfile.mkdtemp()) / "survey.glu"
    start = time.perf_counter()
    app.save_session(str(session), include_data=False, absolute_paths=True)
    report("session save", seconds=round(time.perf_counter() - start, 3), kb=round(session.stat().st_size / 1e3))
    start = time.perf_counter()
    try:
        restored = app.restore_session(str(session), show=False)
        report("session restore", seconds=to_idle(restored, None, start), viewers=sum(map(len, restored.viewers)))
    except Exception as error:  # noqa: BLE001 - the survey records the failure
        report("session restore", error=f"{type(error).__name__}: {error}")


def part_file(app, path):
    from glue.core.data_factories.helpers import auto_data, load_data
    from glue.core.edit_subset_mode import ReplaceMode
    from glue_qt.viewers.image import ImageViewer

    start = time.perf_counter()
    cube = load_data(path, factory=auto_data)  # File > Open with 'Auto'
    app.add_datasets([cube])  # with glue-qt's autolinker
    report("open", seconds=round(time.perf_counter() - start, 3), shape=cube.shape)
    viewer = None

    def new():
        nonlocal viewer
        viewer = app.new_data_viewer(ImageViewer, data=cube)

    report("image viewer", seconds=timed(app, None, new))
    shown = {viewer.state.x_att.axis, viewer.state.y_att.axis}
    for axis in (axis for axis in range(cube.ndim) if axis not in shown and cube.shape[axis] > 1):
        def step(index):
            slices = list(viewer.state.slices)
            slices[axis] = index
            return timed(app, None, lambda: setattr(viewer.state, "slices", tuple(slices)))

        first = [step(index) for index in range(1, cube.shape[axis])]
        warm = [step(index) for index in list(range(cube.shape[axis])) * 2]
        report(f"slider step, axis {axis}", first_ms=median_ms(first), warm_ms=median_ms(warm), n=cube.shape[axis])
    SAMPLER.mark()
    start = time.perf_counter()
    viewer.toolbar.tools["profile-viewer"].activate()  # glue-qt's Profile button
    frozen = time.perf_counter() - start
    report("profile button", frozen_s=round(frozen, 3), seconds=to_idle(app, None, start))
    mode = app.session.edit_subset_mode
    *_, rows, columns = cube.shape
    y, x = rows // 2, columns // 2
    report("pixel click with the profile", seconds=timed(
        app, None, lambda: mode.update(app.data_collection, point(cube, y, x), override_mode=ReplaceMode)))
    moves = [timed(app, None, lambda i=i: mode.update(app.data_collection, point(cube, y + 2 * i, x + 3 * i),
                                                      override_mode=ReplaceMode)) for i in range(1, 11)]
    report("pixel drag with the profile", move_ms=median_ms(moves[2:]), first_ms=median_ms(moves[:1]))
    save_and_restore(app)


def part_quicklook(app, path):
    import numpy as np

    from glue_solar.quicklook import coordinator, quicklook
    from glue_solar.sources.sst import sst_data

    cube = sst_data(path)
    coord = coordinator(app.data_collection)
    views = {}
    report("quicklook open", seconds=timed(app, coord, lambda: views.update(quicklook(app, [cube]))))
    group = next(g for g in coord._owners if g.subset_state.reference_data is cube)
    *_, rows, columns = cube.shape
    y, x = rows // 3, columns // 3  # off the centre, where the quicklook puts its first point
    report("point click", seconds=timed(app, coord, lambda: setattr(group, "subset_state", point(cube, y, x))))
    moves = [timed(app, coord, lambda i=i: setattr(group, "subset_state", point(cube, y + 2 * i, x + 3 * i)))
             for i in range(1, 11)]
    report("point drag", move_ms=median_ms(moves[2:]), first_ms=median_ms(moves[:1]))
    scans = cube.shape[0]
    if scans > 1:
        steps = []
        for index in list(range(1, scans)) + [0]:
            slices = list(views["map"].state.slices)
            slices[0] = index
            steps.append(timed(app, coord, lambda s=tuple(slices): setattr(views["map"].state, "slices", s)))
        report("scan step", step_ms=median_ms(steps), n=scans)
    tool = views["map"].toolbar.tools["solar:path"]
    xs, ys = np.array([0.3, 0.7]) * columns, np.array([0.4, 0.6]) * rows
    report("path diagram", seconds=timed(app, coord, lambda: tool._open_or_update(xs, ys)))


def part_link(app, paths):
    from glue_solar.quicklook import coordinator, quicklook
    from glue_solar.sources.loaders.iris import link_hpc
    from glue_solar.sources.sst import sst_data

    cubes = [sst_data(path) for path in paths]
    coord = coordinator(app.data_collection)
    for cube in cubes:
        report(f"quicklook open {cube.label}", seconds=timed(app, coord, lambda c=cube: quicklook(app, [c])))
    start = time.perf_counter()
    app.data_collection.add_link(link_hpc(app.data_collection, others=cubes))
    report("link", seconds=round(time.perf_counter() - start, 3), links=len(app.data_collection.external_links))
    first = cubes[0]
    groups = {g.subset_state.reference_data: g for g in coord._owners}
    *_, rows, columns = first.shape
    moves = []
    for fy, fx in ((0.5, 0.5), (0.3, 0.6), (0.7, 0.4), (0.45, 0.55)):
        state = point(first, int(fy * rows), int(fx * columns))
        moves.append(timed(app, coord, lambda s=state: setattr(groups[first], "subset_state", s)))
    others = {c.label: [s.start for s in groups[c].subset_state.slices[-2:]] for c in cubes[1:] if c in groups}
    report("linked point moves", move_ms=median_ms(moves), others_last_yx=others)


def part_iris(app, root, obsid):
    """
    An IRIS observation as the observation browser opens it: every raster window and slit-jaw image ticked, scans
    stacked when there are several raster files, then its quicklook.
    """
    from functools import partial

    import numpy as np
    from matplotlib.backend_bases import MouseEvent

    from glue_solar.quicklook import coordinator, quicklook
    from glue_solar.sources import iris
    from glue_solar.sources.loaders import iris as loaders
    from glue_solar.sources.loaders.scan import scan_directory

    start = time.perf_counter()
    obs = next(o for o in scan_directory(root) if o.obsid == obsid and (o.rasters or o.sji))
    report("scan", seconds=round(time.perf_counter() - start, 3), raster_files=len(obs.rasters), windows=obs.windows,
           sji=sorted(obs.sji))
    picks = [(0, "raster", window) for window in obs.windows] + [(0, "sji", name) for name in sorted(obs.sji)]
    start = time.perf_counter()
    _, loaded, error = loaders._load(0, [obs], picks, len(obs.rasters) > 1, partial(iris._shown, quicklooks=True),
                                     threading.Event(), lambda *_: None)
    if error:
        raise RuntimeError(error)
    datasets = [data for *_, got in loaded for data in got]
    report("load", seconds=round(time.perf_counter() - start, 3), datasets=len(datasets),
           shapes=sorted({tuple(data.shape) for data in datasets}))
    (shown, window), = iris._quicklooks(loaded)
    coord = coordinator(app.data_collection)
    views = {}
    report("quicklook open", seconds=timed(app, coord, lambda: views.update(quicklook(app, shown, window=window))))
    panels = [(name, views[name]) for name in ("map", "spectrogram", "wavelength") if views.get(name)]
    panels += [(f"sji {i}", viewer) for i, viewer in enumerate(views.get("sji", []))]
    for name, viewer in panels:
        data = viewer.state.reference_data
        shown_axes = {viewer.state.x_att.axis, viewer.state.y_att.axis}
        for axis in (axis for axis in range(data.ndim) if axis not in shown_axes and data.shape[axis] > 1):
            def step(index, viewer=viewer, axis=axis):
                slices = list(viewer.state.slices)
                slices[axis] = index
                return timed(app, coord, lambda: setattr(viewer.state, "slices", tuple(slices)))

            back = viewer.state.slices[axis]
            indices = [int(i) for i in np.linspace(0, data.shape[axis] - 1, min(10, data.shape[axis]))]
            first = [step(index) for index in indices[1:]]
            warm = [step(index) for index in indices]
            step(back)
            report(f"{name} step, axis {axis}", first_ms=median_ms(first), warm_ms=median_ms(warm),
                   n=data.shape[axis], data=data.label)
    view = views["map"]  # the Pixel tool is active on it
    data = view.state.reference_data
    rows, columns = data.shape[view.state.y_att.axis], data.shape[view.state.x_att.axis]

    def mouse(event, x, y):
        canvas = view.figure.canvas
        canvas.callbacks.process(event, MouseEvent(event, canvas, *view.axes.transData.transform((x, y)), button=1))

    def at():  # the point's pixel on the map, to confirm the mouse moved it
        group = next(g for g in coord._owners if g.subset_state.reference_data is data)
        return [group.subset_state.slices[axis].start for axis in (view.state.y_att.axis, view.state.x_att.axis)]

    x, y = columns // 3, rows // 3
    report("point click", seconds=timed(app, coord, lambda: (mouse("button_press_event", x, y),
                                                             mouse("button_release_event", x, y))), at_yx=at())
    timed(app, coord, lambda: mouse("button_press_event", x, y))
    moves = [timed(app, coord, lambda i=i: mouse("motion_notify_event", min(columns - 1, x + i), min(rows - 1, y + 2 * i)))
             for i in range(1, 11)]
    timed(app, coord, lambda: mouse("button_release_event", x, y))
    report("point drag", move_ms=median_ms(moves[2:]), first_ms=median_ms(moves[:1]), at_yx=at())
    save_and_restore(app)


if __name__ == "__main__":
    PART, paths = sys.argv[1], sys.argv[2:]
    SAMPLER.start()
    start = time.perf_counter()
    from glue.viewers.image.pixel_selection_subset_state import PixelSubsetState
    from glue_qt.app import GlueApplication
    from qtpy.QtWidgets import QApplication

    import glue_solar

    glue_solar.setup()
    answer_dialogs()
    app = GlueApplication()
    app.resize(1600, 1000)
    app.show()  # as a user's: glue-solar draws a quicklook panel only once it is in sight
    report("start", seconds=round(time.perf_counter() - start, 3), machine=platform.platform(),
           python=platform.python_version(), ram_gb=round(physical_memory() / GB),
           glue_solar=getattr(glue_solar, "__version__", None),
           **{name: version(name) for name in ("glue-core", "glue-qt", "astropy", "irispy-lmsal", "numpy", "matplotlib")},
           files=[f"{Path(p).name} {Path(p).stat().st_size / GB:.2f} GB" for p in paths if Path(p).is_file()])
    {"file": lambda: part_file(app, paths[0]), "quicklook": lambda: part_quicklook(app, paths[0]),
     "link": lambda: part_link(app, paths), "iris": lambda: part_iris(app, *paths)}[PART]()
    report("end", seconds=round(time.perf_counter() - start, 3))
