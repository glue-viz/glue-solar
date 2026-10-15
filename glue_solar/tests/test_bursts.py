"""
'IRIS: detect UV bursts…', on irispy's burst test files, int16 copies of its test raster and irispy-data files: what glue
gets of irispy's labels and events, of a scan or a stack.
"""

import numpy as np
import pytest
from glue.core import Data
from glue.core.subset import RangeSubsetState
from glue_qt.app.application import GlueApplication
from glue_qt.viewers.table import TableViewer
from glue_qt.viewers.table.data_viewer import DataTableModel
from irispy.io.sji import read_sji_lvl2
from irispy.io.spectrograph import read_spectrograph_lvl2
from irispy.sji import SJICube
from irispy.utils.bursts import find_si_iv_bursts, find_sji_bursts
from qtpy import QtCore, QtWidgets

import astropy.units as u

import glue_solar
from glue_solar import glue_patches
from glue_solar.conftest import find_irispy_test_file
from glue_solar.sources.bursts import si_iv_bursts, sji_bursts
from glue_solar.sources.calibration import remove_dust
from glue_solar.sources.loaders import iris
from glue_solar.sources.loaders.iris import image_data, keep_hpc_linked, link_hpc, raster_data
from glue_solar.tests.helpers import refused
from glue_solar.tests.test_lazy import SJI
from glue_solar.tests.test_quicklook import SCAN

ACTION = "IRIS: detect UV bursts… (Si IV, SJI 1400)"
# irispy's cutouts of 4000005156's Si IV 1403 and 4000255147's SJI 1400, stored as int16: lazy in glue
SI_IV = "iris_l2_20130902_182935_4000005156_raster_t000_r00000_si_iv.fits"
SJI_1400 = "iris_l2_20130902_163935_4000255147_SJI_1400_t000.fits"
# irispy's columns of the brightest pixel of each, after its own
POSITION = ["time", "coordinate.Tx", "coordinate.Ty", "intensity"]


@pytest.fixture
def app(qtbot):
    glue_solar.setup()
    app = GlueApplication()
    qtbot.addWidget(app)
    return app


def answer(monkeypatch, accept=True, **typed):
    """
    Make each bursts dialog return as if the ``typed`` values were entered in the boxes of those names and OK, or
    Cancel, pressed; returns the values each dialog opened with.
    """
    opened = []

    def exec_(dialog):
        boxes = {box.objectName(): box for box in dialog.findChildren(QtWidgets.QWidget) if box.objectName()}
        boxes = {name: box for name, box in boxes.items() if not name.startswith("qt_")}
        opened.append({name: box.text() if hasattr(box, "setText") else box.value() for name, box in boxes.items()})
        for name, value in typed.items():
            boxes[name].setText(value) if isinstance(value, str) else boxes[name].setValue(value)
        return QtWidgets.QDialog.Accepted if accept else QtWidgets.QDialog.Rejected

    monkeypatch.setattr(QtWidgets.QDialog, "exec", exec_)
    return opened


def run(app, qtbot, data, count):
    """
    Trigger the action on ``data`` and wait for the two datasets it adds and for its thread to end, the status bar
    then saying ``count`` bursts.
    """
    collection, tree = app.data_collection, app._layer_widget
    before = len(collection)
    tree.ui.layerTree.set_selected_layers([data])
    tree._actions[ACTION].trigger()
    assert iris._RUNNING  # on glue-qt's worker
    assert app.statusBar().currentMessage() == f"Detecting UV bursts in {data.label}…"
    qtbot.waitUntil(lambda: len(collection) == before + 2 and not iris._RUNNING)
    labels, table = collection[-2:]
    assert app.statusBar().currentMessage() == f"{labels.label}: {count} bursts"
    return labels, table


def assert_irispys(labels, table, direct, events):
    """``labels`` and ``table`` are irispy's ``direct`` labels and ``events``."""
    np.testing.assert_array_equal(labels["label"], direct.data)
    assert table.size == len(events)
    for name, column in events.columns.items():
        if name == "coordinate":
            np.testing.assert_array_equal(table["coordinate.Tx"], column.Tx.to_value(u.arcsec))
            np.testing.assert_array_equal(table["coordinate.Ty"], column.Ty.to_value(u.arcsec))
        elif name == "time":
            np.testing.assert_array_equal(table["time"], column.utc.to_value("datetime64"))
        else:
            np.testing.assert_array_equal(table[name], getattr(column, "value", column))
            assert table.get_component(name).units == str(getattr(column, "unit", None) or "")


