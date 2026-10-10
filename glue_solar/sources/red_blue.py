"""
'IRIS: red-blue asymmetry…': irispy's red-blue asymmetry of a line in a raster window or a stack of its scans, as a new
dataset.
"""

import gc
import itertools

import numpy as np
from glue.core.component import Component
from glue_qt.utils.decorators import messagebox_on_error
from qtpy import QtWidgets

import astropy.units as u

from glue_solar.glue_patches import layer_action
from glue_solar.lines import _wavelength
from glue_solar.sources.loaders.iris import WCS_LOCK
from glue_solar.sources.moments import SLAB, _accepted, _check, _cube, _dataset, _read, _rest_field, _start, _window

__all__ = ["red_blue_asymmetry", "red_blue_iris"]

# The wavelengths the dialog takes at first, in Angstrom below and above the rest wavelength: irispy takes the peak of
# all it is given, which in a Mg II k window can be Mg II h
WAVELENGTHS = (1.0, 1.0)
# iris_xfiles' red-blue settings, in km/s: its double Gaussian fit averages red minus blue over 5 km/s from each of 30,
# 35, ... 50 km/s, so from 30 to 55 km/s (SolarSoft iris/idl/uio/objects/iris_moment__dgf.pro, lines 49-53, and
# uio/utils/iris_gen_rb_profile.pro, lines 7-11)
VELOCITIES = (30.0, 55.0)
STEP = 5.0


def _taken(data, rest, wavelengths):
    """The `_window` of the wavelengths of ``data`` within ``wavelengths``, below and above ``rest``, in Angstrom."""
    below, above = wavelengths
    return _window(data, (rest - below, rest + above), f"{below} Å below and {above} Å above {rest} Å")


