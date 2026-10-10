"""
'IRIS: Doppler image…': the red wing less the blue wing of a line at typed velocities in a raster window or a stack of
its scans, as a new dataset (D16).
"""

import numpy as np
from glue.core.component import Component
from glue_qt.utils.decorators import messagebox_on_error
from qtpy import QtWidgets

import astropy.units as u

from glue_solar.glue_patches import layer_action
from glue_solar.lines import _wavelength
from glue_solar.sources.moments import _accepted, _check, _dataset, _read, _rest_field, _start, _unit

__all__ = ["doppler_image", "doppler_iris"]

# The velocities the dialog takes at first, in km/s from the rest wavelength
VELOCITIES = (10.0, 20.0, 30.0, 40.0, 50.0)


def _wings(data, rest, velocities):
    """
    For each scan of ``data``, its index, the wavelength pixels read and, for the red wing at each of ``velocities``
    and then the blue, the pixel below it among them and its weight in a linear interpolation; raises why for data
    `_check` refuses, a velocity that is not positive or a wing outside the window.
    """
    _check(data)
    if not (len(velocities) and np.all(np.asarray(velocities, float) > 0)):  # NaN too
        raise ValueError(f"The velocities must be positive, not {', '.join(f'{v:g}' for v in velocities)} km/s.")
    speeds = np.concatenate([velocities, np.negative(velocities)])
    targets = (speeds * u.km / u.s).to_value(u.AA, equivalencies=u.doppler_optical(rest * u.AA))
    unit = u.Unit(data.coords.world_axis_units[0])
    wings = []
    for scan in np.ndindex(data.shape[:-3]):  # each scan of a stack at its own wavelengths
        # through the WCS: glue's Wavelength component of a stack, depending on no scan pixel, is scan 0's at each
        wavelengths = data.coords.pixel_to_world_values(np.arange(data.shape[-1]), 0, 0, *scan)[0]
        wavelengths = (wavelengths * unit).to_value(u.AA)
        below = np.clip(np.searchsorted(wavelengths, targets, side="right") - 1, 0, wavelengths.size - 2)
        weight = (targets - wavelengths[below]) / np.diff(wavelengths)[below]
        outside = (weight < 0) | (weight > 1)
        if outside.any():
            listed = ", ".join(f"{v:g}" for v in sorted(set(np.abs(speeds[outside]))))
            raise ValueError(
                f"The wings at ±{listed} km/s from {rest} Å lie outside {data.label} "
                f"({wavelengths[0]:.2f} to {wavelengths[-1]:.2f} Å)."
            )
        crop = slice(below.min(), below.max() + 2)
        wings.append((scan, crop, below - crop.start, weight))
    return wings


def _doppler(data, rest, velocities, normalised, wings, unit):
    """`doppler_image` given its `_wings` and ``unit`` the unit of the values read (`_read`); on any thread."""
    planes = []
    for scan, crop, below, weight in wings:
        for step in range(data.shape[-3]):  # a step at a time
            values, _ = _read(data, (*scan, slice(step, step + 1), slice(None)), crop)
            with np.errstate(invalid="ignore"):  # +Inf, saturated, at a weight of 0 gives NaN
                wing = values[..., below] * (1 - weight) + values[..., below + 1] * weight
            wing[np.isinf(wing)] = np.nan  # NaN where either sample is missing or saturated
            planes.append(wing)
    red, blue = np.split(np.concatenate(planes).reshape(*data.shape[:-1], -1), 2, axis=-1)
    doppler = _dataset(data, f"{data.label} Doppler image {rest}")
    doppler.meta.update(doppler_rest=rest, doppler_velocities=tuple(velocities), doppler_sign="red - blue")
    difference = red - blue
    for k, v in enumerate(velocities):
        doppler.add_component(Component(difference[..., k], units=str(unit)), f"red - blue {v:g} km/s")
    if normalised:
        positive = (red > 0) & (blue > 0)  # else the ratio is not one of intensities, and unbounded
        ratio = np.divide(difference, red + blue, out=np.full(red.shape, np.nan), where=positive)
        for k, v in enumerate(velocities):
            doppler.add_component(Component(ratio[..., k]), f"(red - blue) / (red + blue) {v:g} km/s")
    return doppler


