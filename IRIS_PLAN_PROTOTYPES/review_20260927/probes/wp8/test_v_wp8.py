import pathlib
import threading
import time

from qtpy.QtCore import Qt

import wp8_scan
from glue_solar.conftest import OBS_A, iris_tree  # noqa: F401
from glue_solar.sources.loaders import iris
from wp8_proto import ProtoImporter


def _wait(qtbot, dlg):
    qtbot.waitUntil(lambda: not dlg.scanning)
    return dlg


def _row(dlg, obsid):
    return next(dlg.obs_tree.topLevelItem(i) for i in range(dlg.obs_tree.topLevelItemCount())
                if dlg.obs_tree.topLevelItem(i).text(1) == obsid)


def test_f2_load_during_rescan(qtbot, iris_tree, monkeypatch):
    dlg = _wait(qtbot, ProtoImporter(iris_tree))
    qtbot.addWidget(dlg)
    row = _row(dlg, OBS_A[2])
    child = next(row.child(i) for i in range(row.childCount()) if row.child(i).text(0).startswith("C II"))
    child.setCheckState(0, Qt.Checked)
    before = [(p, dlg.observations[p[0]].obsid, len(dlg.observations[p[0]].rasters)) for p in dlg.selected()]
    gate = threading.Event()
    real = wp8_scan.scan_directory
    monkeypatch.setattr(wp8_scan, "scan_directory", lambda *a, **k: (gate.wait(5), real(*a, **k))[1])
    dlg.recursive.setChecked(False)  # rescan now running
    assert dlg.scanning and dlg.ok.isEnabled()
    gate.set()
    dlg.worker.wait()  # finished, result queued but not delivered
    calls = []
    monkeypatch.setattr(iris, "raster_data", lambda files, windows, stack=False: calls.append((list(files), windows)) or [])
    dlg.ok.click()
    print("before", before, "calls", calls, "populate", dlg.populate_threads)
    assert calls == [([], ["C II 1336"])]


def test_f3_reject_blocks_during_walk(qtbot, iris_tree, monkeypatch):
    real = pathlib.Path.is_file
    n = []

    def slow(self):
        n.append(1)
        time.sleep(0.1)
        return real(self)

    monkeypatch.setattr(pathlib.Path, "is_file", slow)
    dlg = ProtoImporter(iris_tree)
    qtbot.addWidget(dlg)
    qtbot.waitUntil(lambda: len(n) >= 1)
    t0 = time.perf_counter()
    dlg.reject()
    dt = time.perf_counter() - t0
    print(f"reject blocked {dt:.2f}s, is_file calls {len(n)}")
    assert dt > 0.5


def test_f4_truncated_after_stop(qtbot, iris_tree):
    full = {o.obsid: len(o.rasters) for o in wp8_scan.scan_directory(iris_tree)}
    reads = []
    real = wp8_scan.fits.getheader

    def stop():
        return len(reads) >= 1 and "r00000" in str(reads[-1])

    def gh(p, *a, **k):
        reads.append(p)
        return real(p, *a, **k)

    wp8_scan.fits.getheader, saved = gh, wp8_scan.fits.getheader
    try:
        part = {o.obsid: len(o.rasters) for o in wp8_scan.scan_directory(iris_tree, stop=stop)}
    finally:
        wp8_scan.fits.getheader = saved
    print("full", full, "partial", part)
    assert part.get(OBS_A[2]) == 1 and full[OBS_A[2]] == 2


def test_f11_stop_after_finish(qtbot, iris_tree):
    dlg = ProtoImporter(iris_tree)
    qtbot.addWidget(dlg)
    dlg.worker.wait()  # finished; result still queued
    dlg.stop_scan.click()
    _wait(qtbot, dlg)
    print("rows", dlg.obs_tree.topLevelItemCount(), "format", dlg.progress.format())
    assert dlg.obs_tree.topLevelItemCount() == 4 and dlg.progress.format() == "Scan stopped"
