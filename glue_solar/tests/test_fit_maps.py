"""
'Fit every spectrum' on a Profile viewer's Fit tab, on int16 copies of irispy's test scans: the button, the viewer's
own last IRIS fit handed to the window's fit, in Angstrom from a length or km / s, the dataset and links it adds, a
stack scan by scan, Cancel and the refusals. dask's synchronous scheduler stands in for its processes, which take
seconds to start.
"""

import gc
import re
import sys
import weakref

import dask.local
import dask.multiprocessing
import irispy.utils.fitting
import numpy as np
import pytest
from glue.core.fitters import PolynomialFitter
from glue.core.link_helpers import LinkSame
from glue_qt.viewers.profile import ProfileViewer
from qtpy import QtWidgets

import astropy.modeling.fitting
import astropy.units as u
import astropy.wcs.wcsapi.fitswcs
from astropy import constants
from astropy.io import fits
from astropy.modeling import models

from glue_solar.fitters import GaussianConstantFitter, _component
from glue_solar.quicklook import _wavelengths
from glue_solar.sources import fit_maps
from glue_solar.sources.loaders import iris
from glue_solar.sources.loaders.iris import WCS_LOCK, keep_hpc_linked, link_hpc, raster_data
from glue_solar.tests.helpers import add_component, click, fit_settings

LINE = (1401.9, 1403.7)  # Si IV 1402.77, in Angstrom: seven of the window's 0.25 Å samples
REST = 1402.77  # the window's rest wavelength


@pytest.fixture(autouse=True)
def _synchronous(monkeypatch):
    monkeypatch.setattr(dask.multiprocessing, "get", dask.local.get_sync)


@pytest.fixture
def calls(monkeypatch):
    """The keyword arguments of each call of astropy's ``parallel_fit_dask``, which runs as it would."""
    made, fit = [], astropy.modeling.fitting.parallel_fit_dask
    monkeypatch.setattr(astropy.modeling.fitting, "parallel_fit_dask", lambda **kw: made.append(kw) or fit(**kw))
    return made


@pytest.fixture
def once(monkeypatch, calls):
    """One iteration of each spectrum's fit, where the fitted values do not matter, as CI's coverage run is slow."""
    fit = astropy.modeling.fitting.parallel_fit_dask
    monkeypatch.setattr(
        astropy.modeling.fitting,
        "parallel_fit_dask",
        lambda **kw: fit(**{**kw, "fitter_kwargs": {**kw["fitter_kwargs"], "maxiter": 1}}),
    )


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
    """Fit over ``x_range`` on ``tools``; returns the model the viewer keeps of its reference data."""
    data = tools.viewer.state.reference_data
    before = getattr(tools, "_iris_fits", {}).get(data)
    tools.rng_mode.state.x_min, tools.rng_mode.state.x_max = x_range
    tools.ui.button_fit.click()
    tools.wait_for_fit()  # its thread, which keeps it
    qtbot.waitUntil(tools.ui.button_fit.isEnabled)  # for the next fit
    model = tools._iris_fits[data]
    assert model is not before
    return model


def run(app, qtbot, tools):
    """Press 'Fit every spectrum' on ``tools``; returns the dataset it adds."""
    collection, (data, _) = app.data_collection, fit_maps._viewer_fit(tools)
    count = len(collection)
    tools.button_fit_every.click()
    assert iris._RUNNING  # on glue-qt's worker
    assert app.statusBar().currentMessage() == f"Fitting every spectrum of {data.label}…"
    qtbot.waitUntil(lambda: len(collection) == count + 1 and not iris._RUNNING, timeout=60_000)
    qtbot.waitUntil(lambda: not app.findChildren(QtWidgets.QProgressDialog))  # closed once done
    return collection[-1]


def test_the_button_follows_the_viewer_s_iris_fit(app, qtbot, scan_path):
    [raster] = raster_data([scan_path], ["Si IV 1403"])
    app.data_collection.append(raster)
    tools = profile(app, raster)
    button = tools.button_fit_every
    [row] = [row for row in tools.findChildren(QtWidgets.QHBoxLayout) if row.indexOf(button) >= 0]
    assert row.indexOf(button) == row.indexOf(tools.ui.button_fit) + 1  # beside Fit
    none = "This viewer has no IRIS fit: fit a spectrum of a raster window with 'Gaussian + constant (IRIS)' first."
    assert (button.isEnabled(), button.toolTip()) == (False, none)
    tools.fit_function = PolynomialFitter  # glue's own
    tools.rng_mode.state.x_min, tools.rng_mode.state.x_max = LINE
    tools.ui.button_fit.click()
    tools.wait_for_fit()
    qtbot.waitUntil(tools.ui.button_fit.isEnabled)
    assert (button.isEnabled(), button.toolTip()) == (False, none)
    tools.fit_function = GaussianConstantFitter
    fit(qtbot, tools)
    assert button.isEnabled()
    assert button.toolTip() == f"Fit every spectrum of {raster.label} with this viewer's last IRIS fit"


