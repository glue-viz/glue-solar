"""
'IRIS: line fit maps', on int16 copies of irispy's test scans: the last IRIS fit on a Profile viewer's Fit tab handed
to the window's fit, the dataset and links it adds, a stack scan by scan, Cancel and the refusals. dask's synchronous
scheduler stands in for its processes, which take seconds to start.
"""

import dask.local
import dask.multiprocessing
import numpy as np
import pytest
from glue_qt.viewers.profile import ProfileViewer, profile_tools
from qtpy import QtWidgets

import astropy.modeling.fitting
import astropy.units as u

from glue_solar.fitters import GaussianConstantFitter
from glue_solar.sources import fit_maps
from glue_solar.sources.loaders import iris
from glue_solar.sources.loaders.iris import keep_hpc_linked, link_hpc, raster_data
from glue_solar.tests.helpers import run_action

ACTION = "IRIS: line fit maps"
LINE = (1401.9, 1403.7)  # Si IV 1402.77, in Angstrom: seven of the window's 0.25 Å samples


@pytest.fixture(autouse=True)
def _synchronous(monkeypatch):
    monkeypatch.setattr(dask.multiprocessing, "get", dask.local.get_sync)


@pytest.fixture
def calls(monkeypatch):
    """The keyword arguments of each call of astropy's ``parallel_fit_dask``, which runs as it would."""
    made, fit = [], astropy.modeling.fitting.parallel_fit_dask
    monkeypatch.setattr(astropy.modeling.fitting, "parallel_fit_dask", lambda **kw: made.append(kw) or fit(**kw))
    return made


def profile(app, data, unit="Angstrom", function="mean"):
    """The Fit tab of a new Profile viewer of ``data`` against its wavelength in ``unit``, with the IRIS fitter."""
    viewer = app.new_data_viewer(ProfileViewer, data=data)
    viewer.state.x_att = data.world_component_ids[-1]
    viewer.state.x_display_unit = unit
    viewer.state.function = function
    viewer.toolbar.active_tool = "profile-analysis"
    tools = viewer.toolbar.tools["profile-analysis"]._profile_tools
    tools.fit_function = GaussianConstantFitter
    return tools


def fit(qtbot, tools, x_range=LINE):
    """Fit over ``x_range`` on ``tools``; returns the model the viewer keeps of its data."""
    before = getattr(tools, "_iris_fits", None)
    tools.rng_mode.state.x_min, tools.rng_mode.state.x_max = x_range
    tools.ui.button_fit.click()
    tools.wait_for_fit()  # its thread, which keeps it
    qtbot.waitUntil(tools.ui.button_fit.isEnabled)  # for the next fit
    assert tools._iris_fits is not before
    [model] = tools._iris_fits.values()
    return model


def run(app, qtbot, data):
    """Trigger the action on ``data``; returns the dataset it adds."""
    [maps] = run_action(app, qtbot, data, ACTION, f"Fitting every spectrum of {data.label}…")
    qtbot.waitUntil(lambda: not app.findChildren(QtWidgets.QProgressDialog))  # closed once done
    return maps


