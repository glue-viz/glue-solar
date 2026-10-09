"""
'IRIS: detect UV bursts…', on irispy's burst test files and irispy-data files: what glue gets of irispy's labels and
events.
"""

import numpy as np
import pytest
from glue.core import Data
from glue_qt.app.application import GlueApplication
from irispy.io.sji import read_sji_lvl2
from irispy.io.spectrograph import read_spectrograph_lvl2
from irispy.sji import SJICube
from irispy.utils.bursts import find_si_iv_bursts, find_sji_bursts
from qtpy import QtWidgets

import astropy.units as u

import glue_solar
from glue_solar.conftest import find_irispy_test_file
from glue_solar.sources.bursts import si_iv_bursts, sji_bursts
from glue_solar.sources.calibration import remove_dust
from glue_solar.sources.loaders import iris
from glue_solar.sources.loaders.iris import image_data, keep_hpc_linked, link_hpc, raster_data
from glue_solar.tests.test_lazy import SJI
from glue_solar.tests.test_quicklook import SCAN

ACTION = "IRIS: detect UV bursts…"
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
    # 'Shift pointing…' moves the table's coordinates as the map's
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
    [stack] = raster_data(
        sorted(p for p in irispy_test_files if "3860258481_raster" in p.name)[:2], ["Si IV 1403"], stack=True
    )
    sji = image_data(find_irispy_test_file(irispy_test_files, SJI.replace("1400", "1330")))
    plain = Data(label="plain", x=np.zeros((3, 4, 5)))
    collection = app.data_collection
    collection.extend([raster, c_ii, stack, sji, plain])
    shown = []
    monkeypatch.setenv("GLUE_TESTING", "False")  # glue raises the error instead while testing
    monkeypatch.setattr(QtWidgets.QMessageBox, "exec_", lambda box: shown.append(box.text()))
    tree = app._layer_widget
    action = tree._actions[ACTION]
    opened = answer(monkeypatch)
    for data in (c_ii, stack, sji, plain):
        tree.ui.layerTree.set_selected_layers([data])
        action.trigger()
    assert opened == []  # refused before asking
    for typed in ({"threshold": "Si IV"}, {"velocity_range": 0.1}):
        answer(monkeypatch, **typed)
        tree.ui.layerTree.set_selected_layers([raster])
        action.trigger()
    assert all(text.startswith("Could not detect UV bursts\n") for text in shown)
    assert [text.split("\n", 1)[1] for text in shown] == [
        f"No wavelength of {c_ii.label} (1332.73 to 1336.88 Å) lies within 50.0 km/s of Si IV 1402.77 Å.",
        f"{stack.label} is a stack of raster scans: UV bursts take one scan, as the observation browser loads them "
        "without 'Stack sequential raster scans'.",
        f"{sji.label} is not a 1400 Å slit-jaw image, in which irispy finds UV bursts.",
        "plain is not an IRIS raster window or slit-jaw image.",
        "'Si IV' is not a threshold in DN/s, such as 500.",
        f"No wavelength of {raster.label} (1402.50 to 1403.04 Å) lies within 0.1 km/s of Si IV 1402.77 Å.",
    ]
    # Cancel adds nothing
    answer(monkeypatch, accept=False)
    action.trigger()
    assert not iris._RUNNING  # no thread started
    assert len(collection) == 5


@pytest.mark.remote_data
def test_a_full_si_iv_window_and_slit_jaw_image_give_irispys_bursts(irispy_data):
    """4000005156's full Si IV 1403 and the first 50 full-size frames of 4000255147's SJI 1400, both lazy."""
    path = irispy_data("iris_l2_20130902_182935_4000005156_raster_t000_r00000_si_iv.fits.gz")
    [raster] = raster_data([path])
    direct = find_si_iv_bursts(read_spectrograph_lvl2(path)["Si IV 1403"][0], threshold=80)
    assert_irispys(*si_iv_bursts(raster, threshold=80), *direct)
    path = irispy_data("iris_l2_20130902_163935_4000255147_SJI_1400_t000_f050.fits.gz")
    assert_irispys(*sji_bursts(image_data(path)), *find_sji_bursts(read_sji_lvl2(path)))
