"""
'IRIS: detect UV bursts…': irispy's UV bursts in a Si IV raster window, or a stack of its scans, or a 1400 Å slit-jaw
image, as a map of their labels and a table of them, two new datasets.
"""

import numpy as np
from glue.config import layer_action
from glue.core.component import Component
from glue.core.data import Data
from glue_qt.utils.decorators import messagebox_on_error
from qtpy import QtWidgets

import astropy.units as u
from astropy.coordinates import SkyCoord
from astropy.table import vstack
from astropy.time import Time
from astropy.wcs.wcsapi.wrappers import SlicedLowLevelWCS

from glue_solar.quicklook import _role, _wavelengths
from glue_solar.sources.loaders.iris import WCS_LOCK, _GlueWCS, _irispy_meta, _per_frame
from glue_solar.sources.moments import _accepted, _check, _dataset, _start

__all__ = ["bursts_iris", "si_iv_bursts", "sji_bursts"]

# irispy's defaults: the half-width averaged about Si IV 1402.77 Å in km/s and the particle-hit test factor; the
# slit-jaw threshold in standard deviations and the fewest pixels of an event
VELOCITY_RANGE = 50.0
MEDIAN_FACTOR = 10.0
SIGMA_FACTOR = 10.0
MIN_PIXELS = 2


def _is_sji(data):
    """Whether ``data`` is a 1400 Å slit-jaw image, else an IRIS raster window or stack; raise why for neither."""
    if _role(data) == "sji" and data.ndim == 3:
        if data.meta.get("TWAVE1") != 1400:
            raise ValueError(f"{data.label} is not a 1400 Å slit-jaw image, in which irispy finds UV bursts.")
        return True
    if _role(data) != "raster":
        raise ValueError(f"{data.label} is not an IRIS raster window or slit-jaw image.")
    _check(data)
    return False


def _crop(data, velocity_range):
    """
    The wavelength pixels of ``data`` from the first to the last within ``velocity_range`` km/s of Si IV 1402.77 Å, a
    pixel wider at either end, so irispy picks the same within them; raises why for none.
    """
    from irispy.utils.bursts import _SI_IV

    wavelengths, _ = _wavelengths(data)
    velocity = (wavelengths * u.AA).to_value(u.km / u.s, equivalencies=u.doppler_optical(_SI_IV))
    inside = np.flatnonzero(np.abs(velocity) <= velocity_range)
    if not inside.size:
        raise ValueError(
            f"No wavelength of {data.label} ({wavelengths[0]:.2f} to {wavelengths[-1]:.2f} Å) lies within "
            f"{velocity_range} km/s of Si IV 1402.77 Å."
        )
    return slice(max(inside[0] - 1, 0), min(inside[-1] + 2, wavelengths.size))


def _table(events, label, meta, offset):
    """
    A dataset of irispy's ``events``, a row each: ``time`` as glue's times, and ``coordinate`` as
    ``coordinate.Tx`` and ``coordinate.Ty`` in arcsec, as glue reads a FITS table's, plus the data's pointing ``offset``.
    """
    table = Data(label=label)
    table.meta = meta
    for name, column in events.columns.items():
        if isinstance(column, SkyCoord):
            for axis, shift in zip(("Tx", "Ty"), offset):
                values = getattr(column, axis).to_value(u.arcsec) + shift
                table.add_component(Component(values, units="arcsec"), f"{name}.{axis}")
        elif isinstance(column, Time):
            table.add_component(Component.autotyped(column.utc.to_value("datetime64")), name)
        else:
            table.add_component(Component(np.asarray(column), units=str(getattr(column, "unit", None) or "")), name)
    return table


def _si_iv_bursts(data, crop, threshold, velocity_range, median_factor):
    """`si_iv_bursts` given ``crop`` of the wavelength pixels; on any thread."""
    from irispy.spectrograph import SpectrogramCube
    from irispy.utils.bursts import find_si_iv_bursts
    from irispy.utils.constants import DN_UNIT

    labels, tables = [], []
    for k, scan in enumerate(np.ndindex(data.shape[:-3])):  # each scan of a stack, as that scan alone gives them
        rows = (*scan, slice(None), slice(None), crop)
        values = data[data.main_components[0], rows]  # scaled float32 DN, NaN where missing
        times = Time(data[data.id["Time"], (*scan, slice(None), 0, 0)], scale="utc")
        with WCS_LOCK:  # irispy reads the wavelengths and positions through the raster's astropy WCS
            meta = _irispy_meta(data, scan)
            cube = SpectrogramCube(
                values,
                SlicedLowLevelWCS(data.coords._wcs, rows),
                unit=DN_UNIT[meta.detector_band],
                mask=np.isnan(values),
                meta=meta.slice[rows[len(scan) :]],  # irispy's, with each step's exposure time
            )
            cube.extra_coords.add("time", 0, times, physical_types="time")
            found, events = find_si_iv_bursts(
                cube, threshold=threshold, velocity_range=velocity_range * u.km / u.s, median_factor=median_factor
            )
        # numbered on through the scans, as irispy numbers a sequence's
        count = sum(len(table) for table in tables)
        labels.append(np.where(found.data > 0, found.data + count, 0))
        events["label"] += count
        events["raster"] = k
        tables.append(events)
    maps = _dataset(data, f"{data.label} bursts")
    thresholds = tuple(float(events.meta["threshold"].value) for events in tables)
    maps.meta.update(
        bursts_threshold=thresholds if data.ndim == 4 else thresholds[0],  # a stack's, each scan's at its own date
        bursts_velocity_range=velocity_range,
        bursts_median_factor=median_factor,
    )
    maps.add_component(Component(np.reshape(labels, data.shape[:-1])), "label")
    events = vstack(tables, metadata_conflicts="silent")  # their thresholds are the map's
    return [maps, _table(events, f"{data.label} burst events", dict(maps.meta), data.coords.pointing_offset)]