def test_each_viewer_fits_the_window_with_its_own_fit(app, qtbot, scan_path, calls, once):
    """Of two Profile viewers of a window, each button takes its own viewer's fit, the second's the newer (D88)."""
    [raster] = raster_data([scan_path], ["Si IV 1403"])
    app.data_collection.append(raster)
    first, second = profile(app, raster), profile(app, raster)
    narrow = (1402.1, 1403.5)
    fitted = fit(qtbot, first), fit(qtbot, second, narrow)
    for tools in (first, second):
        run(app, qtbot, tools)
    wavelengths = _wavelengths(raster)[0]
    for call, model, (low, high) in zip(calls, fitted, (LINE, narrow), strict=True):
        np.testing.assert_array_equal(call["world"][0].value, wavelengths[(wavelengths >= low) & (wavelengths <= high)])
        np.testing.assert_array_equal(call["model"].stddev_1.value, model.stddev_1.value)  # the width kept


def test_the_viewer_keeps_the_last_fit_of_each_dataset(app, qtbot, scan_path):
    first, second = (raster_data([scan_path], ["Si IV 1403"])[0] for _ in range(2))
    app.data_collection.extend([first, second])
    tools = profile(app, first)
    kept = fit(qtbot, tools)
    state = tools.viewer.state
    # no style editor: glue-qt keeps a removed layer's, and through it the data, for the viewer's life (report candidate)
    tools.viewer._view.layer_style_widget_cls = None
    tools.viewer.add_data(second)
    state.reference_data, state.x_att = second, second.world_component_ids[-1]  # the first's layer not fitted
    state.x_display_unit = "Angstrom"
    fit(qtbot, tools)
    assert set(tools._iris_fits) == {first, second}
    assert tools._iris_fits[first] is kept
    assert fit_maps._viewer_fit(tools)[0] is second  # the newest
    # a dataset removed is not kept alive by its fit (D86)
    tools.viewer.remove_data(second)
    app.data_collection.remove(second)
    assert fit_maps._viewer_fit(tools)[0] is first  # its fit, still kept, skipped
    state.x_att, state.x_display_unit = first.world_component_ids[-1], "Angstrom"
    fit(qtbot, tools)  # glue-qt holds its last fit's layers until the next
    removed = weakref.ref(second)
    del second
    gc.collect()
    assert removed() is None
    assert list(tools._iris_fits) == [first]


@pytest.mark.parametrize("background", [models.Linear1D(), models.Polynomial1D(2)])
def test_a_fit_in_km_s_converts_to_the_same_fit_in_angstrom(background):
    """
    Two lines on a linear or a quadratic background, a center bounded, fitted against km / s from the rest wavelength
    and against Angstrom: both in Angstrom are the same model, to rounding (D88).
    """
    wavelengths = 1402 + 0.025 * np.arange(64)
    doppler = u.doppler_optical(REST * u.AA)
    spectrum = background.copy()
    spectrum.parameters = [12, 0.5, 3][: len(spectrum.parameters)]  # about 0 Å, 10 DN at the line
    lines = [models.Gaussian1D(100, REST, 0.05), models.Gaussian1D(30, 1403.07, 0.06)]
    spectrum = spectrum(wavelengths - REST) + sum(line(wavelengths) for line in lines)
    converted = []
    for unit in ("Angstrom", "km / s"):
        leaves = background.copy(), models.Gaussian1D(), models.Gaussian1D()
        fitter = GaussianConstantFitter(components=[_component(leaf) for leaf in leaves])
        limits = (np.array([1402.7, 1402.85]) * u.AA).to_value(unit, doppler)
        fitter.set_constraint("mean_1", limits=tuple(limits))
        model, _ = fitter.build_and_fit((wavelengths * u.AA).to_value(unit, doppler), spectrum)
        converted.append(fit_maps._in_angstrom(model, *fit_maps._to_angstrom(unit, REST)))
    angstrom, km_s = converted
    assert angstrom.mean_1.value == pytest.approx(REST)
    for name in angstrom.param_names:
        assert getattr(km_s, name).value == pytest.approx(getattr(angstrom, name).value, rel=1e-8)
        # a width's lower bound is astropy's least positive float32, which converts as a width
        assert km_s.bounds[name] == pytest.approx(angstrom.bounds[name], rel=1e-12, abs=1e-30)


