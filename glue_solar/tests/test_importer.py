import copy
import gzip
import os
import shutil
import subprocess
import sys
import threading
from types import SimpleNamespace

import numpy as np
import pytest
from irispy.io import read_files
from qtpy.QtCore import QMetaObject, Qt
from qtpy.QtWidgets import QDialog, QFileDialog

import astropy.units as u
from astropy.io import fits
from astropy.utils.masked import Masked
from astropy.wcs.wcsapi import HighLevelWCSWrapper
from astropy.wcs.wcsapi.high_level_api import values_to_high_level_objects
from astropy.wcs.wcsapi.wrappers import BaseWCSWrapper

from glue_solar.conftest import MD5, OBS_A, OBS_B, OBS_C, OBS_S, find_irispy_test_file, startobs
from glue_solar.sources.iris import is_iris_fits, read_iris_file
from glue_solar.sources.loaders.iris import (
    _RUNNING,
    QtIRISImporter,
    _raster_collection_data,
    _raster_windows_data,
    image_data,
    raster_data,
)
from glue_solar.sources.loaders.scan import extract_archive, scan_directory
from glue_solar.sources.loaders.stack_spectrograms import stack_spectrogram_sequence
from glue_solar.tests.helpers import load_selected, scanned

# The unit glue is shown each world axis in, by physical type; time, scan and the others keep their own
SHOWN = {"em.wl": u.AA, "custom:pos.helioprojective.lat": u.arcsec, "custom:pos.helioprojective.lon": u.arcsec}


@pytest.fixture
def dialog(qtbot, iris_tree):
    dlg = QtIRISImporter(iris_tree)
    qtbot.addWidget(dlg)
    scanned(qtbot, dlg)
    return dlg


def _row(dialog, obsid):
    tree = dialog.obs_tree
    return next(tree.topLevelItem(i) for i in range(tree.topLevelItemCount()) if tree.topLevelItem(i).text(1) == obsid)


@pytest.mark.parametrize("suffix", ["", "_test"])
def test_find_irispy_test_file(tmp_path, suffix):
    path = tmp_path / f"iris_l2_example{suffix}.fits"
    assert find_irispy_test_file([path], "iris_l2_example.fits") == path


def test_tests_keep_off_the_users_settings(tmp_path):
    from glue import config

    from glue_solar.sources.loaders import iris

    assert os.path.dirname(iris.QSettings("glue-solar", "glue-solar").fileName()) == str(tmp_path)
    assert config.CFG_DIR != os.path.join(os.path.expanduser("~"), ".glue")


def test_tree_lists_observations_and_files(dialog):
    assert dialog.obs_tree.topLevelItemCount() == 3
    row = _row(dialog, OBS_A[2])
    children = [row.child(i).text(0) for i in range(row.childCount())]
    assert children == [
        "SJI_1400",
        "C II 1336 — 2 raster file(s)",
        "Mg II k 2796 — 2 raster file(s)",
        "AIA 171_THIN",
    ]
    assert all(row.child(i).isFirstColumnSpanned() for i in range(row.childCount()))
    assert row.text(2) == "Test raster 1x2 3s"
    assert row.text(6) == "4"


def test_derived_raster_file_is_never_a_window_and_counted(dialog, qtbot, tmp_path):
    tree = dialog.obs_tree
    assert OBS_S not in [tree.topLevelItem(i).text(1) for i in range(tree.topLevelItemCount())]
    assert dialog.progress.text() == "Skipped 1 raster file(s) that are not Level 2"
    dialog.set_directory(tmp_path)  # nothing left out, so the count goes
    scanned(qtbot, dialog)
    assert dialog.progress.format() == "%p%"


def test_ticking_the_observation_ticks_its_files(dialog):
    row = _row(dialog, OBS_A[2])
    row.setCheckState(0, Qt.Checked)
    assert len(dialog.selected()) == 4


def test_load_selected_real_sji(qtbot, tmp_path, irispy_test_files):
    source = find_irispy_test_file(irispy_test_files, "iris_l2_20210905_001833_3620258102_SJI_1400_t000.fits")
    shutil.copy2(source, tmp_path / source.name)
    dialog = QtIRISImporter(tmp_path)
    qtbot.addWidget(dialog)
    scanned(qtbot, dialog)
    dialog.obs_tree.topLevelItem(0).setCheckState(0, Qt.Checked)
    load_selected(qtbot, dialog)
    assert len(dialog.datasets) == 1
    data = dialog.datasets[0]
    assert data is dialog.first_image
    assert data.label == "SJI_1400-3620258102-2021-09-05T00:18:33"
    assert data.shape == (62, 40, 37)
    assert data.style.preferred_cmap.name == "irissji1400"


def counted_reads(monkeypatch, on_read=None):
    """
    The ``(files, spectral_windows)`` of each read of raster files, as the loaders make them; ``on_read(n)`` after the
    n-th, on the thread that reads.
    """
    reads = []

    def read(files, **kwargs):
        collection = read_files(files, **kwargs)
        reads.append((files, kwargs["spectral_windows"]))
        if on_read is not None:
            on_read(len(reads))
        return collection

    monkeypatch.setattr("irispy.io.read_files", read)  # the loaders import it as they read
    return reads


def test_ticked_raster_windows_of_an_observation_are_read_together_file_by_file(qtbot, monkeypatch,
                                                                                 irispy_test_files):
    # each read maps the file, and a mapped file stays open; one file at a time, so that a load can stop between them
    reads = counted_reads(monkeypatch)
    scans = sorted(path for path in irispy_test_files if "3860258481_raster_t000_r" in path.name)
    dialog = QtIRISImporter(scans[0].parent)
    qtbot.addWidget(dialog)
    scanned(qtbot, dialog)
    row = _row(dialog, "3860258481")
    entries = [row.child(i) for i in range(row.childCount()) if "raster file(s)" in row.child(i).text(0)][:2]
    for entry in entries:
        entry.setCheckState(0, Qt.Checked)
    load_selected(qtbot, dialog)
    windows = [name for _, _, name, _ in dialog.loaded]
    assert reads == [([scan], windows) for scan in scans]
    assert len(windows) == 2
    for _, _, name, datasets in dialog.loaded:
        assert [data.label for data in datasets] == [data.label for data in raster_data(scans, [name])]


def test_raster_files_are_read_until_the_load_stops(monkeypatch, irispy_test_files):
    reads = counted_reads(monkeypatch)
    scans = sorted(path for path in irispy_test_files if "3860258481_raster_t000_r" in path.name)
    stop, steps = threading.Event(), []

    def step():
        steps.append(len(reads))
        if len(steps) == 2:
            stop.set()

    assert _raster_windows_data(scans, ["C II 1336"], stack=True, stop=stop, step=step) is None
    assert steps == [1, 2]
    assert [files for files, _ in reads] == [[scan] for scan in scans[:2]]


def tick(dialog, *entries):
    """Tick the entries of ``OBS_A`` whose names start with any of ``entries``."""
    row = _row(dialog, OBS_A[2])
    for item in map(row.child, range(row.childCount())):
        if item.text(0).startswith(entries):
            item.setCheckState(0, Qt.Checked)


