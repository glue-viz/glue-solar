"""
'IRIS: red-blue asymmetry…', on an int16 copy of irispy's test raster and one irispy-data cutout: what glue gets of
irispy's maps.
"""

import numpy as np
import pytest
from glue.core import Data
from glue_qt.app.application import GlueApplication
from irispy.utils.constants import DN_UNIT
from irispy.utils.red_blue import RBAQualityFlag, calculate_red_blue_asymmetry
from qtpy import QtWidgets

import astropy.units as u

import glue_solar
from glue_solar.conftest import find_irispy_test_file
from glue_solar.quicklook import _wavelengths
from glue_solar.sources.loaders import iris
from glue_solar.sources.loaders.iris import image_data, keep_hpc_linked, link_hpc, raster_data
from glue_solar.sources.red_blue import red_blue_asymmetry
from glue_solar.tests.test_lazy import SJI, int16_copy, int16_raster_copy
from glue_solar.tests.test_moments import dn_per_second_cube
from glue_solar.tests.test_quicklook import SCAN

ACTION = "IRIS: red-blue asymmetry…"
BOXES = ("below", "above", "from", "to", "step")


@pytest.fixture
def app(qtbot):
    glue_solar.setup()
    app = GlueApplication()
    qtbot.addWidget(app)
    return app


@pytest.fixture
def scan_path(tmp_path, irispy_test_files):
    """Scan 0 of 3860258481, stored as int16."""
    return int16_raster_copy(find_irispy_test_file(irispy_test_files, SCAN), tmp_path / SCAN)


def answer(monkeypatch, rest, values=(), accept=True):
    """
    Make each red-blue dialog return as if ``rest`` and any ``values`` of its boxes were typed and OK, or Cancel,
    pressed; returns the values each dialog opened with.
    """
    opened = []

    def exec_(dialog):
        boxes = [dialog.findChild(QtWidgets.QDoubleSpinBox, name) for name in BOXES]
        opened.append(tuple(box.value() for box in boxes))
        dialog.findChild(QtWidgets.QLineEdit, "rest").setText(rest)
        for box, value in zip(boxes, values):
            box.setValue(value)
        return QtWidgets.QDialog.Accepted if accept else QtWidgets.QDialog.Rejected

    monkeypatch.setattr(QtWidgets.QDialog, "exec", exec_)
    return opened


def run(app, qtbot, data):
    """Trigger the action on ``data`` and wait for the dataset it adds and for its thread to end."""
    collection, tree = app.data_collection, app._layer_widget
    count = len(collection)
    tree.ui.layerTree.set_selected_layers([data])
    tree._actions[ACTION].trigger()
    assert iris._RUNNING  # on glue-qt's worker
    assert app.statusBar().currentMessage() == f"Computing red-blue asymmetry of {data.label}…"
    qtbot.waitUntil(lambda: len(collection) == count + 1 and not iris._RUNNING)
    assert app.statusBar().currentMessage() == ""
    return collection[-1]


def assert_irispys(maps, raster, rest, wavelengths=(1, 1), velocities=(30, 55), step=5, unit=DN_UNIT["FUV"]):
    """``maps`` are irispy's own, in one call, on ``raster``'s DN/s within ``wavelengths`` of ``rest``."""
    window, _ = _wavelengths(raster)
    taken = np.flatnonzero((window >= rest - wavelengths[0]) & (window <= rest + wavelengths[1]))
    direct = calculate_red_blue_asymmetry(
        dn_per_second_cube(raster, unit)[..., taken[0] : taken[-1] + 1],
        rest_wavelength=rest * u.AA,
        velocity_range=velocities * u.km / u.s,
        dv=step * u.km / u.s,
        return_profiles=False,
    )
    assert [cid.label for cid in maps.main_components] == list(direct) == ["red_blue_asymmetry", "quality"]
    for name, cube in direct.items():
        np.testing.assert_array_equal(maps[name], cube.data)
    assert maps["quality"].dtype == np.uint8
    assert {RBAQualityFlag.OK, RBAQualityFlag.NO_FINITE_DATA} <= set(np.unique(maps["quality"]))


def test_the_action_adds_irispys_maps_as_one_linked_dataset_and_no_viewer(
    app, qtbot, monkeypatch, tmp_path, scan_path, irispy_test_files
):
    [raster] = raster_data([scan_path], ["Si IV 1403"])
    sji = image_data(int16_copy(find_irispy_test_file(irispy_test_files, SJI), tmp_path / SJI, [0]))
    collection = app.data_collection
    collection.extend([sji, raster])
    keep_hpc_linked(collection)
    opened = answer(monkeypatch, "1402.77")
    maps = run(app, qtbot, raster)
    assert opened == [(1.0, 1.0, 30.0, 55.0, 5.0)]  # iris_xfiles' wing velocities
    assert maps.label == f"{raster.label} red-blue asymmetry 1402.77"
    assert maps.shape == raster.shape[:2]
    assert maps.meta == {
        "OBSID": raster.meta["OBSID"],
        "STARTOBS": raster.meta["STARTOBS"],
        "red_blue_rest": 1402.77,
        "red_blue_wavelengths": (1.0, 1.0),
        "red_blue_velocities": (30.0, 55.0),
        "red_blue_step": 5.0,
    }
    assert not any(app.viewers)
    # on the raster's steps and slit pixels, its helioprojective coordinates linked with the others'
    assert maps.coords.world_axis_units == ("arcsec", "arcsec")
    for cid, raster_cid in zip(maps.world_component_ids, raster.world_component_ids):
        np.testing.assert_allclose(maps[cid], raster[raster_cid, (..., 0)], rtol=0, atol=1e-9)
    assert link_hpc(collection) == []
    linked = {cid for link in collection.links for cid in (link.get_to_id(), *link.get_from_ids())}
    assert set(maps.world_component_ids) <= linked
    assert_irispys(maps, raster, 1402.77)


