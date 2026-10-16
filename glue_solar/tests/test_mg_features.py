"""
'IRIS: Mg II features…', on irispy's Mg II features test raster and int16 copies of its test raster: what glue gets of
irispy's maps, its saturated maps too, of a scan or a stack, from irispy's rest wavelengths or one set, and what a
session keeps of them.
"""

import numpy as np
import pytest
from glue.core import Data, DataCollection
from irispy.spectrograph import SpectrogramCube
from irispy.utils.constants import DN_UNIT
from irispy.utils.mg_features import _REST_WAVELENGTH, calculate_mg_features
from ndcube.wcs.wrappers import ResampledLowLevelWCS
from qtpy import QtWidgets

import astropy.units as u
from astropy import constants

from glue_solar.conftest import SCAN, find_irispy_test_file, int16_copy
from glue_solar.quicklook import _wavelengths
from glue_solar.sources import mg_features
from glue_solar.sources.loaders import iris
from glue_solar.sources.loaders.iris import image_data, keep_hpc_linked, link_hpc, raster_data
from glue_solar.tests import helpers
from glue_solar.tests.helpers import refused, run_action
from glue_solar.tests.test_lazy import SJI
from glue_solar.tests.test_moments import dn_per_second_cube
from glue_solar.tests.test_sessions import twice

ACTION = "IRIS: Mg II features… (Mg II)"
# 4000005156 cut to Mg II k and to Mg II h, the line's ±44 km / s only, as two windows; 150 spectra of each hold -200
FEATURES = "iris_l2_20130902_182935_4000005156_raster_t000_r00000_mg_features.fits"
KH = ("k", "h")


def answer(monkeypatch, velocities=(), ticks=(), accept=True):
    """`helpers.answer` for the Mg II features dialog, ``velocities`` from and to, and ``ticks`` k and h."""
    return helpers.answer(monkeypatch, accept, **dict(zip(("from", "to"), velocities)), **dict(zip(KH, ticks)))


def run(app, qtbot, data, message=""):
    """Trigger the action on ``data``; returns the dataset it adds, the status bar then saying ``message``."""
    [maps] = run_action(app, qtbot, data, ACTION, f"Computing Mg II features of {data.label}…", message)
    return maps


def assert_irispys(maps, raster, velocities=(-40, 40), lines=KH, cube=None):
    """
    ``maps`` are irispy's own, in one call, on the whole of ``raster``'s DN / s, or on ``cube``, its saturated maps as
    glue's int64 named 'k saturated' and 'h saturated'.
    """
    if cube is None:
        cube = dn_per_second_cube(raster, DN_UNIT["NUV"])
    direct = calculate_mg_features(cube, velocity_range=velocities * u.km / u.s, lines=lines)
    names = [key.replace("_saturated", " saturated") for key in direct]
    assert [cid.label for cid in maps.main_components] == names
    for name, cube in zip(names, direct.values()):
        np.testing.assert_array_equal(maps[name], cube.data)
        assert maps.get_component(name).units == str(cube.unit)
        assert maps[name].dtype == (np.int64 if name.endswith(" saturated") else cube.data.dtype)


def test_the_action_adds_irispys_maps_as_one_linked_dataset_and_no_viewer(
    app, qtbot, monkeypatch, tmp_path, scan_path, irispy_test_files
):
    [raster] = raster_data([scan_path], ["Mg II k 2796"])
    sji = image_data(int16_copy(find_irispy_test_file(irispy_test_files, SJI), tmp_path / SJI, [0]))
    collection = app.data_collection
    collection.extend([sji, raster])
    keep_hpc_linked(collection)
    opened = answer(monkeypatch)
    monkeypatch.setattr("glue_solar.sources.moments.SLAB", 3 * 109 * 33)  # slabs of 3 steps on the crop of both lines
    maps = run(app, qtbot, raster)
    assert opened == [{"from": -40.0, "to": 40.0, "k": True, "h": True}]  # irispy's defaults
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
    monkeypatch.setattr("glue_solar.sources.moments.SLAB", 3 * 109 * 33)  # slabs of 3 steps on the crop of both lines
    [raster] = raster_data([scan_path], ["Mg II k 2796"])
    app.data_collection.append(raster)
    clean = calculate_mg_features(dn_per_second_cube(raster, DN_UNIT["NUV"]))
    assert np.isfinite(clean["h2v_velocity"].data[:, 10]).all()  # found unless saturated
    assert np.isfinite(clean["k3_velocity"].data[0, 30])
    cid = raster.main_components[0]
    values = np.array(raster[cid])
    values[:, 10, 51] = np.inf  # h's core, at -6 km / s, at every step
    values[0, 30, 23] = np.inf  # k's core, at -0.6 km / s
    raster.update_components({cid: values})
    answer(monkeypatch)
    message = "the k features at 1 saturated pixel and the h features at 8 saturated pixels are NaN"
    maps = run(app, qtbot, raster, f"{raster.label} Mg II features: {message}")
    assert maps.meta["mg_features_saturated"] == {"k": 1, "h": 8}
    assert_irispys(maps, raster)
    for blanked, names in (((0, 30), ("k2v", "k3", "k2r")), ((slice(None), 10), ("h2v", "h3", "h2r"))):
        for name in names:
            assert np.isnan(maps[f"{name}_velocity"][blanked]).all()
    # the saturated maps show the pixels the status bar counts, and only them
    assert list(zip(*np.nonzero(maps["k saturated"]))) == [(0, 30)]
    assert list(zip(*np.nonzero(maps["h saturated"]))) == [(step, 10) for step in range(8)]


