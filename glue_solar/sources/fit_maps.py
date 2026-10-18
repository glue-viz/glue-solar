"""
'Fit every spectrum' on the Fit tab of glue's Profile viewer: the viewer's last IRIS fit of a spectrum of a raster
window fitted to every spectrum of the window, or of each scan of a stack (D59), with astropy's ``parallel_fit_dask``,
as irispy's ``maps_from_fit`` maps in one new dataset (D86, D88).
"""

import math
from concurrent.futures import ProcessPoolExecutor
from functools import partial

import numpy as np
from glue.core.component import Component
from glue_qt.utils.decorators import messagebox_on_error
from glue_qt.viewers.profile.profile_tools import ProfileTools
from qtpy import QtCore, QtWidgets

import astropy.units as u
from astropy import constants

from glue_solar.glue_patches import _application
from glue_solar.lines import DopplerConverter, rest_wavelength
from glue_solar.quicklook import _wavelengths
from glue_solar.sources.loaders.iris import _RUNNING
from glue_solar.sources.loaders.lazy import at_ceiling
from glue_solar.sources.moments import _check, _cube, _dataset, _read, _start, _window

__all__ = []


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


def _to_angstrom(x_unit, rest):
    """
    The ``scale`` and ``shift`` of λ = scale x + shift, in Angstrom, for x in ``x_unit``: a length, or a velocity, the
    optical Doppler from ``rest`` of `glue_solar.lines.DopplerConverter`, λ = rest (1 + x / c); raises a TypeError or
    ValueError for any other x, such as pixels.
    """
    unit = u.Unit(x_unit)
    if unit.is_equivalent(u.AA):
        return unit.to(u.AA), 0
    return rest / constants.c.to_value(unit), rest


def _in_angstrom(model, scale, shift):
    """
    ``model``, fitted against x, against λ = scale x + shift in Angstrom (`_to_angstrom`), exactly, as the map is
    linear (D88): each line's center at scale x + shift and its width times scale, their bounds and the separations of
    their ties (`glue_solar.fitters._tie`) alike, and a linear or polynomial background re-expressed in λ, its terms'
    bounds scaled for a length; raises why for such a background with a bound or a fixed term against a velocity,
    which mixes its terms.
    """
    from astropy.modeling import models

    from glue_solar.fitters import _LINES, _leaves, _tie

    model, compound = model.copy(), model.n_submodels > 1
    for index, leaf in enumerate(_leaves(model)):
        parameters = [getattr(model, name + (f"_{index}" if compound else "")) for name in leaf.param_names]
        if isinstance(leaf, _LINES):
            _, center, width = parameters
            for parameter, offset in ((center, shift), (width, 0)):
                parameter.value = parameter.value * scale + offset
                parameter.bounds = tuple(
                    None if bound is None else bound * scale + offset for bound in parameter.bounds
                )
                if args := getattr(parameter.tied, "args", None):
                    other, factor, separation = args
                    parameter.tied = _tie(other, factor, separation * scale + (1 - factor) * offset)
        elif not isinstance(leaf, models.Const1D):  # p(x) = p(a λ + b), its terms constant first
            terms = parameters[::-1] if isinstance(leaf, models.Linear1D) else parameters
            if shift and any(term.fixed or term.bounds != (None, None) for term in terms):
                raise ValueError(
                    "A linear or polynomial background with a bound or a fixed term takes a fit against a length, "
                    "such as Angstrom: against km / s, each of its terms in Angstrom combines all of them."
                )
            a, b, values = 1 / scale, -shift / scale, [term.value for term in terms]
            for j, term in enumerate(terms):
                term.value = sum(values[i] * math.comb(i, j) * a**j * b ** (i - j) for i in range(j, len(terms)))
                term.bounds = tuple(None if bound is None else bound * a**j for bound in term.bounds)
    return model


def _viewer_fit(tools):
    """
    The data of the last IRIS fit on ``tools``, a Profile viewer's Fit tab (`glue_solar.fitters._fit`), of data in its
    collection, and the fit's model; raises why for none, or for data that is not an IRIS raster window or stack.
    """
    from glue_solar.fitters import GaussianConstantFitter

    collection = tools.viewer.session.data_collection
    fits = [(data, model) for data, model in vars(tools).get("_iris_fits", {}).items() if data in collection]
    if not fits:
        raise ValueError(
            f"This viewer has no IRIS fit: fit a spectrum of a raster window with '{GaussianConstantFitter.label}' "
            "first."
        )
    data, model = max(fits, key=lambda fit: fit[1].meta["fitted"])
    _check(data)
    return data, model


