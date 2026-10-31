"""
'IRIS: line maps…' and its Doppler image, on int16 copies of irispy's test files, Gaussian lines and one irispy-data
cutout: the maps glue gets, of a scan or a stack, against numpy's interpolation of each pixel's spectrum.
"""

from unittest.mock import Mock

import numpy as np
import pytest
from glue.core import Data
from qtpy import QtWidgets

import astropy.units as u
from astropy import constants
from astropy.io import fits

from glue_solar.conftest import find_irispy_test_file, int16_copy
from glue_solar.quicklook import _wavelengths, quicklook
from glue_solar.sources import doppler
from glue_solar.sources.doppler import doppler_image
from glue_solar.sources.loaders import iris
from glue_solar.sources.loaders.iris import image_data, keep_hpc_linked, link_hpc, raster_data
from glue_solar.tests import test_moments
from glue_solar.tests.helpers import mouse_click, refused, run_action
from glue_solar.tests.test_lazy import SJI
from glue_solar.tests.test_moments import ACTION
from glue_solar.tests.test_quicklook import crosshair

VELOCITIES = (10, 20, 30, 40, 50)


def answer(monkeypatch, rest, accept=True):
    """`test_moments.answer` with the Doppler image alone ticked."""
    return test_moments.answer(monkeypatch, rest, accept=accept, moments=False, doppler=True)


def run(app, qtbot, data):
    """Trigger the action on ``data``; returns the dataset it adds."""
    [maps] = run_action(app, qtbot, data, ACTION, f"Computing line maps of {data.label}…")
    return maps


def numpys(raster, rest, velocities):
    """
    The red and the blue wing of ``raster``'s DN / s at each of ``velocities`` from ``rest``, by numpy's `~numpy.interp`
    of each pixel's spectrum, velocity first.
    """
    wavelengths, _ = _wavelengths(raster)
    rate = iris.per_second(np.asarray(raster[raster.main_components[0]], dtype=float), raster["Exposure time"])
    spectra = rate.reshape(-1, rate.shape[-1])
    shift = np.asarray(velocities) / constants.c.to_value(u.km / u.s)
    return [
        np.array([np.interp(rest * (1 + sign * shift), wavelengths, spectrum) for spectrum in spectra]).T.reshape(
            len(velocities), *rate.shape[:-1]
        )
        for sign in (1, -1)
    ]


def assert_numpys(maps, raster, rest, velocities=VELOCITIES, normalized=False):
    """``maps`` are numpy's red less blue wing of ``raster``'s DN / s, and with ``normalized``, over their sum."""
    red, blue = numpys(raster, rest, velocities)
    names = [f"red - blue {v:g} km / s" for v in velocities]
    if normalized:
        names += [f"(red - blue) / (red + blue) {v:g} km / s" for v in velocities]
    assert [cid.label for cid in maps.main_components] == names
    for k, v in enumerate(velocities):
        np.testing.assert_allclose(maps[names[k]], red[k] - blue[k], rtol=1e-12, atol=1e-12)
        if normalized:
            with np.errstate(invalid="ignore"):
                expected = np.where((red[k] > 0) & (blue[k] > 0), (red[k] - blue[k]) / (red[k] + blue[k]), np.nan)
            np.testing.assert_allclose(maps[names[len(velocities) + k]], expected, rtol=1e-12, atol=1e-12)


