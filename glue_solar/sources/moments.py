"""
'IRIS: line moments…': irispy's moment maps of a line in a raster window, as a new dataset; and 'IRIS: subtract mean
spectrum': a raster window's values less its mean spectrum, as a glue derived component.
"""

import gc
from functools import partial

import numpy as np
from glue.config import layer_action
from glue.core.component import Component
from glue.core.data import Data
from glue_qt.utils.decorators import messagebox_on_error
from glue_qt.utils.threading import Worker
from qtpy import QtWidgets

import astropy.units as u
from astropy.wcs.wcsapi.wrappers import SlicedLowLevelWCS

from glue_solar.quicklook import _role, _spectral_axes, _wavelengths
from glue_solar.sources.loaders.iris import _RUNNING, WCS_LOCK, _GlueWCS, keep_hpc_linked, per_second

__all__ = ["line_moments", "mean_spectrum_iris", "moments_iris", "subtract_mean_spectrum"]

# The wavelengths the dialog takes at first, in Angstrom below and above the line centre
WINGS = (0.5, 0.5)
# Samples per irispy call, which copies its input about seven times as float64, and per read of a mean spectrum
SLAB = 2**21
# irispy picks the wavelengths within the wings again, rounding its own way: a crop wider by this many Angstrom keeps
# every one it picks
_HAIR = 1e-6


def _check(data, what="line moments"):
    """Raise why ``data`` is not an IRIS raster window of one scan, (raster step, slit, wavelength), for ``what``."""
    if _role(data) == "raster" and data.ndim == 4:
        raise ValueError(
            f"{data.label} is a stack of raster scans: {what} take one scan, as the observation "
            "browser loads them without 'Stack sequential raster scans'."
        )
    if _role(data) != "raster" or data.ndim != 3 or _spectral_axes(data) != {2}:
        raise ValueError(f"{data.label} is not an IRIS raster window.")


def _window(data, centre, wings, continuum=None):
    """
    The wavelength pixels of ``data`` from the first to the last within ``wings`` of ``centre`` or a ``continuum``
    window, those within the wings, both `_HAIR` wider, and the unit of the values irispy is given (`_read`); raises
    why for data that has none within the wings, or a continuum window that overlaps them or has none.
    """
    _check(data)
    wavelengths, _ = _wavelengths(data)
    span = f"{data.label} ({wavelengths[0]:.2f} to {wavelengths[-1]:.2f} Å)"
    lines = f"{wings[0]} Å below and {wings[1]} Å above {centre} Å"

    def within(low, high):
        return np.flatnonzero((wavelengths >= low - _HAIR) & (wavelengths <= high + _HAIR))

    inside = within(centre - wings[0], centre + wings[1])
    if not inside.size:
        raise ValueError(f"No wavelength of {span} lies within {lines}.")
    ends = [inside[0], inside[-1]]
    for low, high in continuum or ():
        if low <= centre + wings[1] and high >= centre - wings[0]:
            raise ValueError(f"The continuum window {low}-{high} Å overlaps the wings, {lines}.")
        window = within(low, high)
        if not window.size:
            raise ValueError(f"No wavelength of {span} lies within the continuum window {low}-{high} Å.")
        ends += [window[0], window[-1]]
    return slice(min(ends), max(ends) + 1), slice(inside[0], inside[-1] + 1), _unit(data)


def _unit(data):
    """The unit of the values of ``data`` that irispy is given (`_read`)."""
    from irispy.utils.constants import DN_UNIT  # with the first use rather than at glue's launch

    cid = data.main_components[0]
    with u.add_enabled_units(DN_UNIT.values()):  # astropy's registry, global: on the calling thread
        unit = u.Unit(data.get_component(cid).units)
    if data.find_component_id(f"{cid.label} DN/s") is not None:
        unit = unit / u.s
    return unit


def _read(data, rows, wavelengths):
    """
    The values of ``data`` at ``rows`` and ``wavelengths`` that irispy is given, and each step's exposure time in s:
    of a window with the loader's ``<label> DN/s``, its DN over each step's exposure time (D4), from the DN read here,
    in float64, else its scaled float32 and None; NaN where missing, on any thread.
    """
    cid = data.main_components[0]
    values = data[cid, (*rows, wavelengths)]  # scaled float32 of these steps and wavelengths only, NaN where missing
    if data.find_component_id(f"{cid.label} DN/s") is None:
        return values, None
    # glue's derived component reads them again; irispy's limit is 16182 DN over the exposure times given it, in
    # float64: in float32, as the loader's, a sample at 16182 DN can round below it
    seconds = data["Exposure time", (rows[0], slice(0, 1), slice(0, 1))].astype(np.float32)
    return per_second(values.astype(float), seconds), seconds


