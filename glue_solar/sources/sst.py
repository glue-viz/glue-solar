"""
SST CRISP and CHROMIS cubes as the SST archive exports them from the SSTRED pipeline: SOLARNET FITS files with a
tabulated (-TAB) WCS, read by File → Open Data Set and `sst_data`.
"""

import warnings
from functools import cached_property
from pathlib import Path
from uuid import uuid4

import dask.array as da
import numpy as np
from glue.config import data_factory
from glue.core.component import Component, DaskComponent
from glue.core.data import Data

from astropy.io import fits
from astropy.wcs import WCS, FITSFixedWarning

from glue_solar.sources.loaders.iris import WCS_LOCK, _LockedWCS, _logged, _wcs_from_state, _wcs_state
from glue_solar.sources.loaders.lazy import RawStack
from glue_solar.sources.loaders.scan import _primary_header

__all__ = ["is_sst_fits", "sst_data"]


class _TabularWCS(_LockedWCS):
    """
    The tabulated WCS of an SST cube as wcslib reads it, behind `WCS_LOCK`, with the pixel axes each world axis depends
    on and an inverse of its own.

    SSTRED tabulates the wavelength of each tuning, the time of each tuning of each scan, and the pointing of each scan
    at the field's corners. astropy says each world axis depends on its own pixel axis only, so glue gave every tuning of
    a scan the time of its first. wcslib inverts the table in 0.4 ms a point, and gives NaN for a wavelength or time
    outside it, such as the CRVAL, 0, glue gives for those of linked data that have none. This inverse places a
    longitude and latitude in the scan nearest the time, at the tuning of the wavelength, from the pointing wcslib gives
    there: in the nearest scan for a time outside them, and at the line core, the middle tuning, for a wavelength
    outside them (D67).
    """

    # glue's autolinker takes `celestial` of a cube beside data of other dimensions with celestial axes, such as a map,
    # and wcslib crashes (SIGSEGV) cutting those axes out of the table; with this, astropy gives the longitude and
    # latitude as quantities rather than a SkyCoord
    has_celestial = False

    @cached_property
    def axis_correlation_matrix(self):
        with WCS_LOCK:
            matrix = WCS.axis_correlation_matrix.fget(self).copy()
            (table,) = self.wcs.tab
        # each coordinate of the table, as each index of it, is that of world axis map[m], and pixel axis, PC being 1
        for m, world in enumerate(table.map):
            for k, pixel in enumerate(table.map):
                matrix[world, pixel] |= np.ptp(table.coord[..., m], axis=table.M - 1 - k).any()
        return matrix

    @cached_property
    def _corners(self):
        """Whether the table gives the pointing at the field's corners only, as SSTRED's do, which the inverse solves."""
        with WCS_LOCK:
            (table,) = self.wcs.tab
            return all(table.K[m] == 2 for m, axis in enumerate(table.map) if axis < 2)

    @cached_property
    def _grid(self):
        """
        At each scan and tuning, (scan, tuning) arrays: the longitude and latitude at pixel (0, 0), their steps along x
        and y, and the time; the wavelength of each tuning; and the Stokes axis's CRVAL, CDELT and CRPIX.
        """
        # ponytail: a pointing linear in x and y, as SSTRED's tables at the field's corners give; a table of more
        # points takes wcslib's inverse (`_corners`), but a bilinear one of corners would want it too
        _, _, tunings, _, scans = self.pixel_shape
        t, k = np.indices((scans, tunings))
        lon, lat, wave, _, time = self.pixel_to_world_values([[0], [1], [0]], [[0], [0], [1]], k.ravel(), 0, t.ravel())
        lon, lat = (np.reshape(values, (3, scans, tunings)) for values in (lon, lat))
        with WCS_LOCK:
            stokes = self.wcs.crval[3], self.wcs.cdelt[3], self.wcs.crpix[3]
        return (
            lon[0],
            lat[0],
            lon[1:] - lon[0],
            lat[1:] - lat[0],
            time[0].reshape(scans, tunings),
            wave[0, :tunings],
            stokes,
        )

    def world_to_pixel_values(self, *world_arrays):
        if not self._corners:  # wcslib's, NaN for a wavelength or time outside the table
            return super().world_to_pixel_values(*world_arrays)
        lon, lat, wave, stokes, time = np.broadcast_arrays(
            *(np.asarray(values, dtype=float) for values in world_arrays)
        )
        lon0, lat0, dlon, dlat, times, waves, (crval, cdelt, crpix) = self._grid
        # the tuning of each wavelength, or the line core, the middle tuning, for one outside them, as glue gives
        inside = np.isclose(wave, np.clip(wave, waves[0], waves[-1]))  # but for rounding
        w = np.where(inside, np.interp(wave, waves, np.arange(len(waves))), np.nan)
        tuning = np.where(inside, np.round(np.nan_to_num(w)), len(waves) // 2).astype(int)
        x, y, t = (np.full(lon.shape, np.nan) for _ in range(3))
        for k in np.unique(tuning):
            at = tuning == k
            # the scan nearest each time, ties to the earlier, the nearest end outside them
            t[at] = np.interp(time[at], times[:, k], np.arange(len(times)))
            scan = np.searchsorted((times[1:, k] + times[:-1, k]) / 2, time[at])
            u, v = lon[at] - lon0[scan, k], lat[at] - lat0[scan, k]
            (a, c), (b, d) = dlon[:, scan, k], dlat[:, scan, k]  # d lon / dx, d lon / dy; d lat / dx, d lat / dy
            x[at], y[at] = (d * u - c * v) / (a * d - b * c), (a * v - b * u) / (a * d - b * c)
        x[np.isnan(t)] = y[np.isnan(t)] = np.nan  # no time
        return x, y, w, (stokes - crval) / cdelt + crpix - 1, t

    # glue saves a dataset's coordinates in its session, those of data it reloads from a file too
    def __gluestate__(self, context):
        with WCS_LOCK:
            return {"wcs": _wcs_state(self)}

    @classmethod
    def __setgluestate__(cls, rec, context):
        with warnings.catch_warnings(action="ignore", category=FITSFixedWarning):  # as `sst_data`
            wcs = _wcs_from_state(rec["wcs"])
        wcs.__class__ = cls
        return wcs


def is_sst_fits(filename, **_kwargs):
    """A CRISP or CHROMIS cube with a tabulated WCS and five axes, as the SST archive exports them."""
    try:
        header = _primary_header(filename)
    except (OSError, ValueError, EOFError):  # not a FITS file
        return False
    instrument, axes = header.get("INSTRUME"), str(header.get("CTYPE1"))
    return instrument in ("CRISP", "CHROMIS") and axes.endswith("-TAB") and header.get("NAXIS") == 5


def _cavity_maps(header, tunings):
    """
    The ``EXTVER`` of the ``WCSDVARR`` cavity map of each tuning, 0 for none. SSTRED's record-valued ``DW3`` keywords
    give each map, one per CHROMIS prefilter, from its ``EXTVER``: it applies to every tuning, or with ``OFFSET.3`` and
    ``SCALE.3`` to those whose index plus the offset, times the scale, lies in ]0.5, 1.5[ (its ``red_fitscube_addcmap``).
    """
    extvers, index = np.zeros(tunings, int), np.arange(tunings)
    maps = []
    for card in header["DW3.*"].cards:
        field = card.keyword.split(".", 1)[1]
        if field == "EXTVER":
            maps.append({})
        maps[-1][field] = card.value
    for keys in maps:
        position = (index + keys["OFFSET.3"]) * keys["SCALE.3"] if "SCALE.3" in keys else np.ones(tunings)
        extvers[(0.5 < position) & (position < 1.5)] = keys["EXTVER"]
    return extvers


@data_factory("SST CRISP or CHROMIS cube (SOLARNET FITS)", is_sst_fits, priority=200)  # glue's own "FITS file" is 100
def sst_data(path):
    """
    Load an SST CRISP or CHROMIS cube, as the SST archive exports them from the SSTRED pipeline, as one dataset.

    Its axes are the file's, in numpy order: scan, Stokes, tuning, y and x. Its values stay in the file, memory-mapped,
    and its coordinates are the file's tabulated WCS (`_TabularWCS`), with the nominal wavelength of each tuning, given
    ``SPECSYS = 'TOPOCENT'`` where the file has none, as astropy needs for a ground-based observatory. ``Time`` is the
    UTC time of each tuning of each scan, and ``Cavity error`` the wavelength offset of each pixel at each scan from the
    nominal one, from the file's cavity maps, in the unit of the wavelength axis, NaN for a tuning without a map. The
    file's ``VAR-EXT`` tables are left out. A glue session refers to the file rather than holding the values.

    Returns
    -------
    `~glue.core.data.Data`
    """
    with fits.open(path, memmap=True) as hdulist:
        header = hdulist[0].header.copy()
        if not header.get("SPECSYS"):
            header["SPECSYS"] = "TOPOCENT"
        # wcslib's notes on the keywords it derives, such as MJDREF from DATEREF
        with warnings.catch_warnings(action="ignore", category=FITSFixedWarning):
            wcs = _TabularWCS(header, hdulist)
        data = Data(label=Path(path).stem, coords=wcs)
        data.meta.update(header.items())
        data.add_component(Component(hdulist[0].data, units=header.get("BUNIT")), header.get("BTYPE") or "PRIMARY")
        scans, _, tunings, rows, columns = data.shape
        seconds = wcs._grid[4]  # since DATEREF, of each scan and tuning
        times = np.datetime64(header["DATEREF"], "ns") + np.round(seconds * 1e9).astype("timedelta64[ns]")
        data.add_component(np.broadcast_to(times[:, None, :, None, None], data.shape), "Time")
        extvers = _cavity_maps(header, tunings)
        if extvers.any():
            maps = {extver: hdulist["WCSDVARR", extver].data[:, :, 0] for extver in set(extvers.tolist()) - {0}}
            none = np.broadcast_to(np.float32(np.nan), (scans, 1, rows, columns))
            # by tuning first, in the file until read: dask copies, so reads, a NumPy array it is given
            cavity = da.from_array(
                RawStack([maps.get(extver, none) for extver in extvers]),
                (1, 1, 1, rows, columns),
                name=f"sst-cavity-{uuid4().hex}",
                meta=np.empty((0,) * 5, np.float32),
            )
            cavity = da.broadcast_to(cavity.transpose(1, 2, 0, 3, 4), data.shape)
            data.add_component(DaskComponent(cavity, units=header["CUNIT3"]), "Cavity error")
    return _logged([data], path, sst_data)[0]
