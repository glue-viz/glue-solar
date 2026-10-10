"""
'IRIS: Mg II features…', on irispy's Mg II features test raster and int16 copies of its test raster: what glue gets of
irispy's maps, of a scan or a stack.
"""

import numpy as np
import pytest
from glue.core import Data
from glue_qt.app.application import GlueApplication
from irispy.utils.constants import DN_UNIT
from irispy.utils.mg_features import calculate_mg_features
from qtpy import QtWidgets

import astropy.units as u

import glue_solar
from glue_solar.conftest import find_irispy_test_file
from glue_solar.sources import mg_features
from glue_solar.sources.loaders import iris
from glue_solar.sources.loaders.iris import image_data, keep_hpc_linked, link_hpc, raster_data
from glue_solar.tests.test_lazy import SJI, int16_copy, int16_raster_copy
from glue_solar.tests.test_moments import dn_per_second_cube
from glue_solar.tests.test_quicklook import SCAN

ACTION = "IRIS: Mg II features…"
# 4000005156 cut to Mg II k and to Mg II h, the line's ±44 km/s only, as two windows; 150 spectra of each hold -200
FEATURES = "iris_l2_20130902_182935_4000005156_raster_t000_r00000_mg_features.fits"
KH = ("k", "h")


@pytest.fixture
def app(qtbot):
    glue_solar.setup()
    app = GlueApplication()
    qtbot.addWidget(app)
    return app


@pytest.fixture
def scan_path(tmp_path, irispy_test_files):
    """Scan 0 of 3860258481, stored as int16; its Mg II k window covers h too."""
    return int16_raster_copy(find_irispy_test_file(irispy_test_files, SCAN), tmp_path / SCAN)


def answer(monkeypatch, velocities=None, ticks=None, accept=True):
    """
    Make each Mg II features dialog return as if any ``velocities`` were typed and the lines ticked as ``ticks``, and
    OK, or Cancel, pressed; returns the velocities and ticks each dialog opened with.
    """
    opened = []

    def exec_(dialog):
        boxes = [dialog.findChild(QtWidgets.QDoubleSpinBox, name) for name in ("from", "to")]
        lines = [dialog.findChild(QtWidgets.QCheckBox, line) for line in KH]
        opened.append((*(box.value() for box in boxes), *(tick.isChecked() for tick in lines)))
        for box, value in zip(boxes, velocities or ()):
            box.setValue(value)
        for tick, value in zip(lines, ticks or ()):
            tick.setChecked(value)
        return QtWidgets.QDialog.Accepted if accept else QtWidgets.QDialog.Rejected

    monkeypatch.setattr(QtWidgets.QDialog, "exec", exec_)
    return opened


def run(app, qtbot, data, message=""):
    """
    Trigger the action on ``data`` and wait for the dataset it adds and for its thread to end, the status bar then
    saying ``message``.
    """
    collection, tree = app.data_collection, app._layer_widget
    count = len(collection)
    tree.ui.layerTree.set_selected_layers([data])
    tree._actions[ACTION].trigger()
    assert iris._RUNNING  # on glue-qt's worker
    assert app.statusBar().currentMessage() == f"Computing Mg II features of {data.label}…"
    qtbot.waitUntil(lambda: len(collection) == count + 1 and not iris._RUNNING)
    assert app.statusBar().currentMessage() == message
    return collection[-1]


def assert_irispys(maps, raster, velocities=(-40, 40), lines=KH):
    """``maps`` are irispy's own, in one call, on the whole of ``raster``'s DN/s, its saturated maps only counted."""
    direct = calculate_mg_features(
        dn_per_second_cube(raster, DN_UNIT["NUV"]), velocity_range=velocities * u.km / u.s, lines=lines
    )
    direct = {name: cube for name, cube in direct.items() if not name.endswith("_saturated")}
    assert [cid.label for cid in maps.main_components] == list(direct)
    for name, cube in direct.items():
        np.testing.assert_array_equal(maps[name], cube.data)
        assert maps.get_component(name).units == str(cube.unit)