def test_a_tied_separation_reaches_the_window_in_angstrom():
    fitter = GaussianConstantFitter(components=[_component(models.Gaussian1D()), _component(models.Gaussian1D())])
    fitter.components[1][1]["mean"]["tie"] = (0, 0.1)  # in nm, the x unit of the fit
    fitter.components[1][1]["amplitude"]["tie"] = (0, 0.5)
    model = fitter.model_cls(amplitude_0=4, mean_0=140.2, stddev_0=0.01, stddev_1=0.01)
    assert model.tied["mean_1"](model) == pytest.approx(140.3)
    converted = fit_maps._in_angstrom(model, *fit_maps._to_angstrom("nm", None))
    assert converted.tied["mean_1"](converted) == pytest.approx(1403)
    assert converted.tied["amplitude_1"](converted) == 2  # a ratio, of no unit
    background = models.Linear1D(bounds={"slope": (0, 5)}) + models.Gaussian1D()  # per nm, then per Å
    converted = fit_maps._in_angstrom(background, *fit_maps._to_angstrom("nm", None))
    assert converted.bounds["slope_0"] == pytest.approx((0, 0.5))
    # in km / s from the rest wavelength: 64 km / s is 0.2995 Å from it
    fitter.components[1][1]["mean"]["tie"] = (0, 64)
    model = fitter.model_cls(amplitude_0=4, mean_0=0, stddev_0=10, stddev_1=10)
    converted = fit_maps._in_angstrom(model, *fit_maps._to_angstrom("km / s", REST))
    assert converted.mean_0.value == REST
    separation = converted.tied["mean_1"](converted) - REST
    assert separation == pytest.approx(64 * REST / constants.c.to_value("km / s"), rel=1e-9)
    assert converted.tied["amplitude_1"](converted) == 2
    # a bound or a fixed term of a background, which km / s mixes, refused
    for background in (models.Linear1D(bounds={"slope": (0, None)}), models.Polynomial1D(2, fixed={"c2": True})):
        with pytest.raises(ValueError, match="with a bound or a fixed term takes a fit against a length"):
            fit_maps._in_angstrom(background + models.Gaussian1D(), *fit_maps._to_angstrom("km / s", REST))


def test_the_profile_fit_of_a_window_maps_every_spectrum_into_one_linked_dataset(app, qtbot, scan_path, calls):
    [raster] = raster_data([scan_path], ["Si IV 1403"])
    collection = app.data_collection
    collection.append(raster)
    keep_hpc_linked(collection)
    tools = profile(app, raster)
    fitted = fit(qtbot, tools)
    maps = run(app, qtbot, tools)
    # the Profile fit's model, a start per spectrum seeded from it, on dask's processes
    [call] = calls
    start = call["model"]
    assert (start.param_names, start.bounds) == (fitted.param_names, fitted.bounds)
    assert start.mean_1.value.shape == raster.shape[:2]
    np.testing.assert_array_equal(start.stddev_1.value, fitted.stddev_1.value)  # the width kept
    assert (call["fitting_axes"], call["fitter_kwargs"]) == (2, {"filter_non_finite": True})
    assert call["fit_info"] == ("param_cov", "success")  # what irispy reads, not every fit's Jacobian
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