def test_the_typed_values_and_a_blank_or_cancelled_rest(app, qtbot, monkeypatch, scan_path):
    [raster] = raster_data([scan_path], ["Si IV 1403"])
    collection = app.data_collection
    collection.append(raster)
    answer(monkeypatch, " 1402.77 ", (0.6, 1.2, 20, 60, 2.5))
    maps = run(app, qtbot, raster)
    assert maps.meta["red_blue_wavelengths"] == (0.6, 1.2)
    assert (maps.meta["red_blue_velocities"], maps.meta["red_blue_step"]) == ((20, 60), 2.5)
    assert_irispys(maps, raster, 1402.77, (0.6, 1.2), (20, 60), 2.5)
    # nothing more is added
    tree = app._layer_widget
    tree.ui.layerTree.set_selected_layers([raster])  # glue selects the dataset added
    action = tree._actions[ACTION]
    for rest, accept in (("", True), ("1402.77", False)):
        answer(monkeypatch, rest, accept=accept)
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
    tree.ui.layerTree.set_selected_layers([raster])
    for rest in ("3000", "Si IV"):
        answer(monkeypatch, rest)
        action.trigger()
    # and an error of irispy's, on the thread
    answer(monkeypatch, "1402.77", (1, 1, 60, 30))
    action.trigger()
    qtbot.waitUntil(lambda: len(shown) == 6 and not iris._RUNNING)
    assert all(text.startswith("Could not compute red-blue asymmetry\n") for text in shown)
    assert [text.split("\n", 1)[1] for text in shown] == [
        f"{stack.label} is a stack of raster scans: red-blue asymmetry maps take one scan, as the observation browser "
        "loads them without 'Stack sequential raster scans'.",
        f"{sji.label} is not an IRIS raster window.",
        "plain is not an IRIS raster window.",
        f"No wavelength of {raster.label} (1398.63 to 1405.75 Å) lies within 1.0 Å below and 1.0 Å above 3000.0 Å.",
        "'Si IV' is not a wavelength in Angstrom, such as 1402.77.",
        "velocity_range must be positive and increasing",
    ]
    assert app.statusBar().currentMessage() == ""
    assert len(collection) == 4
    tree.ui.layerTree.set_selected_layers([raster, sji])  # one dataset at a time
    assert not action.isVisible()


def test_a_peak_at_16182_dn_is_saturated_at_each_steps_exposure_time(monkeypatch, scan_path):
    """
    irispy flags a pixel saturated where the peak of the wavelengths taken is at 16182 DN, its limit over the step's
    exposure time where the window has DN/s: the same DN/s is 16182 DN in an 8 s step, saturated, not in a 4 s one.
    """
    monkeypatch.setattr(iris, "LAZY", False)
    [raster] = raster_data([scan_path], ["Si IV 1403"])
    cid, (wavelengths, _) = raster.main_components[0], _wavelengths(raster)
    taken = np.flatnonzero(abs(wavelengths - 1402.77) <= 1)
    values, seconds = np.array(raster[cid]), np.array(raster["Exposure time"])
    seconds[:2] = [[[8]], [[4]]]
    values[:2, 10, taken[4]] = [16182, 16182 / 2]
    values[:, 20, wavelengths > 1404] = 16182  # not taken
    raster.update_components({cid: values, raster.id["Exposure time"]: seconds})
    for rate in (True, False):
        if not rate:  # irispy is given the DN themselves
            raster.remove_component(raster.id[f"{raster.label} DN/s"])
        maps = red_blue_asymmetry(raster, 1402.77)
        saturated = maps["quality"] == RBAQualityFlag.SATURATED
        assert np.flatnonzero(saturated).tolist() == [10]  # step 0, slit pixel 10
        assert np.isnan(maps["red_blue_asymmetry"][0, 10])


@pytest.mark.remote_data
def test_a_full_mg_ii_k_window_gives_irispys_maps(irispy_data):
    """3400109360's Mg II k, at full resolution, read lazily and its steps negative, gives irispy's maps."""
    [path] = irispy_data("iris_l2_20250328_225628_3400109360_cutout_raster.tar.gz")
    [raster] = raster_data([path], ["Mg II k 2796"])
    assert_irispys(red_blue_asymmetry(raster, 2796.352), raster, 2796.352, unit=DN_UNIT["NUV"])