def from_the_worker(widget, method):
    """The user's ``widget.method()`` on the GUI thread, which the worker thread waits for."""
    # on the GUI thread it would wait for itself: a load moved back there fails rather than hangs
    assert threading.current_thread() is not threading.main_thread()
    QMetaObject.invokeMethod(widget, method, Qt.BlockingQueuedConnection)


def test_load_reads_a_file_at_a_time_off_the_gui_thread(dialog, qtbot, monkeypatch):
    tick(dialog, "SJI_1400", "Mg II k")
    dialog.stack.setChecked(True)
    on_gui = []
    reads = counted_reads(monkeypatch, lambda n: on_gui.append(threading.current_thread() is threading.main_thread()))
    dialog.accepted.connect(lambda: on_gui.append(threading.current_thread() is threading.main_thread()),
                            Qt.DirectConnection)  # on the thread that accepts
    progress = []  # and whether anything that would start or change a load can be used meanwhile
    widgets = dialog.ok, dialog.change, dialog.recursive, dialog.obs_tree, dialog.stack, dialog.quicklook
    dialog.progress.valueChanged.connect(lambda value: progress.append((value, any(w.isEnabled() for w in widgets))))
    load_selected(qtbot, dialog)
    assert dialog.result() == QDialog.Accepted
    assert len(reads) == 2
    assert on_gui == [False, False, True]  # the reads, then the result
    # from the scan's 100%, the slit-jaw file, each raster file, then the colour limits
    assert progress == [(0, False), (25, False), (50, False), (75, False), (100, False)]
    assert [data.ndim for data in dialog.datasets] == [3, 4]


def test_stop_keeps_the_entries_read_in_full(dialog, qtbot, monkeypatch):
    tick(dialog, "SJI_1400", "Mg II k")
    dialog.stack.setChecked(True)
    dialog.shown = lambda loaded, quicklooks: [datasets[0] for *_, datasets in loaded]

    def stop_in_the_first_file(n):
        if n == 1:  # the user presses Stop while raster file 1 is read
            from_the_worker(dialog.cancel, "click")

    reads = counted_reads(monkeypatch, stop_in_the_first_file)
    load_selected(qtbot, dialog)
    assert len(reads) == 1  # file 2 is not read
    assert dialog.result() == QDialog.Accepted
    assert [kind for _, kind, _, _ in dialog.loaded] == ["sji"]
    assert [data.label for data in dialog.datasets] == [f"SJI_1400-{OBS_A[2]}-2025-03-28T22:56:28"]
    [data] = dialog.datasets
    assert data.get_component(data.main_components[0])._counts is not None  # not left to its first viewer


def test_stop_keeps_every_window_of_a_raster_read_in_full(dialog, qtbot, monkeypatch):
    # both windows of OBS_A come from the same two raster files, read together: Stop during file 2 (the last)
    tick(dialog, "C II", "Mg II k")
    dialog.stack.setChecked(True)

    def stop_in_the_last_file(n):
        if n == 2:
            from_the_worker(dialog.cancel, "click")

    reads = counted_reads(monkeypatch, stop_in_the_last_file)
    load_selected(qtbot, dialog)
    assert len(reads) == 2
    assert dialog.result() == QDialog.Accepted
    assert [name for _, _, name, _ in dialog.loaded] == ["C II 1336", "Mg II k 2796"]


def test_stop_ends_the_look_for_the_file_that_fails(dialog, qtbot, monkeypatch):
    tick(dialog, "Mg II k")
    dialog.stack.setChecked(True)

    def fail(collection, **kwargs):
        if any(len(cubes) > 1 for cubes in collection.values()):  # the scans together, not one alone
            raise ValueError("the scans differ")
        return _raster_collection_data(collection, **kwargs)

    monkeypatch.setattr("glue_solar.sources.loaders.iris._raster_collection_data", fail)

    def stop_in_the_first_read_again(n):
        if n == 3:  # files 1 and 2 were read; the look for the one that fails reads them again
            from_the_worker(dialog.cancel, "click")

    reads = counted_reads(monkeypatch, stop_in_the_first_read_again)
    load_selected(qtbot, dialog)
    assert len(reads) == 3
    assert dialog.progress.format() == "Loading Mg II k 2796 from 2 raster files failed: the scans differ"


def test_closing_the_dialog_drops_the_load(dialog, qtbot, monkeypatch):
    tick(dialog, "SJI_1400", "Mg II k")

    def close_in_the_first_file(n):
        if n == 1:
            from_the_worker(dialog, "reject")

    reads = counted_reads(monkeypatch, close_in_the_first_file)
    dialog.ok.click()
    qtbot.waitUntil(lambda: not _RUNNING, timeout=60_000)
    assert len(reads) == 1
    assert dialog.result() == QDialog.Rejected
    assert dialog.datasets == []
    assert dialog.loaded == []
    assert dialog.ok.isEnabled()  # ready for another
    assert dialog.cancel.text() == "Cancel"


@pytest.mark.parametrize(
    ("quicklook", "shown"), [(True, ["SJI_1400", "C_II_1336", "Mg_II_k_2796"]), (False, ["SJI_1400"])]
)
def test_colour_limits_of_what_browse_iris_shows_are_counted_in_the_background(qtbot, monkeypatch, iris_tree, quicklook,
                                                                              shown):
    from glue_solar.sources.iris import browse_iris

    loaded = []

    def load(dialog):
        qtbot.addWidget(dialog)
        scanned(qtbot, dialog)
        _row(dialog, OBS_A[2]).setCheckState(0, Qt.Checked)
        dialog.quicklook.setChecked(quicklook)
        load_selected(qtbot, dialog)
        loaded.extend(dialog.datasets)
        return QDialog.Rejected  # before browse_iris opens a viewer

    monkeypatch.setattr(QFileDialog, "getExistingDirectory", lambda *args, **kwargs: str(iris_tree))
    monkeypatch.setattr(QtIRISImporter, "exec", load)
    browse_iris(SimpleNamespace(application=None), None)
    assert len(loaded) == 6  # the slit-jaw image, scans 0 and 1 of two raster windows, and the AIA cutout
    # the quicklook's slit-jaw image and scan 0 of each window, which has a λ–time panel, or the Image viewer's
    # slit-jaw image: no viewer has asked
    counted = [data.label for data in loaded if data.get_component(data.main_components[0])._counts is not None]
    assert counted == [f"{name}-{OBS_A[2]}-2025-03-28T22:56:28" + "-scan-0" * (name != "SJI_1400") for name in shown]


def test_a_failure_after_the_reads_stays_in_the_dialog(qtbot, iris_tree, capsys):
    def shown(loaded, quicklooks):
        raise ValueError("no viewer to show")

    dialog = QtIRISImporter(iris_tree, shown=shown)
    qtbot.addWidget(dialog)
    scanned(qtbot, dialog)
    tick(dialog, "SJI_1400")
    load_selected(qtbot, dialog)
    assert dialog.result() == 0
    assert dialog.datasets == []
    assert dialog.progress.format() == "Loading failed: no viewer to show"
    assert 'raise ValueError("no viewer to show")' in capsys.readouterr().err  # the traceback of the bug


