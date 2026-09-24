"""Proposed glue_solar/sources/fitting.py (WP6). Per-pixel Gaussian fit maps of IRIS raster windows."""

import traceback

import numpy as np
from glue.core.component import Component
from glue.core.data import Data
from glue.core.link_helpers import LinkSame
from glue_qt.config import layer_action
from glue_qt.utils.threading import Worker
from qtpy import QtWidgets

import astropy.units as u
from astropy.modeling import models
from astropy.modeling.fitting import LMLSQFitter, parallel_fit_dask
from astropy.wcs.wcsapi import SlicedLowLevelWCS
from glue_solar.sources.loaders.iris import _GlueWCS

__all__ = ["fit_gaussians", "gaussian_fit_data", "start_fit", "wavelength_angstrom"]

SIGMA_SEED = {1: 0.05, 2: 0.08}  # Angstrom; irispy gallery 01 (0.005 nm) and 07 (0.008 nm)
SPLIT_SEED = 0.15  # Angstrom; half the k2v/k2r seed separation of gallery 07 (279.621 / 279.650 nm)
_WORKERS = []  # keep running fits alive (a Worker that is garbage collected mid-run crashes Qt)


def wavelength_angstrom(data):
    """Wavelength of every spectral pixel (the last pixel axis of a glue-solar raster dataset) in Angstrom."""
    coords = data.coords
    if getattr(coords, "world_axis_physical_types", [None])[0] != "em.wl":
        raise ValueError(f"{data.label} is not an IRIS spectrogram (no wavelength axis)")
    # pixel_to_world_values takes pixel axes in Cartesian order: the wavelength index goes FIRST
    wavelength = coords.pixel_to_world_values(np.arange(data.shape[-1]), *([0] * (data.ndim - 1)))[0]
    return (np.asarray(wavelength, dtype=float) * u.Unit(coords.world_axis_units[0])).to_value(u.AA)


def fit_gaussians(cube, wavelength, n_gaussians=1, rest=None, scheduler="processes"):
    """
    Fit a constant background plus ``n_gaussians`` Gaussians to every spectrum of ``cube``.

    Parameters
    ----------
    cube : array-like
        Spectra along the last axis; NaN and negative values are set to zero (irispy gallery recipe).
    wavelength : array-like
        Wavelength of each spectral pixel in Angstrom.
    n_gaussians : {1, 2}
    rest : float, optional
        Rest wavelength in Angstrom. Seeds the line centre when it lies inside the window; otherwise
        (cropped windows, unknown line) the peak of the spatially averaged spectrum seeds it.
    scheduler : str
        dask scheduler. ``"processes"`` for real rasters; ``"single-threaded"`` in tests.

    Returns
    -------
    fit : compound astropy model
        Parameters ``amplitude_0`` (background), ``amplitude_i``, ``mean_i``, ``stddev_i`` for
        ``i`` in 1..n are arrays of shape ``cube.shape[:-1]``, NaN where the fit failed.
    residual : `numpy.ndarray`
        ``cube - fit``, same shape as ``cube``.
    """
    cube = np.nan_to_num(np.asarray(cube, dtype=float).clip(min=0))
    wavelength = np.asarray(wavelength, dtype=float)
    mean = cube.mean(axis=tuple(range(cube.ndim - 1)))
    background = np.percentile(mean, 10)
    if rest is not None and wavelength.min() < rest < wavelength.max():
        centres = [rest] if n_gaussians == 1 else [rest - SPLIT_SEED, rest + SPLIT_SEED]  # gallery 07 recipe
    elif n_gaussians == 1:
        centres = [wavelength[mean.argmax()]]
    else:  # the two highest interior local maxima of the mean spectrum (k2v, k2r), blue first
        peaks = np.flatnonzero((mean[1:-1] > mean[:-2]) & (mean[1:-1] >= mean[2:])) + 1
        peaks = np.sort(peaks[np.argsort(mean[peaks])[-2:]])
        centres = (
            wavelength[peaks] if len(peaks) == 2 else wavelength[mean.argmax()] + np.array([-SPLIT_SEED, SPLIT_SEED])
        )
    model = models.Const1D(amplitude=background)
    for centre in centres:
        model += models.Gaussian1D(amplitude=mean.max() - background, mean=centre, stddev=SIGMA_SEED[n_gaussians])
    # ponytail: no TRF prefit on the mean spectrum (gallery step); it degenerates on cropped windows
    # and made the per-pixel fit 1.8x slower on the bundled sns raster with no NaN gain.
    fit = parallel_fit_dask(
        data=cube,
        fitting_axes=cube.ndim - 1,
        world=(wavelength,),
        model=model,
        fitter=LMLSQFitter(),
        scheduler=scheduler,
    )
    model_cube = fit(wavelength.reshape((-1,) + (1,) * (cube.ndim - 1)))  # (nwl, *spatial)
    return fit, cube - np.moveaxis(model_cube, 0, -1)