def test_saturated_samples_are_left_out_of_the_fits(app, qtbot, monkeypatch, scan_path, calls):
    """
    A sample at the Level 2 ceiling, 16182 DN, a lower bound only, is left out of each spectrum's fit and its start,
    irispy's ``starts_from_model`` of the masked cube; the window's mean, whose other pixels are not saturated there,
    keeps it in its Profile fit, which says so (D86, D87).
    """
    [raster] = raster_data([scan_path], ["Si IV 1403"])
    peak = np.argmin(np.abs(_wavelengths(raster)[0] - 1402.77))
    with fits.open(scan_path, mode="update", do_not_scale_image_data=True) as hdulist:  # Si IV 1403's raw int16
        hdulist[5].data[:, 10, peak] = 32760
    [raster] = raster_data([scan_path], ["Si IV 1403"])
    app.data_collection.append(raster)
    assert (raster[raster.main_components[0], :, 10, peak] == 16182).all()
    tools = profile(app, raster)
    fitted = fit(qtbot, tools)
    assert (fitted.meta["saturated"], fitted.meta["partly_saturated"]) == (0, 1)
    handed, starts = [], irispy.utils.fitting.starts_from_model
    monkeypatch.setattr(
        irispy.utils.fitting, "starts_from_model", lambda *args: handed.append((*args, starts(*args))) or handed[-1][2]
    )
    run(app, qtbot, tools)
    [call] = calls
    [(model, cube, start)] = handed
    np.testing.assert_array_equal(model.parameters, fitted.parameters)  # in Angstrom already
    assert call["model"] is start
    [wavelengths] = call["world"]
    [sample] = np.flatnonzero(wavelengths.value == _wavelengths(raster)[0][peak])
    assert cube.mask[:, 10, sample].all()
    np.testing.assert_array_equal(call["data"], np.where(cube.mask, np.nan, cube.data))


def test_the_fit_reaches_the_window_in_angstrom_with_its_settings(app, qtbot, monkeypatch, scan_path, calls):
    """A fit of DN / s, in nm, with a fixed background and a bound set in Settings, reaches the window in Angstrom."""
    [raster] = raster_data([scan_path], ["Si IV 1403"])
    app.data_collection.append(raster)

    def settings(dialog):
        start, fixed, *_ = dialog.rows["amplitude_0"]
        start.setText("2")
        fixed.setChecked(True)
        _, _, lower, upper, *_ = dialog.rows["mean_1"]
        lower.setText("140.27")
        upper.setText("140.29")

    tools = profile(app, raster, "nm")
    tools.viewer.state.layers[0].attribute = raster.id[f"{raster.main_components[0].label} DN / s"]
    fit_settings(monkeypatch, tools, settings)
    fitted = fit(qtbot, tools, np.divide(LINE, 10))
    maps = run(app, qtbot, tools)
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


def test_a_fit_in_km_s_maps_as_the_same_fit_in_angstrom(app, qtbot, scan_path, calls, once):
    """The window fit of a Profile fit made against km / s from the rest wavelength, as that of one against Angstrom."""
    [raster] = raster_data([scan_path], ["Si IV 1403"])
    app.data_collection.append(raster)
    velocities = (LINE * u.AA).to_value(u.km / u.s, u.doppler_optical(REST * u.AA))
    maps = [
        run(app, qtbot, (fit(qtbot, tools, x_range), tools)[1])
        for tools, x_range in ((profile(app, raster), LINE), (profile(app, raster, "km / s"), velocities))
    ]
    angstrom, km_s = calls
    np.testing.assert_array_equal(km_s["world"][0], angstrom["world"][0])  # the same wavelengths
    for name in angstrom["model"].param_names:
        np.testing.assert_allclose(getattr(km_s["model"], name).value, getattr(angstrom["model"], name).value, 1e-6)
    assert [cid.label for cid in maps[1].main_components] == [cid.label for cid in maps[0].main_components]
    for cid in maps[0].main_components:
        np.testing.assert_allclose(maps[1][cid.label], maps[0][cid], rtol=1e-6, atol=1e-9, err_msg=cid.label)