def si_iv_bursts(data, threshold=None, velocity_range=VELOCITY_RANGE, median_factor=MEDIAN_FACTOR):
    """
    irispy's UV bursts in ``data``, an IRIS raster window of one scan covering Si IV 1402.77 Å or a stack of its
    scans, by ``find_si_iv_bursts``: a map of their labels on the window's scans, raster steps and slit pixels, and a
    table of them; a stack's scan by scan, each as that scan alone gives them, at its own coordinates, times, exposure
    times and date, its labels numbered on from the previous scan's, as irispy numbers a sequence's rasters.

    irispy is given the window's scaled DN, NaN masked, and only the wavelengths within ``velocity_range`` of the line,
    and finds a burst pixel where their mean over the step's exposure time reaches ``threshold`` and stays below
    ``median_factor`` times their median; pixels that touch, diagonally too, are one burst. The map,
    ``<label> bursts``, has ``label``, 0 outside bursts and 1 to N for the N bursts, and ``meta`` with the
    observation's ``OBSID`` and ``STARTOBS``, ``bursts_threshold``, irispy's in DN/s per wavelength bin, a stack's a
    tuple of each scan's, ``bursts_velocity_range`` and ``bursts_median_factor``. The table, ``<label> burst events``,
    has irispy's columns a row a burst: ``label``, ``raster``, the scan, ``npix``, and the ``step``, ``y``, ``time``,
    ``coordinate.Tx``, ``coordinate.Ty`` and ``intensity`` of its brightest pixel; and the map's ``meta``.

    Parameters
    ----------
    data : `~glue.core.data.Data`
        An IRIS raster window of one scan, (raster step, slit, wavelength), or a stack of its scans, (scan, raster
        step, slit, wavelength).
    threshold : float, optional
        In DN/s per wavelength bin of data summed by 2 in wavelength, which irispy scales by the data's summing; None
        for irispy's, 500 DN/s scaled by the effective area at the observation's date, each scan's.
    velocity_range : float
        The half-width averaged, in km / s.
    median_factor : float or None
        The particle-hit test's factor; None switches it off.

    Raises
    ------
    ValueError
        For other data than an IRIS raster window or stack, or one with no wavelength within ``velocity_range``.
    """
    if _is_sji(data):
        raise ValueError(f"{data.label} is not an IRIS raster window.")
    crop = _crop(data, velocity_range)
    return _si_iv_bursts(data, crop, threshold, velocity_range, median_factor)


def sji_bursts(data, sigma_factor=SIGMA_FACTOR, min_pixels=MIN_PIXELS):
    """
    irispy's UV bursts in ``data``, a 1400 Å slit-jaw image, by ``find_bright_image_events``: ``find_sji_bursts``
    without its band check, which needs irispy's ``meta``, so that a dust-removed image works too. A cube of their
    labels on its coordinates, and a table of them.

    irispy is given the scaled values, NaN masked, and finds a burst pixel at ``sigma_factor`` standard deviations
    above the median of its frame; pixels that touch within a frame, diagonally too, are one burst, and bursts of
    fewer than ``min_pixels`` are dropped. The cube, ``<label> bursts``, has ``label``, 0 outside bursts and 1 to N for
    the N bursts, the image's ``Time`` and ``meta``, its per-frame pointing included, so that the time sync and the
    helioprojective links reach it, and ``bursts_sigma_factor`` and ``bursts_min_pixels``. The table,
    ``<label> burst events``, has irispy's columns a row a burst: ``label``, ``frame``, ``npix``, the frame's
    ``threshold``, and the ``y``, ``x``, ``time``, ``coordinate.Tx``, ``coordinate.Ty`` and ``intensity`` of its
    brightest pixel; and the observation's ``OBSID`` and ``STARTOBS`` and those parameters in ``meta``.

    Raises
    ------
    ValueError
        For other data than a 1400 Å slit-jaw image.
    """
    from irispy.sji import SJICube
    from irispy.utils.bursts import find_bright_image_events
    from irispy.utils.constants import DN_UNIT

    if not _is_sji(data):
        raise ValueError(f"{data.label} is not an IRIS slit-jaw image.")
    values = data[data.main_components[0], (slice(None),)]  # scaled float32, NaN where missing, read with a view
    # ponytail: one irispy call on every frame, about 6 times the image's float32 at its peak (1.6 GB for the 400
    # frames of 4000255147's SJI 1400); slabs of frames, their labels offset, if larger images need less
    cube = SJICube(values, data.coords._wcs, unit=DN_UNIT["SJI"], mask=np.isnan(values), meta=data.meta)
    labels, events = find_bright_image_events(cube, sigma_factor=sigma_factor, min_pixels=min_pixels)
    parameters = {"bursts_sigma_factor": sigma_factor, "bursts_min_pixels": min_pixels}
    bursts = Data(label=f"{data.label} bursts", coords=_GlueWCS(data.coords._wcs))
    bursts.coords.pointing_offset = data.coords.pointing_offset
    bursts.meta = {**data.meta, **parameters}
    bursts.add_component(Component(labels.data), "label")
    bursts.add_component(_per_frame(data[data.id["Time"], (slice(None), 0, 0)], bursts.shape), "Time")
    meta = {key: data.meta[key] for key in ("OBSID", "STARTOBS") if key in data.meta}
    table = _table(events, f"{data.label} burst events", {**meta, **parameters}, data.coords.pointing_offset)
    return [bursts, table]


