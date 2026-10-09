"""
'IRIS: line moments…', on int16 copies of irispy's test files, Gaussian lines and one irispy-data cutout: what glue
gets of irispy's maps; 'IRIS: subtract mean spectrum', as a Profile shows it; the maps exported with their
coordinates; and the rest wavelength the line dialogs start at.
"""

import warnings
from unittest.mock import Mock

import irispy.utils.moments
import numpy as np
import pytest
from glue.core import Data
from glue_qt.app.application import GlueApplication
from glue_qt.core.data_exporters import dialog
from glue_qt.viewers.image import ImageViewer
from glue_qt.viewers.profile import ProfileViewer
from irispy.io import read_files
from irispy.spectrograph import SpectrogramCube
from irispy.utils.constants import DN_UNIT
from irispy.utils.spectrograph import subtract_background
from qtpy import QtWidgets

import astropy.units as u
from astropy import constants
from astropy.io import fits
from astropy.wcs import WCS
from astropy.wcs.wcsapi import HighLevelWCSWrapper
from astropy.wcs.wcsapi.wrappers import SlicedLowLevelWCS

import glue_solar
from glue_solar.conftest import find_irispy_test_file
from glue_solar.lines import rest_wavelength
from glue_solar.quicklook import _wavelengths
from glue_solar.sources import moments
from glue_solar.sources.loaders import iris
from glue_solar.sources.loaders.iris import _HPC, _GlueWCS, image_data, keep_hpc_linked, link_hpc, raster_data
from glue_solar.sources.moments import line_moments
from glue_solar.tests.helpers import select_point
from glue_solar.tests.test_lazy import RASTER, SJI, int16_copy, int16_raster_copy, zero_exposure
from glue_solar.tests.test_quicklook import SCAN

ACTION = "IRIS: line moments…"
MEAN = "IRIS: subtract mean spectrum"
EXPORT = "IRIS FITS (coordinates and Time)"


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


def answer(monkeypatch, centre, wings=(), continuum="", accept=True, errors=False):
    """
    Make each line dialog return as if ``centre``, any ``wings`` and ``continuum`` were typed, "Error maps" ticked with
    ``errors``, and OK, or Cancel, pressed; returns the centre, wings, continuum and tick each dialog opened with.
    """
    opened = []

    def exec_(dialog):
        boxes = [dialog.findChild(QtWidgets.QDoubleSpinBox, side) for side in ("below", "above")]
        windows, field = (dialog.findChild(QtWidgets.QLineEdit, name) for name in ("continuum", "centre"))
        tick = dialog.findChild(QtWidgets.QCheckBox, "errors")
        opened.append((field.text(), *(box.value() for box in boxes), windows.text(), tick.isChecked()))
        field.setText(centre)
        windows.setText(continuum)
        tick.setChecked(errors)
        for box, wing in zip(boxes, wings):
            box.setValue(wing)
        return QtWidgets.QDialog.Accepted if accept else QtWidgets.QDialog.Rejected

    monkeypatch.setattr(QtWidgets.QDialog, "exec", exec_)
    return opened


def missing(raster, low, high):
    """Where every sample of ``raster`` from ``low`` to ``high`` Angstrom is missing."""
    wavelengths, _ = _wavelengths(raster)
    return np.isnan(raster[raster.main_components[0]][..., (wavelengths >= low) & (wavelengths <= high)]).all(-1)


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
    assert app.statusBar().currentMessage() == f"Computing line moments of {data.label}…"
    qtbot.waitUntil(lambda: len(collection) == count + 1 and not iris._RUNNING)
    assert app.statusBar().currentMessage() == message
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
    assert opened == [("1402.77", 0.5, 0.5, "", False)]  # Si IV 1402.77, the window's main line
    assert maps.label == f"{raster.label} moments 1402.77"
    assert maps.shape == raster.shape[:2]
    assert [(cid.label, maps.get_component(cid).units) for cid in maps.main_components] == [
        ("intensity", "DN_IRIS_FUV / s"),  # of the window's DN/s
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
    for centre, continuum in (
        ("3000", ""),
        ("Si IV", ""),
        ("1402.77", "1401.5"),
        ("1402.77", "1401.5-1402,"),
        ("1402.77", "1401.5-1402, 1402-1402.5"),
        ("1402.77", "1300-1301"),
    ):
        answer(monkeypatch, centre, continuum=continuum)
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
        "'1401.5' is not a list of continuum windows in Angstrom, such as 1401.5-1402, 1404-1405.",
        "'1401.5-1402,' is not a list of continuum windows in Angstrom, such as 1401.5-1402, 1404-1405.",
        "The continuum window 1402.0-1402.5 Å overlaps the wings, 0.5 Å below and 0.5 Å above 1402.77 Å.",
        f"No wavelength of {raster.label} (1398.63 to 1405.75 Å) lies within the continuum window 1300.0-1301.0 Å.",
    ]
    assert len(collection) == 4
    # and an error of irispy's, on the thread
    monkeypatch.setattr(irispy.utils.moments, "calculate_moments", Mock(side_effect=RuntimeError("irispy failed")))
    answer(monkeypatch, "1402.77")
    action.trigger()
    qtbot.waitUntil(lambda: len(shown) == 10 and not iris._RUNNING)
    assert shown[-1] == "Could not compute line moments\nirispy failed"
    assert app.statusBar().currentMessage() == ""
    assert len(collection) == 4
    tree.ui.layerTree.set_selected_layers([raster, sji])  # one dataset at a time
    assert not action.isVisible()