@pytest.mark.filterwarnings("ignore:The fit may be unsuccessful")  # a blend 0.05 Å apart, sampled every 0.26 Å
def test_c_ii_built_in_settings_fits_one_spectrum_then_the_window(app, qtbot, monkeypatch, scan_path, calls):
    """
    C II's three lines built in Settings, 1334.53, 1335.66 and 1335.71 Å, the last two a blend: Gaussians on a
    quadratic, the second's and third's centers tied to the first's by their separations and each amplitude at least 0,
    fitted to the mean spectrum of the scan's C II window, then to the window with 'Fit every spectrum' from irispy's
    starts (D86).
    """
    [raster] = raster_data([scan_path], ["C II 1336"])
    app.data_collection.append(raster)
    tools = profile(app, raster)

    def build(dialog):
        click(dialog.table, "Remove")  # the constant
        add_component(dialog, "Gaussian")
        add_component(dialog, "Gaussian")
        add_component(dialog, "Polynomial", 2)
        dialog.rows["mean_0"][0].setText("1334.53")
        for line, separation in ((1, "1.1305"), (2, "1.1756")):
            *_, tie, by = dialog.rows[f"mean_{line}"]
            tie.setCurrentText("mean_0")
            by.setText(separation)
        for line in (0, 1, 2):
            dialog.rows[f"amplitude_{line}"][2].setText("0")

    fit_settings(monkeypatch, tools, build)
    fitted = fit(qtbot, tools, (1333.5, 1336.5))
    assert fitted.mean_1.value - fitted.mean_0.value == pytest.approx(1.1305)
    assert fitted.mean_2.value - fitted.mean_0.value == pytest.approx(1.1756)
    assert [fitted.bounds[f"amplitude_{line}"] for line in (0, 1, 2)] == [(0, None)] * 3
    assert all(f"center_{line} = " in tools.text_log.toPlainText() for line in (0, 1, 2))
    recorded = astropy.modeling.fitting.parallel_fit_dask  # one iteration each: this checks the model, not the fits
    monkeypatch.setattr(
        astropy.modeling.fitting,
        "parallel_fit_dask",
        lambda **kw: recorded(**{**kw, "fitter_kwargs": {**kw["fitter_kwargs"], "maxiter": 1}}),
    )
    maps = run(app, qtbot, tools)
    [call] = calls
    assert {name for name, tie in call["model"].tied.items() if tie} == {"mean_1", "mean_2"}
    tied = {"filter_non_finite": True, "estimate_jacobian": True, "epsilon": 1e-12, "maxiter": 1}  # #291's Jacobian
    assert call["fitter_kwargs"] == tied
    assert {f"velocity_{line}" for line in (0, 1, 2)} <= {cid.label for cid in maps.main_components}
    fits = np.isfinite(maps["mean_0"])
    assert fits.any()
    np.testing.assert_allclose((maps["mean_2"] - maps["mean_0"])[fits], 1.1756)


def test_a_stack_is_fitted_scan_by_scan(app, qtbot, monkeypatch, stack_paths, calls):
    [stack] = raster_data(stack_paths, ["Si IV 1403"], stack=True)
    collection = app.data_collection
    collection.append(stack)
    keep_hpc_linked(collection)
    tools = profile(app, stack)
    fit(qtbot, tools)
    # each wcslib call on the scans' WCSes holds WCS_LOCK for itself, and irispy's maps_from_fit runs without it, as
    # test_linking's analyses (#311)
    raws = [*stack.coords._wcs._wcses, stack.coords._wcs._wcs._wcs[1]._wcs]
    owners = {id(owner) for raw in raws for owner in (raw, raw.wcs)}  # each WCS and its wcslib struct
    files = {astropy.wcs.wcs.__file__, astropy.wcs.wcsapi.fitswcs.__file__}
    wcs_calls, entered, fit_maps_ = [], [], fit_maps._fit_maps

    def trace(frame, event, arg):
        if event == "c_call" and id(getattr(arg, "__self__", None)) in owners:
            wcs_calls.append((arg.__name__, WCS_LOCK._is_owned()))
        elif event == "call" and frame.f_code.co_filename in files and id(frame.f_locals.get("self")) in owners:
            wcs_calls.append((frame.f_code.co_name, WCS_LOCK._is_owned()))
        elif event == "call" and frame.f_code.co_name == "maps_from_fit":
            entered.append(WCS_LOCK._is_owned())

    def traced(*args):  # on glue-qt's Worker, a QThread, which threading.setprofile_all_threads does not reach
        sys.setprofile(trace)
        try:
            return fit_maps_(*args)
        finally:
            sys.setprofile(None)

    fit_ = astropy.modeling.fitting.parallel_fit_dask

    def untraced(**kw):  # the fits take no WCS, and traced take minutes on a slow runner
        # one iteration each: this checks the scans, not the fits, whose three scans took CI's coverage run past 60 s
        kw["fitter_kwargs"] = {**kw["fitter_kwargs"], "maxiter": 1}
        sys.setprofile(None)
        try:
            return fit_(**kw)
        finally:
            sys.setprofile(trace)

    monkeypatch.setattr(fit_maps, "_fit_maps", traced)
    monkeypatch.setattr(astropy.modeling.fitting, "parallel_fit_dask", untraced)
    maps = run(app, qtbot, tools)
    assert wcs_calls
    assert {name for name, locked in wcs_calls if not locked} <= {"serialized_classes"}  # astropy's False, no wcslib
    assert entered == [False] * 3
    assert maps.shape == stack.shape[:-1]
    assert [call["data"].shape[:2] for call in calls] == [stack.shape[1:3]] * 3  # each scan alone
    [pool] = {call["scheduler"].keywords["pool"] for call in calls}  # one for the run
    with pytest.raises(RuntimeError, match="after shutdown"):
        pool.submit(int)
    assert link_hpc(collection) == []