def doppler_image(data, rest, velocities=VELOCITIES, normalised=False):
    """
    The red wing less the blue wing of a line in ``data``, an IRIS raster window of one scan or a stack of its scans,
    at each of ``velocities`` from ``rest``, as one dataset on the window's scans, raster steps and slit pixels, each
    scan's at its own coordinates.

    Each wing is the window's ``<label> DN/s`` where it has one, else its values, interpolated linearly at
    ``rest * (1 ± v / c)``, the optical Doppler shift of velocity v, between the two samples about it, each scan at its
    own wavelengths; NaN where either sample is missing or saturated, +Inf, as the loader reads the Level 2 ceiling. Its
    components are ``red - blue <v> km/s``, in that unit, positive for a brighter red wing, and with ``normalised``,
    ``(red - blue) / (red + blue) <v> km/s``, NaN where a wing is not positive. ``meta`` holds the observation's
    ``OBSID`` and ``STARTOBS``, ``doppler_rest``, ``doppler_velocities`` and ``doppler_sign``, ``"red - blue"``. The
    window is read a raster step at a time.

    Parameters
    ----------
    data : `~glue.core.data.Data`
        An IRIS raster window of one scan, (raster step, slit, wavelength), or a stack of its scans, (scan, raster
        step, slit, wavelength).
    rest : float
        The rest wavelength of the line, in Angstrom.
    velocities : sequence of float
        The velocities of the wings from ``rest``, positive, in km / s.
    normalised : bool
        Whether to add each map over the sum of its wings too.

    Raises
    ------
    ValueError
        For other data than an IRIS raster window or stack, a velocity that is not positive, or a wing outside the
        window.
    """
    return _doppler(data, rest, velocities, normalised, _wings(data, rest, velocities), _unit(data))


def _ask(data):
    """
    The rest wavelength typed for ``data``, at first its `rest_wavelength`, in Angstrom, the velocities typed, in
    km/s, increasing, and whether the normalised maps are ticked; or None for a blank rest wavelength or Cancel.
    """
    dialog = QtWidgets.QDialog(QtWidgets.QApplication.activeWindow())
    dialog.setWindowTitle(f"IRIS: Doppler image of {data.label}")
    form = QtWidgets.QFormLayout(dialog)
    rest = _rest_field(data, "rest")  # D11: never the window's TWAVE
    form.addRow("Rest wavelength [Å]:", rest)
    velocities = QtWidgets.QLineEdit(", ".join(f"{v:g}" for v in VELOCITIES), objectName="velocities")
    form.addRow("Velocities [km/s]:", velocities)
    normalised = QtWidgets.QCheckBox("(red - blue) / (red + blue) too", objectName="normalised")
    form.addRow(normalised)
    text = rest.text().strip() if _accepted(dialog, form) else ""
    if not text:
        return None
    typed = velocities.text()
    try:
        speeds = sorted({float(part) for part in typed.replace(",", " ").split()})
    except ValueError:
        speeds = []
    if not speeds:
        raise ValueError(f"'{typed}' is not a list of velocities in km/s, such as 10, 20, 30.")
    return _wavelength(text), speeds, normalised.isChecked()


@messagebox_on_error("Could not compute the Doppler image")
def _failed(exc_info):
    raise exc_info[1]


@layer_action(
    "IRIS: Doppler image…",
    single=True,
    data=True,
    check=_check,
    tooltip="Add red minus blue wing maps of a line at typed velocities in this raster window or stack",
)
@messagebox_on_error("Could not compute the Doppler image")
def doppler_iris(data, data_collection):
    """
    Add the `doppler_image` of ``data`` about a typed rest wavelength at typed velocities, normalised too if ticked,
    to the data collection, with its helioprojective coordinates linked, and no viewer; glue shows why for data that
    has none. It is computed in the background, while glue's status bar says so.
    """
    _check(data)  # before asking
    asked = _ask(data)
    if asked is None:
        return
    rest, velocities, normalised = asked
    wings = _wings(data, rest, velocities)
    text = f"Computing the Doppler image of {data.label}…"
    _start(data_collection, text, _failed, _doppler, data, rest, velocities, normalised, wings, _unit(data))
