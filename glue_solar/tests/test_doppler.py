"""
'IRIS: Doppler image…', on int16 copies of irispy's test files, Gaussian lines and one irispy-data cutout: the maps
glue gets, of a scan or a stack, against numpy's interpolation of each pixel's spectrum.
"""

from unittest.mock import Mock

import numpy as np
import pytest
from glue.core import Data
from glue_qt.app.application import GlueApplication
from qtpy import QtWidgets

import astropy.units as u
from astropy import constants
from astropy.io import fits

import glue_solar
from glue_solar.conftest import find_irispy_test_file
from glue_solar.quicklook import _wavelengths
from glue_solar.sources import doppler
from glue_solar.sources.doppler import doppler_image
from glue_solar.sources.loaders import iris
from glue_solar.sources.loaders.iris import image_data, keep_hpc_linked, link_hpc, raster_data
from glue_solar.tests.helpers import refused
from glue_solar.tests.test_lazy import SJI, int16_copy, int16_raster_copy
from glue_solar.tests.test_quicklook import SCAN

ACTION = "IRIS: Doppler image…"
VELOCITIES = (10, 20, 30, 40, 50)


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


def answer(monkeypatch, rest, velocities=None, normalised=False, accept=True):
    """
    Make each Doppler image dialog return as if ``rest`` and any ``velocities`` were typed, "(red - blue) / (red +
    blue) too" ticked with ``normalised``, and OK, or Cancel, pressed; returns what each dialog opened with.
    """
    opened = []

    def exec_(dialog):
        fields = [dialog.findChild(QtWidgets.QLineEdit, name) for name in ("rest", "velocities")]
        tick = dialog.findChild(QtWidgets.QCheckBox, "normalised")
        opened.append((*(field.text() for field in fields), tick.isChecked()))
        fields[0].setText(rest)
        if velocities is not None:
            fields[1].setText(velocities)
        tick.setChecked(normalised)
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
    assert app.statusBar().currentMessage() == f"Computing the Doppler image of {data.label}…"
    qtbot.waitUntil(lambda: len(collection) == count + 1 and not iris._RUNNING)
    assert app.statusBar().currentMessage() == ""
    return collection[-1]