def test_the_action_adds_irispys_maps_as_one_linked_dataset_and_no_viewer(
    app, qtbot, monkeypatch, tmp_path, scan_path, irispy_test_files
):
    [raster] = raster_data([scan_path], ["Mg II k 2796"])
    sji = image_data(int16_copy(find_irispy_test_file(irispy_test_files, SJI), tmp_path / SJI, [0]))
    collection = app.data_collection
    collection.extend([sji, raster])
    keep_hpc_linked(collection)
    opened = answer(monkeypatch)
    monkeypatch.setattr(mg_features, "SLAB", 3 * 109 * 33)  # slabs of 3 steps on the crop of both lines
    maps = run(app, qtbot, raster)
    assert opened == [(-40.0, 40.0, True, True)]  # irispy's defaults
    assert maps.label == f"{raster.label} Mg II features"
    assert maps.shape == raster.shape[:2]
    assert maps.meta == {
        "OBSID": raster.meta["OBSID"],
        "STARTOBS": raster.meta["STARTOBS"],
        "mg_features_velocities": (-40.0, 40.0),
        "mg_features_lines": KH,
    }
    assert not any(app.viewers)
    # on the raster's steps and slit pixels, its helioprojective coordinates linked with the others'
    assert maps.coords.world_axis_units == ("arcsec", "arcsec")
    for cid, raster_cid in zip(maps.world_component_ids, raster.world_component_ids):
        np.testing.assert_allclose(maps[cid], raster[raster_cid, (..., 0)], rtol=0, atol=1e-9)
    assert link_hpc(collection) == []
    linked = {cid for link in collection.links for cid in (link.get_to_id(), *link.get_from_ids())}
    assert set(maps.world_component_ids) <= linked
    assert_irispys(maps, raster)
    assert_irispys(mg_features.mg_features(raster), raster)  # the same in glue's terminal


def test_a_saturated_sample_blanks_its_lines_features_at_its_pixel(app, qtbot, monkeypatch, scan_path):
    """
    A saturated sample, +Inf, among those searched for a line makes that line's features NaN at its pixel, as irispy
    finds them; the status bar says how many pixels.
    """
    monkeypatch.setattr(iris, "LAZY", False)
    monkeypatch.setattr(mg_features, "SLAB", 3 * 109 * 33)  # slabs of 3 steps on the crop of both lines
    [raster] = raster_data([scan_path], ["Mg II k 2796"])
    app.data_collection.append(raster)
    clean = calculate_mg_features(dn_per_second_cube(raster, DN_UNIT["NUV"]))
    assert np.isfinite(clean["h2v_velocity"].data[:, 10]).all()  # found unless saturated
    assert np.isfinite(clean["k3_velocity"].data[0, 30])
    cid = raster.main_components[0]
    values = np.array(raster[cid])
    values[:, 10, 51] = np.inf  # h's core, at -6 km/s, at every step
    values[0, 30, 23] = np.inf  # k's core, at -0.6 km/s
    raster.update_components({cid: values})
    answer(monkeypatch)
    message = "the k features at 1 saturated pixel and the h features at 8 saturated pixels are NaN"
    maps = run(app, qtbot, raster, f"{raster.label} Mg II features: {message}")
    assert maps.meta["mg_features_saturated"] == {"k": 1, "h": 8}
    assert_irispys(maps, raster)
    for blanked, names in (((0, 30), ("k2v", "k3", "k2r")), ((slice(None), 10), ("h2v", "h3", "h2r"))):
        for name in names:
            assert np.isnan(maps[f"{name}_velocity"][blanked]).all()


def test_a_stack_gives_each_scans_maps_at_its_coordinates(app, qtbot, monkeypatch, stack_paths):
    """
    A lazy stack of 3860258481's three scans, in slabs of 3 steps, gives one dataset whose maps and coordinates at
    each scan are those of the scan loaded alone.
    """
    monkeypatch.setattr(mg_features, "SLAB", 3 * 109 * 33)
    [stack] = raster_data(stack_paths, ["Mg II k 2796"], stack=True)
    collection = app.data_collection
    collection.append(stack)
    keep_hpc_linked(collection)
    answer(monkeypatch)
    maps = run(app, qtbot, stack)
    assert maps.shape == stack.shape[:-1]
    assert link_hpc(collection) == []
    for k, path in enumerate(stack_paths):
        [scan] = raster_data([path], ["Mg II k 2796"])
        alone = mg_features.mg_features(scan)
        assert maps.meta == alone.meta
        for cid in alone.main_components:
            np.testing.assert_array_equal(maps[cid.label][k], alone[cid])
        for cid in alone.world_component_ids:
            np.testing.assert_allclose(maps[cid.label][k], alone[cid], rtol=0, atol=1e-9)