def _cube(data, values, rows, wavelengths, unit, meta=None):
    """irispy's cube of ``values`` in ``unit``, of ``data`` at ``rows`` and ``wavelengths``, NaN and -Inf masked."""
    from irispy.spectrograph import SpectrogramCube

    view = SlicedLowLevelWCS(data.coords._wcs, (*rows, wavelengths))
    return SpectrogramCube(values, view, unit=unit, mask=np.isnan(values) | np.isneginf(values), meta=meta)


def _dataset(data, label):
    """A new dataset ``label`` on the raster steps and slit pixels of ``data``, with its observation's meta."""
    maps = Data(label=label)
    with WCS_LOCK:
        # the raster's own steps and slit pixels: its wavelength does not move them
        maps.coords = _GlueWCS(SlicedLowLevelWCS(data.coords._wcs, (slice(None), slice(None), 0)))
    # the observation's, for the quicklook's grouping and transparent NaN, without INSTRUME, which makes a raster
    maps.meta = {key: data.meta[key] for key in ("OBSID", "STARTOBS") if key in data.meta}
    return maps


def _moments(data, centre, wings, continuum, crop, inner, unit):
    """
    `line_moments` given ``crop`` of the wavelength pixels, ``inner`` those within the wings, and ``unit`` the unit of
    the values irispy is given; on any thread.
    """
    from irispy.utils.constants import SATURATION_LIMIT
    from irispy.utils.moments import calculate_moments
    from irispy.utils.spectrograph import subtract_background
    from ndcube.meta import NDMeta

    maps, saturated = {}, 0
    # a slab takes about 100 bytes per sample, 150 with a continuum: half the steps then, generously, keeps a small
    # window's cold peak under 3x
    steps = max(1, SLAB // (data.shape[1] * (crop.stop - crop.start) * (2 if continuum else 1)))
    degree = 1 if len(continuum or ()) > 1 else 0  # a constant for one continuum window, a straight line for more
    inside = slice(inner.start - crop.start, inner.stop - crop.start)  # inner, within the crop
    for start in range(0, data.shape[0], steps):
        rows = (slice(start, start + steps), slice(None))
        values, seconds = _read(data, rows, crop)
        meta = NDMeta()
        if seconds is not None:
            meta.add("exposure time", seconds.ravel() * u.s, None, 0)
        with WCS_LOCK:  # irispy reads the wavelengths through the raster's astropy WCS
            # saturated within the wings, before any background is subtracted: NaN in every map
            slab = calculate_moments(
                _cube(data, values[..., inside], rows, inner, unit, meta),
                rest_wavelength=centre * u.AA,
                wings=wings * u.AA,
                saturation_limit=SATURATION_LIMIT,
            )
            reached = slab.pop("saturated").data
            if continuum:  # the moments of the line less the background, in which irispy would miss saturation
                values = subtract_background(
                    _cube(data, values, rows, crop, unit), continuum * u.AA, degree=degree
                ).data
                # NaN where irispy fits no background: missing at every wavelength within the wings, NaN maps
                slab = calculate_moments(
                    _cube(data, values[..., inside], rows, inner, unit),
                    rest_wavelength=centre * u.AA,
                    wings=wings * u.AA,
                )
        saturated += int(reached.sum())
        for name, moment in slab.items():
            # irispy sums masked samples, NaN and -Inf, as 0, and masks a pixel masked at every wavelength: NaN there (D17)
            maps.setdefault(name, []).append((np.where(moment.mask | reached, np.nan, moment.data), moment.unit))
        # ndcube's cubes are reference cycles, and irispy's hold the slab's values: else every slab's stay until
        # Python's collector runs
        gc.collect(0)
    moments = _dataset(data, f"{data.label} moments {centre}")
    moments.meta.update(moments_centre=centre, moments_wings=tuple(wings))
    if continuum:
        moments.meta.update(moments_continuum=tuple(map(tuple, continuum)), moments_continuum_degree=degree)
    if saturated:  # for the status bar and scripts; maps without keep the meta they had
        moments.meta["moments_saturated"] = saturated
    for name, parts in maps.items():
        values, unit = np.concatenate([values for values, _ in parts]), parts[0][1]
        if unit.is_equivalent(u.AA):  # irispy's centroid and width are in nm
            values, unit = unit.to(u.AA, values), u.AA
        moments.add_component(Component(values, units=str(unit)), name)
    return moments


def line_moments(data, centre, wings=WINGS, continuum=None):
    """
    irispy's moments of a line in ``data``, an IRIS raster window of one scan, about ``centre`` within ``wings``, as
    one dataset on the window's raster steps and slit pixels; with ``continuum`` windows, of the line less irispy's
    background fitted to them: a constant to one window, a straight line to more.

    irispy is given the window's ``<label> DN/s`` where it has one, else its values, with NaN and -Inf masked. Its
    components are irispy's: ``intensity`` in that unit, ``centroid`` and ``width`` in Angstrom, and ``velocity`` and
    ``velocity_width`` in km / s, relative to ``centre``; all are NaN where every sample within the wings is missing,
    no background could be fitted, or irispy finds a sample within the wings saturated: at or above its
    ``SATURATION_LIMIT``, 16182 DN, before any background is subtracted. ``meta`` holds the observation's ``OBSID`` and
    ``STARTOBS``, ``moments_centre`` and ``moments_wings``, with a continuum ``moments_continuum`` and
    ``moments_continuum_degree``, the degree of the background, and with saturated pixels ``moments_saturated``, how
    many. irispy is given only the wavelengths from the first to the last within the wings or a continuum
    window, a slab of steps at a time.

    Parameters
    ----------
    data : `~glue.core.data.Data`
        An IRIS raster window of one scan, (raster step, slit, wavelength).
    centre : float
        The line centre, in Angstrom.
    wings : tuple of float
        The wavelengths taken, in Angstrom below and above ``centre``.
    continuum : sequence of tuple of float, optional
        The ``(lower, upper)`` wavelengths of each continuum window, in Angstrom, ends included, outside the wings.

    Raises
    ------
    ValueError
        For other data than an IRIS raster window of one scan, one with no wavelength within the wings, or a
        continuum window with none or overlapping the wings.
    """
    return _moments(data, centre, wings, continuum, *_window(data, centre, wings, continuum))


def _accepted(dialog, form):
    """Add OK and Cancel to ``form``, run ``dialog`` and say whether OK was pressed."""
    buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    form.addRow(buttons)
    accepted = dialog.exec() == QtWidgets.QDialog.Accepted
    dialog.deleteLater()  # else each run keeps a hidden dialog under the main window
    return accepted


def _wavelength(text):
    """``text``, typed in Angstrom, as a float."""
    try:
        return float(text)
    except ValueError:
        raise ValueError(f"'{text}' is not a wavelength in Angstrom, such as 1402.77.") from None


def _ask(data):
    """
    The line centre typed for ``data``, the wings below and above it, and the continuum windows, or None for none, in
    Angstrom; or None for a blank centre or Cancel.
    """
    dialog = QtWidgets.QDialog(QtWidgets.QApplication.activeWindow())
    dialog.setWindowTitle(f"IRIS: line moments of {data.label}")
    form = QtWidgets.QFormLayout(dialog)
    centre = QtWidgets.QLineEdit(objectName="centre")  # D24: typed, never the window's TWAVE
    form.addRow("Line centre [Å]:", centre)
    wings = []
    for side, wing in zip(("below", "above"), WINGS):
        box = QtWidgets.QDoubleSpinBox(objectName=side, decimals=3, singleStep=0.1, value=wing, suffix=" Å")
        form.addRow(f"Wing {side} the centre:", box)
        wings.append(box)
    continuum = QtWidgets.QLineEdit(objectName="continuum", placeholderText="none, or such as 1401.5-1402, 1404-1405")
    form.addRow("Continuum windows [Å]:", continuum)
    text = centre.text().strip() if _accepted(dialog, form) else ""
    if not text:
        return None
    line = _wavelength(text), tuple(box.value() for box in wings)
    text = continuum.text().strip()
    if not text:
        return *line, None
    try:
        return *line, [
            tuple(sorted((float(low), float(high)))) for low, high in (part.split("-") for part in text.split(","))
        ]
    except ValueError:
        raise ValueError(
            f"'{text}' is not a list of continuum windows in Angstrom, such as 1401.5-1402, 1404-1405."
        ) from None


@messagebox_on_error("Could not compute line moments")
def _failed(exc_info):
    raise exc_info[1]


def _add(data_collection, status, moments):
    data_collection.append(moments)
    keep_hpc_linked(data_collection)
    count = moments.meta.get("moments_saturated")
    if count and status is not None:  # in place of what it says while they are computed
        pixels = f"{count} pixels" if count > 1 else "1 pixel"
        status.showMessage(f"{moments.label}: {pixels} saturated within the wings {'are' if count > 1 else 'is'} NaN")


def _status_bar(data_collection):
    """The status bar of the glue window of ``data_collection``, or None."""
    windows = QtWidgets.QApplication.topLevelWidgets()
    app = next((window for window in windows if getattr(window, "data_collection", None) is data_collection), None)
    return None if app is None else app.statusBar()


def _clear(status, text):
    if status.currentMessage() == text:  # unless something else has said more since
        status.clearMessage()


def _start(data_collection, text, failed, function, *args):
    """
    Compute ``function(*args)``, a dataset, on glue-qt's `Worker`, while glue's status bar says ``text``, and add it to
    ``data_collection``, or show its error with ``failed``.
    """
    worker = Worker(function, *args)
    status = _status_bar(data_collection)
    worker.result.connect(partial(_add, data_collection, status))
    worker.error.connect(failed)
    if status is not None:  # until the dataset is added or the error shown (D46)
        status.showMessage(text)
        worker.finished.connect(partial(_clear, status, text))
    _RUNNING.add(worker)
    worker.finished.connect(lambda: _RUNNING.discard(worker))  # last: queued, so the message is cleared by then
    worker.start()


@layer_action(
    "IRIS: line moments…",
    single=True,
    data=True,
    tooltip="Add irispy's intensity, centroid, width and velocity maps of a line in this raster window",
)
@messagebox_on_error("Could not compute line moments")
def moments_iris(data, data_collection):
    """
    Add the `line_moments` of ``data`` about a typed line centre, within typed wings, less any background fitted to
    typed continuum windows, to the data collection, with its helioprojective coordinates linked, and no viewer; glue
    shows why for data that has none. irispy computes them in the background, while glue's status bar says so, and then
    how many pixels saturated, if any.
    """
    _check(data)  # before asking
    line = _ask(data)
    if line is None:
        return
    text = f"Computing line moments of {data.label}…"
    _start(data_collection, text, _failed, _moments, data, *line, *_window(data, *line))


def _mean_spectrum(data, cid):
    """
    The nanmean of ``cid`` over every axis of ``data`` but wavelength, its last, NaN where every sample is missing;
    summed in float64 a slab of `SLAB` samples at a time.
    """
    total, count = np.zeros(data.shape[-1]), np.zeros(data.shape[-1])
    steps = max(1, SLAB // (data.shape[-2] * data.shape[-1]))
    for scan in np.ndindex(data.shape[:-3]):  # each scan of a stack
        for start in range(0, data.shape[-3], steps):
            values = data[cid, (*scan, slice(start, start + steps))]
            valid = ~np.isnan(values)
            total += values.sum((0, 1), dtype=float, where=valid)
            count += valid.sum((0, 1))
    with np.errstate(invalid="ignore"):  # 0 / 0
        return total / count


def subtract_mean_spectrum(data):
    """
    Add ``<label> mean spectrum`` to ``data``, an IRIS raster window or a stack of its scans: the nanmean of its values
    at each wavelength over every raster step or exposure, slit pixel and scan, missing data left out, NaN where every
    sample is missing; and ``<label> minus mean spectrum``, the values less it, a glue derived component. The mean is
    computed once, a slab of steps at a time, and held as one spectrum.

    Returns
    -------
    `~glue.core.component_id.ComponentID`
        The derived component's.

    Raises
    ------
    ValueError
        For other data than an IRIS raster window or stack, or one that has the components already.
    """
    if _role(data) != "raster" or _spectral_axes(data) != {data.ndim - 1}:
        raise ValueError(f"{data.label} is not an IRIS raster window.")
    cid = data.main_components[0]
    label = f"{cid.label} minus mean spectrum"
    if data.find_component_id(label) is not None:
        raise ValueError(f"{data.label} has its mean spectrum subtracted already.")
    units = data.get_component(cid).units
    mean = np.broadcast_to(_mean_spectrum(data, cid), data.shape)  # a view: one spectrum held
    difference = cid - data.add_component(Component(mean, units=units), f"{cid.label} mean spectrum")
    data.add_component_link(difference, label).units = units
    return difference.get_to_id()


@layer_action(
    "IRIS: subtract mean spectrum",
    single=True,
    data=True,
    tooltip="Add this raster window's values less its mean spectrum over every pixel and scan",
)
@messagebox_on_error("Could not subtract the mean spectrum")
def mean_spectrum_iris(data, data_collection):
    """Add the `subtract_mean_spectrum` components to ``data``; glue shows why for other data or a second run."""
    subtract_mean_spectrum(data)