def test_deconvolved_sji_is_listed_and_loaded_beside_the_plain_one(qtbot, tmp_path, irispy_test_files):
    source = find_irispy_test_file(irispy_test_files, "iris_l2_20210905_001833_3620258102_SJI_1400_t000.fits")
    plain = tmp_path / "iris_l2_20210905_001833_3620258102_SJI_1400_t000.fits"
    deconvolved = tmp_path / "iris_l2_20210905_001833_3620258102_SJI_1400_t000_deconvolved.fits"
    shutil.copy2(source, plain)
    shutil.copy2(source, deconvolved)
    [observation] = scan_directory(tmp_path)
    assert observation.sji == {"SJI_1400": plain, "SJI_1400 (deconvolved)": deconvolved}

    dialog = QtIRISImporter(tmp_path)
    qtbot.addWidget(dialog)
    scanned(qtbot, dialog)
    dialog.obs_tree.topLevelItem(0).setCheckState(0, Qt.Checked)
    load_selected(qtbot, dialog)
    labels = [data.label for data in dialog.datasets]
    assert labels == [
        "SJI_1400-3620258102-2021-09-05T00:18:33",
        "SJI_1400_deconvolved-3620258102-2021-09-05T00:18:33",
    ]
    assert read_iris_file(str(deconvolved)).label == labels[1]  # File -> Open labels it the same way
    assert read_iris_file(str(plain)).label == labels[0]


def test_single_entry_observation_is_ticked_on_its_own_row(dialog):
    row = _row(dialog, OBS_B[2])  # SJI only
    assert row.childCount() == 0
    assert row.text(6) == "1 — SJI_2832"
    row.setCheckState(0, Qt.Checked)
    assert [(kind, name) for _, kind, name in dialog.selected()] == [("sji", "SJI_2832")]


def _listed(dialog):
    tree = dialog.obs_tree
    return [row.text(1) for row in map(tree.topLevelItem, range(tree.topLevelItemCount())) if not row.isHidden()]


def test_filter_lists_the_observations_whose_row_or_entries_hold_the_text(dialog):
    dialog.filter.setText("mg II")  # a raster window of OBS_A, in any case
    assert _listed(dialog) == [OBS_A[2]]
    dialog.filter.setText("2014-07-08")  # OBS_C's start date
    assert _listed(dialog) == [OBS_C[2]]
    dialog.filter.setText("sji_")  # an entry of OBS_A and the one on OBS_B's own row
    assert _listed(dialog) == [OBS_B[2], OBS_A[2]]
    dialog.filter.setText("3s 1.5")  # the end of a description and XCEN: never across texts
    assert _listed(dialog) == []
    dialog.filter.clear()
    assert _listed(dialog) == [OBS_C[2], OBS_B[2], OBS_A[2]]


def test_load_selected_leaves_out_the_ticks_the_filter_hides(dialog):
    _row(dialog, OBS_A[2]).setCheckState(0, Qt.Checked)
    _row(dialog, OBS_B[2]).setCheckState(0, Qt.Checked)
    dialog.filter.setText("2832")
    assert [(kind, name) for _, kind, name in dialog.selected()] == [("sji", "SJI_2832")]
    dialog.filter.clear()  # the hidden ticks stay
    assert len(dialog.selected()) == 5


def test_filter_survives_a_rescan(dialog, qtbot):
    dialog.filter.setText("2025-03-28")
    dialog.recursive.setChecked(False)
    scanned(qtbot, dialog)
    assert _row(dialog, OBS_A[2]).text(6) == "1 — SJI_1400"  # listed anew
    assert _listed(dialog) == [OBS_A[2]]


def test_recursive_toggle_rescans(dialog, qtbot):
    dialog.recursive.setChecked(False)
    scanned(qtbot, dialog)
    row = _row(dialog, OBS_A[2])
    assert row.childCount() == 0  # only the top-level SJI is left, so it collapses onto the row
    assert row.text(6) == "1 — SJI_1400"


def gated_scan(monkeypatch, widget, method, last):
    """
    The names of the files whose headers the browser's scan reads, with the user's ``widget.method()`` as the header of
    the one whose name ends with ``last`` is read.
    """
    from glue_solar.sources.loaders import scan

    reads, read = [], scan._primary_header

    def gated(path):
        reads.append(path.name)
        if path.name.endswith(last):
            from_the_worker(widget, method)
        return read(path)

    monkeypatch.setattr(scan, "_primary_header", gated)
    return reads


def test_stop_lists_what_the_scan_found_so_far(qtbot, monkeypatch, iris_tree):
    dialog = QtIRISImporter()
    qtbot.addWidget(dialog)
    reads = gated_scan(monkeypatch, dialog.cancel, "click", "_SJI_1400_t000.fits.gz")  # OBS_A's, before its rasters
    dialog.set_directory(iris_tree)
    assert dialog.cancel.text() == "Stop"
    assert not dialog.change.isEnabled()
    scanned(qtbot, dialog)
    assert reads[-1].endswith("_SJI_1400_t000.fits.gz")  # no header is read after it
    tree = dialog.obs_tree
    assert [tree.topLevelItem(i).text(1) for i in range(tree.topLevelItemCount())] == [OBS_C[2], OBS_B[2], OBS_A[2]]
    assert _row(dialog, OBS_A[2]).text(6) == "2"  # its slit-jaw image and AIA cutout, not its rasters
    assert dialog.progress.value() == 100 * 5 // 9  # 5 of the folder's 9 files were read
    assert dialog.progress.format().startswith("Scan stopped at %p% of the files")
    assert dialog.cancel.text() == "Cancel"


def test_stop_once_every_header_is_read_lists_the_whole_folder(qtbot, monkeypatch, iris_tree):
    from glue_solar.sources.loaders import scan

    dialog = QtIRISImporter()
    qtbot.addWidget(dialog)
    describe = scan._obsid_description

    def stop_then_describe(obsid):  # OBS_C's archive has no header to describe it, so after the last one is read
        from_the_worker(dialog.cancel, "click")
        return describe(obsid)

    monkeypatch.setattr(scan, "_obsid_description", stop_then_describe)
    dialog.set_directory(iris_tree)
    scanned(qtbot, dialog)
    assert dialog.obs_tree.topLevelItemCount() == 3
    assert dialog.progress.value() == 100
    assert dialog.progress.format() == "Skipped 1 raster file(s) that are not Level 2"


def test_closing_the_dialog_drops_the_scan(qtbot, monkeypatch, iris_tree):
    dialog = QtIRISImporter()
    qtbot.addWidget(dialog)
    reads = gated_scan(monkeypatch, dialog, "reject", "_SJI_2832_t000.fits.gz")
    dialog.set_directory(iris_tree)
    qtbot.waitUntil(lambda: not _RUNNING, timeout=60_000)
    assert reads[-1].endswith("_SJI_2832_t000.fits.gz")
    assert dialog.result() == QDialog.Rejected
    assert dialog.observations == []
    assert dialog.obs_tree.topLevelItemCount() == 0