def test_a_raster_window_gives_irispys_labels_and_events_linked_and_no_viewer(
    app, qtbot, monkeypatch, irispy_test_files
):
    path = find_irispy_test_file(irispy_test_files, SI_IV)
    [raster] = raster_data([path])
    collection = app.data_collection
    collection.append(raster)
    opened = answer(monkeypatch, threshold=" 80 ")
    labels, table = run(app, qtbot, raster, 3)
    assert opened == [{"threshold": "", "velocity_range": 50.0, "median_factor": 10.0}]
    assert not any(app.viewers)
    cube = read_spectrograph_lvl2(path)["Si IV 1403"][0]
    direct, events = find_si_iv_bursts(cube, threshold=80)
    assert_irispys(labels, table, direct, events)
    assert (labels.label, table.label) == (f"{raster.label} bursts", f"{raster.label} burst events")
    assert labels.meta == {
        "OBSID": raster.meta["OBSID"],
        "STARTOBS": raster.meta["STARTOBS"],
        "bursts_threshold": 40.0,  # irispy's, for data not summed in wavelength
        "bursts_velocity_range": 50.0,
        "bursts_median_factor": 10.0,
    }
    assert table.meta == labels.meta
    assert [cid.label for cid in table.main_components] == ["label", "raster", "npix", "step", "y", *POSITION]
    # on the raster's steps and slit pixels, their helioprojective coordinates linked with the others'
    assert labels.shape == raster.shape[:2]
    for cid, raster_cid in zip(labels.world_component_ids, raster.world_component_ids):
        np.testing.assert_allclose(labels[cid], raster[raster_cid, (..., 0)], rtol=0, atol=1e-9)
    assert link_hpc(collection) == []
    # the typed velocities and the median test off
    answer(monkeypatch, threshold="80", velocity_range=30.0, median_factor=0.0)
    labels, table = run(app, qtbot, raster, 6)
    assert (labels.meta["bursts_velocity_range"], labels.meta["bursts_median_factor"]) == (30.0, None)
    direct, events = find_si_iv_bursts(cube, threshold=80, velocity_range=30 * u.km / u.s, median_factor=None)
    assert_irispys(labels, table, direct, events)
    # 'IRIS: shift pointing…' moves the table's coordinates as the map's
    raster.coords.pointing_offset = (5.0, -3.0)
    shifted = si_iv_bursts(raster, 80, 30.0, None)[1]
    np.testing.assert_allclose(shifted["coordinate.Tx"], table["coordinate.Tx"] + 5, rtol=0, atol=1e-9)
    np.testing.assert_allclose(shifted["coordinate.Ty"], table["coordinate.Ty"] - 3, rtol=0, atol=1e-9)
    raster.coords.pointing_offset = (0.0, 0.0)
    # irispy's threshold, left blank, which finds none here
    answer(monkeypatch)
    labels, table = run(app, qtbot, raster, 0)
    direct, events = find_si_iv_bursts(cube)
    assert_irispys(labels, table, direct, events)
    assert labels.meta["bursts_threshold"] == events.meta["threshold"].value


def test_the_event_table_opens_in_a_table_viewer(app, irispy_test_files):
    installed = DataTableModel.get_filter_mask is glue_patches.get_filter_mask
    assert installed == glue_patches.needs_table_time_workaround()  # probes glue-qt's own method
    assert not glue_patches.needs_table_time_workaround(glue_patches.get_filter_mask)
    [raster] = raster_data([find_irispy_test_file(irispy_test_files, SI_IV)])
    _, table = si_iv_bursts(raster, threshold=80)
    app.data_collection.append(table)
    # glue-qt 0.4.2 alone: "argument of type 'numpy.datetime64' is not iterable"
    viewer = app.new_data_viewer(TableViewer, data=table)
    model = viewer.model
    column = [cid.label for cid in model.columns].index("time")

    def shown():
        return [model.data(model.index(row, column), QtCore.Qt.DisplayRole) for row in range(model.rowCount())]

    times = [str(time) for time in table["time"]]  # numpy's ISO times, to the nanosecond
    assert shown() == times
    model.sort(column, QtCore.Qt.DescendingOrder)
    assert shown() == sorted(times, reverse=True)
    # the search box, on the time column, finds the text of the times shown
    assert viewer.state.filter_att is table.id["time"]
    viewer.state.filter = times[1][11:19]
    assert shown() == [times[1]]
    viewer.state.regex = True
    viewer.state.filter = f"{times[0]}|{times[2]}"
    assert shown() == sorted([times[0], times[2]], reverse=True)
    viewer.state.filter = ""
    # a range of times, as the time master's "Master exposure" gives, highlights their rows
    lo, hi = np.sort(table["time"])[[1, -1]]
    app.data_collection.new_subset_group("later", RangeSubsetState(lo, hi, table.id["time"]))
    rows = range(model.rowCount())
    highlighted = [model.data(model.index(row, column), QtCore.Qt.BackgroundRole) is not None for row in rows]
    assert highlighted == [time > min(times) for time in shown()]