def test_a_continuum_window_is_irispys_background(app, qtbot, monkeypatch, scan_path):
    [raster] = raster_data([scan_path], ["Si IV 1403"])
    app.data_collection.append(raster)
    plain = line_moments(raster, 1402.77)
    cube = dn_per_second_cube(raster, DN_UNIT["FUV"])
    wavelengths, _ = _wavelengths(raster)
    wings = (wavelengths >= 1402.27) & (wavelengths <= 1403.27)
    # the second fits no background to 8 pixels missing from 1403.46 Å on but not within the wings
    for typed, windows, degree, nan in (
        ("1401.5-1402, 1403.5 - 1404", ((1401.5, 1402.0), (1403.5, 1404.0)), 1, 24),
        (" 1403.5-1404 ", ((1403.5, 1404.0),), 0, 32),
    ):
        answer(monkeypatch, "1402.77", continuum=typed)
        maps = run(app, qtbot, raster)
        assert maps.meta == {
            **plain.meta,
            "moments_continuum": windows,
            "moments_continuum_degree": degree,
        }
        background = subtract_background(cube, windows * u.AA, degree=degree)
        direct = irispy.utils.moments.calculate_moments(background, rest_wavelength=1402.77 * u.AA, wings=0.5 * u.AA)
        # NaN too where every sample within the wings is missing, or no background is fitted
        fill = np.isnan(background.data[..., wings]).all(-1)
        assert fill.sum() == nan
        # a straight line fitted to a constant spectrum leaves 2e-13, not 0, on the slab or the whole window alike:
        # what irispy's roundoff gives such a non-line, a centroid or not, is not compared
        line = (direct["intensity"].data > 1e-9) | fill
        for name, moment in direct.items():
            expected = np.where(fill | moment.mask, np.nan, moment.data)
            if moment.unit.is_equivalent(u.AA):
                expected = moment.unit.to(u.AA, expected)
            compared = Ellipsis if name == "intensity" else line
            np.testing.assert_allclose(maps[name][compared], expected[compared], rtol=1e-9, atol=1e-9)
            assert not np.allclose(maps[name], plain[name], equal_nan=True)
    # a blank one changes nothing
    answer(monkeypatch, "1402.77", continuum=" ")
    maps = run(app, qtbot, raster)
    assert maps.meta == plain.meta
    for cid in plain.main_components:
        np.testing.assert_array_equal(maps[cid.label], plain[cid])