def test_extract_archive_then_lists_its_windows(qtbot, iris_tree, tmp_path):
    tree = tmp_path / "copy"
    shutil.copytree(iris_tree, tree)  # extraction writes next to the archive; keep the shared fixture pristine
    dlg = QtIRISImporter(tree)
    qtbot.addWidget(dlg)
    scanned(qtbot, dlg)
    row = _row(dlg, OBS_C[2])
    assert row.childCount() == 0
    assert row.text(6).startswith("0 — Extract ")
    row.setCheckState(0, Qt.Checked)
    load_selected(qtbot, dlg)
    assert dlg.result() == 0  # stays open
    assert dlg.datasets == []
    assert (tree / f"{MD5}iris_l2_{'_'.join(OBS_C)}_raster").is_dir()
    row = _row(dlg, OBS_C[2])
    assert [row.child(i).text(0) for i in range(row.childCount())] == [  # archive entry gone once unpacked
        "C II 1336 — 1 raster file(s)",
        "Mg II k 2796 — 1 raster file(s)",
    ]


def test_stop_keeps_the_archives_unpacked_in_full(qtbot, iris_tree, tmp_path, monkeypatch):
    tree = tmp_path / "copy"
    shutil.copytree(iris_tree, tree)
    later = tree / f"iris_l2_20140709_000000_{OBS_C[2]}_raster.tar.gz"  # another run of the program
    shutil.copy2(tree / f"{MD5}iris_l2_{'_'.join(OBS_C)}_raster.tar.gz", later)
    dlg = QtIRISImporter(tree)
    qtbot.addWidget(dlg)
    scanned(qtbot, dlg)
    for row in map(dlg.obs_tree.topLevelItem, range(dlg.obs_tree.topLevelItemCount())):
        if row.text(6).startswith("0 — Extract "):
            row.setCheckState(0, Qt.Checked)
    unpacked = []

    def extract(path):
        unpacked.append(extract_archive(path))
        from_the_worker(dlg.cancel, "click")  # Stop, as the first is unpacked

    monkeypatch.setattr("glue_solar.sources.loaders.iris.extract_archive", extract)
    load_selected(qtbot, dlg)
    assert unpacked == [tree / f"{MD5}iris_l2_{'_'.join(OBS_C)}_raster"]
    assert dlg.result() == 0  # stays open, listing what it holds
    assert dlg.progress.format() == "Extracted 1 archive(s) — now tick what to load"
    assert [row.text(6) for row in map(dlg.obs_tree.topLevelItem, range(dlg.obs_tree.topLevelItemCount()))
            if row.text(6).startswith("0 — Extract ")] == [f"0 — Extract {later.name} (0 MB, next to the archive)"]


def test_closing_the_dialog_drops_the_unpacking(dialog, qtbot, monkeypatch):
    _row(dialog, OBS_C[2]).setCheckState(0, Qt.Checked)
    monkeypatch.setattr("glue_solar.sources.loaders.iris.extract_archive", lambda path: from_the_worker(dialog, "reject"))
    dialog.ok.click()
    qtbot.waitUntil(lambda: not _RUNNING, timeout=60_000)
    assert dialog.result() == QDialog.Rejected
    assert dialog.progress.format() == "%p%"  # the closed dialog does not list the folder again


def test_browser_and_file_open_read_only_the_primary_header_of_a_gzipped_file(tmp_path):
    d, t, o = OBS_B
    header = fits.PrimaryHDU(np.zeros((100, 100), np.int16)).header
    header.update(TELESCOP="IRIS", INSTRUME="SJI", OBSID=o, STARTOBS=startobs(d, t), TDESC1="SJI_2832")
    path = tmp_path / f"iris_l2_{d}_{t}_{o}_SJI_2832_t000.fits.gz"
    # not even gzip after the header: reading on into the data, as astropy's getheader does, fails
    path.write_bytes(gzip.compress(header.tostring().encode()) + b"not the data")
    [observation] = scan_directory(tmp_path)
    assert observation.sji == {"SJI_2832": path}
    assert is_iris_fits(str(path))


def test_scan_skips_the_hidden_folder_an_archive_is_unpacked_into(tmp_path):
    d, t, o = OBS_B
    header = fits.Header({"TELESCOP": "IRIS", "INSTRUME": "SJI", "OBSID": o, "STARTOBS": startobs(d, t),
                          "TDESC1": "SJI_2832"})
    unpacking = tmp_path / f".iris_l2_{d}_{t}_{o}_SJI-k2v9x0"  # as extract_archive names it
    unpacking.mkdir()
    fits.PrimaryHDU(header=header).writeto(unpacking / f"iris_l2_{d}_{t}_{o}_SJI_2832_t000.fits")
    assert scan_directory(tmp_path) == []


def test_file_open_reads_no_header_from_a_file_that_does_not_start_as_fits(tmp_path):
    # File > Open asks about every file; read on to an END card, a large file of another kind is read whole
    path = tmp_path / "table.csv"
    path.write_text(fits.Header({"TELESCOP": "IRIS"}).tostring())
    assert not is_iris_fits(str(path))


def test_real_sji_adapter_preserves_mask_units_and_coordinates(irispy_test_files):
    path = find_irispy_test_file(irispy_test_files, "iris_l2_20210905_001833_3620258102_SJI_1400_t000.fits")
    cube = read_files(path, memmap=False, uncertainty=False)
    data = image_data(path)

    science, mask, _time, exposure = data.main_components
    assert data.shape == cube.shape
    assert data.get_component(exposure).units == "s"
    with fits.open(path) as hdul:
        aux = hdul[1]
        np.testing.assert_array_equal(data[exposure][:, 0, 0], aux.data[:, aux.header["EXPTIMES"]])
        for key, column in (("pztx", "PZTX"), ("pzty", "PZTY"), ("xcenix", "XCENIX"), ("slit x position", "SLTPX1IX")):
            np.testing.assert_array_equal(data.meta[key], aux.data[:, aux.header[column]])
    assert data.get_component(science).units == str(cube.unit)
    [rate] = data.derived_components
    assert rate.label == f"{science.label} DN/s"
    assert data.get_component(rate).units == "DN/s"
    np.testing.assert_allclose(data[rate], data[science] / data[exposure], rtol=1e-6)
    mask = data.get_component(mask).data
    assert mask.dtype == np.uint8
    np.testing.assert_array_equal(mask, np.isnan(data.get_component(science).data))
    np.testing.assert_array_equal(mask, cube.mask)  # -200 and -199, which irispy masks too

    longitude = next(component for component in data.world_component_ids if component.label == "Helioprojective Longitude")
    expected = cube.axis_world_coords()[0][0, 0, 0].Tx.to_value(u.arcsec)
    assert data.get_component(longitude).units == "arcsec"
    assert data.get_component(longitude).data[0, 0, 0] == pytest.approx(expected)
    assert np.nanmax(np.abs(data.get_component(longitude).data)) < 180 * 3600
    world = data.coords.pixel_to_world_values(0, 0, 0)
    assert data.coords.world_to_pixel_values(*world) == pytest.approx((0, 0, 0), abs=1e-8)