def _ask(data, sji):
    """irispy's parameters typed for ``data``, a slit-jaw image's if ``sji``, by name; or None for Cancel."""
    dialog = QtWidgets.QDialog(QtWidgets.QApplication.activeWindow())
    dialog.setWindowTitle(f"IRIS: UV bursts in {data.label}")
    form = QtWidgets.QFormLayout(dialog)
    if sji:
        sigma = QtWidgets.QDoubleSpinBox(objectName="sigma_factor", decimals=1, maximum=1000)
        sigma.setValue(SIGMA_FACTOR)
        form.addRow("Threshold [standard deviations]:", sigma)
        pixels = QtWidgets.QSpinBox(objectName="min_pixels", minimum=1, maximum=10**6)
        pixels.setValue(MIN_PIXELS)
        form.addRow("Fewest pixels of a burst:", pixels)
        return {"sigma_factor": sigma.value(), "min_pixels": pixels.value()} if _accepted(dialog, form) else None
    threshold = QtWidgets.QLineEdit(objectName="threshold", placeholderText="irispy's, from the effective area")
    form.addRow("Threshold [DN/s, summed by 2]:", threshold)
    velocity = QtWidgets.QDoubleSpinBox(objectName="velocity_range", decimals=1, maximum=1000, suffix=" km/s")
    velocity.setValue(VELOCITY_RANGE)
    form.addRow("Velocities averaged, ±:", velocity)
    # 0 would find no burst: it switches irispy's test off
    median = QtWidgets.QDoubleSpinBox(objectName="median_factor", decimals=1, maximum=1000, specialValueText="off")
    median.setValue(MEDIAN_FACTOR)
    form.addRow("Particle-hit test, times the median:", median)
    if not _accepted(dialog, form):
        return None
    text = threshold.text().strip()
    try:
        value = float(text) if text else None
    except ValueError:
        raise ValueError(f"'{text}' is not a threshold in DN/s, such as 500.") from None
    return {"threshold": value, "velocity_range": velocity.value(), "median_factor": median.value() or None}


@messagebox_on_error("Could not detect UV bursts")
def _failed(exc_info):
    raise exc_info[1]


def _found(datasets):
    """What glue's status bar says of the bursts found."""
    count = datasets[1].size
    return f"{datasets[0].label}: {count} burst{'' if count == 1 else 's'}"


@layer_action(
    "IRIS: detect UV bursts…",
    single=True,
    data=True,
    tooltip="Add irispy's UV burst labels and table of this Si IV raster window, stack or 1400 Å slit-jaw image",
)
@messagebox_on_error("Could not detect UV bursts")
def bursts_iris(data, data_collection):
    """
    Add the `si_iv_bursts` of a raster window or stack, or the `sji_bursts` of a 1400 Å slit-jaw image, with irispy's
    parameters typed, to the data collection, the map's helioprojective coordinates linked, and no viewer; glue shows
    why for data that has none. irispy finds them in the background, while glue's status bar says so, and then how
    many.
    """
    sji = _is_sji(data)  # before asking
    if not sji:
        _crop(data, VELOCITY_RANGE)
    parameters = _ask(data, sji)
    if parameters is None:
        return
    text = f"Detecting UV bursts in {data.label}…"
    if sji:
        _start(data_collection, text, _failed, sji_bursts, data, *parameters.values(), said=_found)
    else:
        crop = _crop(data, parameters["velocity_range"])
        _start(data_collection, text, _failed, _si_iv_bursts, data, crop, *parameters.values(), said=_found)