def gaussian_fit_data(data, n_gaussians=1, rest=None, scheduler="processes"):
    """
    Fit the raster dataset ``data`` and return ``(maps, residual)``.

    ``maps`` is a new dataset on the spatial pixel grid of ``data`` (its WCS with the wavelength axis
    sliced away) with one component per fitted parameter; ``residual`` is the data-minus-model cube.
    """
    cid = data.main_components[0]
    units = data.get_component(cid).units
    fit, residual = fit_gaussians(data[cid], wavelength_angstrom(data), n_gaussians, rest, scheduler)
    maps = Data(label=f"{data.label}-gauss{n_gaussians}")
    raw_wcs = data.coords._wcs if isinstance(data.coords, _GlueWCS) else data.coords
    maps.coords = _GlueWCS(SlicedLowLevelWCS(raw_wcs, (slice(None),) * (data.ndim - 1) + (0,)))
    maps.meta = {"source": data.label, "n_gaussians": n_gaussians, "rest_wavelength_angstrom": rest}
    maps.add_component(Component(fit.amplitude_0.value, units=units), "background")
    for i in range(1, n_gaussians + 1):
        suffix = f" {i}" if n_gaussians > 1 else ""
        maps.add_component(Component(getattr(fit, f"amplitude_{i}").value, units=units), f"amplitude{suffix}")
        maps.add_component(Component(getattr(fit, f"mean_{i}").value, units="Angstrom"), f"centroid{suffix}")
        maps.add_component(Component(getattr(fit, f"stddev_{i}").value, units="Angstrom"), f"width{suffix}")
    if data.find_component_id("Time") is not None:  # per-exposure time of each spatial pixel (sit-and-stare: axis 0)
        maps.add_component(data["Time"][..., 0], "Time")
    return maps, residual


def add_fit_products(data, data_collection, maps, residual):
    """Add ``maps`` to the collection, pixel-link it to ``data`` and attach the residual cube to ``data``."""
    data_collection.append(maps)
    for source_pixel, map_pixel in zip(data.pixel_component_ids, maps.pixel_component_ids):  # drops wavelength
        data_collection.add_link(LinkSame(source_pixel, map_pixel))
    units = data.get_component(data.main_components[0]).units
    data.add_component(Component(residual, units=units), f"{maps.label} residual")


def _ask(data):
    """Model choice and optional line centre; returns ``(n_gaussians, rest)`` or None when cancelled."""
    dialog = QtWidgets.QDialog()
    dialog.setWindowTitle(f"Gaussian fit of {data.label}")
    form = QtWidgets.QFormLayout(dialog)
    model = QtWidgets.QComboBox()
    model.addItems(["1 Gaussian + background", "2 Gaussians + background (Mg II k2v/k2r)"])
    form.addRow("Model", model)
    # no prefill (TWAVE is the window's nominal wavelength, not the line core; seeding from it was worse
    # than the data-driven seed on the gallery raster): blank means seed from the mean spectrum
    centre = QtWidgets.QLineEdit()
    centre.setPlaceholderText("blank: strongest peak(s) of the mean spectrum")
    form.addRow("Line centre (Å)", centre)
    buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    form.addRow(buttons)
    if dialog.exec() != QtWidgets.QDialog.Accepted:
        return None
    text = centre.text().strip()
    return model.currentIndex() + 1, float(text) if text else None


def start_fit(data, data_collection, n_gaussians=1, rest=None, scheduler="processes"):
    """Run the fit in a background thread; the products are added when it finishes. Returns the Worker."""
    progress = QtWidgets.QProgressDialog(f"Fitting {n_gaussians} Gaussian(s) to {data.label}…", None, 0, 0)
    progress.setWindowTitle("Gaussian fit")
    progress.show()
    worker = Worker(gaussian_fit_data, data, n_gaussians, rest, scheduler)
    worker.progress = progress  # the parentless dialog is Python-owned: without a reference it is deleted on return
    worker.result.connect(lambda result: add_fit_products(data, data_collection, *result))
    worker.error.connect(
        lambda info: QtWidgets.QMessageBox.critical(
            None, "Gaussian fit failed", "".join(traceback.format_exception(*info))
        )
    )
    worker.finished.connect(progress.close)
    worker.finished.connect(lambda: _WORKERS.remove(worker))
    _WORKERS.append(worker)
    worker.start()
    return worker


@layer_action("IRIS: Gaussian fit maps…", single=True, data=True)
def fit_gaussians_action(data, data_collection):
    """Right-click action on a raster dataset: fit every spectrum and add the parameter maps."""
    try:
        wavelength_angstrom(data)
    except ValueError as error:
        QtWidgets.QMessageBox.warning(None, "Gaussian fit", str(error))
        return
    choice = _ask(data)
    if choice is not None:
        start_fit(data, data_collection, *choice)
