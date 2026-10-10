"""
'IRIS: Mg II features… (Mg II)': irispy's line centres and emission peaks of Mg II k and h in a raster window or a
stack of its scans, as a new dataset.
"""

import gc
import itertools

import numpy as np
from glue.core.component import Component
from glue_qt.utils.decorators import messagebox_on_error
from qtpy import QtWidgets

import astropy.units as u

from glue_solar.glue_patches import layer_action
from glue_solar.quicklook import _wavelengths
from glue_solar.sources.loaders.iris import WCS_LOCK
from glue_solar.sources.moments import SLAB, _accepted, _check, _cube, _dataset, _read, _start, _unit

__all__ = ["mg_features", "mg_features_iris"]

# irispy's defaults: the Doppler velocities searched, in km/s from each line's rest wavelength, and the lines measured
VELOCITIES = (-40.0, 40.0)
LINES = ("k", "h")


def _crop(data, velocities, lines):
    """
    Those of ``lines`` that ``data`` covers over ``velocities``, as irispy finds them, and the wavelength pixels it
    takes of them, a pixel wider at either end, so it finds the same within them; raises why for none.
    """
    from irispy.utils.mg_features import _REST_WAVELENGTH

    if not lines or not set(lines) <= set(_REST_WAVELENGTH):
        raise ValueError(f"lines must be 'k', 'h' or both, not {lines!r}")
    low, high = velocities
    if not low < high:
        raise ValueError(f"The velocities, from {low} to {high} km/s, do not increase.")
    wavelengths, _ = _wavelengths(data)
    covered, starts, stops = [], [], []
    for line in lines:
        velocity = (wavelengths * u.AA).to_value(u.km / u.s, equivalencies=u.doppler_optical(_REST_WAVELENGTH[line]))
        if velocity[0] <= low and high <= velocity[-1]:  # irispy skips a line otherwise
            covered.append(line)
            # irispy's, within 3 km/s of the velocities
            starts.append(np.searchsorted(velocity, low - 3, "right") - 1)
            stops.append(np.searchsorted(velocity, high + 3) + 1)
    if not covered:
        raise ValueError(
            f"{data.label} ({wavelengths[0]:.2f} to {wavelengths[-1]:.2f} Å) does not cover Mg II "
            f"{' or '.join(lines)} from {low} to {high} km/s."
        )
    return tuple(covered), slice(max(min(starts), 0), min(max(stops), wavelengths.size))


def _covered(data):
    """Those of `LINES` that ``data`` covers over `VELOCITIES` (`_crop`); raise why for data `_check` refuses or none."""
    _check(data)
    return _crop(data, VELOCITIES, LINES)[0]