def test_a_stacks_saturated_pixels_are_counted_over_its_scans(app, qtbot, monkeypatch, stack_paths):
    monkeypatch.setattr(iris, "LAZY", False)
    [stack] = raster_data(stack_paths, ["Mg II k 2796"], stack=True)
    app.data_collection.append(stack)
    cid = stack.main_components[0]
    values = np.array(stack[cid])
    values[[0, 2], :, 10, 51] = np.inf  # h's core, at every step of scans 0 and 2
    values[1, 0, 30, 23] = np.inf  # k's core
    stack.update_components({cid: values})
    answer(monkeypatch)
    message = "the k features at 1 saturated pixel and the h features at 16 saturated pixels are NaN"
    maps = run(app, qtbot, stack, f"{stack.label} Mg II features: {message}")
    assert maps.meta["mg_features_saturated"] == {"k": 1, "h": 16}
    assert np.isnan(maps["h3_velocity"][[0, 2], :, 10]).all()


def test_the_lines_ticked_at_first_are_those_covered_and_the_typed_values(app, qtbot, monkeypatch, irispy_test_files):
    k, h = raster_data([find_irispy_test_file(irispy_test_files, FEATURES)], ["Mg II k 2796", "Mg II h 2803"])
    collection = app.data_collection
    collection.extend([k, h])
    opened = answer(monkeypatch)
    maps = run(app, qtbot, k)
    assert maps.meta["mg_features_lines"] == ("k",)
    assert_irispys(maps, k, lines=("k",))
    assert_irispys(run(app, qtbot, h), h, lines=("h",))
    assert opened == [(-40.0, 40.0, True, False), (-40.0, 40.0, False, True)]
    answer(monkeypatch, (-30, 35), (True, True))  # h ticked too: left out, as the window does not cover it
    maps = run(app, qtbot, k)
    assert maps.meta["mg_features_velocities"] == (-30, 35)
    assert_irispys(maps, k, (-30, 35), ("k",))
    # nothing more is added
    tree = app._layer_widget
    tree.ui.layerTree.set_selected_layers([k])  # glue selects the dataset added
    action = tree._actions[ACTION]
    for ticks, accept in (((False, False), True), ((True, False), False)):
        answer(monkeypatch, ticks=ticks, accept=accept)
        action.trigger()
        assert not iris._RUNNING  # and no thread started
        assert len(collection) == 5


def test_refusals_and_errors_show_why(app, qtbot, monkeypatch, irispy_test_files):
    [k] = raster_data([find_irispy_test_file(irispy_test_files, FEATURES)], ["Mg II k 2796"])
    [si_iv] = raster_data([find_irispy_test_file(irispy_test_files, SCAN)], ["Si IV 1403"])
    sji = image_data(find_irispy_test_file(irispy_test_files, SJI))
    plain = Data(label="plain", x=np.zeros((3, 4, 5)))
    collection = app.data_collection
    collection.extend([k, si_iv, sji, plain])
    shown = []
    monkeypatch.setenv("GLUE_TESTING", "False")  # glue raises the error instead while testing
    monkeypatch.setattr(QtWidgets.QMessageBox, "exec_", lambda box: shown.append(box.text()))
    tree = app._layer_widget
    action = tree._actions[ACTION]
    opened = answer(monkeypatch)
    for data in (si_iv, sji, plain):
        tree.ui.layerTree.set_selected_layers([data])
        action.trigger()
    assert opened == []  # refused before asking
    tree.ui.layerTree.set_selected_layers([k])
    for velocities in ((40, -40), (-40, 60)):
        answer(monkeypatch, velocities)
        action.trigger()
    # and an error of irispy's, on the thread
    answer(monkeypatch, (0, 1))
    action.trigger()
    qtbot.waitUntil(lambda: len(shown) == 6 and not iris._RUNNING)
    assert all(text.startswith("Could not compute Mg II features\n") for text in shown)
    assert [text.split("\n", 1)[1] for text in shown] == [
        f"{si_iv.label} (1398.63 to 1405.75 Å) does not cover Mg II k or h from -40.0 to 40.0 km/s.",
        f"{sji.label} is not an IRIS raster window.",
        "plain is not an IRIS raster window.",
        "The velocities, from 40.0 to -40.0 km/s, do not increase.",
        f"{k.label} (2795.94 to 2796.78 Å) does not cover Mg II k from -40.0 to 60.0 km/s.",
        "Too few wavelength points of Mg II k between 0.0 and 1.0 km/s",
    ]
    assert app.statusBar().currentMessage() == ""
    assert len(collection) == 4
    tree.ui.layerTree.set_selected_layers([k, sji])  # one dataset at a time
    assert not action.isVisible()