def test_the_profile_fit_of_a_window_maps_every_spectrum_into_one_linked_dataset(app, qtbot, scan_path, calls):
    [raster] = raster_data([scan_path], ["Si IV 1403"])
    collection = app.data_collection
    collection.append(raster)
    keep_hpc_linked(collection)
    fitted = fit(qtbot, profile(app, raster))
    maps = run(app, qtbot, raster)
    # the Profile fit's model, a start per spectrum seeded from it, on dask's processes
    [call] = calls
    start = call["model"]
    assert (start.param_names, start.bounds) == (fitted.param_names, fitted.bounds)
    assert start.mean_1.value.shape == raster.shape[:2]
    np.testing.assert_array_equal(start.stddev_1.value, fitted.stddev_1.value)  # the width kept
    assert (call["fitting_axes"], call["fit_info"], call["fitter_kwargs"]) == (2, True, {"filter_non_finite": True})
    assert call["scheduler"].func is dask.local.get_sync  # dask.multiprocessing.get, patched
    assert str(call["data_unit"]) == "DN_IRIS_FUV"
    [wavelengths] = call["world"]
    assert wavelengths.unit == u.AA
    assert LINE[0] <= wavelengths[0].value < wavelengths[-1].value <= LINE[1]
    assert call["data"].shape == (*raster.shape[:2], len(wavelengths))
    missing = np.isnan(call["data"]).all(-1)  # the window's fill, as its mask has it
    assert missing.any()

    assert maps.label == f"{raster.label} fit 1402.77"
    assert maps.shape == raster.shape[:2]
    maps_first = ["velocity_1", "fwhm_1", "fwhm_velocity_1", "integrated_intensity_1"]
    labels = [cid.label for cid in maps.main_components]
    assert labels[:9] == [label + end for label in maps_first for end in ("", " error")] + ["quality"]
    assert labels[9:] == [label + end for label in fitted.param_names for end in ("", " error")]
    units = {cid.label: maps.get_component(cid).units for cid in maps.main_components}
    assert [units[label] for label in (*maps_first, "quality")] == [
        "km / s",
        "Angstrom",
        "km / s",
        str(call["data_unit"] * u.AA),
        "",
    ]
    assert maps.meta == {
        "OBSID": raster.meta["OBSID"],
        "STARTOBS": raster.meta["STARTOBS"],
        "fit_rest_wavelength": 1402.77,
        "fit_range": (wavelengths[0].value, wavelengths[-1].value),
    }
    assert np.isnan(maps["velocity_1"][missing]).all()
    assert (maps["quality"][missing] == 1).all()  # irispy's no fit
    [*_, viewer] = app.viewers[0]  # glue's Image viewer of its first map
    assert viewer.state.layers[0].attribute is maps.main_components[0]
    assert link_hpc(collection) == []
    linked = {cid for link in collection.links for cid in (link.get_to_id(), *link.get_from_ids())}
    assert set(maps.world_component_ids) <= linked


def test_the_fit_reaches_the_window_in_angstrom_with_its_settings(app, qtbot, monkeypatch, scan_path, calls):
    """A fit of DN / s, in nm, with a fixed background and a bound set in Settings, reaches the window in Angstrom."""
    [raster] = raster_data([scan_path], ["Si IV 1403"])
    app.data_collection.append(raster)

    def settings(dialog):
        _, value, fixed, *_ = dialog.constraints._widgets["amplitude_0"]
        value.setText("2")
        fixed.setChecked(True)
        *_, bounded, lower, upper = dialog.constraints._widgets["mean_1"]
        bounded.setChecked(True)
        lower.setText("140.27")
        upper.setText("140.29")
        dialog.accept()

    tools = profile(app, raster, "nm")
    tools.viewer.state.layers[0].attribute = raster.id[f"{raster.main_components[0].label} DN / s"]
    monkeypatch.setattr(profile_tools.FitSettingsWidget, "exec_", settings)
    tools.ui.button_settings.click()
    fitted = fit(qtbot, tools, np.divide(LINE, 10))
    maps = run(app, qtbot, raster)
    [call] = calls
    start = call["model"]
    assert start.fixed["amplitude_0"]
    assert (start.amplitude_0.value == 2).all()
    assert start.bounds["mean_1"] == pytest.approx((1402.7, 1402.9))
    assert ((1402.7 <= start.mean_1.value) & (start.mean_1.value <= 1402.9)).all()
    np.testing.assert_allclose(start.stddev_1.value, 10 * fitted.stddev_1.value)
    [wavelengths] = call["world"]
    assert LINE[0] <= wavelengths[0].value < wavelengths[-1].value <= LINE[1]
    assert str(call["data_unit"]) == "DN_IRIS_FUV / s"
    assert maps.get_component("integrated_intensity_1").units == str(call["data_unit"] * u.AA)


