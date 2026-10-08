"""
'IRIS: remove dust': a slit-jaw image with irispy's dust removed, as a new dataset; and 'IRIS: radiometric
calibration': a raster window's DN/s in radiance, as a glue derived component.
"""

import gc

import numpy as np
from glue.config import layer_action
from glue.core.component import Component
from glue_qt.utils.decorators import messagebox_on_error

import astropy.units as u
from astropy.wcs.wcsapi.wrappers import SlicedLowLevelWCS

from glue_solar.quicklook import _role
from glue_solar.sources.loaders.iris import WCS_LOCK, _add_exposure, _dataset, _per_frame
from glue_solar.sources.moments import _check, _start, _unit

__all__ = ["radiometric_calibration", "radiometric_calibration_iris", "remove_dust", "remove_dust_iris"]

# The frames on either side of a frame that irispy takes its replacements from: its default, as SolarSoft's
FRAMES = 2
# Samples per irispy call, which holds about 25 bytes for each: four times the line moments' slab, since each slab
# reads `FRAMES` more on either side (17 s, not 22 s, for the 400 frames of 4000255147's SJI 1400; 15 s in one call)
SLAB = 2**23


def _check_sji(data):
    """Raise why ``data`` is not an IRIS slit-jaw image, (frame, y, x)."""
    if _role(data) != "sji" or data.ndim != 3:
        raise ValueError(f"{data.label} is not an IRIS slit-jaw image.")


def remove_dust(data):
    """
    ``data``, an IRIS slit-jaw image, with irispy's dust removed, as a new dataset ``<label> dust removed`` on its
    coordinates, with its ``Time``, ``Exposure time``, ``<label> DN/s`` and ``meta``.

    irispy's ``SJICube.remove_dust`` is given the scaled values, NaN masked, a slab of frames at a time with the
    `FRAMES` on either side it takes replacements from, and each frame's exposure time. It finds dust where a value
    lies above -199 and below 0.5 DN, and the pixels about it, and puts in the median of those pixels over the frames
    on either side, scaled by the exposure times, else of the 5 by 5 pixels about it; dust it cannot replace is NaN.
    The values are float32, as the loader's.

    Raises
    ------
    ValueError
        For other data than an IRIS slit-jaw image.
    """
    from irispy.sji import SJICube

    _check_sji(data)
    cid, exposure = data.main_components[0], data.id["Exposure time"]
    values = np.empty(data.shape, np.float32)
    frames = max(1, SLAB // (data.shape[1] * data.shape[2]))
    for start in range(0, data.shape[0], frames):
        low, high = max(0, start - FRAMES), min(data.shape[0], start + frames + FRAMES)
        rows = (slice(low, high),)
        slab = data[cid, rows]  # scaled float32, NaN where missing: irispy finds no dust in the raw int16
        meta = {"exposure time": data[exposure, (*rows, 0, 0)] * u.s}
        with WCS_LOCK:
            wcs = SlicedLowLevelWCS(data.coords._wcs, (*rows, slice(None), slice(None)))
        clean = SJICube(slab, wcs, mask=np.isnan(slab), meta=meta).remove_dust(temporal_window=FRAMES)
        kept = slice(start - low, start - low + frames)
        values[start : start + frames] = np.where(clean.mask[kept], np.nan, clean.data[kept])
        gc.collect()  # ndcube's cubes are reference cycles, holding the slab's values, and irispy's work ages them
    lead = (slice(None), 0, 0)
    dust = _dataset(
        data.coords._wcs,
        dict(data.meta),
        data.get_component(cid).units,
        values,
        f"{data.label} dust removed",
        color=data.style.color,
        cmap=data.style.preferred_cmap,
        missing=(),
    )
    dust.add_component(_per_frame(data[data.id["Time"], lead], dust.shape), "Time")
    _add_exposure(dust, data[exposure, lead])
    return dust


@messagebox_on_error("Could not remove dust")
def _failed(exc_info):
    raise exc_info[1]


@layer_action(
    "IRIS: remove dust",
    single=True,
    data=True,
    tooltip="Add this slit-jaw image with irispy's dust removed",
)
@messagebox_on_error("Could not remove dust")
def remove_dust_iris(data, data_collection):
    """
    Add ``data`` with its dust removed (`remove_dust`) to the data collection, with its helioprojective coordinates
    linked, and no viewer; glue shows why for other data. irispy removes it in the background, while glue's status bar
    says so.
    """
    _check_sji(data)
    _start(data_collection, f"Removing dust from {data.label}…", _failed, remove_dust, data)


def radiometric_calibration(data):
    """
    Add ``<label> radiance per DN/s`` to ``data``, an IRIS raster window of one scan: irispy's factor from DN/s to
    radiance at each of its wavelengths, held as one spectrum; and ``<label> radiance``, its ``<label> DN/s`` times
    it, a glue derived component, in irispy's ``RADIANCE_UNIT``, erg / (Å cm2 s sr).

    The factor is irispy's ``radiometric_calibration``'s: ``calculate_dn_to_radiance_factor`` of the window's
    wavelengths, detector, spectral dispersion and pixel solid angle, with the effective area of irispy's latest
    response at its ``DATE_OBS``; NaN at wavelengths the response does not cover.

    Returns
    -------
    `~glue.core.component_id.ComponentID`
        The derived component's.

    Raises
    ------
    ValueError
        For other data than an IRIS raster window of one scan, or one calibrated already.
    """
    from irispy.spectrograph import SpectrogramCube
    from irispy.utils.constants import RADIANCE_UNIT
    from irispy.utils.response import get_latest_response
    from irispy.utils.spectrograph import calculate_dn_to_radiance_factor

    _check(data, "radiance components")
    cid = data.main_components[0]
    label = f"{cid.label} radiance"
    if data.find_component_id(label) is not None:
        raise ValueError(f"{data.label} has its radiance already.")
    rate, unit = data.id[f"{cid.label} DN/s"], _unit(data)
    with WCS_LOCK:  # irispy reads the window's astropy WCS
        cube = SpectrogramCube(np.broadcast_to(np.float32(0), data.shape), data.coords._wcs, meta=data.meta)
        factor = calculate_dn_to_radiance_factor(
            iris_response=get_latest_response(cube.meta.date_reference),
            wavelength=cube.axis_world_coords(cube.wavelength_axis)[0],
            detector_type=cube.meta.detector_band,
            spectral_dispersion_per_pixel=cube.spectral_dispersion,
            solid_angle=cube.solid_angle,
        )
    factor = (unit.to(u.photon / u.s) * u.photon / u.s * factor).to_value(RADIANCE_UNIT)  # of 1 DN/s, as irispy's
    per_rate = Component(np.broadcast_to(factor, data.shape), units=str(RADIANCE_UNIT / (u.DN / u.s)))
    radiance = rate * data.add_component(per_rate, f"{cid.label} radiance per DN/s")  # a view: one spectrum held
    data.add_component_link(radiance, label).units = str(RADIANCE_UNIT)
    return radiance.get_to_id()


@layer_action(
    "IRIS: radiometric calibration",
    single=True,
    data=True,
    tooltip="Add this raster window's DN/s in radiance, erg / (Å cm2 s sr), with irispy's calibration",
)
@messagebox_on_error("Could not calibrate the radiance")
def radiometric_calibration_iris(data, data_collection):
    """Add the `radiometric_calibration` components to ``data``; glue shows why for other data or a second run."""
    radiometric_calibration(data)
