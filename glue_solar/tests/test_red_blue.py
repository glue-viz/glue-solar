"""
'IRIS: line maps…' and its red-blue asymmetry, on int16 copies of irispy's test raster and one irispy-data cutout: what
glue gets of irispy's maps, of a scan or a stack.
"""

import numpy as np
import pytest
from glue.core import Data
from irispy.utils.constants import DN_UNIT
from irispy.utils.red_blue import RBAQualityFlag, calculate_red_blue_asymmetry
from qtpy import QtWidgets

import astropy.units as u

from glue_solar.conftest import find_irispy_test_file, int16_copy
from glue_solar.quicklook import _wavelengths
from glue_solar.sources import moments
from glue_solar.sources.loaders import iris
from glue_solar.sources.loaders.iris import image_data, keep_hpc_linked, link_hpc, raster_data
from glue_solar.sources.red_blue import red_blue_asymmetry
from glue_solar.tests import test_moments
from glue_solar.tests.helpers import refused, run_action
from glue_solar.tests.test_lazy import SJI
from glue_solar.tests.test_moments import ACTION, dn_per_second_cube


def answer(monkeypatch, rest, accept=True):
    """`test_moments.answer` with red-blue asymmetry alone ticked."""
    return test_moments.answer(monkeypatch, rest, accept=accept, moments=False, red_blue=True)


def run(app, qtbot, data):
    """Trigger the action on ``data``; returns the dataset it adds."""
    [maps] = run_action(app, qtbot, data, ACTION, f"Computing line maps of {data.label}…")
    return maps


def assert_irispys(maps, raster, rest, wavelengths=(1, 1), velocities=(30, 55), step=5, unit=DN_UNIT["FUV"]):
    """``maps`` are irispy's own, in one call, on ``raster``'s DN / s within ``wavelengths`` of ``rest``."""
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


def test_the_action_adds_irispys_maps_as_one_linked_dataset_in_a_viewer(
    app, qtbot, monkeypatch, tmp_path, scan_path, irispy_test_files
):
    [raster] = raster_data([scan_path], ["Si IV 1403"])
    sji = image_data(int16_copy(find_irispy_test_file(irispy_test_files, SJI), tmp_path / SJI, [0]))
    collection = app.data_collection
    collection.extend([sji, raster])
    keep_hpc_linked(collection)
    opened = answer(monkeypatch, "1402.77")
    maps = run(app, qtbot, raster)
    assert opened[0]["rest"] == "1402.77"  # the window's main line
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
    [[viewer]] = app.viewers  # glue's Image viewer of its first map (D83)
    assert viewer.state.layers[0].attribute is maps.main_components[0]
    # on the raster's steps and slit pixels, its helioprojective coordinates linked with the others'
    assert maps.coords.world_axis_units == ("arcsec", "arcsec")
    for cid, raster_cid in zip(maps.world_component_ids, raster.world_component_ids):
        np.testing.assert_allclose(maps[cid], raster[raster_cid, (..., 0)], rtol=0, atol=1e-9)
    assert link_hpc(collection) == []
    linked = {cid for link in collection.links for cid in (link.get_to_id(), *link.get_from_ids())}
    assert set(maps.world_component_ids) <= linked
    assert_irispys(maps, raster, 1402.77)


def test_other_values_and_a_blank_or_canceled_rest(app, qtbot, monkeypatch, scan_path):
    """Other wavelengths, wing velocities and step are the function's; a blank rest wavelength or Cancel adds nothing."""
    [raster] = raster_data([scan_path], ["Si IV 1403"])
    collection = app.data_collection
    collection.append(raster)
    maps = red_blue_asymmetry(raster, 1402.77, (0.6, 1.2), (20, 60), 2.5)
    assert maps.meta["red_blue_wavelengths"] == (0.6, 1.2)
    assert (maps.meta["red_blue_velocities"], maps.meta["red_blue_step"]) == ((20, 60), 2.5)
    assert_irispys(maps, raster, 1402.77, (0.6, 1.2), (20, 60), 2.5)
    tree = app._layer_widget
    tree.ui.layerTree.set_selected_layers([raster])
    action = tree._actions[ACTION]
    for rest, accept in (("", True), ("1402.77", False)):
        answer(monkeypatch, rest, accept=accept)
        action.trigger()
        assert not iris._RUNNING  # and no thread started
        assert len(collection) == 1


