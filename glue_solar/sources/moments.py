"""
'IRIS: line moments…': irispy's moment maps of a line in a raster window or a stack of its scans, as a new dataset;
and 'IRIS: subtract mean spectrum': a raster window's values less its mean spectrum, as a glue derived component.
"""

import gc
import itertools
from functools import partial

import numpy as np
from glue.config import layer_action
from glue.core.component import Component
from glue.core.data import Data
from glue.core.units import UnitConverter
from glue_qt.utils.decorators import messagebox_on_error
from glue_qt.utils.threading import Worker
from glue_qt.viewers.profile import ProfileViewer
from qtpy import QtWidgets

import astropy.units as u
from astropy import constants
from astropy.nddata import StdDevUncertainty
from astropy.wcs.wcsapi.wrappers import SlicedLowLevelWCS

from glue_solar.lines import MAIN_LINES, _wavelength, rest_wavelength
from glue_solar.quicklook import _role, _spectral_axes, _wavelengths
from glue_solar.sources.loaders.iris import _RUNNING, WCS_LOCK, _GlueWCS, keep_hpc_linked, per_second

__all__ = ["line_moments", "mean_spectrum_iris", "moments_iris", "subtract_mean_spectrum"]

# The velocity range the dialog takes at first, in km/s from the line centre: ±0.5 Å at Si IV 1402.77 (D57)
VELOCITY_RANGE = (-107.0, 107.0)
# Samples per irispy call, which copies its input about seven times as float64, and per read of a mean spectrum
SLAB = 2**21
# irispy picks the wavelengths within the velocity range again, rounding its own way: a crop wider by this many
# Angstrom keeps every one it picks
_HAIR = 1e-6


def _check(data):
    """
    Raise why ``data`` is not an IRIS raster window of one scan, (raster step, slit, wavelength), or a stack of its
    scans, (scan, raster step, slit, wavelength).
    """
    if _role(data) != "raster" or data.ndim not in (3, 4) or _spectral_axes(data) != {data.ndim - 1}:
        raise ValueError(f"{data.label} is not an IRIS raster window.")


def _ends(centre, velocity_range):
    """
    The wavelengths, in Angstrom, at ``velocity_range``, a ``(lower, upper)`` pair in km/s from ``centre``, as irispy's
    ``calculate_moments`` takes them, and the words for the range; raises why for velocities that do not increase.
    """
    low, high = velocity_range
    if not low < high:
        raise ValueError(f"The velocity range, from {low:g} to {high:g} km/s, does not increase.")
    c = constants.c.to_value(u.km / u.s)
    words = f"the velocity range, {low:g} to {high:g} km/s from {centre} Å"
    return (centre * (1 + low / c), centre * (1 + high / c)), words


