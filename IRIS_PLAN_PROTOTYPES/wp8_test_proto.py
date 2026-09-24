import shutil
import time

import pytest
from qtpy.QtCore import Qt

import wp8_scan
from glue_solar.conftest import MD5, OBS_A, OBS_B, OBS_C, OBS_S, iris_tree  # noqa: F401 (fixture)
from wp8_proto import ProtoImporter


def _wait(qtbot, dlg):
    qtbot.waitUntil(lambda: not dlg.scanning)
    return dlg


def _rows(dlg):
    return [dlg.obs_tree.topLevelItem(i) for i in range(dlg.obs_tree.topLevelItemCount())]


def _visible(dlg):
    return [row.text(1) for row in _rows(dlg) if not row.isHidden()]


def _row(dlg, obsid):
    return next(row for row in _rows(dlg) if row.text(1) == obsid)


@pytest.fixture
def dialog(qtbot, iris_tree):
    dlg = ProtoImporter(iris_tree)
    assert dlg.scanning and dlg.stop_scan.isEnabled() and dlg.progress.maximum() == 0  # busy bar
    qtbot.addWidget(dlg)
    return _wait(qtbot, dlg)


@pytest.fixture
def slow_headers(monkeypatch):
    """Each header read takes 0.2 s and is counted, so tests can act mid-scan deterministically."""
    real = wp8_scan.fits.getheader
    calls = []

    def slow(path, *args, **kwargs):
        calls.append(path)
        time.sleep(0.2)
        return real(path, *args, **kwargs)

    monkeypatch.setattr(wp8_scan.fits, "getheader", slow)
    return calls


def test_scan_directory_stop_kwarg(iris_tree):
    assert wp8_scan.scan_directory(iris_tree, stop=lambda: True) == []
    polls = []

    def stop():
        polls.append(1)
        return len(polls) > 2  # let two files through: the OBS_C archive and the sparse OBS_S file

    partial = wp8_scan.scan_directory(iris_tree, stop=stop)
    assert [o.obsid for o in partial] == [OBS_C[2], OBS_S]
    assert len(polls) == 3
    assert len(wp8_scan.scan_directory(iris_tree)) == 4  # default: never stops


def test_tree_is_populated_on_the_gui_thread_after_the_worker_finishes(dialog):
    assert dialog.obs_tree.topLevelItemCount() == 4
    assert dialog.populate_threads == [True]
    assert not dialog.stop_scan.isEnabled()
    assert dialog.progress.maximum() == 100
    assert dialog.worker.isFinished()


def test_filter_hides_non_matching_observations(dialog):
    dialog.filter.setText("2014-07")
    assert _visible(dialog) == [OBS_C[2]]
    dialog.filter.setText(OBS_B[2])
    assert _visible(dialog) == [OBS_B[2]]
    dialog.filter.setText("TEST RASTER")  # case-insensitive, description column (OBS_A and OBS_B share it)
    assert _visible(dialog) == [OBS_B[2], OBS_A[2]]
    dialog.filter.setText("")
    assert len(_visible(dialog)) == 4


def test_filter_survives_rescan_and_hidden_ticks_still_load(qtbot, dialog):
    _row(dialog, OBS_B[2]).setCheckState(0, Qt.Checked)
    dialog.filter.setText("2014-07")
    assert _visible(dialog) == [OBS_C[2]]
    assert [(kind, name) for _, kind, name in dialog.selected()] == [("sji", "SJI_2832")]  # hidden but ticked
    dialog.recursive.setChecked(False)
    _wait(qtbot, dialog)
    assert _visible(dialog) == [OBS_C[2]]
    assert dialog.filter.text() == "2014-07"


def test_stop_scan_keeps_what_was_found(qtbot, iris_tree, slow_headers):
    dlg = ProtoImporter(iris_tree)
    qtbot.addWidget(dlg)
    qtbot.waitUntil(lambda: len(slow_headers) >= 1)  # the worker is inside its first header read
    dlg.stop_scan.click()
    _wait(qtbot, dlg)
    assert [row.text(1) for row in _rows(dlg)] == [OBS_C[2], OBS_S]  # archive (no header) + one header
    assert dlg.progress.format() == "Scan stopped"
    assert not dlg.stop_scan.isEnabled()
    assert dlg.progress.maximum() == 100
    assert len(slow_headers) == 1


def test_rescan_while_scanning_cancels_the_running_scan(qtbot, iris_tree, slow_headers):
    dlg = ProtoImporter(iris_tree)
    qtbot.addWidget(dlg)
    qtbot.waitUntil(lambda: len(slow_headers) >= 1)
    dlg.recursive.setChecked(False)  # re-enters set_directory while the first scan runs
    _wait(qtbot, dlg)
    assert dlg.populate_threads == [True]  # the cancelled scan's partial result never reached the tree
    assert _row(dlg, OBS_A[2]).text(6) == "1 — SJI_1400"  # non-recursive result
    assert dlg.obs_tree.topLevelItemCount() == 4


def test_extract_archive_then_lists_its_windows(qtbot, iris_tree, tmp_path):
    tree = tmp_path / "copy"
    shutil.copytree(iris_tree, tree)
    dlg = _wait(qtbot, ProtoImporter(tree))
    qtbot.addWidget(dlg)
    row = _row(dlg, OBS_C[2])
    assert row.text(6).startswith("0 — Extract ")
    row.setCheckState(0, Qt.Checked)
    dlg.finalize()
    assert dlg.progress.format().startswith("Extracted 1 archive(s)")
    _wait(qtbot, dlg)
    assert dlg.progress.format().startswith("Extracted 1 archive(s)")  # the rescan does not clobber it
    assert dlg.progress.value() == 100
    assert (tree / f"{MD5}iris_l2_{'_'.join(OBS_C)}_raster").is_dir()
    row = _row(dlg, OBS_C[2])
    assert [row.child(i).text(0) for i in range(row.childCount())] == [
        "C II 1336 — 1 raster file(s)",
        "Mg II k 2796 — 1 raster file(s)",
    ]


def test_closing_the_dialog_stops_the_scan(qtbot, iris_tree, slow_headers):
    dlg = ProtoImporter(iris_tree)
    qtbot.addWidget(dlg)
    qtbot.waitUntil(lambda: len(slow_headers) >= 1)
    dlg.reject()
    assert dlg.worker.isFinished()
    assert len(slow_headers) == 1
