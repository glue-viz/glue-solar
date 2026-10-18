"""
'IRIS: line fit maps': the last IRIS fit of a spectrum of a raster window on the Fit tab of glue's Profile viewer,
fitted to every spectrum of the window, or of each scan of a stack (D59), with astropy's ``parallel_fit_dask``, as
irispy's ``maps_from_fit`` maps in one new dataset (D86).
"""

import warnings
from concurrent.futures import ProcessPoolExecutor
from functools import partial

import numpy as np
from glue.core.component import Component
from glue_qt.utils.decorators import messagebox_on_error
from glue_qt.viewers.profile import ProfileViewer
from qtpy import QtCore, QtWidgets

import astropy.units as u

from glue_solar.glue_patches import _application, layer_action
from glue_solar.lines import rest_wavelength
from glue_solar.quicklook import _wavelengths
from glue_solar.sources.loaders.iris import _RUNNING
from glue_solar.sources.loaders.lazy import at_ceiling
from glue_solar.sources.moments import _check, _cube, _dataset, _read, _start, _window

__all__ = ["line_fit_maps_iris"]


class _Canceled(Exception):
    pass


class _Progress:
    """
    The tasks done of the fits of ``scans`` scans, one dask graph alike each, for the progress dialog, and its Cancel:
    dask callbacks of each call, as dask swaps its global ones out while it computes, which glue's own reads would see.
    """

    def __init__(self, scans):
        self.scans, self.done, self.total, self.canceled, self.ended = scans, 0, 0, False, False
        self.callbacks = (None, self._start_state, None, self._posttask, None)  # dask's tuple of callbacks

    def _start_state(self, dsk, state):
        self.total = self.scans * sum(len(state[key]) for key in ("ready", "waiting", "running", "finished"))

    def _posttask(self, key, result, dsk, state, worker_id):
        self.done += 1
        if self.canceled:
            raise _Canceled

    def cancel(self):
        self.canceled = True


def _in_angstrom(model, x_unit):
    """
    ``model``, fitted against wavelengths in ``x_unit``, a length, against them in Angstrom, its bounds and the
    separations of its ties (`glue_solar.fitters._tie`) too.
    """
    from glue_solar.fitters import _tie

    shown, taken = (model.with_units_from_data(x=1 * u.Unit(unit), y=1 * u.one) for unit in (x_unit, u.AA))
    model = model.copy()
    for name in model.param_names:
        scale = getattr(shown, name).unit.to(getattr(taken, name).unit)  # 1 / x for a slope
        parameter = getattr(model, name)
        parameter.value = parameter.value * scale
        parameter.bounds = tuple(None if bound is None else bound * scale for bound in parameter.bounds)
        if args := getattr(parameter.tied, "args", None):
            other, factor, offset = args
            parameter.tied = _tie(other, factor, offset * scale)
    return model


def _last_fit(data, data_collection):
    """
    The model of the last IRIS fit of a spectrum of ``data`` in its Profile viewers (`glue_solar.fitters`), in
    Angstrom, the wavelength pixels within its range, the unit of the values it fits, whether they are DN / s, and the
    rest wavelength of ``data``; raises why for none, or for one the window cannot take.
    """
    from glue_solar.fitters import GaussianConstantFitter

    app = _application(data_collection)
    viewers = [viewer for tab in getattr(app, "viewers", ()) for viewer in tab if isinstance(viewer, ProfileViewer)]
    fits = [getattr(v.toolbar.tools["profile-analysis"]._profile_tools, "_iris_fits", {}).get(data) for v in viewers]
    fits = [model for model in fits if model is not None]
    if not fits:
        raise ValueError(
            f"{data.label} has no IRIS fit: fit one of its spectra with '{GaussianConstantFitter.label}' on the Fit tab "
            "of a Profile viewer first."
        )
    model = max(fits, key=lambda model: model.meta["fitted"])
    meta, last = model.meta, f"The last IRIS fit of {data.label}"
    if meta["function"] == "sum":
        raise ValueError(f"{last} is of the sum of its spectra, which scales its amplitudes: fit their Mean or Median.")
    cid = data.main_components[0]
    rate = f"{cid.label} DN / s"
    if meta["attribute"] not in (cid.label, rate):
        raise ValueError(f"{last} is of {meta['attribute']}: fit its values, in DN or DN / s.")
    try:
        scale = u.Unit(meta["x_unit"]).to(u.AA)
    except (TypeError, ValueError):
        raise ValueError(
            f"{last} is against {meta['x_unit'] or 'pixels'}: fit against its wavelength in a length, such as Angstrom."
        ) from None
    rest = rest_wavelength(data)
    if rest is None:
        raise ValueError(f"{data.label} has no rest wavelength: set one with 'IRIS: set rest wavelength…'.")
    low, high = np.multiply(meta["x_range"], scale)
    crop, unit = _window(data, (low, high), f"the range of the last IRIS fit, {low:.3f} to {high:.3f} Å")
    per_second = meta["attribute"] == rate
    if not per_second and data.find_component_id(rate) is not None:  # `_window`'s unit is that of DN / s
        unit = unit * u.s
    # shortcut: the y unit is the attribute's own, glue's only choice for IRIS data; convert as x where it has others
    return _in_angstrom(model, meta["x_unit"]), crop, unit, per_second, rest