@pytest.mark.parametrize("continuum", ["", "1401.5-1402, 1403.5-1404"])
def test_ticked_error_maps_are_irispys_from_its_readers_uncertainty(app, qtbot, monkeypatch, scan_path, continuum):
    """
    "Error maps", unticked at first, adds each map's error, a slab of steps at a time: irispy's own, of the window read
    with its ``uncertainty=True``, in DN/s, less any background, but NaN where every sample within the wings is
    missing.
    """
    monkeypatch.setattr(moments, "SLAB", 3 * 109 * 4)  # slabs of 1 step: halved with errors
    [raster] = raster_data([scan_path], ["Si IV 1403"])
    app.data_collection.append(raster)
    opened = answer(monkeypatch, "1402.77", continuum=continuum, errors=True)
    maps = run(app, qtbot, raster)
    assert opened == [("1402.77", 0.5, 0.5, "", False)]
    cube = read_files([scan_path], spectral_windows=["Si IV 1403"], uncertainty=True)["Si IV 1403"][0]
    cube = cube.apply_exposure_time_correction()
    if continuum:
        cube = subtract_background(cube, [(1401.5, 1402.0), (1403.5, 1404.0)] * u.AA, degree=1)
    direct = irispy.utils.moments.calculate_moments(cube, rest_wavelength=1402.77 * u.AA, wings=0.5 * u.AA)
    fill = np.asarray(missing(raster, 1402.27, 1403.27))
    assert [cid.label for cid in maps.main_components] == [
        label for name in direct for label in (name, f"{name} error")
    ]
    # which samples a pixel with no line keeps, less a background, is roundoff (see above): not compared
    line = (direct["intensity"].data > 1e-9) | fill
    for name, moment in direct.items():
        assert maps.get_component(f"{name} error").units == maps.get_component(name).units
        expected = np.where(fill | moment.mask, np.nan, moment.uncertainty.array)
        if moment.unit.is_equivalent(u.AA):
            expected = moment.unit.to(u.AA, expected)
        assert np.isfinite(expected[line]).sum() > 600  # of 872
        np.testing.assert_allclose(maps[f"{name} error"][line], expected[line], rtol=1e-6, atol=1e-9, err_msg=name)


def test_nuv_error_maps_take_irispys_nuv_noise(tmp_path, irispy_test_files):
    """3620258102's Mg II k 2796, in DN_IRIS_NUV / s: irispy's NUV gain and read noise, not the FUV's."""
    path = int16_raster_copy(find_irispy_test_file(irispy_test_files, RASTER), tmp_path / RASTER)
    [raster] = raster_data([path], ["Mg II k 2796"])
    maps = line_moments(raster, 2796.35, errors=True)
    assert maps.get_component("intensity error").units == "DN_IRIS_NUV / s"
    cube = read_files([path], spectral_windows=["Mg II k 2796"], uncertainty=True)["Mg II k 2796"][0]
    cube = cube.apply_exposure_time_correction()
    direct = irispy.utils.moments.calculate_moments(cube, rest_wavelength=2796.35 * u.AA, wings=0.5 * u.AA)
    fill = np.asarray(missing(raster, 2795.85, 2796.85))
    for name, moment in direct.items():
        expected = np.where(fill | moment.mask, np.nan, moment.uncertainty.array)
        if moment.unit.is_equivalent(u.AA):
            expected = moment.unit.to(u.AA, expected)
        assert np.isfinite(expected).any()
        np.testing.assert_allclose(maps[f"{name} error"], expected, rtol=1e-6, err_msg=name)


@pytest.mark.parametrize("continuum", [None, [(1401.5, 1402.0), (1403.5, 1404.0)]])
def test_lazy_data_give_the_moments_of_data_in_memory(monkeypatch, scan_path, continuum):
    [raster] = raster_data([scan_path], ["Si IV 1403"])
    lazy = line_moments(raster, 1402.77, continuum=continuum)
    monkeypatch.setattr(moments, "SLAB", 3 * 109 * 4)  # steps 0-2, 3-5 and 6-7, or one at a time on the crop of both
    monkeypatch.setattr(iris, "LAZY", False)
    [eager] = raster_data([scan_path], ["Si IV 1403"])
    assert type(eager) is Data
    slabs = line_moments(eager, 1402.77, continuum=continuum)
    for cid in lazy.main_components:
        np.testing.assert_array_equal(slabs[cid.label], lazy[cid])


def test_the_dn_per_second_of_a_window_that_has_it(scan_path):
    """The maps of the window's DN/s are those of its DN over each step's exposure time, NaN at a step of 0 s."""
    [raster] = raster_data([zero_exposure(scan_path, 3)], ["Si IV 1403"])
    maps = line_moments(raster, 1402.77)
    seconds = raster["Exposure time"][:, :1, 0]
    raster.remove_component(raster.id[f"{raster.label} DN/s"])
    dn = line_moments(raster, 1402.77)
    assert maps.get_component("intensity").units == "DN_IRIS_FUV / s"
    assert dn.get_component("intensity").units == "DN_IRIS_FUV"
    assert seconds[3] == 0
    assert (np.delete(seconds, 3, 0) > 0).all()
    assert not np.isnan(dn["intensity"][3]).all()
    for cid in maps.main_components:
        assert np.isnan(maps[cid][3]).all()
        expected = dn[cid.label] / (seconds if cid.label == "intensity" else 1)
        np.testing.assert_allclose(np.delete(maps[cid], 3, 0), np.delete(expected, 3, 0), rtol=1e-6, atol=1e-5)