def test_cancel_adds_nothing(app, qtbot, monkeypatch, scan_path):
    [raster] = raster_data([scan_path], ["Si IV 1403"])
    collection = app.data_collection
    collection.append(raster)
    tools = profile(app, raster)
    fit(qtbot, tools)
    shown = []
    monkeypatch.setenv("GLUE_TESTING", "False")  # glue raises the error instead while testing
    monkeypatch.setattr(QtWidgets.QMessageBox, "exec_", lambda box: shown.append(box.text()))
    tools.button_fit_every.click()
    tools.button_fit_every.click()  # while it runs: one run a dataset
    [dialog] = app.findChildren(QtWidgets.QProgressDialog)
    assert dialog.isVisible()
    qtbot.waitUntil(lambda: dialog.maximum() > 0, timeout=60000)  # the tasks counted
    [cancel] = dialog.findChildren(QtWidgets.QPushButton)
    cancel.click()
    # after the chunk being fitted, which a slow runner takes seconds over
    qtbot.waitUntil(lambda: not iris._RUNNING and not app.findChildren(QtWidgets.QProgressDialog), timeout=60000)
    assert len(collection) == 1
    assert shown == [f"Could not fit the line maps\nThe line fit maps of {raster.label} are being computed."]
    assert app.statusBar().currentMessage() == ""


def test_refusals_show_why(app, qtbot, monkeypatch, scan_path):
    [raster] = raster_data([scan_path], ["Si IV 1403"])
    collection = app.data_collection
    collection.append(raster)
    shown = []
    monkeypatch.setenv("GLUE_TESTING", "False")
    monkeypatch.setattr(QtWidgets.QMessageBox, "exec_", lambda box: shown.append(box.text()))
    tools = profile(app, raster, function="sum")
    fit(qtbot, tools)
    tools.button_fit_every.click()
    tools = profile(app, raster)
    tools.viewer.state.x_att = raster.pixel_component_ids[-1]
    fit(qtbot, tools, (12, 20))  # about 1402.77 Å
    tools.button_fit_every.click()
    # the fraction missing, which the 24 pixels missing make a line
    mask = raster.id[f"{raster.main_components[0].label} mask"]
    tools.viewer.state.x_att = raster.world_component_ids[-1]
    tools.viewer.state.layers[0].attribute = mask
    fit(qtbot, tools)
    tools.button_fit_every.click()
    tools.viewer.state.layers[0].attribute = raster.main_components[0]
    fit(qtbot, tools)
    monkeypatch.setattr(fit_maps, "rest_wavelength", lambda data: None)
    tools.button_fit_every.click()
    title = "Could not fit the line maps\n"
    assert all(text.startswith(title) for text in shown)
    last = f"The last IRIS fit of {raster.label}"
    assert [text.removeprefix(title) for text in shown] == [
        f"{last} is of the sum of its spectra, which scales its amplitudes: fit their Mean or Median.",
        f"{last} is against pixels: fit against its wavelength, in a length such as Angstrom or in km / s.",
        f"{last} is of {mask.label}: fit its values, in DN or DN / s.",
        f"{raster.label} has no rest wavelength: set one with 'IRIS: set rest wavelength…'.",
    ]
    assert len(collection) == 1
    assert not iris._RUNNING


def test_a_km_s_fit_of_a_layer_not_the_reference_data_is_refused(app, qtbot, scan_path):
    """glue converts every layer's x to km / s from the reference data's rest wavelength: another layer's has none."""
    first, second = (raster_data([scan_path], ["Si IV 1403"])[0] for _ in range(2))
    app.data_collection.extend([first, second])
    app.data_collection.add_link(LinkSame(first.world_component_ids[-1], second.world_component_ids[-1]))
    tools = profile(app, second, "km / s")
    tools.viewer.add_data(first)  # its layer last, so its fit the newest
    fit(qtbot, tools, (LINE * u.AA).to_value(u.km / u.s, u.doppler_optical(REST * u.AA)))
    data, model = fit_maps._viewer_fit(tools)
    assert data is first
    assert model.meta["rest_wavelength"] is None
    refusal = (
        f"The last IRIS fit of {first.label} is against km / s from the viewer's reference data: make {first.label} "
        "the reference data and fit again."
    )
    with pytest.raises(ValueError, match=f"^{re.escape(refusal)}$"):
        fit_maps._last_fit(data, model)
