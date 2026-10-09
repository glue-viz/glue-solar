"""Stack a series of IRIS raster scans into one NDCube."""

import tempfile
from pathlib import Path

import numpy as np

from astropy.wcs import WCS
from astropy.wcs.wcsapi.wrappers import BaseWCSWrapper, SlicedLowLevelWCS

# IRIS Level 2 missing-data codes, as in iris_raster_browser (missing=[-200, -199])
MISSING_VALUES = (-200, -199)


def stack_spectrogram_sequence(cube_sequence, memmap=True):
    """
    Given a sequence of IRIS rasters stack them into a single `ndcube.NDCube`.

    Parameters
    ----------
    cube_sequence : `irispy.spectrograph.SpectrogramCubeSequence`
        The raster scans to stack. They must have identical shapes.
    memmap : `bool`
        Use a temporary file to store the stacked data rather than memory.

    Returns
    -------
    tuple
        A 4D cube with a leading scan dimension, plus its `stack_times`.
        Each scan keeps its own WCS (`stack_wcs`).
    """
    from ndcube import NDCube  # with the first stack rather than at glue's launch

    if len(cube_sequence) == 1:
        raise ValueError("No point doing this to one raster")

    target_shape = cube_sequence[0].data.shape
    if any(cube.data.shape != target_shape for cube in cube_sequence):
        raise ValueError("All raster scans must have the same shape to be stacked")

    cube_shape = (len(cube_sequence), *target_shape)
    dtype = np.result_type(cube_sequence[0].data.dtype, np.float32)
    if memmap:
        temporary = None if isinstance(memmap, Path) else tempfile.TemporaryFile()
        output = np.memmap(memmap if isinstance(memmap, Path) else temporary, dtype, "w+", shape=cube_shape)
        if temporary is not None:
            temporary.close()
    else:
        output = np.empty(cube_shape, dtype=dtype)

    for i, cube in enumerate(cube_sequence):
        scan = output[i]
        scan[...] = cube.data
        # irispy's eager read leaves the missing codes in a raster's values
        scan[np.isin(scan, MISSING_VALUES)] = np.nan

    wcs = stack_wcs([cube.wcs for cube in cube_sequence])
    cube = NDCube(output, wcs, meta=dict(cube_sequence[0].meta), unit=cube_sequence[0].unit)
    return cube, stack_times(cube_sequence)


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