def test_minus_infinity_is_missing(monkeypatch, scan_path):
    """A sample at -Inf, which only data stored as floating point can hold, is missing, as NaN is."""
    monkeypatch.setattr(iris, "LAZY", False)
    [raster] = raster_data([scan_path], ["Si IV 1403"])
    cid, (wavelengths, _) = raster.main_components[0], _wavelengths(raster)
    inside = np.flatnonzero((wavelengths >= 1402.27) & (wavelengths <= 1403.27))
    assert np.isfinite(line_moments(raster, 1402.77)["intensity"][2:4, 10]).all()
    values = np.array(raster[cid])
    values[2, 10, inside[1]] = -np.inf
    values[3, 10, inside] = -np.inf
    raster.update_components({cid: values})
    maps = line_moments(raster, 1402.77)
    values[np.isneginf(values)] = np.nan
    raster.update_components({cid: values})
    missing = line_moments(raster, 1402.77)
    for cid in maps.main_components:
        assert np.isnan(maps[cid][3, 10])
        assert np.isfinite(maps[cid][2, 10])
        np.testing.assert_array_equal(maps[cid], missing[cid.label])


@pytest.mark.parametrize("continuum", ["", "1401.5-1402, 1403.5-1404"])
def test_saturated_pixels_within_the_wings_are_nan_and_counted(app, qtbot, monkeypatch, scan_path, continuum):
    """
    A pixel with a sample at 16182 DN within the wings, irispy's limit, is NaN in every map, and the status bar says
    how many; one outside the wings, here in a continuum window, is not.
    """
    monkeypatch.setattr(iris, "LAZY", False)
    monkeypatch.setattr(moments, "SLAB", 3 * 109 * 4)  # slabs of 3 steps, or of 1 with a continuum
    [raster] = raster_data([scan_path], ["Si IV 1403"])
    app.data_collection.append(raster)
    cid, (wavelengths, _) = raster.main_components[0], _wavelengths(raster)
    inside = np.flatnonzero((wavelengths >= 1402.27) & (wavelengths <= 1403.27))
    outside = np.flatnonzero((wavelengths >= 1403.5) & (wavelengths <= 1404))
    assert not missing(raster, 1402.27, 1403.27)[:, [10, 20]].any()
    values = np.array(raster[cid])
    # at every step: in float32 DN/s, 16182 DN over 6 of their 8 exposure times rounds below irispy's limit
    values[:, 10, inside[1]] = 16182
    values[:, 20, outside] = 16182
    raster.update_components({cid: values})
    answer(monkeypatch, "1402.77", continuum=continuum)
    maps = run(app, qtbot, raster, f"{raster.label} moments 1402.77: 8 pixels saturated within the wings are NaN")
    assert maps.meta["moments_saturated"] == 8
    for cid in maps.main_components:
        assert np.isnan(maps[cid][:, 10]).all()
    assert np.isfinite(maps["intensity"][:, 20]).all()


def test_a_dn_per_second_window_saturates_at_each_steps_exposure_time(monkeypatch, scan_path):
    """irispy is given each step's exposure time: the same DN/s is 16182 DN in an 8 s step, saturated, not in a 4 s one."""
    monkeypatch.setattr(iris, "LAZY", False)
    [raster] = raster_data([scan_path], ["Si IV 1403"])
    cid, (wavelengths, _) = raster.main_components[0], _wavelengths(raster)
    inside = np.flatnonzero((wavelengths >= 1402.27) & (wavelengths <= 1403.27))
    values, seconds = np.array(raster[cid]), np.array(raster["Exposure time"])
    seconds[:2] = [[[8]], [[4]]]
    values[:2, 10, inside[1]] = [16182, 16182 / 2]
    raster.update_components({cid: values, raster.id["Exposure time"]: seconds})
    maps = line_moments(raster, 1402.77)
    assert maps.get_component("intensity").units == "DN_IRIS_FUV / s"
    assert maps.meta["moments_saturated"] == 1
    assert np.isnan(maps["intensity"][0, 10])
    assert np.isfinite(maps["intensity"][1, 10])