def assert_each_scans(labels, table, paths, **parameters):
    """
    ``labels`` and ``table`` of a stack are those of each scan of ``paths`` loaded alone, the labels numbered on
    through the scans and ``raster`` the scan, and its threshold each scan's within 0.2%.
    """
    count = 0
    for k, path in enumerate(paths):
        [scan] = raster_data([path], ["Si IV 1403"])
        alone, events = si_iv_bursts(scan, **parameters)
        # irispy's, at the stack's first date rather than the scan's own: the effective area, which scales it, changes
        # by at most 0.12% in 10 hours
        assert labels.meta["bursts_threshold"] == pytest.approx(alone.meta["bursts_threshold"], rel=2e-3, abs=0)
        np.testing.assert_array_equal(labels["label"][k], np.where(alone["label"] > 0, alone["label"] + count, 0))
        rows, shifted = table["raster"] == k, {"label": events["label"] + count, "raster": np.full(events.size, k)}
        for cid in events.main_components:
            expected = shifted.get(cid.label, events[cid])
            np.testing.assert_array_equal(table[cid.label][rows], expected, err_msg=cid.label)
        count += events.size
    assert table.size == count


def test_a_stack_gives_each_scans_labels_and_events(app, qtbot, monkeypatch, stack_paths):
    """
    A lazy stack of 3860258481's three scans gives the labels and events of each scan loaded alone, numbered on
    through the scans, irispy's threshold at the stack's first date; the status bar counts them all.
    """
    [stack] = raster_data(stack_paths, ["Si IV 1403"], stack=True)
    collection = app.data_collection
    collection.append(stack)
    keep_hpc_linked(collection)
    answer(monkeypatch, threshold="5", median_factor=0.0)
    labels, table = run(app, qtbot, stack, 12)
    assert labels.shape == stack.shape[:-1]
    assert sorted(set(table["raster"])) == [0, 1, 2]
    assert link_hpc(collection) == []
    assert labels.meta["bursts_threshold"] == 5.0
    assert_each_scans(labels, table, stack_paths, threshold=5, median_factor=None)
    # irispy's threshold, from the effective area at the stack's DATE_OBS, its first scan's
    labels, table = si_iv_bursts(stack)
    [first] = raster_data(stack_paths[:1], ["Si IV 1403"])
    assert labels.meta["bursts_threshold"] == si_iv_bursts(first)[0].meta["bursts_threshold"]
    assert_each_scans(labels, table, stack_paths)


