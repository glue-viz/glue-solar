"""The two prototype tests that used a prototype-only attribute, rewritten the way they ship (monkeypatch)."""
import time

import pytest
from qtpy.QtCore import QThread
from qtpy.QtWidgets import QApplication

import wp8_scan
from glue_solar.conftest import OBS_A, iris_tree  # noqa: F401
from wp8_proto import ProtoImporter as QtIRISImporter


def _row(dlg, obsid):
    tree = dlg.obs_tree
    return next(tree.topLevelItem(i) for i in range(tree.topLevelItemCount()) if tree.topLevelItem(i).text(1) == obsid)


@pytest.fixture
def slow_headers(monkeypatch):
    real = wp8_scan.fits.getheader
    calls = []

    def slow(path, *args, **kwargs):
        calls.append(path)
        time.sleep(0.2)
        return real(path, *args, **kwargs)

    monkeypatch.setattr(wp8_scan.fits, "getheader", slow)
    return calls


@pytest.fixture
def populates(monkeypatch):
    """Thread of every populate() call."""
    threads = []
    original = QtIRISImporter.populate

    def recording(self):
        threads.append(QThread.currentThread() == QApplication.instance().thread())
        original(self)

    monkeypatch.setattr(QtIRISImporter, "populate", recording)
    return threads


def test_tree_is_populated_on_the_gui_thread(qtbot, iris_tree, populates):
    dlg = QtIRISImporter(iris_tree)
    qtbot.addWidget(dlg)
    assert dlg.scanning
    assert dlg.progress.maximum() == 0  # busy bar
    assert dlg.stop_scan.isEnabled()
    qtbot.waitUntil(lambda: not dlg.scanning)
    assert populates == [True]
    assert dlg.obs_tree.topLevelItemCount() == 4
    assert dlg.progress.maximum() == 100
    assert not dlg.stop_scan.isEnabled()


def test_rescan_while_scanning_cancels_the_running_scan(qtbot, iris_tree, slow_headers, populates):
    dlg = QtIRISImporter(iris_tree)
    qtbot.addWidget(dlg)
    qtbot.waitUntil(lambda: len(slow_headers) >= 1)
    dlg.recursive.setChecked(False)  # re-enters set_directory while the first scan runs
    qtbot.waitUntil(lambda: not dlg.scanning)
    assert populates == [True]  # the cancelled scan's partial result never reached the tree
    assert _row(dlg, OBS_A[2]).text(6) == "1 — SJI_1400"  # the non-recursive result
    assert dlg.obs_tree.topLevelItemCount() == 4