def test_aia_cube_uses_the_same_irispy_adapter(tmp_path, irispy_test_files):
    source = find_irispy_test_file(irispy_test_files, "iris_l2_20210905_001833_3620258102_SJI_1400_t000.fits")
    path = tmp_path / "aia_l2_20210905_001833_3620258102_171.fits"
    shutil.copy2(source, path)
    with fits.open(path, mode="update") as hdul:
        hdul[0].header["INSTRUME"] = "AIA_3"
        hdul[0].header["OBSID"] = "20210905_001833_3620258102"
        hdul[0].header["TDESC1"] = "171_THIN"
        hdul[0].header["TWAVE1"] = 171

    data = image_data(path)
    assert data.label == "171_THIN-3620258102-2021-09-05T00:18:33"
    assert data.style.preferred_cmap.name == "sdoaia171"
    assert len(data.main_components) == 4  # science, mask and the per-frame Time and Exposure time


def test_real_raster_preserves_exact_exposure_times(irispy_test_files):
    path = find_irispy_test_file(irispy_test_files, "iris_l2_20140329_140938_3860258481_raster_t000_r00000.fits")
    data = raster_data([path], ["C II 1336"], stack=True)
    cube = read_files(path, spectral_windows=["C II 1336"], memmap=False, uncertainty=False)["C II 1336"][0]
    expected_times = cube.axis_world_coords("time", wcs=cube.extra_coords)[0].utc.to_value("datetime64")

    assert len(data) == 1
    assert data[0].label == "C_II_1336-3860258481-2014-03-29T14:09:38-scan-0"
    assert data[0].shape == (8, 109, 17)
    assert [c.label for c in data[0].world_component_ids] == [
        "Helioprojective Longitude",
        "Helioprojective Latitude",
        "Wavelength",
    ]
    assert data[0].get_component(data[0].main_components[0]).units == "DN_IRIS_FUV"
    assert [data[0].get_component(cid).units for cid in data[0].world_component_ids[:2]] == ["arcsec", "arcsec"]
    np.testing.assert_array_equal(data[0]["Time"][:, 0, 0], expected_times)
    np.testing.assert_array_equal(data[0]["Time"][:, -1, -1], expected_times)
    world = data[0].coords.pixel_to_world_values(0, 0, 0)
    assert data[0].coords.world_to_pixel_values(*world) == pytest.approx((0, 0, 0), abs=1e-8)
    assert len(data[0].main_components) == 4
    np.testing.assert_array_equal(data[0]["Exposure time"][:, 0, 0], cube.meta["exposure time"].to_value(u.s))


def test_real_rasters_stack_without_resampling_and_keep_scan_times(irispy_test_files):
    paths = sorted(path for path in irispy_test_files if "20140329_140938_3860258481_raster_t000_r" in path.name)
    sequence = read_files(paths, spectral_windows=["C II 1336"], memmap=False, uncertainty=False)["C II 1336"]
    expected_times = [
        cube.axis_world_coords("time", wcs=cube.extra_coords)[0].utc.to_value("datetime64") for cube in sequence
    ]
    data = raster_data(paths, ["C II 1336"], stack=True)[0]

    science = data.id[data.label]
    mask = data.id[f"{data.label} mask"]
    values = data.get_component(science).data
    times = data["Time"]
    raw_last = np.asarray(sequence[-1].data, dtype=np.float32).copy()
    raw_last[np.isin(raw_last, (-200, -199))] = np.nan
    assert data.shape == (len(paths), 8, 109, 17)
    assert [c.label for c in data.world_component_ids][0] == "Scan"
    assert data.coords.world_axis_units == ("Angstrom", "arcsec", "arcsec", "")
    np.testing.assert_array_equal(values[-1], raw_last)
    assert data.get_component(mask).data.dtype == np.uint8
    np.testing.assert_array_equal(data.get_component(mask).data, np.isnan(values))
    for i, expected in enumerate(expected_times):
        np.testing.assert_array_equal(times[i, :, 0, 0], expected)
        np.testing.assert_array_equal(times[i, :, -1, -1], expected)
    for i, scan in enumerate(sequence):  # each scan's own exposure times, not scan 0's
        exposure = scan.meta["exposure time"].to_value(u.s)
        np.testing.assert_array_equal(data["Exposure time"][i, :, 0, 0], exposure)
        np.testing.assert_allclose(data[f"{data.label} DN/s"][i], values[i] / exposure[:, None, None], rtol=1e-6)
    np.testing.assert_array_equal(
        data.coords.pixel_to_world_values(0, 0, 0, np.arange(len(paths)))[-1], np.arange(len(paths))
    )

    # every scan's pixels in that scan's own coordinates, a tenth of an arcsec apart here, in one call or one scan at a
    # time, and glue's world components too
    pixel = np.meshgrid(np.arange(17), np.arange(109), np.arange(8), np.arange(len(paths)), indexing="ij")
    stacked_world = data.coords.pixel_to_world_values(*pixel)
    for k, cube in enumerate(sequence):
        scan_world = data.coords.pixel_to_world_values(*(p[..., k] for p in pixel[:3]), k)
        source_world = cube.wcs.pixel_to_world_values(*(p[..., k] for p in pixel[:3]))
        for expected, actual, alone, unit, physical_type in zip(
            source_world, stacked_world[:3], scan_world, cube.wcs.world_axis_units, cube.wcs.world_axis_physical_types
        ):
            if physical_type in SHOWN:
                expected = (expected * u.Unit(unit)).to_value(SHOWN[physical_type])
            np.testing.assert_allclose(actual[..., k], expected)
            np.testing.assert_array_equal(alone, actual[..., k])
    assert np.ptp(stacked_world[2][0, 0, 0]) > 0.05  # longitude, arcsec
    for i, name in ((1, "Helioprojective Latitude"), (2, "Helioprojective Longitude")):
        np.testing.assert_array_equal(data[name], stacked_world[i].T)
    for actual, expected in zip(data.coords.world_to_pixel_values(*stacked_world), pixel):
        np.testing.assert_allclose(actual, expected, atol=3e-6)

    with pytest.raises(ValueError, match="same shape"):
        stack_spectrogram_sequence([sequence[0], sequence[1][:-1]], memmap=False)


def test_real_raster_fill_values_become_nan(irispy_test_files):
    path = find_irispy_test_file(irispy_test_files, "iris_l2_20210905_001833_3620258102_raster_t000_r00000.fits")
    data = raster_data([path], ["Si IV 1403"])[0]
    values = data[data.main_components[0]]
    assert values.size == 216_920
    assert not np.isin(values, (-200, -199)).any()
    assert np.isnan(values).sum() == 35_027
    mask = data[f"{data.label} mask"]
    assert mask.dtype == np.uint8
    np.testing.assert_array_equal(mask, np.isnan(values))


