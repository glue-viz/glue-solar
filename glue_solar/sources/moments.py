"""
'IRIS: line moments…': irispy's moment maps of a line in a raster window, as a new dataset.
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

__all__ = ["line_moments", "moments_iris"]

# The wavelengths the dialog takes at first, in Angstrom below and above the line centre
WINGS = (0.5, 0.5)
# Samples per irispy call, which copies its input about seven times as float64
SLAB = 2**21
# irispy picks the wavelengths within the wings again, rounding its own way: a crop wider by this many Angstrom keeps
# every one it picks
_HAIR = 1e-6


def _check(data):
    """Raise why ``data`` is not an IRIS raster window of one scan, (raster step, slit, wavelength)."""
    if _role(data) == "raster" and data.ndim == 4:
        raise ValueError(
            f"{data.label} is a stack of raster scans: line moments take one scan, as the observation "
            "browser loads them without 'Stack sequential raster scans'."
        )
    if _role(data) != "raster" or data.ndim != 3 or _spectral_axes(data) != {2}:
        raise ValueError(f"{data.label} is not an IRIS raster window.")


def _window(data, centre, wings, continuum=None):
    """
    The wavelength pixels of ``data`` from the first to the last within ``wings`` of ``centre`` or a ``continuum``
    window, those within the wings, both `_HAIR` wider, and the unit of its values; raises why for data that has none
    within the wings, or a continuum window that overlaps them or has none.
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
    from irispy.utils.constants import DN_UNIT  # with the first use rather than at glue's launch

    with u.add_enabled_units(DN_UNIT.values()):  # astropy's registry, global: on the calling thread
        unit = u.Unit(data.get_component(data.main_components[0]).units)
    return slice(min(ends), max(ends) + 1), slice(inside[0], inside[-1] + 1), unit


def _moments(data, centre, wings, continuum, crop, inner, unit):
    """
    `line_moments` given ``crop`` of the wavelength pixels, ``inner`` those within the wings, and ``unit`` the unit of
    the values; on any thread.
    """
    from irispy.spectrograph import SpectrogramCube
    from irispy.utils.constants import SATURATION_LIMIT
    from irispy.utils.moments import calculate_moments
    from irispy.utils.spectrograph import subtract_background
    from ndcube.meta import NDMeta

    cid, maps, saturated = data.main_components[0], {}, 0
    # the loader's DN/s, its DN over each step's exposure time (D4), from the DN read here: glue's derived component
    # reads them again
    rate = data.find_component_id(f"{cid.label} DN/s") is not None
    if rate:
        unit = unit / u.s
    # a slab takes about 100 bytes per sample, 150 with a continuum: half the steps then, generously, keeps a small
    # window's cold peak under 3x
    steps = max(1, SLAB // (data.shape[1] * (crop.stop - crop.start) * (2 if continuum else 1)))
    degree = 1 if len(continuum or ()) > 1 else 0  # a constant for one continuum window, a straight line for more
    inside = slice(inner.start - crop.start, inner.stop - crop.start)  # inner, within the crop

    def cube(values, rows, wavelengths, meta=None):
        view = SlicedLowLevelWCS(data.coords._wcs, (*rows, wavelengths))
        return SpectrogramCube(values, view, unit=unit, mask=np.isnan(values) | np.isneginf(values), meta=meta)

    for start in range(0, data.shape[0], steps):
        rows = (slice(start, start + steps), slice(None))
        values = data[cid, (*rows, crop)]  # scaled float32 of these steps and wavelengths only, NaN where missing
        meta = NDMeta()
        if rate:
            # irispy's limit is 16182 DN over the exposure times given it, in float64: in float32, as the loader's,
            # a sample at 16182 DN can round below it
            seconds = data["Exposure time", (rows[0], slice(0, 1), slice(0, 1))].astype(np.float32)
            values = per_second(values.astype(float), seconds)
            meta.add("exposure time", seconds.ravel() * u.s, None, 0)
        with WCS_LOCK:  # irispy reads the wavelengths through the raster's astropy WCS
            # saturated within the wings, before any background is subtracted: NaN in every map
            slab = calculate_moments(
                cube(values[..., inside], rows, inner, meta),
                rest_wavelength=centre * u.AA,
                wings=wings * u.AA,
                saturation_limit=SATURATION_LIMIT,
            )
            reached = slab.pop("saturated").data
            if continuum:  # the moments of the line less the background, in which irispy would miss saturation
                values = subtract_background(cube(values, rows, crop), continuum * u.AA, degree=degree).data
                # NaN where irispy fits no background: missing at every wavelength within the wings, NaN maps
                slab = calculate_moments(
                    cube(values[..., inside], rows, inner), rest_wavelength=centre * u.AA, wings=wings * u.AA
                )
        saturated += int(reached.sum())
        for name, moment in slab.items():
            # irispy sums masked samples, NaN and -Inf, as 0, and masks a pixel masked at every wavelength: NaN there (D17)
            maps.setdefault(name, []).append((np.where(moment.mask | reached, np.nan, moment.data), moment.unit))
        # ndcube's cubes are reference cycles, and irispy's hold the slab's values: else every slab's stay until
        # Python's collector runs
        gc.collect(0)
    moments = Data(label=f"{data.label} moments {centre}")
    with WCS_LOCK:
        # the raster's own steps and slit pixels: its wavelength does not move them
        moments.coords = _GlueWCS(SlicedLowLevelWCS(data.coords._wcs, (slice(None), slice(None), 0)))
    # the observation's, for the quicklook's grouping and transparent NaN, without INSTRUME, which makes a raster
    moments.meta = {key: data.meta[key] for key in ("OBSID", "STARTOBS") if key in data.meta}
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
    buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    form.addRow(buttons)
    accepted = dialog.exec() == QtWidgets.QDialog.Accepted
    dialog.deleteLater()  # else each run keeps a hidden dialog under the main window
    text = centre.text().strip() if accepted else ""
    if not text:
        return None
    try:
        line = float(text), tuple(box.value() for box in wings)
    except ValueError:
        raise ValueError(f"'{text}' is not a wavelength in Angstrom, such as 1402.77.") from None
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
    worker = Worker(_moments, data, *line, *_window(data, *line))
    status, text = _status_bar(data_collection), f"Computing line moments of {data.label}…"
    worker.result.connect(partial(_add, data_collection, status))
    worker.error.connect(_failed)
    _RUNNING.add(worker)
    worker.finished.connect(lambda: _RUNNING.discard(worker))
    if status is not None:  # until the dataset is added or the error shown (D46)
        status.showMessage(text)
        worker.finished.connect(partial(_clear, status, text))
    worker.start()