def _window(data, ends, lines, continuum=None):
    """
    The wavelength pixels of ``data`` from the first to the last within ``ends``, a ``(lower, upper)`` pair in Angstrom
    ``lines`` says in words, or a ``continuum`` window, `_HAIR` wider, and the unit of the values irispy is given
    (`_read`); raises why for data that has none within ``ends``, or a continuum window that overlaps them or has none.
    """
    _check(data)
    wavelengths, _ = _wavelengths(data)
    span = f"{data.label} ({wavelengths[0]:.2f} to {wavelengths[-1]:.2f} Å)"

    def within(low, high):
        return np.flatnonzero((wavelengths >= low - _HAIR) & (wavelengths <= high + _HAIR))

    inside = within(*ends)
    if not inside.size:
        raise ValueError(f"No wavelength of {span} lies within {lines}.")
    taken = [inside[0], inside[-1]]
    for low, high in continuum or ():
        if low <= ends[1] and high >= ends[0]:
            raise ValueError(f"The continuum window {low}-{high} Å overlaps {lines}.")
        window = within(low, high)
        if not window.size:
            raise ValueError(f"No wavelength of {span} lies within the continuum window {low}-{high} Å.")
        taken += [window[0], window[-1]]
    return slice(min(taken), max(taken) + 1), _unit(data)


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
    The values of ``data`` at ``rows``, the scan of a stack, raster steps and slit pixels, and ``wavelengths`` that
    irispy is given, and each step's exposure time in s:
    of a window with the loader's ``<label> DN/s``, its DN over each step's exposure time (D4), from the DN read here,
    in float64, else its scaled float32 and None; NaN where missing, +Inf where saturated, on any thread.
    """
    cid = data.main_components[0]
    values = data[cid, (*rows, wavelengths)]  # scaled float32 of these steps and wavelengths only
    if data.find_component_id(f"{cid.label} DN/s") is None:
        return values, None
    # glue's derived component reads them again
    seconds = data["Exposure time", (*rows[:-1], slice(0, 1), slice(0, 1))].astype(np.float32)
    return per_second(values.astype(float), seconds), seconds


def _sigma(values, unit, seconds):
    """
    The standard deviation of each of ``values`` in ``unit`` (`_read`), as irispy's reader computes it with
    ``uncertainty=True``: its ``calculate_uncertainty`` of their DN, the photon and read noise, over each step's
    exposure time with ``seconds``.
    """
    from irispy.utils import calculate_uncertainty
    from irispy.utils.constants import DN_UNIT, READOUT_NOISE

    detector = "FUV" if (unit if seconds is None else unit * u.s) == DN_UNIT["FUV"] else "NUV"
    if seconds is None:
        return calculate_uncertainty(values, READOUT_NOISE[detector], DN_UNIT[detector])
    return per_second(calculate_uncertainty(values * seconds, READOUT_NOISE[detector], DN_UNIT[detector]), seconds)


def _cube(data, values, rows, wavelengths, unit, sigma=None):
    """
    irispy's cube of ``values`` in ``unit``, of ``data`` at ``rows`` and ``wavelengths``, NaN and -Inf masked, +Inf, in
    which irispy finds saturation, not; with ``sigma``, each value's standard deviation (`_sigma`).
    """
    from irispy.spectrograph import SpectrogramCube

    view = SlicedLowLevelWCS(data.coords._wcs, (*rows, wavelengths))
    uncertainty = None if sigma is None else StdDevUncertainty(sigma)
    return SpectrogramCube(values, view, uncertainty, unit, mask=np.isnan(values) | np.isneginf(values))


def _dataset(data, label):
    """
    A new dataset ``label`` on the scans of a stack, raster steps and slit pixels of ``data``, at its pointing offset,
    with its observation's meta.
    """
    maps = Data(label=label)
    with WCS_LOCK:
        # the raster's own steps and slit pixels, each scan's: its wavelength does not move them
        maps.coords = _GlueWCS(SlicedLowLevelWCS(data.coords._wcs, (..., 0)))
    maps.coords.pointing_offset = data.coords.pointing_offset
    # the observation's, for the quicklook's grouping and transparent NaN, without INSTRUME, which makes a raster
    maps.meta = {key: data.meta[key] for key in ("OBSID", "STARTOBS") if key in data.meta}
    return maps


def _moments(data, centre, velocity_range, continuum, crop, unit, errors=False):
    """
    `line_moments` given ``crop`` of the wavelength pixels and ``unit`` the unit of the values irispy is given; on any
    thread.
    """
    from irispy.utils.moments import calculate_moments
    from irispy.utils.spectrograph import subtract_background

    if errors and "rebinned" in data.meta:  # 'Rebin…'
        raise ValueError(f"{data.label} is rebinned: irispy would give each bin the noise of one sample.")
    maps, saturated = {}, 0
    # a slab takes about 100 bytes per sample, 150 with a continuum or errors: half the steps then, generously, keeps
    # a small window's cold peak under 3x
    steps = max(1, SLAB // (data.shape[-2] * (crop.stop - crop.start) * (2 if continuum or errors else 1)))
    degree = 1 if len(continuum or ()) > 1 else 0  # a constant for one continuum window, a straight line for more
    # each scan of a stack, as its own WCS and exposure times give it
    for scan, start in itertools.product(np.ndindex(data.shape[:-3]), range(0, data.shape[-3], steps)):
        rows = (*scan, slice(start, start + steps), slice(None))
        values, seconds = _read(data, rows, crop)
        # irispy's uncertainty of the values, which its background leaves as they are
        cube = _cube(data, values, rows, crop, unit, _sigma(values, unit, seconds) if errors else None)
        with WCS_LOCK:  # irispy reads the wavelengths through the raster's astropy WCS
            if continuum:  # NaN where irispy fits no background; +Inf, saturated, stays +Inf
                cube = subtract_background(cube, continuum * u.AA, degree=degree)
            slab = calculate_moments(cube, rest_wavelength=centre * u.AA, velocity_range=velocity_range * u.km / u.s)
        saturated += int(slab.pop("saturated").data.sum())
        for name, moment in slab.items():
            # irispy sums masked samples, NaN and -Inf, as 0, and masks a pixel with none in the velocity range, or
            # with +Inf there, saturated: NaN there (D17)
            maps.setdefault(name, []).append((np.where(moment.mask, np.nan, moment.data), moment.unit))
            if errors:  # NaN too where irispy leaves them undefined
                maps.setdefault(f"{name} error", []).append(
                    (np.where(moment.mask, np.nan, moment.uncertainty.array), moment.unit)
                )
        # ndcube's cubes are reference cycles, and irispy's hold the slab's values: else every slab's stay until
        # Python's collector runs
        gc.collect(0)
    moments = _dataset(data, f"{data.label} moments {centre}")
    moments.meta.update(moments_centre=centre, moments_velocity_range=tuple(velocity_range))
    if continuum:
        moments.meta.update(moments_continuum=tuple(map(tuple, continuum)), moments_continuum_degree=degree)
    if saturated:  # for the status bar and scripts; maps without keep the meta they had
        moments.meta["moments_saturated"] = saturated
    for name, parts in maps.items():
        values, unit = np.concatenate([values for values, _ in parts]).reshape(data.shape[:-1]), parts[0][1]
        if unit.is_equivalent(u.AA):  # irispy's centroid and width are in nm
            values, unit = unit.to(u.AA, values), u.AA
        moments.add_component(Component(values, units=str(unit)), name)
    return moments


def line_moments(data, centre, velocity_range=VELOCITY_RANGE, continuum=None, errors=False):
    """
    irispy's moments of a line in ``data``, an IRIS raster window of one scan or a stack of its scans, about
    ``centre`` within ``velocity_range``, as one dataset on the window's scans, raster steps and slit pixels, each
    scan's at its own coordinates; with ``continuum`` windows, of the line less irispy's background fitted to them: a
    constant to one window, a straight line to more.

    irispy is given the window's ``<label> DN/s`` where it has one, else its values, with NaN and -Inf masked. Its
    components are irispy's: ``intensity`` in that unit, ``centroid`` and ``width`` in Angstrom, and ``velocity`` and
    ``velocity_width`` in km / s, relative to ``centre``; all are NaN where every sample within the velocity range is
    missing, no background could be fitted, or irispy finds a sample there saturated: +Inf, as the loader reads the
    Level 2 ceiling, 16182 DN, which a background leaves +Inf. ``meta`` holds the observation's ``OBSID`` and
    ``STARTOBS``, ``moments_centre`` and ``moments_velocity_range``, with a continuum ``moments_continuum`` and
    ``moments_continuum_degree``, the degree of the background, and with saturated pixels ``moments_saturated``, how
    many. irispy is given only the wavelengths from the first to the last within the velocity range or a continuum
    window, a slab of steps of one scan at a time, in one call.

    With ``errors``, each map ``<name>`` has ``<name> error``, irispy's standard deviation of it, in its unit, propagated
    to first order from that of each sample its reader gives with ``uncertainty=True``: the photon and read noise of
    its DN, over the step's exposure time for DN/s, taken as independent (a background's error is left out). irispy
    leaves it NaN where it is undefined: the intensity's where no sample is left, the centroid's and the velocity's
    where fewer than two are, and the widths' where the width is 0.

    Parameters
    ----------
    data : `~glue.core.data.Data`
        An IRIS raster window of one scan, (raster step, slit, wavelength), or a stack of its scans, (scan, raster
        step, slit, wavelength).
    centre : float
        The line centre, in Angstrom.
    velocity_range : tuple of float
        The ``(lower, upper)`` Doppler velocities of the wavelengths taken, in km / s from ``centre``.
    continuum : sequence of tuple of float, optional
        The ``(lower, upper)`` wavelengths of each continuum window, in Angstrom, ends included, outside the velocity
        range.
    errors : bool
        Whether to add each map's error.

    Raises
    ------
    ValueError
        For other data than an IRIS raster window or stack, a velocity range that does not increase or has no
        wavelength of the window, or a continuum window with none or overlapping the velocity range.
    """
    window = _window(data, *_ends(centre, velocity_range), continuum)
    return _moments(data, centre, velocity_range, continuum, *window, errors)


def _accepted(dialog, form):
    """Add OK and Cancel to ``form``, run ``dialog`` and say whether OK was pressed."""
    buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    form.addRow(buttons)
    accepted = dialog.exec() == QtWidgets.QDialog.Accepted
    dialog.deleteLater()  # else each run keeps a hidden dialog under the main window
    return accepted


def _rest_field(data, name):
    """A line edit ``name`` holding the `rest_wavelength` of ``data``, if any, its tooltip saying where it is from."""
    rest = rest_wavelength(data)
    field = QtWidgets.QLineEdit("" if rest is None else str(rest), objectName=name)
    if data.meta.get("rest_wavelength") is not None:
        field.setToolTip(f"{data.label}'s, set with 'Set rest wavelength…'")
    elif rest is not None:
        field.setToolTip(f"{next(line for line, wave in MAIN_LINES if wave == rest)}, of the main IRIS lines")
    return field


def _profile_range(data, data_collection):
    """
    The wavelengths, from and to, in Angstrom, of the range shown on a Profile of ``data`` against its wavelength,
    glue-qt's Fit and Collapse range, or None.
    """
    app = _application(data_collection)
    for viewer in (viewer for tab in getattr(app, "viewers", ()) for viewer in tab):
        state = viewer.state
        if not isinstance(viewer, ProfileViewer) or state.reference_data is not data:
            continue
        mode = viewer.toolbar.tools["profile-analysis"]._profile_tools.rng_mode
        if state.x_att is data.world_component_ids[-1] and mode.active and None not in mode.state.x_range:
            ends = UnitConverter().to_native(data, state.x_att, np.array(mode.state.x_range), state.x_display_unit)
            return tuple(float(end) for end in sorted(ends))
    return None


def _ask(data, drawn=None):
    """
    The line centre typed for ``data``, at first its `rest_wavelength`, in Angstrom, the velocity range about it, in
    km/s, the continuum windows, or None for none, in Angstrom, and whether error maps are ticked; or None for a blank
    centre or Cancel. With ``drawn``, a Profile range, the velocity range reaches its ends from a centre within it, at
    first or typed.
    """
    dialog = QtWidgets.QDialog(QtWidgets.QApplication.activeWindow())
    dialog.setWindowTitle(f"IRIS: line moments of {data.label}")
    form = QtWidgets.QFormLayout(dialog)
    centre = _rest_field(data, "centre")  # D11: never the window's TWAVE
    form.addRow("Line centre [Å]:", centre)
    boxes = []
    for name, value in zip(("from", "to"), VELOCITY_RANGE):
        box = QtWidgets.QDoubleSpinBox(objectName=name, decimals=3, minimum=-1e4, maximum=1e4, suffix=" km/s")
        box.setValue(value)
        form.addRow(f"Velocities {name}:", box)
        boxes.append(box)
    if drawn is not None:
        low, high = drawn
        form.addRow("Velocities to the Profile range:", QtWidgets.QLabel(f"{low:.3f} to {high:.3f} Å"))

        def reach(text):
            try:
                typed = float(text)
            except ValueError:
                return
            if low <= typed <= high:
                for box, end in zip(boxes, drawn):
                    box.setValue((end / typed - 1) * constants.c.to_value(u.km / u.s))  # as `_ends` inverts it

        reach(centre.text())  # the rest wavelength it starts at
        centre.textChanged.connect(reach)
    continuum = QtWidgets.QLineEdit(objectName="continuum", placeholderText="none, or such as 1401.5-1402, 1404-1405")
    form.addRow("Continuum windows [Å]:", continuum)
    errors = QtWidgets.QCheckBox("Error maps", objectName="errors")  # off: irispy then takes about 1.7 times as long
    errors.setToolTip("Add each map's error, from irispy's photon and read noise of each sample")
    form.addRow(errors)
    text = centre.text().strip() if _accepted(dialog, form) else ""
    if not text:
        return None
    line = _wavelength(text), tuple(box.value() for box in boxes)
    text = continuum.text().strip()
    if not text:
        return *line, None, errors.isChecked()
    try:
        windows = [
            tuple(sorted((float(low), float(high)))) for low, high in (part.split("-") for part in text.split(","))
        ]
    except ValueError:
        raise ValueError(
            f"'{text}' is not a list of continuum windows in Angstrom, such as 1401.5-1402, 1404-1405."
        ) from None
    return *line, windows, errors.isChecked()


@messagebox_on_error("Could not compute line moments")
def _failed(exc_info):
    raise exc_info[1]


def _add(data_collection, status, said, dataset):
    data_collection.append(dataset)
    keep_hpc_linked(data_collection)
    message = said(dataset) if said else None
    if message and status is not None:  # in place of what it says while it is computed
        status.showMessage(message)


def _saturated(moments):
    """What glue's status bar says of the saturated pixels of ``moments``, or None for none."""
    count = moments.meta.get("moments_saturated")
    if count:
        pixels = f"{count} pixels" if count > 1 else "1 pixel"
        return f"{moments.label}: {pixels} saturated within the velocity range {'are' if count > 1 else 'is'} NaN"
    return None