class _CountedWCS(BaseWCSWrapper):
    """A WCS that counts how often its world axis units and physical types are read, and its conversions to world."""

    def __init__(self, wcs):
        super().__init__(wcs)
        self.reads = 0
        self.conversions = 0

    @property
    def world_axis_units(self):
        self.reads += 1
        return self._wcs.world_axis_units

    @property
    def world_axis_physical_types(self):
        self.reads += 1
        return self._wcs.world_axis_physical_types

    def pixel_to_world_values(self, *pixel_arrays):
        self.conversions += 1
        return self._wcs.pixel_to_world_values(*pixel_arrays)

    def world_to_pixel_values(self, *world_arrays):
        return self._wcs.world_to_pixel_values(*world_arrays)


def test_arcsec_coordinates_read_the_axes_once(irispy_test_files):
    obs = "iris_l2_20210905_001833_3620258102_{}.fits"
    raster = raster_data([find_irispy_test_file(irispy_test_files, obs.format("raster_t000_r00000"))], ["Si IV 1403"])
    sji = image_data(find_irispy_test_file(irispy_test_files, obs.format("SJI_1400_t000")))
    for data in (*raster, sji):
        raw = _CountedWCS(data.coords._wcs)
        wcs = type(data.coords)(raw)
        units, kinds = raw._wcs.world_axis_units, raw._wcs.world_axis_physical_types
        arrays = [np.array([-0.5, 1.5, n - 1.5]) for n in data.shape[::-1]]
        missing = [np.array([np.nan, 1.5])] * raw.pixel_n_dim  # gWCS cannot take NaN back to pixels
        for pixel in (missing, arrays, [1] * raw.pixel_n_dim, [np.float64(2.5)] * raw.pixel_n_dim):
            world = wcs.pixel_to_world_values(*pixel)
            # the values of a Quantity conversion, bit for bit
            for value, expected, unit, kind in zip(world, raw.pixel_to_world_values(*pixel), units, kinds):
                if kind in SHOWN:
                    if kind.endswith(".lon"):
                        circle = (360 * u.deg).to_value(unit)
                        expected = (np.asarray(expected) + circle / 2) % circle - circle / 2
                    expected = (np.asarray(expected) * u.Unit(unit)).to_value(SHOWN[kind])
                assert type(value) is type(expected)
                assert np.asarray(value).tobytes() == np.asarray(expected).tobytes()
            if pixel is not missing:
                # and back, also as a single-precision world position
                for where in (world, [np.asarray(value, dtype=np.float32) for value in world]):
                    native = [
                        value if kind not in SHOWN else (np.asarray(value) * SHOWN[kind]).to_value(unit)
                        for value, unit, kind in zip(where, units, kinds)
                    ]
                    for value, expected in zip(wcs.world_to_pixel_values(*where), raw.world_to_pixel_values(*native)):
                        assert np.asarray(value).tobytes() == np.asarray(expected).tobytes()
        # WCSAxes converts through these dozens of times per draw: the axes are read once, not per call
        assert raw.reads == 2


def _same(shown, wrapped):
    """Whether two high-level world objects are the same position, time or quantity."""
    if hasattr(shown, "Tx"):
        return u.allclose(shown.Tx, wrapped.Tx, rtol=0, atol=1e-9 * u.arcsec) and u.allclose(
            shown.Ty, wrapped.Ty, rtol=0, atol=1e-9 * u.arcsec
        )
    if hasattr(shown, "jd"):
        return abs((shown - wrapped).to_value(u.s)) < 1e-6
    return u.allclose(shown, wrapped, rtol=1e-15)


def test_high_level_objects_agree_with_the_values(irispy_test_files):
    # glue's WCS link builds SkyCoords and SpectralCoords from the values: they said degrees and metres while the
    # values were arcsec and Angstrom, which raised (latitude past 90 deg) or gave positions 3600 times too far out
    obs = "iris_l2_20210905_001833_3620258102_{}.fits"
    [raster] = raster_data([find_irispy_test_file(irispy_test_files, obs.format("raster_t000_r00000"))], ["Si IV 1403"])
    sji = image_data(find_irispy_test_file(irispy_test_files, obs.format("SJI_1400_t000")))
    scans = sorted(str(p) for p in irispy_test_files if "3860258481_raster" in p.name)
    [stack] = raster_data(scans, ["C II 1336"], stack=True)
    for data in (raster, sji, stack):
        pixel = [n / 2 + 0.25 for n in data.shape[::-1]]
        shown, wrapped = HighLevelWCSWrapper(data.coords), HighLevelWCSWrapper(data.coords._wcs)
        objects = shown.pixel_to_world(*pixel)
        assert all(map(_same, objects, wrapped.pixel_to_world(*pixel)))
        assert shown.world_to_pixel(*objects) == pytest.approx(wrapped.world_to_pixel(*objects), abs=1e-9)
        values = map(Masked, data.coords.pixel_to_world_values(*pixel))  # astropy takes masked low-level values too
        assert all(map(_same, values_to_high_level_objects(*values, low_level_wcs=data.coords), objects))


def test_arcsec_coordinates_reuse_identical_conversions(irispy_test_files):
    from glue_solar.sources.loaders.iris import _MEMO_ENTRIES, _MEMO_SAMPLES

    obs = "iris_l2_20210905_001833_3620258102_{}.fits"
    raster = raster_data([find_irispy_test_file(irispy_test_files, obs.format("raster_t000_r00000"))], ["Si IV 1403"])
    sji = image_data(find_irispy_test_file(irispy_test_files, obs.format("SJI_1400_t000")))
    for data in (*raster, sji):
        raw = _CountedWCS(data.coords._wcs)
        wcs, fresh = type(data.coords)(raw), type(data.coords)(raw)
        pixel = [np.array([-0.5, 1.5, n - 1.5]) for n in data.shape[::-1]]
        for inputs in (pixel, [np.float64(2.5)] * raw.pixel_n_dim):
            first = wcs.pixel_to_world_values(*inputs)
            conversions = raw.conversions
            again = wcs.pixel_to_world_values(*copy.deepcopy(inputs))  # the same inputs in other objects
            assert raw.conversions == conversions  # reused
            # bit for bit what the wrapped WCS gives, of the same types
            for value, expected in zip(again, fresh.pixel_to_world_values(*inputs)):
                assert type(value) is type(expected)
                assert np.asarray(value).tobytes() == np.asarray(expected).tobytes()
            # each caller has its own arrays: changing them changes nothing kept
            for value in (*first, *again):
                if isinstance(value, np.ndarray):
                    value[...] = 0
            for value, expected in zip(wcs.pixel_to_world_values(*inputs), fresh.pixel_to_world_values(*inputs)):
                assert np.asarray(value).tobytes() == np.asarray(expected).tobytes()
        # another type, dtype, shape or value is converted again
        conversions = raw.conversions
        wcs.pixel_to_world_values(*[np.asarray(2.5)] * raw.pixel_n_dim)  # a 0-d array, not a scalar
        for change in (lambda p: p.astype(np.float32), lambda p: p[:2], lambda p: np.nextafter(p, 0)):
            wcs.pixel_to_world_values(*map(change, pixel))
        assert raw.conversions == conversions + 4
        # at most the _MEMO_ENTRIES inputs used last are kept, and none larger than _MEMO_SAMPLES samples
        scalars = [np.float64(2.5)] * raw.pixel_n_dim
        for shift in range(1, 2 * _MEMO_ENTRIES + 1):
            wcs.pixel_to_world_values(*[p + shift for p in pixel])
            conversions = raw.conversions
            wcs.pixel_to_world_values(*scalars)  # used after each new input, as by an unchanged panel's redraw
            assert raw.conversions == conversions
        assert len(wcs._memo) == _MEMO_ENTRIES
        conversions = raw.conversions
        wcs.pixel_to_world_values(*[p + 2 * _MEMO_ENTRIES for p in pixel])  # the latest is kept
        wcs.pixel_to_world_values(*pixel)  # the first is not
        large = [np.zeros(_MEMO_SAMPLES + 1)] * raw.pixel_n_dim
        side = int(_MEMO_SAMPLES**0.5) + 1  # small inputs that broadcast to more samples
        spread = [np.zeros((side, 1)), np.zeros((1, side)), *[np.zeros((1, 1))] * (raw.pixel_n_dim - 2)]
        for inputs in (large, large, spread, spread):
            wcs.pixel_to_world_values(*inputs)
        assert raw.conversions == conversions + 5


