"""Stack a series of IRIS raster scans into one NDCube."""

import tempfile
from pathlib import Path

import numpy as np
from ndcube import NDCube
from ndcube.wcs.wrappers import CompoundLowLevelWCS

from astropy.wcs import WCS
from astropy.wcs.wcsapi.wrappers import SlicedLowLevelWCS


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
        A 4D cube with a leading scan dimension, plus a matching
        spatial `~numpy.datetime64` array containing the acquisition time of
        every pixel. The time array is broadcastable over the cube's
        wavelength axis. The first scan supplies the nominal spatial WCS.
    """
    if len(cube_sequence) == 1:
        raise ValueError("No point doing this to one raster")

    target_wcs = cube_sequence[0].wcs
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
    acquisition_times = np.empty(cube_shape[:-1], dtype="datetime64[ns]")

    for i, cube in enumerate(cube_sequence):
        source = np.asarray(cube.data, dtype=dtype)
        if cube.mask is not None:
            source = source.copy()
            source[np.asarray(cube.mask, dtype=bool)] = np.nan
        times = cube.axis_world_coords("time", wcs=cube.extra_coords)[0].utc.to_value("datetime64")
        acquisition_times[i] = np.broadcast_to(
            times.reshape((len(times),) + (1,) * (source.ndim - 2)),
            source.shape[:-1],
        )
        output[i] = source

    # A sliced 2D FITS WCS handles the multidimensional pixel arrays Glue uses;
    # astropy's standalone 1D FITS WCS interprets them as coordinate tables.
    scan_wcs = WCS(naxis=2)
    scan_wcs.wcs.ctype = ["LINEAR", "LINEAR"]
    scan_wcs.wcs.cname = ["", "Scan"]
    scan_wcs.wcs.crpix = [1, 1]
    scan_wcs.wcs.crval = [0, 0]
    scan_wcs.wcs.cdelt = [1, 1]
    scan_wcs = SlicedLowLevelWCS(scan_wcs, [slice(None), 0])
    out_wcs = CompoundLowLevelWCS(target_wcs, scan_wcs)

    return (
        NDCube(
            output,
            out_wcs,
            mask=~np.isfinite(output),
            meta=dict(cube_sequence[0].meta),
            unit=cube_sequence[0].unit,
        ),
        acquisition_times,
    )
