"""
'IRIS: line moments…', on int16 copies of irispy's test files: what glue gets of irispy's maps, not irispy's numbers.
"""

from unittest.mock import Mock

import irispy.utils.moments
import numpy as np
import pytest
from glue.core import Data
from glue_qt.app.application import GlueApplication
from qtpy import QtWidgets

import glue_solar
from glue_solar.conftest import find_irispy_test_file
from glue_solar.quicklook import _wavelengths
from glue_solar.sources import moments
from glue_solar.sources.loaders import iris
from glue_solar.sources.loaders.iris import image_data, keep_hpc_linked, link_hpc, raster_data
from glue_solar.sources.moments import line_moments
from glue_solar.tests.test_lazy import SJI, int16_copy, int16_raster_copy
from glue_solar.tests.test_quicklook import SCAN

ACTION = "IRIS: line moments…"


@pytest.fixture
def app(qtbot):
    glue_solar.setup()
    app = GlueApplication()
    qtbot.addWidget(app)
    return app


@pytest.fixture
def scan_path(tmp_path, irispy_test_files):
    """Scan 0 of 3860258481, stored as int16: its Si IV 1403 window misses every sample of 24 pixels about 1402.77."""
    return int16_raster_copy(find_irispy_test_file(irispy_test_files, SCAN), tmp_path / SCAN)


def answer(monkeypatch, centre, wings=(), accept=True):
    """
    Make each line dialog return as if ``centre`` and any ``wings`` were typed and OK, or Cancel, pressed; returns the
    wings each dialog opened with.
    """
    opened = []

    def exec_(dialog):
        boxes = [dialog.findChild(QtWidgets.QDoubleSpinBox, side) for side in ("below", "above")]
        opened.append(tuple(box.value() for box in boxes))
        dialog.findChild(QtWidgets.QLineEdit, "centre").setText(centre)
        for box, wing in zip(boxes, wings):
            box.setValue(wing)
        return QtWidgets.QDialog.Accepted if accept else QtWidgets.QDialog.Rejected

    monkeypatch.setattr(QtWidgets.QDialog, "exec", exec_)
    return opened


def missing(raster, low, high):
    """Where every sample of ``raster`` from ``low`` to ``high`` Angstrom is missing."""
    wavelengths, _ = _wavelengths(raster)
    return np.isnan(raster[raster.main_components[0]][..., (wavelengths >= low) & (wavelengths <= high)]).all(-1)


def run(app, qtbot, data):
    """Trigger the action on ``data`` and wait for the dataset it adds and for its thread to end."""
    collection, tree = app.data_collection, app._layer_widget
    count = len(collection)
    tree.ui.layerTree.set_selected_layers([data])
    tree._actions[ACTION].trigger()
    assert iris._RUNNING  # on glue-qt's worker
    qtbot.waitUntil(lambda: len(collection) == count + 1 and not iris._RUNNING)
    return collection[-1]


def test_the_action_adds_one_linked_dataset_and_no_viewer(
    app, qtbot, monkeypatch, tmp_path, scan_path, irispy_test_files
):
    [raster] = raster_data([scan_path], ["Si IV 1403"])
    sji = image_data(int16_copy(find_irispy_test_file(irispy_test_files, SJI), tmp_path / SJI, [0]))
    collection = app.data_collection
    collection.extend([sji, raster])
    keep_hpc_linked(collection)
    opened = answer(monkeypatch, "1402.77")
    maps = run(app, qtbot, raster)
    assert opened == [(0.5, 0.5)]
    assert maps.label == f"{raster.label} moments 1402.77"
    assert maps.shape == raster.shape[:2]
    assert [(cid.label, maps.get_component(cid).units) for cid in maps.main_components] == [
        ("intensity", "DN_IRIS_FUV"),
        ("centroid", "Angstrom"),
        ("width", "Angstrom"),
        ("velocity", "km / s"),
        ("velocity_width", "km / s"),
    ]
    assert maps.meta == {
        "OBSID": raster.meta["OBSID"],
        "STARTOBS": raster.meta["STARTOBS"],
        "moments_centre": 1402.77,
        "moments_wings": (0.5, 0.5),
    }
    assert not any(app.viewers)
    # on the raster's steps and slit pixels, its helioprojective coordinates linked with the others'
    assert maps.coords.world_axis_units == ("arcsec", "arcsec")
    for cid, raster_cid in zip(maps.world_component_ids, raster.world_component_ids):
        np.testing.assert_allclose(maps[cid], raster[raster_cid, (..., 0)], rtol=0, atol=1e-9)
    assert link_hpc(collection) == []
    linked = {cid for link in collection.links for cid in (link.get_to_id(), *link.get_from_ids())}
    assert set(maps.world_component_ids) <= linked
    # NaN where every sample within the wings is missing, irispy's 0 there
    fill = missing(raster, 1402.27, 1403.27)
    assert fill.sum() == 24
    np.testing.assert_array_equal(np.isnan(maps["intensity"]), fill)
    assert np.isnan(maps["velocity"][fill]).all()