def _application(data_collection):
    """The glue window of ``data_collection``, or None."""
    windows = QtWidgets.QApplication.topLevelWidgets()
    return next((window for window in windows if getattr(window, "data_collection", None) is data_collection), None)


def _status_bar(data_collection):
    """The status bar of the glue window of ``data_collection``, or None."""
    app = _application(data_collection)
    return None if app is None else app.statusBar()


def _clear(status, text):
    if status.currentMessage() == text:  # unless something else has said more since
        status.clearMessage()


def _start(data_collection, text, failed, function, *args, said=None):
    """
    Compute ``function(*args)``, a dataset, on glue-qt's `Worker`, while glue's status bar says ``text``, and add it to
    ``data_collection``, the status bar then saying ``said(dataset)``, if anything; or show its error with ``failed``.
    """
    worker = Worker(function, *args)
    status = _status_bar(data_collection)
    worker.result.connect(partial(_add, data_collection, status, said))
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
    tooltip="Add irispy's intensity, centroid, width and velocity maps of a line in this raster window or stack",
)
@messagebox_on_error("Could not compute line moments")
def moments_iris(data, data_collection):
    """
    Add the `line_moments` of ``data`` about a typed line centre, within a typed velocity range, or one to the ends of
    the range shown on a Profile of its wavelength, less any background fitted to typed continuum windows, with their
    errors if ticked, to the data collection, with its helioprojective coordinates linked, and no viewer; glue shows
    why for data that has none. irispy computes them in the background, while glue's status bar says so, and then how
    many pixels saturated, if any.
    """
    _check(data)  # before asking
    asked = _ask(data, _profile_range(data, data_collection))
    if asked is None:
        return
    centre, velocity_range, continuum, errors = asked
    window = _window(data, *_ends(centre, velocity_range), continuum)
    line = centre, velocity_range, continuum
    text = f"Computing line moments of {data.label}…"
    _start(data_collection, text, _failed, _moments, data, *line, *window, errors, said=_saturated)