def test_the_action_adds_one_linked_dataset_in_a_viewer_with_the_quicklooks_point(
    app, qtbot, monkeypatch, tmp_path, scan_path, irispy_test_files
):
    [raster] = raster_data([scan_path], ["Si IV 1403"])
    sji = image_data(int16_copy(find_irispy_test_file(irispy_test_files, SJI), tmp_path / SJI, [0]))
    collection = app.data_collection
    viewers = quicklook(app, [sji, raster])
    [point] = collection.subset_groups
    opened = answer(monkeypatch, "1402.77")
    maps = run(app, qtbot, raster)
    assert opened[0]["rest"] == "1402.77"  # the main line
    assert maps.label == f"{raster.label} Doppler image 1402.77"
    assert maps.shape == raster.shape[:2]
    assert {maps.get_component(cid).units for cid in maps.main_components} == {"DN_IRIS_FUV / s"}
    assert maps.meta == {
        "OBSID": raster.meta["OBSID"],
        "STARTOBS": raster.meta["STARTOBS"],
        "doppler_rest": 1402.77,
        "doppler_velocities": (10, 20, 30, 40, 50),
        "doppler_sign": "red - blue",
    }
    # glue's Image viewer of its first map in the quicklook's tab, the point's crosshair at its step and slit (D83)
    [viewer] = [viewer for viewer in app.viewers[-1] if viewer.state.reference_data is maps]
    assert viewer.state.layers[0].attribute is maps.main_components[0]
    assert crosshair(viewer) == (raster.shape[0] // 2, raster.shape[1] // 2)
    # a plain click on it leaves the point the edit subset, so a click on the map moves it (#244)
    app.show()
    qtbot.waitUntil(app.isActiveWindow)
    mouse_click(viewer, 4, 50)
    assert app.session.edit_subset_mode.edit_subset == [point]
    mouse_click(viewers["map"], 2, 3)
    assert collection.subset_groups == (point,)
    assert [index.start for index in point.subset_state.slices[:2]] == [2, 3]
    # on the raster's steps and slit pixels, its helioprojective coordinates linked with the others'
    assert maps.coords.world_axis_units == ("arcsec", "arcsec")
    for cid, raster_cid in zip(maps.world_component_ids, raster.world_component_ids):
        np.testing.assert_allclose(maps[cid], raster[raster_cid, (..., 0)], rtol=0, atol=1e-9)
    assert link_hpc(collection) == []
    linked = {cid for link in collection.links for cid in (link.get_to_id(), *link.get_from_ids())}
    assert set(maps.world_component_ids) <= linked
    pairs = {frozenset((link.get_to_id(), *link.get_from_ids())) for link in collection.links}
    assert all(frozenset(pair) in pairs for pair in zip(raster.pixel_component_ids, maps.pixel_component_ids))  # D83
    assert_numpys(maps, raster, 1402.77)
    assert np.isnan(maps["red - blue 10 km / s"]).sum() == 32  # where either sample interpolated is missing


def test_other_velocities_normalized_and_a_blank_or_canceled_rest(app, qtbot, monkeypatch, scan_path):
    """Other velocities and the normalized maps are the function's; a blank rest wavelength or Cancel adds nothing."""
    [raster] = raster_data([scan_path], ["Si IV 1403"])
    collection = app.data_collection
    collection.append(raster)
    maps = doppler_image(raster, 1402.77, (5, 25), normalized=True)
    assert maps.meta["doppler_velocities"] == (5, 25)
    assert_numpys(maps, raster, 1402.77, (5, 25), normalized=True)
    tree = app._layer_widget
    tree.ui.layerTree.set_selected_layers([raster])
    action = tree._actions[ACTION]
    for rest, accept in (("", True), ("1402.77", False)):
        answer(monkeypatch, rest, accept)
        action.trigger()
        assert not iris._RUNNING  # and no thread started
        assert len(collection) == 1


def test_a_symmetric_line_gives_zero_a_redshift_a_positive_map_and_a_saturated_sample_nan(monkeypatch, scan_path):
    """
    A Gaussian line on a constant, centered at the rest wavelength, on a sample, gives 0 at every velocity to float
    precision, and shifted by +5 km / s, a positive map; a saturated sample, 16182 DN, interpolated in either wing
    makes it NaN.
    """
    monkeypatch.setattr(iris, "LAZY", False)
    [raster] = raster_data([scan_path], ["Si IV 1403"])
    cid, (wavelengths, _) = raster.main_components[0], _wavelengths(raster)
    k = np.argmin(abs(wavelengths - 1402.77))
    rest = wavelengths[k]  # on a sample: a symmetric line's samples are symmetric about it
    for shift in (0, 5):
        center = rest * (1 + shift / constants.c.to_value(u.km / u.s))
        line = 1000 * np.exp(-0.5 * ((wavelengths - center) / 0.3) ** 2) + 50
        raster.update_components({cid: np.broadcast_to(line, raster.shape).astype(np.float32)})
        maps = doppler_image(raster, rest, normalized=True)
        for name in maps.main_components:
            if shift:
                assert (maps[name] > 0).all()
            else:
                np.testing.assert_allclose(maps[name], 0, rtol=0, atol=1e-9)
    # every wing up to 50 km / s, 0.23 Å, lies between sample k and one beside it
    values = np.array(raster[cid])
    values[0, 0, k], values[0, 1, k + 1], values[0, 2, 0] = 16182, 16182, 16182  # both wings, the red, neither
    raster.update_components({cid: values})
    maps = doppler_image(raster, rest)
    for name in maps.main_components:
        assert np.flatnonzero(np.isnan(maps[name])).tolist() == [0, 1]  # step 0, slit pixels 0 and 1


def test_a_stack_gives_each_scans_maps_at_its_coordinates(app, qtbot, monkeypatch, stack_paths):
    """
    A lazy stack of 3860258481's three scans, the second's Si IV 1403 a third of a sample redder, gives one dataset
    whose maps at each scan are the scan's alone.
    """
    with fits.open(stack_paths[1], mode="update") as hdulist:
        hdulist[5].header["CRVAL1"] += hdulist[5].header["CDELT1"] / 3
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
        alone = doppler_image(scan, 1402.77)
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
    for rest in ("3000", "Si IV", "1398.7"):
        answer(monkeypatch, rest)
        action.trigger()
    # and an error on the thread
    monkeypatch.setattr(doppler, "_read", Mock(side_effect=RuntimeError("unreadable")))
    answer(monkeypatch, "1402.77")
    action.trigger()
    qtbot.waitUntil(lambda: len(shown) == 6 and not iris._RUNNING)
    assert all(text.startswith("Could not compute line maps\n") for text in shown)
    span = f"{raster.label} (1398.63 to 1405.75 Å)"
    assert [text.split("\n", 1)[1] for text in shown] == [
        f"{sji.label} is not an IRIS raster window.",
        "plain is not an IRIS raster window.",
        f"The wings at ±10, 20, 30, 40, 50 km / s from 3000.0 Å lie outside {span}.",
        "'Si IV' is not a wavelength in Angstrom, such as 1402.77.",
        f"The wings at ±20, 30, 40, 50 km / s from 1398.7 Å lie outside {span}.",
        "unreadable",
    ]
    assert app.statusBar().currentMessage() == ""
    assert len(collection) == 3
    for velocities, said in (((0, 10), "0, 10"), ((np.nan,), "nan")):  # the function's
        with pytest.raises(ValueError, match=f"^The velocities must be positive, not {said} km / s.$"):
            doppler_image(raster, 1402.77, velocities)
