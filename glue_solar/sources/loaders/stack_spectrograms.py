"""The coordinates and times of a stack of IRIS raster scans."""

import numpy as np

from astropy.wcs import WCS
from astropy.wcs.wcsapi.wrappers import BaseWCSWrapper, SlicedLowLevelWCS

# IRIS Level 2 missing-data codes, as in iris_raster_browser (missing=[-200, -199])
MISSING_VALUES = (-200, -199)


def stack_times(cube_sequence):
    """The UTC acquisition time of every raster step of every scan, as `~numpy.datetime64` of shape (scan, step)."""
    times = [cube.axis_world_coords("time", wcs=cube.extra_coords)[0] for cube in cube_sequence]
    return np.stack([time.utc.to_value("datetime64") for time in times])


def stack_wcs(wcses):
    """
    The WCS of a stack of scans of WCSes ``wcses``: scan 0's with a leading ``Scan`` axis of scan numbers, through which
    each scan's pixels take their own scan's coordinates (`_PerScanWCS`).
    """
    from ndcube.wcs.wrappers import CompoundLowLevelWCS

    # A sliced 2D FITS WCS handles the multidimensional pixel arrays Glue uses;
    # astropy's standalone 1D FITS WCS interprets them as coordinate tables.
    scan_wcs = WCS(naxis=2)
    scan_wcs.wcs.ctype = ["LINEAR", "LINEAR"]
    scan_wcs.wcs.cname = ["", "Scan"]
    scan_wcs.wcs.crpix = [1, 1]
    scan_wcs.wcs.crval = [0, 0]
    scan_wcs.wcs.cdelt = [1, 1]
    scan_wcs = SlicedLowLevelWCS(scan_wcs, [slice(None), 0])
    return _PerScanWCS(CompoundLowLevelWCS(wcses[0], scan_wcs), wcses)


class _PerScanWCS(BaseWCSWrapper):
    """
    ``wcs``, scan 0's WCS with a last pixel and world axis ``Scan`` of scan numbers (`stack_wcs`), whose pixels take
    the coordinates of their scan, the nearest, from that scan's own WCS in ``wcses``, and invert through that of the
    scan nearest their ``Scan`` value. The world axes that a scan's pointing moves along its steps, its last pixel axis,
    depend on the scan too.
    """

    def __init__(self, wcs, wcses):
        super().__init__(wcs)
        self._wcses = list(wcses)
        self._matrix = wcs.axis_correlation_matrix
        self._matrix[:-1, -1] = self._matrix[:-1, -2]

    @property
    def axis_correlation_matrix(self):
        return self._matrix.copy()

    def _per_scan(self, method, values, scan):
        """Each scan's WCS ``method`` of the ``values`` at the scan nearest ``scan``, of a square WCS."""
        index = np.clip(np.round(np.asarray(scan, dtype=float)), 0, len(self._wcses) - 1)
        if index.size == 0 or index.min() == index.max():  # one scan, as its own WCS gives them
            return tuple(getattr(self._wcses[int(index.max(initial=0))], method)(*values))
        shape = np.broadcast_shapes(index.shape, *(np.shape(value) for value in values))
        values, index = [np.broadcast_to(value, shape) for value in values], np.broadcast_to(index, shape)
        converted = [np.full(shape, np.nan) for _ in values]
        for k in np.unique(index[~np.isnan(index)]):
            here = index == k
            for array, part in zip(converted, getattr(self._wcses[int(k)], method)(*(v[here] for v in values))):
                array[here] = part
        return tuple(converted)

    def pixel_to_world_values(self, *pixel_arrays):
        *pixel, scan = pixel_arrays
        return (*self._per_scan("pixel_to_world_values", pixel, scan), np.asarray(scan, dtype=float))

    def world_to_pixel_values(self, *world_arrays):
        *world, scan = world_arrays
        return (*self._per_scan("world_to_pixel_values", world, scan), np.asarray(scan, dtype=float))