def _mean_spectrum(data, cid):
    """
    The mean of the finite values of ``cid`` over every axis of ``data`` but wavelength, its last, NaN where none is;
    summed in float64 a slab of `SLAB` samples at a time.
    """
    total, count = np.zeros(data.shape[-1]), np.zeros(data.shape[-1])
    steps = max(1, SLAB // (data.shape[-2] * data.shape[-1]))
    for scan in np.ndindex(data.shape[:-3]):  # each scan of a stack
        for start in range(0, data.shape[-3], steps):
            values = data[cid, (*scan, slice(start, start + steps))]
            valid = np.isfinite(values)  # +Inf, saturated, left out, as glue's Profile leaves it out
            total += values.sum((0, 1), dtype=float, where=valid)
            count += valid.sum((0, 1))
    with np.errstate(invalid="ignore"):  # 0 / 0
        return total / count


def subtract_mean_spectrum(data):
    """
    Add ``<label> mean spectrum`` to ``data``, an IRIS raster window or a stack of its scans: the mean of its values at
    each wavelength over every raster step or exposure, slit pixel and scan, missing and saturated (+Inf) samples left
    out, NaN where every sample is; and ``<label> minus mean spectrum``, the values less it, a glue derived component.
    The mean is computed once, a slab of steps at a time, and held as one spectrum.

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
