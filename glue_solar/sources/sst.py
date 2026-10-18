"""
SST CRISP and CHROMIS cubes as the SST archive exports them from the SSTRED pipeline: SOLARNET FITS files with a
tabulated (-TAB) WCS, read by File → Open Data Set and `sst_data`.
"""

import threading
import warnings
from functools import cached_property
from pathlib import Path
from uuid import uuid4

import dask.array as da
import numpy as np
from glue.config import data_factory
from glue.core.component import Component, DaskComponent
from glue.core.data import Data
from glue.core.state import _load_data_5, _save_data_5

from astropy.io import fits
from astropy.stats import mad_std
from astropy.wcs import WCS, FITSFixedWarning

from glue_solar.sources.loaders.iris import _HeldWCS, _LockedWCS, _logged, _wcs_from_state, _wcs_state
from glue_solar.sources.loaders.lazy import RawStack
from glue_solar.sources.loaders.scan import _is_sst, _primary_header

__all__ = ["is_sst_fits", "sst_data"]

# NIST air wavelengths, in nm, of the lines of the SST archive's cubes: Ca II K and H, H-beta, Fe I 6173, 6301 and 6302,
# H-alpha and Ca II 8542
# ponytail: those lines only; a cube of another line takes the tuning nearest WAVELNTH, the prefilter's center, until its
# line is added here
_LINES = np.array([393.3663, 396.8469, 486.135, 617.3335, 630.1501, 630.2493, 656.279, 854.2091])