def _last_fit(data, model):
    """
    ``model``, the last IRIS fit of a spectrum of ``data`` (`_viewer_fit`), in Angstrom, the wavelength pixels within
    its range, the unit of the values it fits, whether they are DN / s, and the rest wavelength of ``data``; raises why
    for one the window cannot take.
    """
    meta, last = model.meta, f"The last IRIS fit of {data.label}"
    if meta["function"] == "sum":
        raise ValueError(f"{last} is of the sum of its spectra, which scales its amplitudes: fit their Mean or Median.")
    cid = data.main_components[0]
    rate = f"{cid.label} DN / s"
    if meta["attribute"] not in (cid.label, rate):
        raise ValueError(f"{last} is of {meta['attribute']}: fit its values, in DN or DN / s.")
    if meta["rest_wavelength"] is None and meta["x_unit"] == DopplerConverter.VELOCITY:
        raise ValueError(
            f"{last} is against {meta['x_unit']} from the viewer's reference data: make {data.label} the reference "
            "data and fit again."
        )
    try:
        scale, shift = _to_angstrom(meta["x_unit"], meta["rest_wavelength"])
    except (TypeError, ValueError):
        raise ValueError(
            f"{last} is against {meta['x_unit'] or 'pixels'}: fit against its wavelength, in a length such as "
            "Angstrom or in km / s."
        ) from None
    model = _in_angstrom(model, scale, shift)
    rest = rest_wavelength(data)
    if rest is None:
        raise ValueError(f"{data.label} has no rest wavelength: set one with 'IRIS: set rest wavelength…'.")
    low, high = np.multiply(meta["x_range"], scale) + shift
    crop, unit = _window(data, (low, high), f"the range of the last IRIS fit, {low:.3f} to {high:.3f} Å")
    per_second = meta["attribute"] == rate
    if not per_second and data.find_component_id(rate) is not None:  # `_window`'s unit is that of DN / s
        unit = unit * u.s
    # shortcut: the y unit is the attribute's own, glue's only choice for IRIS data; convert as x where it has others
    return model, crop, unit, per_second, rest


def _fit_maps(data, model, crop, unit, per_second, rest, progress):
    """
    ``model`` fitted from irispy's ``starts_from_model`` to every spectrum of ``data`` at ``crop``, in ``unit``, a scan
    at a time, on dask's processes, and irispy's ``maps_from_fit`` of it about ``rest``: a dataset of every map but the
    residual, with ``<name> error`` where irispy gives one, or None once ``progress`` is canceled; on any thread.
    """
    import dask.multiprocessing
    from irispy.utils.fitting import maps_from_fit, starts_from_model

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
                model=starts_from_model(model, cube),  # in Angstrom and unit, as `_last_fit` gives it (D86)
                fitter=fitter,
                data=spectra,
                data_unit=unit,
                fitting_axes=2,
                world=(wavelengths * u.AA,),
                fit_info=("param_cov", "success"),  # irispy's errors and quality; all of it, a C II window took 6.5 GB
                scheduler=scheduler,
                fitter_kwargs={"filter_non_finite": True, **_jacobian(model)},
            )
            # plain dicts: astropy's FitInfoSubset raises KeyError in FitInfoArrayContainer's hasattr (report candidate)
            infos = fitter.fit_info._fit_info_array
            for index in np.ndindex(infos.shape):
                if isinstance(infos[index], dict):
                    infos[index] = dict(infos[index])
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


def _check_running(data):
    """Raise why ``data`` has its line fit maps being computed: one run a dataset, each with its process pool."""
    if any(worker.func is _fit_maps and worker.args[0] is data for worker in _RUNNING):
        raise ValueError(f"The line fit maps of {data.label} are being computed.")


@messagebox_on_error("Could not fit the line maps")
def _fit_every_spectrum(tools, *_):
    """
    Add `_fit_maps` of the last IRIS fit on ``tools`` (`_viewer_fit`), fitted in the background (`_start`) while a
    progress dialog shows the tasks done, its Cancel stopping the run.
    """
    data, model = _viewer_fit(tools)
    _check_running(data)
    model, crop, unit, per_second, rest = _last_fit(data, model)
    data_collection = tools.viewer.session.data_collection
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


def _refresh(tools):
    """'Fit every spectrum' on ``tools``, enabled where `_viewer_fit` takes the viewer's fit, else saying why."""
    try:
        data, _ = _viewer_fit(tools)
        enabled, tip = True, f"Fit every spectrum of {data.label} with this viewer's last IRIS fit"
    except ValueError as exc:
        enabled, tip = False, str(exc)
    tools.button_fit_every.setEnabled(enabled)
    tools.button_fit_every.setToolTip(tip)


_original_enable = ProfileTools.enable


def _enable(self):
    """glue-qt's Fit tab, with 'Fit every spectrum' beside Fit, as glue-qt has no hook for a fitter's actions (D88)."""
    _original_enable(self)
    button = self.button_fit_every = QtWidgets.QToolButton(text="Fit every spectrum")
    button.clicked.connect(partial(_fit_every_spectrum, self))
    row = next(row for row in self.ui.findChildren(QtWidgets.QHBoxLayout) if row.indexOf(self.ui.button_fit) >= 0)
    row.insertWidget(row.indexOf(self.ui.button_fit) + 1, button)
    _refresh(self)


_original_report_fit = ProfileTools._report_fit


def _report_fit(self, report):
    """glue-qt's report of a fit, on the main thread once it ends, then 'Fit every spectrum' following it."""
    _original_report_fit(self, report)
    _refresh(self)


ProfileTools.enable = _enable
ProfileTools._report_fit = _report_fit