def test_the_typed_wings_and_a_blank_or_cancelled_centre(app, qtbot, monkeypatch, scan_path):
    [raster] = raster_data([scan_path], ["Si IV 1403"])
    collection = app.data_collection
    collection.append(raster)
    answer(monkeypatch, " 1402.77 ", wings=(0.2, 1.0))
    maps = run(app, qtbot, raster)
    assert (maps.meta["moments_centre"], maps.meta["moments_wings"]) == (1402.77, (0.2, 1.0))
    np.testing.assert_array_equal(np.isnan(maps["intensity"]), missing(raster, 1402.57, 1403.77))
    # nothing more is added
    tree = app._layer_widget
    tree.ui.layerTree.set_selected_layers([raster])  # glue selects the dataset added
    action = tree._actions[ACTION]
    for centre, accept in (("", True), ("1402.77", False)):
        answer(monkeypatch, centre, accept=accept)
        action.trigger()
        assert not iris._RUNNING  # and no thread started
        assert len(collection) == 2


def test_refusals_and_errors_show_why(app, qtbot, monkeypatch, scan_path, irispy_test_files):
    [raster] = raster_data([scan_path], ["Si IV 1403"])
    [stack] = raster_data(
        sorted(p for p in irispy_test_files if "3860258481_raster" in p.name)[:2], ["Si IV 1403"], stack=True
    )
    sji = image_data(find_irispy_test_file(irispy_test_files, SJI))
    plain = Data(label="plain", x=np.zeros((3, 4, 5)))
    collection = app.data_collection
    collection.extend([raster, stack, sji, plain])
    shown = []
    monkeypatch.setenv("GLUE_TESTING", "False")  # glue raises the error instead while testing
    monkeypatch.setattr(QtWidgets.QMessageBox, "exec_", lambda box: shown.append(box.text()))
    tree = app._layer_widget
    action = tree._actions[ACTION]
    opened = answer(monkeypatch, "1402.77")
    for data in (stack, sji, plain):
        tree.ui.layerTree.set_selected_layers([data])
        action.trigger()
    assert opened == []  # refused before asking
    for centre in ("3000", "Si IV"):
        answer(monkeypatch, centre)
        tree.ui.layerTree.set_selected_layers([raster])
        action.trigger()
    assert all(text.startswith("Could not compute line moments\n") for text in shown)
    assert [text.split("\n", 1)[1] for text in shown] == [
        f"{stack.label} is a stack of raster scans: line moments take one scan, as the observation browser loads them "
        "without 'Stack sequential raster scans'.",
        f"{sji.label} is not an IRIS raster window.",
        "plain is not an IRIS raster window.",
        f"No wavelength of {raster.label} (1398.63 to 1405.75 Å) lies within 0.5 Å below and 0.5 Å above 3000.0 Å.",
        "'Si IV' is not a wavelength in Angstrom, such as 1402.77.",
    ]
    assert len(collection) == 4
    # and an error of irispy's, on the thread
    monkeypatch.setattr(irispy.utils.moments, "calculate_moments", Mock(side_effect=RuntimeError("irispy failed")))
    answer(monkeypatch, "1402.77")
    action.trigger()
    qtbot.waitUntil(lambda: len(shown) == 6 and not iris._RUNNING)
    assert shown[-1] == "Could not compute line moments\nirispy failed"
    assert len(collection) == 4
    tree.ui.layerTree.set_selected_layers([raster, sji])  # one dataset at a time
    assert not action.isVisible()


def test_lazy_data_give_the_moments_of_data_in_memory(monkeypatch, scan_path):
    [raster] = raster_data([scan_path], ["Si IV 1403"])
    lazy = line_moments(raster, 1402.77)
    monkeypatch.setattr(moments, "SLAB", 3 * 109 * 4)  # irispy given steps 0-2, 3-5 and 6-7
    monkeypatch.setattr(iris, "LAZY", False)
    [eager] = raster_data([scan_path], ["Si IV 1403"])
    assert type(eager) is Data
    slabs = line_moments(eager, 1402.77)
    for cid in lazy.main_components:
        np.testing.assert_array_equal(slabs[cid.label], lazy[cid])