def dn_per_second_cube(raster, unit):
    """The whole of ``raster``'s DN/s in ``unit`` / s for irispy, in float64 as it is given them, its mask their NaN."""
    window = iris.per_second(np.asarray(raster[raster.main_components[0]], dtype=float), raster["Exposure time"])
    return SpectrogramCube(window, raster.coords._wcs, unit=unit / u.s, mask=np.isnan(window))


def assert_irispys(maps, raster, centre, wings, unit):
    """
    ``maps`` are irispy's own on ``raster``'s DN/s in ``unit`` / s, but NaN where every sample within the wings is
    missing.
    """
    cube = dn_per_second_cube(raster, unit)
    direct = irispy.utils.moments.calculate_moments(cube, rest_wavelength=centre * u.AA, wings=wings * u.AA)
    fill = missing(raster, centre - wings, centre + wings)
    assert [cid.label for cid in maps.main_components] == list(direct)
    for name, moment in direct.items():
        expected = np.where(fill | moment.mask, np.nan, moment.data)
        if moment.unit.is_equivalent(u.AA):
            expected = moment.unit.to(u.AA, expected)
        np.testing.assert_allclose(maps[name], expected, rtol=1e-9, atol=1e-9)


def test_gaussian_lines_give_irispys_maps_their_width_a_standard_deviation(monkeypatch, scan_path):
    """
    Gaussian lines of known Doppler shift and FWHM, a step a slab, give irispy's maps, ``width`` their standard
    deviation: the FWHM over 2√(2 ln 2), about 2.355.
    """
    monkeypatch.setattr(iris, "LAZY", False)
    monkeypatch.setattr(moments, "SLAB", 1)
    [raster] = raster_data([scan_path], ["Si IV 1403"])
    wavelengths, _ = _wavelengths(raster)
    velocity = np.linspace(-20, 20, raster.shape[0])[:, None]  # km/s, by step
    fwhm = np.linspace(0.6, 0.9, raster.shape[1])  # Å, by slit pixel: sampled by the window's 0.25 Å, within ±2.5 Å
    centre = 1402.77 * (1 + velocity / constants.c.to_value(u.km / u.s))
    sigma = fwhm / (2 * np.sqrt(2 * np.log(2)))
    gaussians = 1000 * np.exp(-0.5 * ((wavelengths - centre[..., None]) / sigma[:, None]) ** 2)
    raster.update_components({raster.main_components[0]: gaussians.astype(np.float32)})
    maps = line_moments(raster, 1402.77, wings=(2.5, 2.5))
    assert_irispys(maps, raster, 1402.77, 2.5, DN_UNIT["FUV"])
    np.testing.assert_allclose(maps["width"], np.broadcast_to(sigma, maps.shape), rtol=1e-6)
    np.testing.assert_allclose(maps["velocity"], np.broadcast_to(velocity, maps.shape), atol=1e-4)


@pytest.mark.remote_data
def test_a_full_mg_ii_k_window_gives_irispys_maps(irispy_data):
    """3400109360's Mg II k, at full resolution, read lazily and its steps negative, gives irispy's maps."""
    [path] = irispy_data("iris_l2_20250328_225628_3400109360_cutout_raster.tar.gz")
    [raster] = raster_data([path], ["Mg II k 2796"])
    maps = line_moments(raster, 2796.352)
    assert maps.get_component("intensity").units == "DN_IRIS_NUV / s"
    assert missing(raster, 2795.852, 2796.852).sum() == 1600  # the slit's last 25 pixels, at every step
    assert_irispys(maps, raster, 2796.352, 0.5, DN_UNIT["NUV"])