def _mg_features(data, velocities, lines, crop, unit):
    """
    `mg_features` of ``lines`` given ``crop`` of the wavelength pixels and ``unit`` the unit of the values irispy is
    given; on any thread.
    """
    from irispy.utils.mg_features import calculate_mg_features

    maps, saturated = {}, dict.fromkeys(lines, 0)
    # irispy measures each step on its own, so a slab of steps gives what the whole window would
    steps = max(1, SLAB // (data.shape[-2] * (crop.stop - crop.start)))
    # each scan of a stack, as its own WCS and exposure times give it
    for scan, start in itertools.product(np.ndindex(data.shape[:-3]), range(0, data.shape[-3], steps)):
        rows = (*scan, slice(start, start + steps), slice(None))
        values, _ = _read(data, rows, crop)
        with WCS_LOCK:  # irispy reads the wavelengths through the raster's astropy WCS
            # a line's features are NaN where a sample it searches is saturated, +Inf
            slab = calculate_mg_features(
                _cube(data, values, rows, crop, unit), velocity_range=velocities * u.km / u.s, lines=lines
            )
        for line in lines:
            saturated[line] += int(slab.pop(f"{line}_saturated").data.sum())
        for name, feature in slab.items():
            maps.setdefault(name, []).append((feature.data, feature.unit))
        gc.collect(0)  # ndcube's cubes are reference cycles, and irispy's hold the slab's values
    features = _dataset(data, f"{data.label} Mg II features")
    features.meta.update(mg_features_velocities=tuple(velocities), mg_features_lines=lines)
    if any(saturated.values()):  # for the status bar and scripts, as line moments'
        features.meta["mg_features_saturated"] = {line: count for line, count in saturated.items() if count}
    for name, parts in maps.items():
        values = np.concatenate([part for part, _ in parts]).reshape(data.shape[:-1])
        features.add_component(Component(values, units=str(parts[0][1])), name)
    return features


def mg_features(data, velocities=VELOCITIES, lines=LINES):
    """
    irispy's line centres and emission peaks of Mg II ``lines`` in ``data``, an IRIS raster window of one scan or a
    stack of its scans, within ``velocities`` of each line's rest wavelength, as one dataset on the window's scans,
    raster steps and slit pixels, each scan's as that scan alone gives them, at its own coordinates.

    irispy is given the window's ``<label> DN/s`` where it has one, else its values, a slab of steps of one scan at a
    time, and only the wavelengths it searches; it skips a line the window does not cover over ``velocities``. For
    each line, ``k`` (2796.35 Å) and ``h`` (2803.53 Å), its components are irispy's: ``k2v``, ``k3`` and ``k2r``
    (``h2v``, ``h3``, ``h2r``), the blue peak, line centre and red peak, each as ``<feature>_velocity`` in km / s and
    ``<feature>_intensity`` in the window's unit; NaN where irispy finds none, or a sample it searches for the line is
    missing or saturated: +Inf, as the loader reads the Level 2 ceiling, 16182 DN. ``meta`` holds the observation's
    ``OBSID`` and ``STARTOBS``, ``mg_features_velocities`` and ``mg_features_lines``, those measured, and with
    saturated pixels ``mg_features_saturated``, how many of each line's, over every scan.

    Parameters
    ----------
    data : `~glue.core.data.Data`
        An IRIS raster window of one scan, (raster step, slit, wavelength), or a stack of its scans, (scan, raster
        step, slit, wavelength).
    velocities : tuple of float
        The Doppler velocities searched, from and to, in km / s from each line's rest wavelength.
    lines : tuple of str
        The lines measured, ``"k"``, ``"h"`` or both.

    Raises
    ------
    ValueError
        For other data than an IRIS raster window or stack, other ``lines``, velocities that do not increase, or a
        window that covers none of ``lines`` over them.
    """
    _check(data)
    return _mg_features(data, velocities, *_crop(data, velocities, lines), _unit(data))


def _ask(data, lines):
    """
    The velocities typed for ``data``, from and to, in km/s, and the lines ticked, at first ``lines``; or None for
    none ticked or Cancel.
    """
    dialog = QtWidgets.QDialog(QtWidgets.QApplication.activeWindow())
    dialog.setWindowTitle(f"IRIS: Mg II features of {data.label}")
    form = QtWidgets.QFormLayout(dialog)
    boxes = []
    for name, value in zip(("from", "to"), VELOCITIES):
        box = QtWidgets.QDoubleSpinBox(objectName=name, decimals=3, minimum=-1000, maximum=1000, suffix=" km/s")
        box.setValue(value)
        form.addRow(f"Velocities {name}:", box)
        boxes.append(box)
    ticks = [QtWidgets.QCheckBox(f"Mg II {line}", objectName=line, checked=line in lines) for line in LINES]
    for tick in ticks:
        form.addRow(tick)
    if not _accepted(dialog, form):
        return None
    lines = tuple(line for line, tick in zip(LINES, ticks) if tick.isChecked())
    return (tuple(box.value() for box in boxes), lines) if lines else None


@messagebox_on_error("Could not compute Mg II features")
def _failed(exc_info):
    raise exc_info[1]


def _saturated(features):
    """What glue's status bar says of the saturated pixels of ``features``, or None for none."""
    counts = features.meta.get("mg_features_saturated")
    if not counts:
        return None
    parts = [
        f"the {line} features at {count} saturated pixel{'s' if count > 1 else ''}" for line, count in counts.items()
    ]
    return f"{features.label}: {' and '.join(parts)} are NaN"


@layer_action(
    "IRIS: Mg II features… (Mg II)",
    single=True,
    data=True,
    check=_covered,
    tooltip="Add irispy's Mg II k and h line centre and emission peak maps of this raster window or stack",
)
@messagebox_on_error("Could not compute Mg II features")
def mg_features_iris(data, data_collection):
    """
    Add the `mg_features` of ``data`` within typed velocities, of the lines ticked, at first those it covers, to the
    data collection, with its helioprojective coordinates linked, and no viewer; glue shows why for data that has
    none. irispy computes them in the background, while glue's status bar says so, and then how many pixels
    saturated, if any.
    """
    chosen = _ask(data, _covered(data))  # checked before asking
    if chosen is None:
        return
    velocities, lines = chosen
    text = f"Computing Mg II features of {data.label}…"
    lines, crop = _crop(data, velocities, lines)
    _start(data_collection, text, _failed, _mg_features, data, velocities, lines, crop, _unit(data), said=_saturated)