def test_a_stack_gives_each_scans_maps_at_its_coordinates(app, qtbot, monkeypatch, stack_paths):
    """
    A lazy stack of 3860258481's three scans, in slabs of 3 steps, with a rest wavelength set 0.3 Å redder than irispy's
    k, gives one dataset whose maps and coordinates at each scan are those of the scan loaded alone.
    """
    monkeypatch.setattr("glue_solar.sources.moments.SLAB", 3 * 109 * 33)
    [stack] = raster_data(stack_paths, ["Mg II k 2796"], stack=True)
    collection = app.data_collection
    rest = _REST_WAVELENGTH["k"].to_value(u.AA) + 0.3
    stack.meta["rest_wavelength"] = rest
    collection.append(stack)
    keep_hpc_linked(collection)
    answer(monkeypatch)
    maps = run(app, qtbot, stack)
    assert maps.shape == stack.shape[:-1]
    assert link_hpc(collection) == []
    for k, path in enumerate(stack_paths):
        [scan] = raster_data([path], ["Mg II k 2796"])
        scan.meta["rest_wavelength"] = rest
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
    # each scan's own saturated maps
    assert list(zip(*np.nonzero(maps["k saturated"]))) == [(1, 0, 30)]
    assert list(zip(*np.nonzero(maps["h saturated"]))) == [(scan, step, 10) for scan in (0, 2) for step in range(8)]


def test_a_rest_wavelength_set_shifts_the_wavelengths_irispy_is_given(app, qtbot, monkeypatch, irispy_test_files):
    """
    A rest wavelength set 0.01 Å redder than irispy's Mg II k gives irispy the window's wavelengths 0.01 Å shorter, as
    irispy advises for IDL's wave_comp: k's velocities 1.07 km / s lower, h's by 0.01 Å at h; none set gives irispy's own
    again, and one over 1 Å from k is refused before asking.
    """
    # the test file's own float32: the int16 copy's rounding leaves spectra with equal samples, whose features jump
    [raster] = raster_data([find_irispy_test_file(irispy_test_files, SCAN)], ["Mg II k 2796"])
    collection = app.data_collection
    collection.append(raster)
    answer(monkeypatch)
    plain = run(app, qtbot, raster)
    rest = {line: _REST_WAVELENGTH[line].to_value(u.AA) for line in KH}
    raster.meta["rest_wavelength"] = rest["k"] + 0.01
    shifted = run(app, qtbot, raster)
    assert shifted.meta["mg_features_rest_wavelength"] == rest["k"] + 0.01
    c = constants.c.to_value(u.km / u.s)
    for line in KH:
        for feature in ("2v", "3", "2r"):
            name = f"{line}{feature}_velocity"
            found = np.isfinite(plain[name])
            assert found.sum() > 200  # of 872
            np.testing.assert_array_equal(np.isfinite(shifted[name]), found)
            np.testing.assert_allclose(shifted[name][found] - plain[name][found], -c * 0.01 / rest[line], atol=1e-5)
            np.testing.assert_allclose(shifted[f"{line}{feature}_intensity"], plain[f"{line}{feature}_intensity"])
    # over a pixel, 0.3 Å, in slabs of 3 steps: what irispy finds on the whole window shifted so, its crop shifted too
    monkeypatch.setattr("glue_solar.sources.moments.SLAB", 3 * 109 * 33)
    raster.meta["rest_wavelength"] = rest["k"] + 0.3
    wavelengths, _ = _wavelengths(raster)
    shift = -(raster.meta["rest_wavelength"] - rest["k"]) * (wavelengths.size - 1) / (wavelengths[-1] - wavelengths[0])
    cube = dn_per_second_cube(raster, DN_UNIT["NUV"])
    cube = SpectrogramCube(cube.data, ResampledLowLevelWCS(cube.wcs, 1, (shift, 0, 0)), unit=cube.unit, mask=cube.mask)
    assert_irispys(mg_features.mg_features(raster), raster, cube=cube)
    del raster.meta["rest_wavelength"]
    again = run(app, qtbot, raster)
    assert again.meta == plain.meta
    for cid in plain.main_components:
        np.testing.assert_array_equal(again[cid.label], plain[cid])
    shown = []
    monkeypatch.setenv("GLUE_TESTING", "False")  # glue raises the error instead while testing
    monkeypatch.setattr(QtWidgets.QMessageBox, "exec_", lambda box: shown.append(box.text()))
    opened = answer(monkeypatch)
    raster.meta["rest_wavelength"] = 2803.53  # Mg II h's
    tree = app._layer_widget
    tree.ui.layerTree.set_selected_layers([raster])  # glue selects the dataset added
    assert tree._actions[ACTION].isVisible()  # offered still
    tree._actions[ACTION].trigger()
    why = (
        f"The rest wavelength set for {raster.label}, 2803.53 Å, is not Mg II k's: Mg II features take one within 1 Å "
        f"of 2796.351 Å. Change or clear it with 'IRIS: set rest wavelength…'."
    )
    assert shown == [f"Could not compute Mg II features\n{why}"]
    assert opened == []
    assert not iris._RUNNING
    with pytest.raises(ValueError, match="is not Mg II k's"):
        mg_features.mg_features(raster)