def test_a_slit_jaw_image_gives_irispys_labels_and_events_on_its_coordinates(
    app, qtbot, monkeypatch, irispy_test_files
):
    path = find_irispy_test_file(irispy_test_files, SJI_1400)
    sji = image_data(path)
    [raster] = raster_data([find_irispy_test_file(irispy_test_files, SI_IV)])
    collection = app.data_collection
    collection.extend([raster, sji])
    keep_hpc_linked(collection)
    opened = answer(monkeypatch)
    labels, table = run(app, qtbot, sji, 26)
    assert opened == [{"sigma_factor": 10.0, "min_pixels": 2}]
    assert not any(app.viewers)
    assert_irispys(labels, table, *find_sji_bursts(read_sji_lvl2(path)))
    assert [cid.label for cid in table.main_components] == ["label", "frame", "npix", "threshold", "y", "x", *POSITION]
    assert table.meta == {
        "OBSID": sji.meta["OBSID"],
        "STARTOBS": sji.meta["STARTOBS"],
        "bursts_sigma_factor": 10.0,
        "bursts_min_pixels": 2,
    }
    # the slit-jaw image's coordinates, times and per-frame pointing, its helioprojective ones linked
    assert labels.coords._wcs is sji.coords._wcs
    np.testing.assert_array_equal(labels["Time"], sji["Time"])
    assert {key: labels.meta[key] for key in ("INSTRUME", "TWAVE1", "bursts_sigma_factor")} == {
        "INSTRUME": "SJI",
        "TWAVE1": 1400,
        "bursts_sigma_factor": 10.0,
    }
    np.testing.assert_array_equal(labels.meta["xcenix"], sji.meta["xcenix"])
    assert link_hpc(collection) == []
    linked = {cid for link in collection.links for cid in (link.get_to_id(), *link.get_from_ids())}
    assert set(labels.world_component_ids[1:]) <= linked
    # the typed threshold and fewest pixels
    answer(monkeypatch, sigma_factor=12.5, min_pixels=1)
    labels, table = run(app, qtbot, sji, 20)
    cube = read_sji_lvl2(path)
    assert_irispys(labels, table, *find_sji_bursts(cube, sigma_factor=12.5, min_pixels=1))
    # a dust-removed one, whose meta is no longer irispy's
    dust = remove_dust(sji)
    collection.append(dust)
    answer(monkeypatch)
    labels, table = run(app, qtbot, dust, 25)
    values = dust[dust.main_components[0]]
    clean = SJICube(values, cube.wcs, unit=cube.unit, mask=np.isnan(values), meta=cube.meta)
    assert_irispys(labels, table, *find_sji_bursts(clean))


def test_refusals_and_errors_show_why(app, monkeypatch, irispy_test_files):
    [raster] = raster_data([find_irispy_test_file(irispy_test_files, SI_IV)])
    [c_ii] = raster_data([find_irispy_test_file(irispy_test_files, SCAN)], ["C II 1336"])
    sji = image_data(find_irispy_test_file(irispy_test_files, SJI.replace("1400", "1330")))
    plain = Data(label="plain", x=np.zeros((3, 4, 5)))
    collection = app.data_collection
    collection.extend([raster, c_ii, sji, plain])
    shown = []
    monkeypatch.setenv("GLUE_TESTING", "False")  # glue raises the error instead while testing
    monkeypatch.setattr(QtWidgets.QMessageBox, "exec_", lambda box: shown.append(box.text()))
    tree = app._layer_widget
    action = tree._actions[ACTION]
    opened = answer(monkeypatch)
    for data in (c_ii, sji, plain):
        tree.ui.layerTree.set_selected_layers([data])
        refused(action)
    assert opened == []  # refused before asking
    for typed in ({"threshold": "Si IV"}, {"velocity_range": 0.1}):
        answer(monkeypatch, **typed)
        tree.ui.layerTree.set_selected_layers([raster])
        action.trigger()
    assert all(text.startswith("Could not detect UV bursts\n") for text in shown)
    assert [text.split("\n", 1)[1] for text in shown] == [
        f"No wavelength of {c_ii.label} (1332.73 to 1336.88 Å) lies within 50.0 km/s of Si IV 1402.77 Å.",
        f"{sji.label} is not a 1400 Å slit-jaw image, in which irispy finds UV bursts.",
        "plain is not an IRIS raster window or slit-jaw image.",
        "'Si IV' is not a threshold in DN/s, such as 500.",
        f"No wavelength of {raster.label} (1402.50 to 1403.04 Å) lies within 0.1 km/s of Si IV 1402.77 Å.",
    ]
    # Cancel adds nothing
    answer(monkeypatch, accept=False)
    action.trigger()
    assert not iris._RUNNING  # no thread started
    assert len(collection) == 4


@pytest.mark.remote_data
def test_a_full_si_iv_window_and_slit_jaw_image_give_irispys_bursts(irispy_data):
    """4000005156's full Si IV 1403 and the first 50 full-size frames of 4000255147's SJI 1400, both lazy."""
    path = irispy_data("iris_l2_20130902_182935_4000005156_raster_t000_r00000_si_iv.fits.gz")
    [raster] = raster_data([path])
    direct = find_si_iv_bursts(read_spectrograph_lvl2(path)["Si IV 1403"][0], threshold=80)
    assert_irispys(*si_iv_bursts(raster, threshold=80), *direct)
    path = irispy_data("iris_l2_20130902_163935_4000255147_SJI_1400_t000_f050.fits.gz")
    assert_irispys(*sji_bursts(image_data(path)), *find_sji_bursts(read_sji_lvl2(path)))