@pytest.mark.parametrize("which", ["window", "stack", pytest.param("4000005156", marks=pytest.mark.remote_data)])
def test_a_pixel_profile_less_the_mean_spectrum_is_its_spectrum_less_numpys_nanmean(app, monkeypatch, request, which):
    """
    On a raster window or a stack of 3860258481's three scans, both lazy, or 4000005156's full Si IV 1403, three steps
    a slab: a Pixel subset's Profile of ``<label> minus mean spectrum`` is the pixel's spectrum less numpy's nanmean
    over every step, slit pixel and scan, within 1e-6.
    """
    if which == "window":
        [data] = raster_data([request.getfixturevalue("scan_path")], ["Si IV 1403"])
    elif which == "stack":
        files = sorted(p for p in request.getfixturevalue("irispy_test_files") if "3860258481_raster" in p.name)
        tmp_path = request.getfixturevalue("tmp_path")
        [data] = raster_data([int16_raster_copy(p, tmp_path / p.name) for p in files], ["Si IV 1403"], stack=True)
    else:
        name = "iris_l2_20130902_182935_4000005156_raster_t000_r00000_si_iv.fits.gz"
        [data] = raster_data([request.getfixturevalue("irispy_data")(name)])
    monkeypatch.setattr(moments, "SLAB", 3 * data.shape[-2] * data.shape[-1])
    cid = data.main_components[0]
    with warnings.catch_warnings():  # before any viewer, whose threads would reset the filters
        warnings.simplefilter("ignore", RuntimeWarning)  # wavelengths with no valid sample give NaN
        nanmean = np.nanmean(np.asarray(data[cid], dtype=float), axis=tuple(range(data.ndim - 1)))
    collection, tree = app.data_collection, app._layer_widget
    collection.append(data)
    tree.ui.layerTree.set_selected_layers([data])
    tree._actions[MEAN].trigger()
    mean, difference = data.id[f"{cid.label} mean spectrum"], data.id[f"{cid.label} minus mean spectrum"]
    assert [data.get_component(c).units for c in (cid, mean, difference)] == [data.get_component(cid).units] * 3
    assert not any(data.get_component(mean).data.strides[:-1])  # one spectrum held
    # a Pixel click on the map of the scan shown, and the Profile of its subset
    image = app.new_data_viewer(ImageViewer, data=data)
    image.state.x_att, image.state.y_att = data.pixel_component_ids[-3], data.pixel_component_ids[-2]
    index = (data.shape[0] - 1,) * (data.ndim - 3) + (data.shape[-3] // 2, data.shape[-2] // 2)
    image.state.slices = (*index[:-2], *image.state.slices[data.ndim - 3 :])
    select_point(image, *index[-2:])
    point = collection.subset_groups[-1]
    assert [s.start for s in point.subset_state.slices[:-1]] == list(index)
    profile = app.new_data_viewer(ProfileViewer, data=data)
    profile.state.x_att, profile.state.function = data.world_component_ids[-1], "mean"
    [layer] = [layer for layer in profile.state.layers if layer.layer is point.subsets[0]]
    layer.attribute = difference
    _, values = layer.profile
    spectrum = np.asarray(data[cid][index], dtype=float)
    assert np.isnan(spectrum).any()  # missing samples stay missing
    np.testing.assert_allclose(values, spectrum - nanmean, rtol=0, atol=1e-6)


def test_subtracting_the_mean_spectrum_refuses_other_data_and_a_second_run(
    app, monkeypatch, scan_path, irispy_test_files
):
    [raster] = raster_data([scan_path], ["Si IV 1403"])
    sji = image_data(find_irispy_test_file(irispy_test_files, SJI))
    plain = Data(label="plain", x=np.zeros((3, 4, 5)))
    app.data_collection.extend([raster, sji, plain])
    shown = []
    monkeypatch.setenv("GLUE_TESTING", "False")  # glue raises the error instead while testing
    monkeypatch.setattr(QtWidgets.QMessageBox, "exec_", lambda box: shown.append(box.text()))
    tree = app._layer_widget
    for data in (sji, plain, raster, raster):
        tree.ui.layerTree.set_selected_layers([data])
        tree._actions[MEAN].trigger()
    assert shown == [
        f"Could not subtract the mean spectrum\n{sji.label} is not an IRIS raster window.",
        "Could not subtract the mean spectrum\nplain is not an IRIS raster window.",
        f"Could not subtract the mean spectrum\n{raster.label} has its mean spectrum subtracted already.",
    ]
    label = raster.main_components[0].label
    assert [cid.label for cid in raster.components if "mean" in cid.label] == [
        f"{label} mean spectrum",
        f"{label} minus mean spectrum",
    ]


def export(monkeypatch, path, data):
    """Export ``data`` to ``path`` as glue-qt's export dialog does, with the IRIS FITS exporter picked."""
    monkeypatch.setattr(dialog.compat, "getsavefilename", lambda **_: (str(path), f"{EXPORT} (*.fits *.fit)"))
    dialog.export_data(data)


def test_moment_and_sliced_maps_export_with_their_coordinates_and_time(qtbot, monkeypatch, tmp_path, scan_path):
    [raster] = raster_data([scan_path], ["Si IV 1403"])
    raster.coords.pointing_offset = (2.5, -3.25)  # 'Shift pointing…'
    maps = line_moments(raster, 1402.77)
    sliced = Data(
        label="sliced",  # a raster window at a wavelength, with each step's time
        coords=_GlueWCS(SlicedLowLevelWCS(raster.coords._wcs, (slice(None), slice(None), 20))),
        values=raster[raster.main_components[0]][..., 20],
        Time=raster["Time"][..., 20],
    )
    sliced.coords.pointing_offset = raster.coords.pointing_offset
    for data in (maps, sliced):
        export(monkeypatch, tmp_path / f"{data.label}.fits", data)
        with fits.open(tmp_path / f"{data.label}.fits") as hdus:
            # every pixel's longitude and latitude, as glue gives them
            y, x = np.indices(data.shape)
            world = dict(zip(data.coords.world_axis_physical_types, data.coords.pixel_to_world_values(x, y)))
            wcs = WCS(hdus[0].header, fobj=hdus)
            lon, lat = np.multiply(wcs.pixel_to_world_values(x, y), 3600)
            np.testing.assert_allclose((lon + 648000) % 1296000 - 648000, world[_HPC[0]], rtol=0, atol=1e-9)
            np.testing.assert_allclose(lat, world[_HPC[1]], rtol=0, atol=1e-9)
            got, want = wcs.pixel_to_world(0, 0).frame, HighLevelWCSWrapper(data.coords).pixel_to_world(0, 0).frame
            assert got.obstime == want.obstime
            assert want.observer.separation_3d(got.observer) < 1 * u.m
            for cid in data.main_components:
                if cid.label != "Time":
                    np.testing.assert_array_equal(hdus[cid.label].data, data[cid])
                    assert hdus[cid.label].header["BUNIT"] == data.get_component(cid).units
            if data is maps:
                assert "TIME" not in hdus
                keys = ("OBSID", "STARTOBS")
                assert [hdus[0].header[key] for key in keys] == [str(raster.meta[key]) for key in keys]
            else:
                time = hdus["TIME"]
                times = np.datetime64(time.header["DATEREF"]) + np.round(time.data * 1e9).astype("timedelta64[ns]")
                np.testing.assert_array_equal(times, data["Time"])


def test_exporting_other_data_than_a_map_shows_why(qtbot, monkeypatch, tmp_path, scan_path):
    [raster] = raster_data([scan_path], ["Si IV 1403"])
    shown = []
    monkeypatch.setenv("GLUE_TESTING", "False")  # glue raises the error instead while testing
    monkeypatch.setattr(QtWidgets.QMessageBox, "exec_", lambda box: shown.append(box.text()))
    for data in (
        raster,
        Data(label="plain", x=np.zeros((3, 4))),
        Data(label="image", coords=WCS(naxis=2), x=np.zeros((3, 4))),  # glue's FITS loader, no CTYPE
    ):
        export(monkeypatch, tmp_path / "refused.fits", data)
    assert shown == [
        f"Could not export the data\n{label} is not a 2-D map on helioprojective coordinates: glue's 'FITS (1 "
        "component/HDU)' exports it without them."
        for label in (raster.label, "plain", "image")
    ]
    assert not (tmp_path / "refused.fits").exists()


def window(low, high, name, twave=None):
    """A spectral window from ``low`` to ``high`` Angstrom, named ``name``, its TWAVE ``twave`` or mid-window."""
    wcs = WCS(naxis=1)
    wcs.wcs.ctype, wcs.wcs.cunit, wcs.wcs.crpix = ["WAVE"], ["Angstrom"], [1]
    wcs.wcs.crval, wcs.wcs.cdelt = [low], [(high - low) / 10]
    data = Data(label=str(name), x=np.zeros(11), coords=wcs)
    data.meta.update(NWIN=1, TDESC1=name, TWAVE1=(low + high) / 2 if twave is None else twave)
    return data


def test_the_rest_wavelength_of_a_window():
    """The one main line within it, else of several the one nearest its name's wavelength, else None; never TWAVE."""
    assert rest_wavelength(window(1398, 1406, "Si IV 1403", twave=1402.8)) == 1402.77
    assert rest_wavelength(window(1398, 1406, None)) == 1402.77  # one line needs no name
    assert rest_wavelength(window(2790, 2810, "Mg II k 2796", twave=2796.2)) == 2796.352  # k, h and the triplet
    assert rest_wavelength(window(2790, 2810, "Mg II h 2803")) == 2803.53
    assert rest_wavelength(window(1332, 1358, "C II 1336")) == 1335.7079  # C II's three, Fe XII, Fe XXI and O I
    for several in ("Mg II k", "Mg II 2800", None):  # a name without a wavelength, one within 1 Å of none, no name
        assert rest_wavelength(window(2790, 2810, several)) is None
    assert rest_wavelength(window(2831, 2834, "2832", twave=2832.7)) is None  # no line: not its TWAVE
    assert rest_wavelength(Data(label="plain", x=np.zeros(3))) is None
    # meta['rest_wavelength'] first
    for data in (window(2790, 2810, "Mg II k 2796"), window(2831, 2834, "2832"), Data(x=np.zeros(3))):
        data.meta["rest_wavelength"] = 2796.2
        assert rest_wavelength(data) == 2796.2


def test_the_line_dialogs_start_at_the_rest_wavelength(app, monkeypatch, irispy_test_files):
    """Both line dialogs start at the window's rest wavelength, their tooltip saying where it is from, else blank."""
    windows = raster_data([find_irispy_test_file(irispy_test_files, SCAN)], ["Mg II k 2796", "2832"])
    [none, mg] = sorted(windows, key=lambda data: data.label)  # 2832 first
    app.data_collection.extend([mg, none])
    opened = []

    def exec_(dialog):
        field = dialog.findChild(QtWidgets.QLineEdit, "centre") or dialog.findChild(QtWidgets.QLineEdit, "rest")
        opened.append((field.text(), field.toolTip()))
        return QtWidgets.QDialog.Rejected

    monkeypatch.setattr(QtWidgets.QDialog, "exec", exec_)
    tree = app._layer_widget

    def both(data):
        tree.ui.layerTree.set_selected_layers([data])
        for action in (ACTION, "IRIS: red-blue asymmetry…"):
            tree._actions[action].trigger()
        return [opened.pop(0) for _ in range(2)]

    assert both(mg) == [("2796.352", "Mg II k, of the main IRIS lines")] * 2  # not the TWAVE, 2796.2
    assert both(none) == [("", "")] * 2
    mg.meta["rest_wavelength"] = 2796.2
    assert both(mg) == [("2796.2", f"{mg.label}'s, set with 'Set rest wavelength…'")] * 2


def test_set_rest_wavelength(app, monkeypatch, irispy_test_files):
    """'Set rest wavelength…' lists the main lines within the window, takes one or a typed wavelength, or a blank."""
    [mg] = raster_data([find_irispy_test_file(irispy_test_files, SCAN)], ["Mg II k 2796"])
    sji = image_data(find_irispy_test_file(irispy_test_files, SJI))
    app.data_collection.extend([mg, sji])
    opened, shown = [], []
    monkeypatch.setenv("GLUE_TESTING", "False")  # glue raises the error instead while testing
    monkeypatch.setattr(QtWidgets.QMessageBox, "exec_", lambda box: shown.append(box.text()))
    tree = app._layer_widget
    action = tree._actions["Set rest wavelength…"]

    def pick(text, ok=True):
        monkeypatch.setattr(QtWidgets.QInputDialog, "getItem", lambda *args: opened.append(args[3:5]) or (text, ok))
        action.trigger()
        return rest_wavelength(mg), mg.meta.get("rest_wavelength")

    tree.ui.layerTree.set_selected_layers([mg])
    lines = ["Mg II 2791.599", "Mg II k 2796.352", "Mg II 2798.754", "Mg II 2798.823", "Mg II h 2803.53"]
    assert pick("Mg II h 2803.53") == (2803.53, 2803.53)
    assert pick(" 2796.2 ") == (2796.2, 2796.2)
    assert pick("2800", ok=False) == (2796.2, 2796.2)  # Cancel
    assert pick("k") == (2796.2, 2796.2)
    assert pick(" ") == (2796.352, None)  # back to the main line
    assert opened == [(lines, 1), (lines, 4), (["2796.2", *lines], 0), (["2796.2", *lines], 0), (["2796.2", *lines], 0)]
    tree.ui.layerTree.set_selected_layers([sji])
    action.trigger()
    assert shown == [
        "Could not set the rest wavelength\n'k' is not a wavelength in Angstrom, such as 1402.77.",
        f"Could not set the rest wavelength\n{sji.label} has no wavelength axis.",
    ]