def test_a_session_keeps_the_maps_and_their_meta(monkeypatch, scan_path):
    monkeypatch.setattr(iris, "LAZY", False)
    [raster] = raster_data([scan_path], ["Mg II k 2796"])
    cid = raster.main_components[0]
    values = np.array(raster[cid])
    values[0, 30, 23] = np.inf  # k's core
    raster.update_components({cid: values})
    raster.meta["rest_wavelength"] = 2796.36
    maps = mg_features.mg_features(raster)
    assert maps.meta["mg_features_saturated"] == {"k": 1}
    for (restored,) in twice(DataCollection([maps])):
        # glue's JSON keeps tuples as lists
        assert restored.meta == {**maps.meta, "mg_features_velocities": [-40.0, 40.0], "mg_features_lines": ["k", "h"]}
        assert [cid.label for cid in restored.main_components] == [cid.label for cid in maps.main_components]
        for cid in maps.main_components:
            np.testing.assert_array_equal(restored[cid.label], maps[cid])
            assert restored[cid.label].dtype == maps[cid].dtype
            assert restored.get_component(cid.label).units == maps.get_component(cid).units


def test_the_lines_ticked_at_first_are_those_covered_and_the_typed_values(app, qtbot, monkeypatch, irispy_test_files):
    k, h = raster_data([find_irispy_test_file(irispy_test_files, FEATURES)], ["Mg II k 2796", "Mg II h 2803"])
    collection = app.data_collection
    collection.extend([k, h])
    opened = answer(monkeypatch)
    maps = run(app, qtbot, k)
    assert maps.meta["mg_features_lines"] == ("k",)
    assert_irispys(maps, k, lines=("k",))
    assert_irispys(run(app, qtbot, h), h, lines=("h",))
    assert opened == [
        {"from": -40.0, "to": 40.0, "k": True, "h": False},
        {"from": -40.0, "to": 40.0, "k": False, "h": True},
    ]
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
        refused(action)
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
        f"{si_iv.label} (1398.63 to 1405.75 Å) does not cover Mg II k or h from -40.0 to 40.0 km / s.",
        f"{sji.label} is not an IRIS raster window.",
        "plain is not an IRIS raster window.",
        "The velocities, from 40.0 to -40.0 km / s, do not increase.",
        f"{k.label} (2795.94 to 2796.78 Å) does not cover Mg II k from -40.0 to 60.0 km / s.",
        "Too few wavelength points of Mg II k between 0.0 and 1.0 km/s",  # irispy's text
    ]
    assert app.statusBar().currentMessage() == ""
    assert len(collection) == 4
    tree.ui.layerTree.set_selected_layers([k, sji])  # one dataset at a time
    assert not action.isVisible()
