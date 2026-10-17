"""
irispy's red-blue asymmetry of a line in a raster window or a stack of its scans, as a new dataset, for 'IRIS: line
maps…' (`~glue_solar.sources.moments`).
"""

import numpy as np
from glue.core.component import Component

import astropy.units as u

from glue_solar.sources.loaders.iris import WCS_LOCK
from glue_solar.sources.moments import _check, _cube, _dataset, _slabs, _window

__all__ = ["red_blue_asymmetry"]

# The wavelengths 'IRIS: line maps…' takes, in Angstrom below and above the rest wavelength: irispy takes the peak of
# all it is given, which in a Mg II k window can be Mg II h
WAVELENGTHS = (1.0, 1.0)
# iris_xfiles' red-blue settings, in km / s: its double Gaussian fit averages red minus blue over 5 km / s from each of 30,
# 35, ... 50 km / s, so from 30 to 55 km / s (SolarSoft iris/idl/uio/objects/iris_moment__dgf.pro, lines 49-53, and
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
    for rows, values, _ in _slabs(data, crop):
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

    irispy is given the window's ``<label> DN / s`` where it has one, else its values, NaN, -Inf and negative samples
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