def _red_blue(data, rest, wavelengths, velocities, step, crop, unit):
    """
    `red_blue_asymmetry` given ``crop`` of the wavelength pixels and ``unit`` the unit of the values irispy is given;
    on any thread.
    """
    from irispy.utils.red_blue import calculate_red_blue_asymmetry

    maps = {}
    # irispy measures each pixel on its own, so a slab of steps gives what the whole window would
    steps = max(1, SLAB // (data.shape[-2] * (crop.stop - crop.start)))
    # each scan of a stack, as its own WCS and exposure times give it
    for scan, start in itertools.product(np.ndindex(data.shape[:-3]), range(0, data.shape[-3], steps)):
        rows = (*scan, slice(start, start + steps), slice(None))
        values, _ = _read(data, rows, crop)
        with WCS_LOCK:  # irispy reads the wavelengths through the raster's astropy WCS
            slab = calculate_red_blue_asymmetry(
                _cube(data, values, rows, crop, unit),
                rest_wavelength=rest * u.AA,
                velocity_range=velocities * u.km / u.s,
                dv=step * u.km / u.s,
                return_profiles=False,
            )
        for name, part in slab.items():
            maps.setdefault(name, []).append(part.data)
        gc.collect(0)  # ndcube's cubes are reference cycles, and irispy's hold the slab's values
    asymmetry = _dataset(data, f"{data.label} red-blue asymmetry {rest}")
    asymmetry.meta.update(
        red_blue_rest=rest,
        red_blue_wavelengths=tuple(wavelengths),
        red_blue_velocities=tuple(velocities),
        red_blue_step=step,
    )
    for name, parts in maps.items():
        asymmetry.add_component(Component(np.concatenate(parts).reshape(data.shape[:-1])), name)
    return asymmetry


def red_blue_asymmetry(data, rest, wavelengths=WAVELENGTHS, velocities=VELOCITIES, step=STEP):
    """
    irispy's red-blue asymmetry of a line in ``data``, an IRIS raster window of one scan or a stack of its scans, from
    its wavelengths within ``wavelengths`` of ``rest``, as one dataset on the window's scans, raster steps and slit
    pixels, each scan's as that scan alone gives them, at its own coordinates.

    irispy is given the window's ``<label> DN/s`` where it has one, else its values, NaN, -Inf and negative samples
    left out, a slab of raster steps of one scan at a time. For each pixel it interpolates the profile about its peak
    every ``step`` and divides the mean red wing, from ``velocities[0]`` to ``velocities[1]`` above the peak, less the
    mean blue wing, as far below it, by the peak. Its components are irispy's: ``red_blue_asymmetry``, NaN where it is not
    computed, and ``quality``, an `~irispy.utils.red_blue.RBAQualityFlag` code, 0 where it is; a pixel with a
    saturated sample taken, +Inf, as the loader reads the Level 2 ceiling, 16182 DN, is flagged saturated. ``meta``
    holds the observation's ``OBSID`` and ``STARTOBS``, ``red_blue_rest``, ``red_blue_wavelengths``,
    ``red_blue_velocities`` and ``red_blue_step``.

    Parameters
    ----------
    data : `~glue.core.data.Data`
        An IRIS raster window of one scan, (raster step, slit, wavelength), or a stack of its scans, (scan, raster
        step, slit, wavelength).
    rest : float
        The rest wavelength of the line, in Angstrom.
    wavelengths : tuple of float
        The wavelengths taken, in Angstrom below and above ``rest``; irispy takes the peak of them all.
    velocities : tuple of float
        The wing velocities, from and to, in km / s from the peak.
    step : float
        The velocity step of the interpolated profile, in km / s.

    Raises
    ------
    ValueError
        For other data than an IRIS raster window or stack, or one with no wavelength within ``wavelengths`` of
        ``rest``.
    """
    _check(data)
    return _red_blue(data, rest, wavelengths, velocities, step, *_taken(data, rest, wavelengths))


def _ask(data):
    """
    The rest wavelength typed for ``data``, at first its `rest_wavelength`, and the wavelengths taken below and above
    it, in Angstrom, and the wing velocities and the velocity step, in km/s; or None for a blank rest wavelength or
    Cancel.
    """
    dialog = QtWidgets.QDialog(QtWidgets.QApplication.activeWindow())
    dialog.setWindowTitle(f"IRIS: red-blue asymmetry of {data.label}")
    form = QtWidgets.QFormLayout(dialog)
    rest = _rest_field(data, "rest")  # D11: never the window's TWAVE
    form.addRow("Rest wavelength [Å]:", rest)
    boxes = []
    for name, label, value, unit in (
        ("below", "Taken below the rest:", WAVELENGTHS[0], "Å"),
        ("above", "Taken above the rest:", WAVELENGTHS[1], "Å"),
        ("from", "Wing velocities from:", VELOCITIES[0], "km/s"),
        ("to", "Wing velocities to:", VELOCITIES[1], "km/s"),
        ("step", "Velocity step:", STEP, "km/s"),
    ):
        step = 0.1 if unit == "Å" else 1
        box = QtWidgets.QDoubleSpinBox(objectName=name, decimals=3, maximum=1000, singleStep=step, suffix=f" {unit}")
        box.setValue(value)
        form.addRow(label, box)
        boxes.append(box)
    text = rest.text().strip() if _accepted(dialog, form) else ""
    if not text:
        return None
    below, above, low, high, step = (box.value() for box in boxes)
    return _wavelength(text), (below, above), (low, high), step


@messagebox_on_error("Could not compute red-blue asymmetry")
def _failed(exc_info):
    raise exc_info[1]


@layer_action(
    "IRIS: red-blue asymmetry…",
    single=True,
    data=True,
    check=_check,
    tooltip="Add irispy's red-blue asymmetry map of a line in this raster window or stack",
)
@messagebox_on_error("Could not compute red-blue asymmetry")
def red_blue_iris(data, data_collection):
    """
    Add the `red_blue_asymmetry` of ``data`` about a typed rest wavelength, with typed wing velocities, to the data
    collection, with its helioprojective coordinates linked, and no viewer; offered only for a raster window or stack,
    and glue shows why for typed values it cannot take. irispy computes it in the background, while glue's status bar
    says so.
    """
    _check(data)  # before asking
    line = _ask(data)
    if line is None:
        return
    text = f"Computing red-blue asymmetry of {data.label}…"
    _start(data_collection, text, _failed, _red_blue, data, *line, *_taken(data, *line[:2]))