def numpys(raster, rest, velocities):
    """
    The red and the blue wing of ``raster``'s DN/s at each of ``velocities`` from ``rest``, by numpy's `~numpy.interp`
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


def assert_numpys(maps, raster, rest, velocities=VELOCITIES, normalised=False):
    """``maps`` are numpy's red less blue wing of ``raster``'s DN/s, and with ``normalised``, over their sum."""
    red, blue = numpys(raster, rest, velocities)
    names = [f"red - blue {v:g} km/s" for v in velocities]
    if normalised:
        names += [f"(red - blue) / (red + blue) {v:g} km/s" for v in velocities]
    assert [cid.label for cid in maps.main_components] == names
    for k, v in enumerate(velocities):
        np.testing.assert_allclose(maps[names[k]], red[k] - blue[k], rtol=1e-12, atol=1e-12)
        if normalised:
            with np.errstate(invalid="ignore"):
                expected = np.where((red[k] > 0) & (blue[k] > 0), (red[k] - blue[k]) / (red[k] + blue[k]), np.nan)
            np.testing.assert_allclose(maps[names[len(velocities) + k]], expected, rtol=1e-12, atol=1e-12)


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
    assert opened == [("1402.77", "10, 20, 30, 40, 50", False)]  # the window's main line
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
    assert not any(app.viewers)
    # on the raster's steps and slit pixels, its helioprojective coordinates linked with the others'
    assert maps.coords.world_axis_units == ("arcsec", "arcsec")
    for cid, raster_cid in zip(maps.world_component_ids, raster.world_component_ids):
        np.testing.assert_allclose(maps[cid], raster[raster_cid, (..., 0)], rtol=0, atol=1e-9)
    assert link_hpc(collection) == []
    linked = {cid for link in collection.links for cid in (link.get_to_id(), *link.get_from_ids())}
    assert set(maps.world_component_ids) <= linked
    assert_numpys(maps, raster, 1402.77)
    assert np.isnan(maps["red - blue 10 km/s"]).sum() == 32  # where either sample interpolated is missing


def test_the_typed_velocities_normalised_and_a_blank_or_cancelled_rest(app, qtbot, monkeypatch, scan_path):
    [raster] = raster_data([scan_path], ["Si IV 1403"])
    collection = app.data_collection
    collection.append(raster)
    answer(monkeypatch, " 1402.77 ", " 25,5 5", normalised=True)
    maps = run(app, qtbot, raster)
    assert maps.meta["doppler_velocities"] == (5, 25)
    assert_numpys(maps, raster, 1402.77, (5, 25), normalised=True)
    # nothing more is added
    tree = app._layer_widget
    tree.ui.layerTree.set_selected_layers([raster])  # glue selects the dataset added
    action = tree._actions[ACTION]
    for rest, accept in (("", True), ("1402.77", False)):
        answer(monkeypatch, rest, accept=accept)
        action.trigger()
        assert not iris._RUNNING  # and no thread started
        assert len(collection) == 2


def test_a_symmetric_line_gives_zero_a_redshift_a_positive_map_and_a_saturated_sample_nan(monkeypatch, scan_path):
    """
    A Gaussian line on a constant, centred at the rest wavelength, on a sample, gives 0 at every velocity to float
    precision, and shifted by +5 km/s, a positive map; a saturated sample, +Inf, interpolated in either wing makes it
    NaN.
    """
    monkeypatch.setattr(iris, "LAZY", False)
    [raster] = raster_data([scan_path], ["Si IV 1403"])
    cid, (wavelengths, _) = raster.main_components[0], _wavelengths(raster)
    k = np.argmin(abs(wavelengths - 1402.77))
    rest = wavelengths[k]  # on a sample: a symmetric line's samples are symmetric about it
    for shift in (0, 5):
        centre = rest * (1 + shift / constants.c.to_value(u.km / u.s))
        line = 1000 * np.exp(-0.5 * ((wavelengths - centre) / 0.3) ** 2) + 50
        raster.update_components({cid: np.broadcast_to(line, raster.shape).astype(np.float32)})
        maps = doppler_image(raster, rest, normalised=True)
        for name in maps.main_components:
            if shift:
                assert (maps[name] > 0).all()
            else:
                np.testing.assert_allclose(maps[name], 0, rtol=0, atol=1e-9)
    # every wing up to 50 km/s, 0.23 Å, lies between sample k and one beside it
    values = np.array(raster[cid])
    values[0, 0, k], values[0, 1, k + 1], values[0, 2, 0] = np.inf, np.inf, np.inf  # both wings, the red, neither
    raster.update_components({cid: values})
    maps = doppler_image(raster, rest)
    for name in maps.main_components:
        assert np.flatnonzero(np.isnan(maps[name])).tolist() == [0, 1]  # step 0, slit pixels 0 and 1


def test_a_stack_gives_each_scans_maps_at_its_coordinates(app, qtbot, monkeypatch, tmp_path, irispy_test_files):
    """
    A lazy stack of 3860258481's three scans, the second's Si IV 1403 a third of a sample redder, gives one dataset
    whose maps at each scan are the scan's alone.
    """
    paths = [
        int16_raster_copy(path, tmp_path / path.name)
        for path in sorted(p for p in irispy_test_files if "3860258481_raster" in p.name)
    ]
    with fits.open(paths[1], mode="update") as hdulist:
        hdulist[5].header["CRVAL1"] += hdulist[5].header["CDELT1"] / 3
    [stack] = raster_data(paths, ["Si IV 1403"], stack=True)
    collection = app.data_collection
    collection.append(stack)
    keep_hpc_linked(collection)
    answer(monkeypatch, "1402.77")
    maps = run(app, qtbot, stack)
    assert maps.shape == stack.shape[:-1]
    assert link_hpc(collection) == []
    for k, path in enumerate(paths):
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
    for rest, velocities in (
        ("3000", None),
        ("Si IV", None),
        ("1402.77", "0, 10"),
        ("1402.77", "nan"),
        ("1402.77", "10 fast"),
        ("1402.77", ""),
    ):
        answer(monkeypatch, rest, velocities)
        action.trigger()
    answer(monkeypatch, "1399", "50, 200, 300")
    action.trigger()
    # and an error on the thread
    monkeypatch.setattr(doppler, "_read", Mock(side_effect=RuntimeError("unreadable")))
    answer(monkeypatch, "1402.77")
    action.trigger()
    qtbot.waitUntil(lambda: len(shown) == 10 and not iris._RUNNING)
    assert all(text.startswith("Could not compute the Doppler image\n") for text in shown)
    span = f"{raster.label} (1398.63 to 1405.75 Å)"
    assert [text.split("\n", 1)[1] for text in shown] == [
        f"{sji.label} is not an IRIS raster window.",
        "plain is not an IRIS raster window.",
        f"The wings at ±10, 20, 30, 40, 50 km/s from 3000.0 Å lie outside {span}.",
        "'Si IV' is not a wavelength in Angstrom, such as 1402.77.",
        "The velocities must be positive, not 0, 10 km/s.",
        "The velocities must be positive, not nan km/s.",
        "'10 fast' is not a list of velocities in km/s, such as 10, 20, 30.",
        "'' is not a list of velocities in km/s, such as 10, 20, 30.",
        f"The wings at ±200, 300 km/s from 1399.0 Å lie outside {span}.",
        "unreadable",
    ]
    assert app.statusBar().currentMessage() == ""
    assert len(collection) == 3


@pytest.mark.remote_data
def test_a_full_mg_ii_k_window_gives_numpys_maps(irispy_data):
    """3400109360's Mg II k, at full resolution, read lazily and its steps negative, gives numpy's maps."""
    [path] = irispy_data("iris_l2_20250328_225628_3400109360_cutout_raster.tar.gz")
    [raster] = raster_data([path], ["Mg II k 2796"])
    maps = doppler_image(raster, 2796.352, normalised=True)
    assert maps.get_component("red - blue 10 km/s").units == "DN_IRIS_NUV / s"
    assert_numpys(maps, raster, 2796.352, normalised=True)