def test_a_stack_gives_each_scans_maps_at_its_coordinates(app, qtbot, monkeypatch, stack_paths):
    """
    A lazy stack of 3860258481's three scans, in slabs of 3 steps, gives one dataset whose maps and coordinates at
    each scan are those of the scan loaded alone.
    """
    monkeypatch.setattr(moments, "SLAB", 3 * 109 * 8)  # slabs of 3 steps on the crop of ±1 Å
    [stack] = raster_data(stack_paths, ["Si IV 1403"], stack=True)
    collection = app.data_collection
    collection.append(stack)
    keep_hpc_linked(collection)
    answer(monkeypatch, "1402.77")
    maps = run(app, qtbot, stack)
    assert maps.shape == stack.shape[:-1]
    assert link_hpc(collection) == []
    for k, path in enumerate(stack_paths):
        [scan] = raster_data([path], ["Si IV 1403"])
        alone = red_blue_asymmetry(scan, 1402.77)
        assert maps.meta == alone.meta
        for cid in alone.main_components:
            np.testing.assert_array_equal(maps[cid.label][k], alone[cid])
        for cid in alone.world_component_ids:
            np.testing.assert_allclose(maps[cid.label][k], alone[cid], rtol=0, atol=1e-9)


def test_refusals_and_errors_show_why(app, qtbot, monkeypatch, scan_path, irispy_test_files):
    [raster] = raster_data([scan_path], ["Si IV 1403"])
    sji = image_data(find_irispy_test_file(irispy_test_files, SJI))
    plain = Data(label="plain", x=np.zeros((3, 4, 5)))
    collection = app.data_collection
    collection.extend([raster, sji, plain])
    shown = []
    monkeypatch.setenv("GLUE_TESTING", "False")  # glue raises the error instead while testing
    monkeypatch.setattr(QtWidgets.QMessageBox, "exec_", lambda box: shown.append(box.text()))
    tree = app._layer_widget
    action = tree._actions[ACTION]
    opened = answer(monkeypatch, "1402.77")
    for data in (sji, plain):
        tree.ui.layerTree.set_selected_layers([data])
        refused(action)
    assert opened == []  # refused before asking
    tree.ui.layerTree.set_selected_layers([raster])
    for rest in ("3000", "Si IV"):
        answer(monkeypatch, rest)
        action.trigger()
    assert all(text.startswith("Could not compute line maps\n") for text in shown)
    assert [text.split("\n", 1)[1] for text in shown] == [
        f"{sji.label} is not an IRIS raster window.",
        "plain is not an IRIS raster window.",
        f"No wavelength of {raster.label} (1398.63 to 1405.75 Å) lies within 1.0 Å below and 1.0 Å above 3000.0 Å.",
        "'Si IV' is not a wavelength in Angstrom, such as 1402.77.",
    ]
    assert app.statusBar().currentMessage() == ""
    assert len(collection) == 3
    tree.ui.layerTree.set_selected_layers([raster, sji])  # one dataset at a time
    assert not action.isVisible()


def test_a_saturated_sample_taken_flags_its_pixel(monkeypatch, scan_path):
    """
    irispy flags a pixel saturated where a sample of the wavelengths taken is saturated, +Inf, in DN or DN / s alike.
    """
    monkeypatch.setattr(iris, "LAZY", False)
    [raster] = raster_data([scan_path], ["Si IV 1403"])
    cid, (wavelengths, _) = raster.main_components[0], _wavelengths(raster)
    taken = np.flatnonzero(abs(wavelengths - 1402.77) <= 1)
    values = np.array(raster[cid])
    values[0, 10, taken[4]] = np.inf
    values[:, 20, wavelengths > 1404] = np.inf  # not taken
    raster.update_components({cid: values})
    for rate in (True, False):
        if not rate:  # irispy is given the DN themselves
            raster.remove_component(raster.id[f"{raster.label} DN / s"])
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