def _starts(model, wavelengths, spectra):
    """
    ``model``, as fitted to one spectrum, with a start for each of ``spectra``, along their last axis at
    ``wavelengths``, as EISPAC's ``scale_guess`` (D86): a constant, linear or polynomial background at its 10th
    percentile at their mean, its shape kept, and each Gaussian or Lorentzian line's center and amplitude at its peak
    above it within two widths of the fitted center, among the samples nearer that center than any other line's, so
    that the lines of a blend start at their own peaks (as irispy draft LM-SAL/irispy#241), its width kept; fixed and
    tied parameters as fitted, the others within their bounds. It takes a model and arrays alone, to move to irispy.
    """
    from astropy.modeling import models

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)  # an all-NaN spectrum, which astropy leaves unfitted
        level = np.nanpercentile(spectra, 10, axis=-1)
    compound = model.n_submodels > 1
    leaves = [model[i] for i in range(model.n_submodels)] if compound else [model]
    lines = (models.Gaussian1D, models.Lorentz1D)
    centers = [leaf.parameters[1] for leaf in leaves if isinstance(leaf, lines)]
    starts = {}
    for index, leaf in enumerate(leaves):
        named = {name: name + (f"_{index}" if compound else "") for name in leaf.param_names}
        value = {name: getattr(model, full).value for name, full in named.items()}
        if isinstance(leaf, models.Const1D):
            starts[named["amplitude"]] = level
        elif isinstance(leaf, (models.Linear1D, models.Polynomial1D)):  # its constant term, the value at 0 Å
            constant = "intercept" if isinstance(leaf, models.Linear1D) else "c0"
            starts[named[constant]] = level - (leaf(wavelengths.mean()) - value[constant])
        elif isinstance(leaf, lines):
            amplitude, center, width = leaf.param_names
            sign = np.sign(value[amplitude]) or 1  # an emission or absorption line
            distance = np.abs(wavelengths - value[center])
            near = (distance <= 2 * value[width]) & np.all([distance <= np.abs(wavelengths - c) for c in centers], 0)
            excess = np.where(near, sign * (spectra - level[..., None]), np.nan)
            excess = np.where(np.isfinite(excess), excess, -np.inf)  # NaN, off the line or masked, is no peak
            peak = np.argmax(excess, axis=-1)
            height = np.take_along_axis(excess, peak[..., None], -1)[..., 0]
            found = np.isfinite(height)
            starts[named[center]] = np.where(found, wavelengths[peak], value[center])
            starts[named[amplitude]] = np.where(found, sign * height, value[amplitude])
    values = {}
    for name in model.param_names:
        value = getattr(model, name).value
        if name in starts and not (model.fixed[name] or model.tied[name]):
            lower, upper = model.bounds[name]
            value = np.clip(starts[name], -np.inf if lower is None else lower, np.inf if upper is None else upper)
        values[name] = np.broadcast_to(value, level.shape)
    seeded = model.copy()
    seeded._reset_parameters(**values)  # how astropy's parallel fitting makes a model of a start per spectrum
    return seeded