def _line_core(waves, wavelnth=None):
    """
    The tuning of the line core, of tunings at ``waves``, in nm: the one nearest the line of `_LINES` within them that is
    nearest ``wavelnth``, the header's WAVELNTH, which is the prefilter's, or the middle tuning's wavelength without it;
    the line's air wavelength itself, not redshifted by the Sun's gravity (232-1). Of tunings as near it to 0.05 pm, half
    the 0.1 pm the table gives the lines to, such as obs 492 Ca II 8542's 9 and 10, each 3.0 pm from it, the one nearer
    the middle tuning. With no line within them, the tuning nearest ``wavelnth``.
    """
    waves = np.asarray(waves)
    center = waves[len(waves) // 2] if wavelnth is None else wavelnth
    lines = _LINES[(waves.min() <= _LINES) & (_LINES <= waves.max())]
    line = lines[np.argmin(abs(lines - center))] if len(lines) else center
    offset = abs(waves - line)
    near = np.flatnonzero(offset <= offset.min() + 5e-5)
    return int(near[np.argmin(abs(near - (len(waves) - 1) / 2))])


class _TabularWCS(_HeldWCS):
    """
    The tabulated WCS of an SST cube as wcslib reads it, on x, y, tuning, any Stokes axis and scan, with the pixel axes
    each world axis depends on, an inverse of its own and its line core, ``core``, the tuning `sst_data` gives it
    (`_line_core`). Its wcslib calls hold a lock of its own, and only that, linked to IRIS data or not: glue-qt computes
    the spectra of a cube of over 1e7 values on worker threads while WCSAxes draws it on the GUI thread, and wcslib
    writes the table's scratch values as it reads them, which gave wrong values and crashed glue. Once linked
    (`_LockedTabularWCS`, as `link_hpc` makes it), the link patches hold `WCS_LOCK` around its links; unlinked it never
    waits for IRIS data's threads.

    SSTRED tabulates the wavelength of each tuning, the time of each tuning of each scan, and the pointing of each scan
    at the field's corners. astropy says each world axis depends on its own pixel axis only, so glue gave every tuning of
    a scan the time of its first. wcslib inverts the table in 0.4 ms a point, and gives NaN for a wavelength or time
    outside it, such as the CRVAL, 0, glue gives for those of linked data that have none. This inverse places a
    longitude and latitude in the scan nearest the time, at the tuning of the wavelength, from the pointing wcslib gives
    there: in the nearest scan for a time outside them, and at the line core for a wavelength outside them (D67).
    """

    core = None

    # glue's autolinker takes `celestial` of a cube beside data of other dimensions with celestial axes, such as a map,
    # and wcslib crashes (SIGSEGV) cutting those axes out of the table; with this, astropy gives the longitude and
    # latitude as quantities rather than a SkyCoord
    has_celestial = False

    @property
    def _lock(self):
        """Its own lock, made at its first use: one, however many threads ask at once."""
        return self.__dict__.setdefault("_lock", threading.RLock())

    def _held(self):
        """
        Its own lock, linked or not: its calls call it again holding it, and one that took `WCS_LOCK` there as
        `link_hpc` linked it waited for good for the GUI thread, which held that and waited for this.
        """
        return self._lock

    @cached_property
    def axis_correlation_matrix(self):
        with self._held():
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
        with self._held():
            (table,) = self.wcs.tab
            return all(table.K[m] == 2 for m, axis in enumerate(table.map) if axis < 2)

    @cached_property
    def _grid(self):
        """
        At each scan and tuning, (scan, tuning) arrays: the longitude and latitude at pixel (0, 0), their steps along x
        and y, and the time; the wavelength of each tuning; and the CRVAL, CDELT and CRPIX of the Stokes axis, if any.
        """
        # ponytail: a pointing linear in x and y, as SSTRED's tables at the field's corners give; a table of more
        # points takes wcslib's inverse (`_corners`), but a bilinear one of corners would want it too
        tunings, scans, stokes = self.pixel_shape[2], self.pixel_shape[-1], [0] * (self.pixel_n_dim - 4)
        t, k = np.indices((scans, tunings))
        x, y = [[0], [1], [0]], [[0], [0], [1]]  # pixel (0, 0), and a step along x and along y
        lon, lat, wave, *_, time = self.pixel_to_world_values(x, y, k.ravel(), *stokes, t.ravel())
        lon, lat = (np.reshape(values, (3, scans, tunings)) for values in (lon, lat))
        with self._held():
            stokes = [(self.wcs.crval[3], self.wcs.cdelt[3], self.wcs.crpix[3])] if stokes else []
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
        lon, lat, wave, *stokes, time = np.broadcast_arrays(
            *(np.asarray(values, dtype=float) for values in world_arrays)
        )
        lon0, lat0, dlon, dlat, times, waves, axes = self._grid
        # the tuning of each wavelength, or the line core for one outside them, as glue gives
        inside = np.isclose(wave, np.clip(wave, waves[0], waves[-1]))  # but for rounding
        w = np.where(inside, np.interp(wave, waves, np.arange(len(waves))), np.nan)
        tuning = np.where(inside, np.round(np.nan_to_num(w)), self.core).astype(int)
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
        stokes = [(s - crval) / cdelt + crpix - 1 for s, (crval, cdelt, crpix) in zip(stokes, axes)]
        return x, y, w, *stokes, t

    def __deepcopy__(self, memo):
        memo[id(self._lock)] = threading.RLock()  # a copy's own, as its wcslib struct is
        return super().__deepcopy__(memo)

    # glue saves a dataset's coordinates in its session, those of data it reloads from a file too
    def __gluestate__(self, context):
        with self._held():
            return {"wcs": _wcs_state(self), "core": self.core}

    @classmethod
    def __setgluestate__(cls, rec, context):
        with warnings.catch_warnings(action="ignore", category=FITSFixedWarning):  # as `sst_data`
            wcs = _wcs_from_state(rec["wcs"])
        wcs.__class__, wcs.core = cls, rec["core"]
        return wcs


class _LockedTabularWCS(_TabularWCS, _LockedWCS):
    """
    An SST cube's `_TabularWCS` once `link_hpc` links it to IRIS data, still behind its own lock: the link patches hold
    `WCS_LOCK` around its links, as they do a `_LockedWCS`'s.
    """


class _Cube(Data):
    """
    An SST cube's dataset, whose sampled statistics of a component held in the file, the color limits of an Image
    layer, its style editor and a Histogram's range, are those of evenly spaced rows and columns of 16 planes, as many
    values as glue samples: glue's 10,000 random values each lie on another page of the file, 0.7 GB read cold and
    0.04 s warm per statistic (SST10), where these lie on a few hundred. Plane k, from 0 to 15, is at the k-th of 16
    evenly spaced tunings, Stokes parameter k modulo their number and the (7k mod 16)-th of 16 evenly spaced scans, so
    every part of the line counts whatever the number of scans (D73); a cube of 16 planes or fewer gives them all. A
    session keeps the class, and reads the ``VAR-EXT`` tables of ``meta`` from the file again.
    """

    def compute_statistic(self, statistic, cid, subset_state=None, axis=None, view=None, random_subset=None, **kwargs):
        sampled = random_subset and subset_state is None and axis is None and view is None
        if sampled and type(self._components.get(cid)) is Component:  # not the cavity error's dask, nor a derived one
            view, random_subset = self._sample(random_subset), None
        return super().compute_statistic(
            statistic, cid, subset_state=subset_state, axis=axis, view=view, random_subset=random_subset, **kwargs
        )

    def _sample(self, size, stokes=None, tuning=None):
        """
        The view of the sample of ``size`` values, or of as many of Stokes parameter ``stokes`` at ``tuning`` alone, from
        16 planes of it in the same way, as the noise level takes them (`_noise`).
        """
        *axes, rows, columns = self.shape
        if stokes is not None:
            axes[1:] = 1, 1  # the planes of a cube of one Stokes parameter and tuning, then moved to them
        if np.prod(axes) <= 16:
            plane = list(np.indices(axes).reshape(len(axes), -1))
        else:
            k = np.arange(16)
            scan = np.linspace(0, axes[0] - 1, 16).round().astype(int)[k * 7 % 16]
            tunings = np.linspace(0, axes[-1] - 1, 16).round().astype(int)
            plane = [scan, k % axes[1], tunings] if len(axes) == 3 else [scan, tunings]
        if stokes is not None:
            plane[1:] = plane[1] + stokes, plane[2] + tuning
        side = max(1, round((size / len(plane[0])) ** 0.5))
        return tuple(index[:, None, None] for index in plane) + (
            np.linspace(0, rows - 1, min(rows, side)).round().astype(int)[:, None],
            np.linspace(0, columns - 1, min(columns, side)).round().astype(int),
        )

    @cached_property
    def _noise(self):
        """
        The noise level of Stokes Q, U and V, by index (F173): the standard deviation of each at the continuum, the end
        tuning farther from the line core, from the median absolute deviation, which the few polarized pixels leave
        alone, of `_sample`'s 10,000 values of it there, NaN, such as a mosaic's edges, left out; 0 if all are NaN.
        """
        waves, core = self.coords._grid[5], self.coords.core
        tuning = max((0, len(waves) - 1), key=lambda k: abs(waves[k] - waves[core]))
        cid = self.main_components[0]
        with warnings.catch_warnings(action="ignore", category=RuntimeWarning):  # 'All-NaN slice encountered'
            return {
                k: np.nan_to_num(mad_std(self[cid, self._sample(10_000, k, tuning)], ignore_nan=True))
                for k in (1, 2, 3)
            }

    @cached_property
    def _field(self):
        """
        The first and last row and column, ``((y0, y1), (x0, x1))``, that can hold the field, a mosaic's NaN border left
        out (P9), from `_sample`'s rows of its planes read whole, the pages its sample reads: the rows between the
        sampled rows next to the outermost with a finite value, and their finite values' columns widened by a row step,
        as a rotated field's corner can lie between them; None if all are NaN.
        """
        *plane, rows, _ = self._sample(10_000)
        rows = rows.ravel()
        finite = np.isfinite(self[self.main_components[0], (*(p[..., 0] for p in plane), rows, slice(None))]).any(0)
        if not finite.any():
            return None
        k, x = np.flatnonzero(finite.any(1)), np.flatnonzero(finite.any(0))
        step = int(np.diff(rows).max(initial=0))
        y0 = rows[k[0] - 1] + 1 if k[0] else 0
        y1 = rows[k[-1] + 1] - 1 if k[-1] + 1 < len(rows) else self.shape[-2] - 1
        return (int(y0), int(y1)), (max(int(x[0]) - step, 0), min(int(x[-1]) + step, self.shape[-1] - 1))

    def __gluestate__(self, context):
        log = getattr(self, "_load_log", None)  # none on a cube restored with its data
        if context.include_data or log is None:
            return _save_data_5(self, context)
        # the file's VAR-EXT tables, 0.15 to 0.2 MB in a session, are read from it again, as the cube's values are
        tables = self.meta.pop("VAR-EXT", {})
        try:
            return {**_save_data_5(self, context), "log": context.id(log)}
        finally:
            self.meta["VAR-EXT"] = tables

    @classmethod
    def __setgluestate__(cls, rec, context):
        restored = _load_data_5(rec, context)
        data = next(restored)
        data.__class__ = cls  # glue's loader makes a Data
        if "log" in rec:  # the file read again, and its log for a session saved from this one
            data._load_log = context.object(rec["log"])
            data.meta["VAR-EXT"] = data._load_log.data[0].meta["VAR-EXT"]
        yield data
        yield from restored


def is_sst_fits(filename, **_kwargs):
    """A CRISP or CHROMIS cube with a tabulated WCS and five axes, as the SST archive exports them."""
    try:
        return _is_sst(_primary_header(filename))
    except (OSError, ValueError, EOFError):  # not a FITS file
        return False


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

    Its axes are the file's, in numpy order: scan, Stokes, tuning, y and x, but for the Stokes axis of length 1 of a
    cube of intensities, which is left out. Its values stay in the file, memory-mapped, and its coordinates are the
    file's tabulated WCS (`_TabularWCS`), with the nominal wavelength of each tuning, given ``SPECSYS = 'TOPOCENT'``
    where the file has none, as astropy needs for a ground-based observatory, and the line core (`_line_core`).
    ``Time`` is the UTC time of each tuning of each scan, as the file's ``DATE-AVG`` table gives it, and ``Cavity
    error`` the wavelength offset of each pixel at each scan from the nominal one, from the file's cavity maps, in the
    unit of the wavelength axis, 0 for a tuning without a map. ``meta['VAR-EXT']`` holds the columns of the file's
    ``VAR-EXT`` tables by name, such as the exposure times (``XPOSURE``) and the seeing (``ATMOS_R0``), each a value per
    scan, tuning or Stokes parameter on the cube's axes, 1 long along those it does not change on, or the table's own
    samples. A glue session refers to the file rather than holding the values.

    Returns
    -------
    `~glue.core.data.Data`
    """
    with fits.open(path, memmap=True) as hdulist:
        header = hdulist[0].header.copy()
        if not header.get("SPECSYS"):
            header["SPECSYS"] = "TOPOCENT"
        # the Stokes axis of a cube of intensities, of length 1, left out of the values and arrays of the file's axes
        stokes = (slice(None), 0) if header["NAXIS4"] == 1 else ()
        # wcslib's notes on the keywords it derives, such as MJDREF from DATEREF
        with warnings.catch_warnings(action="ignore", category=FITSFixedWarning):
            wcs = WCS(header, hdulist)
            wcs = wcs.sub([1, 2, 3, 5]) if stokes else wcs
        wcs.__class__ = _TabularWCS
        wcs.core = _line_core(wcs._grid[5], header.get("WAVELNTH"))
        data = _Cube(label=Path(path).stem, coords=wcs)
        data.meta.update(header.items())
        component = Component(hdulist[0].data[stokes], units=header.get("BUNIT"))
        data.add_component(component, header.get("BTYPE") or "PRIMARY")
        scans, tunings, rows, columns = data.shape[0], *data.shape[-3:]
        seconds = wcs._grid[4]  # since DATEREF, of each scan and tuning
        times = np.datetime64(header["DATEREF"], "ns") + np.round(seconds * 1e9).astype("timedelta64[ns]")
        data.add_component(np.broadcast_to(times[:, None, :, None, None][stokes], data.shape), "Time")
        extvers = _cavity_maps(header, tunings)
        if extvers.any():
            maps = {extver: hdulist["WCSDVARR", extver].data[:, :, 0] for extver in set(extvers.tolist()) - {0}}
            none = np.broadcast_to(np.float32(0), (scans, 1, rows, columns))  # as the nominal wavelength is right
            # by tuning first, in the file until read: dask copies, so reads, a NumPy array it is given
            cavity = da.from_array(
                RawStack([maps.get(extver, none) for extver in extvers]),
                (1, 1, 1, rows, columns),
                name=f"sst-cavity-{uuid4().hex}",
                meta=np.empty((0,) * 5, np.float32),
            )
            cavity = da.broadcast_to(cavity.transpose(1, 2, 0, 3, 4)[stokes], data.shape)
            data.add_component(DaskComponent(cavity, units=header["CUNIT3"]), "Cavity error")
        tables = data.meta["VAR-EXT"] = {}
        for hdu in hdulist:
            if hdu.name.startswith("VAR-EXT-"):  # SOLARNET's variable keywords: one row, a column per keyword
                for name in hdu.columns.names:
                    values = np.array(hdu.data[name][0])  # out of the file, which closes
                    tables[name] = values[stokes] if values.ndim == 5 else values
    return _logged([data], path, sst_data)[0]