_THREADS = """
import os, sys, threading, traceback
import numpy as np
from glue_solar.sources.loaders import iris

wcs = iris.raster_data([sys.argv[1]], ["Si IV 1403"])[0].coords
pixels = [np.arange(1000.0) % n for n in wcs.pixel_shape]
done = threading.Event()

def pixels_of(i):  # more inputs than the wrapper keeps, so each conversion reaches wcslib
    return [p + i % 300 * 1e-3 for p in pixels]

def convert():
    try:
        i = 0
        while not done.is_set():
            wcs.pixel_to_world_values(*pixels_of(i))
            wcs.axis_correlation_matrix
            i += 1
    except Exception:  # wcslib errors from a race are as much a failure as a crash
        traceback.print_exc()
        os._exit(1)

thread = threading.Thread(target=convert)
thread.start()
for i in range(20_000):
    wcs.pixel_to_world_values(*pixels_of(i))
done.set()
thread.join()

# then threads that reuse and evict the wrapper's kept conversions at once, with room for 2 of 4 inputs
iris._MEMO_ENTRIES = 2
wcs._memo.clear()
sys.setswitchinterval(1e-6)

def reuse(seed):
    try:
        for i in np.random.default_rng(seed).integers(0, 4, 5000):
            wcs.pixel_to_world_values(*[p[:2] + i for p in pixels])
    except Exception:
        traceback.print_exc()
        os._exit(1)

threads = [threading.Thread(target=reuse, args=(seed,)) for seed in range(4)]
for thread in threads:
    thread.start()
for thread in threads:
    thread.join()
"""