def _fit_maps(data, model, crop, unit, per_second, rest, progress):
    """
    ``model`` fitted from `_starts` to every spectrum of ``data`` at ``crop``, in ``unit``, a scan at a time, on dask's
    processes, and irispy's ``maps_from_fit`` of it about ``rest``: a dataset of every map but the residual, with
    ``<name> error`` where irispy gives one, or None once ``progress`` is canceled; on any thread.
    """
    import dask.multiprocessing
    from irispy.utils.fitting import maps_from_fit

    from astropy.modeling.fitting import TRFLSQFitter, parallel_fit_dask

    from glue_solar.fitters import _jacobian

    cid = data.main_components[0]
    wavelengths = _wavelengths(data)[0][crop]
    # processes, as the fits on threads hold the GIL, slower than on one; one pool a run, as one takes 1.4 s to start
    pool = ProcessPoolExecutor(mp_context=dask.multiprocessing.get_context())
    scheduler = partial(dask.multiprocessing.get, callbacks=[progress.callbacks], pool=pool)
    maps = {}
    try:
        for scan in np.ndindex(data.shape[:-3]):
            rows = (*scan, slice(None), slice(None))
            if per_second:
                values, _, saturated = _read(data, rows, crop)
            else:
                values = data[cid, (*rows, crop)]
                saturated = at_ceiling(values)
            cube = _cube(data, values, rows, crop, unit, saturated)
            # masked samples, missing or saturated, a lower bound only (D87), left out as NaN by filter_non_finite
            spectra = np.where(cube.mask, np.nan, values)
            fitter = TRFLSQFitter(calc_uncertainties=True)
            fitted = parallel_fit_dask(
                model=_starts(model, wavelengths, spectra),
                fitter=fitter,
                data=spectra,
                data_unit=unit,
                fitting_axes=2,
                world=(wavelengths * u.AA,),
                fit_info=True,  # irispy's errors and quality need its param_cov and success
                scheduler=scheduler,
                fitter_kwargs={"filter_non_finite": True, **_jacobian(model)},
            )
            # each wcslib call irispy makes holds WCS_LOCK for itself (`_GlueWCS`)
            for name, part in maps_from_fit(fitted, cube, fitter=fitter, rest_wavelength=rest * u.AA).items():
                if name != "residual":  # a cube, not a map
                    maps.setdefault(name, []).append(part)
    except _Canceled:
        return None
    finally:
        pool.shutdown(cancel_futures=True)
        progress.ended = True
    if progress.canceled:
        return None
    fit = _dataset(data, f"{data.label} fit {rest}")
    fit.meta.update(fit_rest_wavelength=rest, fit_range=(float(wavelengths[0]), float(wavelengths[-1])))
    # each line's maps first, as glue shows a dataset's first, then irispy's quality, then the parameters
    for name in sorted(maps, key=lambda name: name in model.param_names):
        parts = maps[name]
        units = str(parts[0].unit)
        fit.add_component(Component(np.reshape([part.data for part in parts], data.shape[:-1]), units=units), name)
        if parts[0].uncertainty is not None:
            errors = np.reshape([part.uncertainty.array for part in parts], data.shape[:-1])
            fit.add_component(Component(errors, units=units), f"{name} error")
    return fit


def _shown(dialog, progress):
    """Show ``progress`` on ``dialog`` until its run ends."""
    if progress.ended:
        dialog.deleteLater()
    elif progress.total and not dialog.wasCanceled():
        dialog.setMaximum(progress.total)
        dialog.setValue(progress.done)


def _check_fit(data):
    """Raise why ``data`` is not an IRIS raster window or stack, or has its line fit maps being computed."""
    _check(data)
    if any(worker.func is _fit_maps and worker.args[0] is data for worker in _RUNNING):  # a pool each
        raise ValueError(f"The line fit maps of {data.label} are being computed.")


@layer_action(
    "IRIS: line fit maps",
    single=True,
    data=True,
    check=_check_fit,
    tooltip="Fit the last IRIS fit on a Profile viewer's Fit tab to every spectrum of this raster window or stack",
)
@messagebox_on_error("Could not fit the line maps")
def line_fit_maps_iris(data, data_collection):
    """
    Add `_fit_maps` of ``data`` and `_last_fit`, fitted in the background (`_start`) while a progress dialog shows the
    tasks done, its Cancel stopping the run.
    """
    _check_fit(data)
    model, crop, unit, per_second, rest = _last_fit(data, data_collection)
    progress = _Progress(int(np.prod(data.shape[:-3])))
    text = f"Fitting every spectrum of {data.label}…"
    dialog = QtWidgets.QProgressDialog(text, "Cancel", 0, 0, _application(data_collection))
    dialog.canceled.connect(progress.cancel)
    timer = QtCore.QTimer(dialog, interval=100)
    timer.timeout.connect(partial(_shown, dialog, progress))
    timer.start()
    dialog.show()  # at once
    title = "Could not fit the line maps"
    _start(data_collection, text, title, _fit_maps, data, model, crop, unit, per_second, rest, progress, view=True)