def test_a_stack_is_fitted_scan_by_scan(app, qtbot, stack_paths, calls):
    [stack] = raster_data(stack_paths, ["Si IV 1403"], stack=True)
    collection = app.data_collection
    collection.append(stack)
    keep_hpc_linked(collection)
    fit(qtbot, profile(app, stack))
    maps = run(app, qtbot, stack)
    assert maps.shape == stack.shape[:-1]
    assert [call["data"].shape[:2] for call in calls] == [stack.shape[1:3]] * 3  # each scan alone
    assert link_hpc(collection) == []


def test_cancel_adds_nothing(app, qtbot, monkeypatch, scan_path):
    [raster] = raster_data([scan_path], ["Si IV 1403"])
    collection = app.data_collection
    collection.append(raster)
    fit(qtbot, profile(app, raster))
    shown = []
    monkeypatch.setenv("GLUE_TESTING", "False")  # glue raises the error instead while testing
    monkeypatch.setattr(QtWidgets.QMessageBox, "exec_", lambda box: shown.append(box.text()))
    tree = app._layer_widget
    tree.ui.layerTree.set_selected_layers([raster])
    tree._actions[ACTION].trigger()
    [dialog] = app.findChildren(QtWidgets.QProgressDialog)
    assert dialog.isVisible()
    [cancel] = dialog.findChildren(QtWidgets.QPushButton)
    cancel.click()
    qtbot.waitUntil(lambda: not iris._RUNNING and not app.findChildren(QtWidgets.QProgressDialog))
    assert len(collection) == 1
    assert shown == []
    assert app.statusBar().currentMessage() == ""


def test_refusals_show_why(app, qtbot, monkeypatch, scan_path):
    [raster] = raster_data([scan_path], ["Si IV 1403"])
    collection = app.data_collection
    collection.append(raster)
    shown = []
    monkeypatch.setenv("GLUE_TESTING", "False")
    monkeypatch.setattr(QtWidgets.QMessageBox, "exec_", lambda box: shown.append(box.text()))
    tree = app._layer_widget

    def trigger():
        tree.ui.layerTree.set_selected_layers([raster])
        tree._actions[ACTION].trigger()

    trigger()  # no fit yet
    fit(qtbot, profile(app, raster, function="sum"))
    trigger()
    fit(qtbot, profile(app, raster, "km / s"), (-200, 200))  # the window's rest wavelength, Si IV 1402.77
    trigger()
    tools = profile(app, raster)
    tools.viewer.state.x_att = raster.pixel_component_ids[-1]
    fit(qtbot, tools, (12, 20))  # about 1402.77 Å
    trigger()
    mask = raster.id[f"{raster.label} mask"]  # the fraction missing, which the 24 pixels missing make a line
    tools.viewer.state.x_att = raster.world_component_ids[-1]
    tools.viewer.state.layers[0].attribute = mask
    fit(qtbot, tools)
    trigger()
    tools.viewer.state.layers[0].attribute = raster.main_components[0]
    fit(qtbot, tools)
    monkeypatch.setattr(fit_maps, "rest_wavelength", lambda data: None)
    trigger()
    title = "Could not fit the line maps\n"
    assert all(text.startswith(title) for text in shown)
    last = f"The last IRIS fit of {raster.label}"
    assert [text.removeprefix(title) for text in shown] == [
        f"{raster.label} has no IRIS fit: fit one of its spectra with 'Gaussian + constant (IRIS)' on the Fit tab of a "
        "Profile viewer first.",
        f"{last} is of the sum of its spectra, which scales its amplitudes: fit their Mean or Median.",
        f"{last} is against km / s: fit against its wavelength in a length, such as Angstrom.",
        f"{last} is against pixels: fit against its wavelength in a length, such as Angstrom.",
        f"{last} is of {mask.label}: fit its values, in DN or DN / s.",
        f"{raster.label} has no rest wavelength: set one with 'IRIS: set rest wavelength…'.",
    ]
    assert len(collection) == 1
    assert not iris._RUNNING