def test_raster_coordinates_are_thread_safe(irispy_test_files):
    # wcslib crashes when two threads use one -TAB WCS (astropy/astropy#19174), so run it apart
    path = find_irispy_test_file(irispy_test_files, "iris_l2_20210905_001833_3620258102_raster_t000_r00000.fits")
    env = {**os.environ, "PYTHONPATH": os.pathsep.join(sys.path)}
    result = subprocess.run([sys.executable, "-c", _THREADS, str(path)], env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr[-2000:]


def test_negative_step_raster_fill_follows_the_flipped_data(tmp_path, irispy_test_files):
    # The fill must follow irispy's flip of STEPS_AV < -0.01 rasters and cover -199
    source = find_irispy_test_file(irispy_test_files, "iris_l2_20210905_001833_3620258102_raster_t000_r00000.fits")
    path = tmp_path / source.name
    shutil.copy2(source, path)
    with fits.open(path, mode="update") as hdul:
        hdul[0].header["STEPS_AV"] = -1.0
        window = [hdul[0].header[f"TDESC{i}"] for i in range(1, hdul[0].header["NWIN"] + 1)].index("Si IV 1403") + 1
        first = hdul[window].data[0]
        first[tuple(np.argwhere(first != -200)[0])] = -199  # the fixtures hold no -199
    with fits.open(path) as hdul:
        fill = np.flip(np.isin(hdul[window].data, (-200, -199)), axis=0)
    scan = raster_data([path], ["Si IV 1403"])[0]
    np.testing.assert_array_equal(np.isnan(scan[scan.main_components[0]]), fill)
    np.testing.assert_array_equal(scan[f"{scan.label} mask"], fill)
    stack = raster_data([path, path], ["Si IV 1403"], stack=True)[0]
    for values in stack[stack.main_components[0]]:
        np.testing.assert_array_equal(np.isnan(values), fill)


def test_raster_of_several_exposures_per_position_warns_once(qtbot, tmp_path, irispy_test_files):
    # NEXP_PRP > 1 repeats each raster position along the steps, which world to pixel cannot tell apart
    source = find_irispy_test_file(irispy_test_files, "iris_l2_20140329_140938_3860258481_raster_t000_r00000.fits")
    path = tmp_path / source.name
    shutil.copy2(source, path)
    with fits.open(path, mode="update") as hdul:
        hdul[0].header["NEXP_PRP"] = 2
    sji = find_irispy_test_file(irispy_test_files, "iris_l2_20230408_110821_3880012095_SJI_1400_t000.fits")
    shutil.copy2(sji, tmp_path / sji.name)
    with fits.open(tmp_path / sji.name, mode="update") as hdul:
        hdul[0].header["NEXP_PRP"] = 2  # a slit-jaw image of a 16-position raster, as 4000005156 SJI 2796: not a raster
    expected = "3860258481-2014-03-29T14:09:38 takes 2 exposures at each raster position"
    with pytest.warns(UserWarning, match=expected) as record:
        assert len(raster_data([path])) == 9  # once for all its windows
    assert len(record) == 1
    dialog = QtIRISImporter(tmp_path)
    qtbot.addWidget(dialog)
    scanned(qtbot, dialog)
    for obsid in ("3860258481", "3880012095"):
        _row(dialog, obsid).setCheckState(0, Qt.Checked)
    with pytest.warns(UserWarning, match=expected) as record:  # and from the browser, on the GUI thread
        load_selected(qtbot, dialog)
    assert len(dialog.datasets) == 10
    assert len(record) == 1
    # A sit-and-stare raster's one position takes every exposure (NRASTERP 1, NEXP_PRP 1872): no warning, which the
    # suite would raise
    sit_and_stare = "iris_l2_20210905_001833_3620258102_raster_t000_r00000.fits"
    raster_data([find_irispy_test_file(irispy_test_files, sit_and_stare)])


def test_duplicate_real_raster_is_listed_and_loaded_once(qtbot, tmp_path, irispy_test_files):
    source = find_irispy_test_file(irispy_test_files, "iris_l2_20140329_140938_3860258481_raster_t000_r00000.fits")
    for directory in (tmp_path / "download", tmp_path / "extracted"):
        directory.mkdir()
        shutil.copy2(source, directory / source.name)

    dialog = QtIRISImporter(tmp_path)
    qtbot.addWidget(dialog)
    scanned(qtbot, dialog)
    row = dialog.obs_tree.topLevelItem(0)
    assert row.text(6) == "1"
    assert all("1 raster file(s)" in row.child(i).text(0) for i in range(row.childCount()))
    row.child(0).setCheckState(0, Qt.Checked)
    dialog.stack.setChecked(True)
    load_selected(qtbot, dialog)
    assert len(dialog.datasets) == 1


@pytest.mark.parametrize(
    ("name", "instrume", "band"),
    [
        ("iris_l2_20240101_000000_1234567890_SJI_1400_t000.fits", "SJI", "SJI_1400"),
        ("aia_l2_20240101_000000_1234567890_171.fits", "AIA_3", "171_THIN"),
    ],
)
def test_reader_failure_stays_in_dialog(qtbot, tmp_path, name, instrume, band):
    path = tmp_path / name
    fits.PrimaryHDU(
        header=fits.Header(
            {
                "TELESCOP": "IRIS",
                "INSTRUME": instrume,
                "OBSID": "1234567890",
                "STARTOBS": "2024-01-01T00:00:00",
                "TDESC1": band,
                "TWAVE1": 1400,
            }
        )
    ).writeto(path)

    dialog = QtIRISImporter(tmp_path)
    qtbot.addWidget(dialog)
    scanned(qtbot, dialog)
    dialog.obs_tree.topLevelItem(0).setCheckState(0, Qt.Checked)
    load_selected(qtbot, dialog)

    assert dialog.result() == 0
    assert dialog.datasets == []
    assert dialog.progress.format().startswith(f"Loading {band} from {name} failed:")
    assert dialog.cancel.text() == "Cancel"  # and Load selected is back


def test_raster_load_failure_names_the_file_that_fails(qtbot, tmp_path, irispy_test_files):
    scans = sorted(path for path in irispy_test_files if "3860258481_raster_t000_r0000" in path.name)[:2]
    for scan in scans:
        shutil.copy2(scan, tmp_path / scan.name)
    truncated = tmp_path / scans[1].name
    data = truncated.read_bytes()
    truncated.write_bytes(data[: len(data) // 2])  # as an interrupted download leaves it

    dialog = QtIRISImporter(tmp_path)
    qtbot.addWidget(dialog)
    scanned(qtbot, dialog)
    _row(dialog, "3860258481").child(0).setCheckState(0, Qt.Checked)
    load_selected(qtbot, dialog)

    assert dialog.result() == 0
    window = dialog.observations[0].windows[0]
    assert dialog.progress.format().startswith(f"Loading {window} from {truncated.name} failed:")


def test_raster_load_failure_of_files_that_load_alone_names_how_many(qtbot, tmp_path, monkeypatch, irispy_test_files):
    def fail(_sequence):
        raise ValueError("the scans differ")

    monkeypatch.setattr("glue_solar.sources.loaders.iris.stack_spectrogram_sequence", fail)
    for scan in sorted(path for path in irispy_test_files if "3860258481_raster_t000_r0000" in path.name)[:2]:
        shutil.copy2(scan, tmp_path / scan.name)

    dialog = QtIRISImporter(tmp_path)
    qtbot.addWidget(dialog)
    scanned(qtbot, dialog)
    _row(dialog, "3860258481").child(0).setCheckState(0, Qt.Checked)
    dialog.stack.setChecked(True)
    load_selected(qtbot, dialog)

    window = dialog.observations[0].windows[0]
    assert dialog.progress.format() == f"Loading {window} from 2 raster files failed: the scans differ"


@pytest.mark.remote_data
def test_negative_step_raster_keeps_irispys_orientation(qtbot, irispy_data):
    # D10: a STEPS_AV < 0 raster keeps irispy's orientation, unflipped, and longitude grows with step
    from glue_qt.app.application import GlueApplication
    from glue_qt.viewers.image import ImageViewer

    [path] = irispy_data("iris_l2_20250328_225628_3400109360_cutout_raster.tar.gz")
    [scan] = raster_data([path], ["Mg II k 2796"])
    [stack] = raster_data([path, path], ["Mg II k 2796"], stack=True)
    assert scan.meta["STEPS_AV"] < -0.01
    row = scan.shape[1] // 2

    longitude = scan[scan.id["Helioprojective Longitude"]][:, row, 0]
    with fits.open(path) as hdul:  # the per-step FOV centre, stored in acquisition order
        aux = hdul[hdul[0].header["NWIN"] + 1]
        np.testing.assert_allclose(longitude, aux.data[::-1, aux.header["XCENIX"]], atol=0.01)
    assert longitude[[0, 63]] == pytest.approx([-970.73, -907.89], abs=0.01)
    assert (np.diff(longitude) > 0).all()
    for i in range(2):  # every scan of the stack keeps scan 0's orientation
        np.testing.assert_array_equal(stack[stack.id["Helioprojective Longitude"]][i, :, row, 0], longitude)
    times = scan["Time"][:, 0, 0]
    assert (np.diff(times) < np.timedelta64(0, "s")).all()  # acquired from the last step to the first
    assert np.datetime_as_string(times[[0, 63]], unit="s").tolist() == ["2025-03-28T23:06:15", "2025-03-28T22:56:32"]

    app = GlueApplication()
    qtbot.addWidget(app)
    app.data_collection.append(scan)
    viewer = app.new_data_viewer(ImageViewer, data=scan)
    viewer.state.x_att, viewer.state.y_att = scan.pixel_component_ids[0], scan.pixel_component_ids[1]
    assert viewer.state.x_min < viewer.state.x_max  # unflipped: step, and so longitude, grows to the right
    viewer.figure.canvas.draw()  # WCSAxes only formats positions once drawn
    assert f'{longitude[0]:.2f}"' in viewer.axes.format_coord(0, row)
    assert f'{longitude[63]:.2f}"' in viewer.axes.format_coord(63, row)


def test_raster_rows_show_their_detector_and_wavelength_range(qtbot, monkeypatch, tmp_path, irispy_test_files):
    from glue_solar.sources.loaders import scan

    shutil.copy(find_irispy_test_file(irispy_test_files, "iris_l2_20140329_140938_3860258481_raster_t000_r00000.fits"),
                tmp_path)
    reads = []
    read = scan._primary_header
    monkeypatch.setattr(scan, "_primary_header", lambda path: reads.append(path) or read(path))
    dlg = QtIRISImporter(tmp_path)
    qtbot.addWidget(dlg)
    scanned(qtbot, dlg)
    top = dlg.obs_tree.topLevelItem(0)
    tips = {top.child(i).text(0).split(" — ")[0]: top.child(i).toolTip(0) for i in range(top.childCount())}
    assert tips["C II 1336"] == "FUV1, 1332.7–1337.2 Å"
    assert tips["Mg II k 2796"] == "NUV, 2790.5–2806.6 Å"
    assert len(reads) == 1  # from the header the scan reads anyway
