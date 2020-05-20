"""
Reproject a series of IRIS raster scans in to one NDCube.

"""
import numpy as np
import tempfile
from pathlib import Path

import dask.array as da
import astropy.units as u
import sunpy.coordinates
from astropy.time import Time
from astropy.wcs import WCS
from reproject.interpolation import reproject_interp

from sunraster.io.iris import read_iris_spectrograph_level2_fits
from ndcube import NDCube


def stack_spectrogram_sequence(cube_sequence, memmap=True, reproject=False):
    """
    Given a sequence of IRIS rasters stack them into a single `ndcube.NDCube`.

    .. warning::

        This is intended to be used for plotting only, it will not preserve the
        flux in the image.

    Parameters
    ----------
    cube_sequence : `sunraster.spectrogram_sequence.RasterSequence`
        The input arrays to regrid.

    memmap : `bool`
        Use a temporary file to store the re-gridded data in rather than in memory.

    Returns
    -------
    `ndcube.NDCube`: A 4D cube with a new time dimension

    """
    if len(cube_sequence.data) == 1:
        raise ValueError("No point doing this to one raster")

    if memmap:
        if not isinstance(memmap, Path):
            memmap = tempfile.TemporaryFile()

    target_wcs = cube_sequence[0].wcs
    target_shape = cube_sequence[0].data.shape

    cube_shape = tuple([len(cube_sequence.data)] + list(target_shape))
    memmap = np.memmap(memmap, cube_sequence[0].data.dtype,
                       "w+", shape=cube_shape) if memmap else np.empty(cube_shape)

    times = [cube_sequence[0].extra_coords['time']['value'][0]]
    memmap[0] = cube_sequence[0].data
    for i, cube in enumerate(cube_sequence.data[1:]):
        if not reproject:
            memmap[i+1] = cube_sequence[i+1].data
        else:
            reproject_interp((cube.data, cube.wcs),
                             target_wcs, shape_out=target_shape,
                             hdu_in=0,
                             order=0,
                             return_footprint=False,
                             output_array=memmap[i+1])
        times.append(cube.extra_coords['time']['value'][0])

    times = Time(times)
    dts = times[1:] - times[:-1]

    if u.allclose(dts[0].to(u.s), dts.to(u.s), atol=0.5*u.s):
        dt = dts[0]
    else:
        raise ValueError("Can't handle tabular wcs")

    out_wcs = WCS(naxis=4)
    out_wcs.wcs.crpix = list(target_wcs.wcs.crpix) + [0]
    out_wcs.wcs.crval = list(target_wcs.wcs.crval) + [0]
    out_wcs.wcs.cdelt = list(target_wcs.wcs.cdelt) + [dt.to(u.s).value]
    out_wcs.wcs.ctype = list(target_wcs.wcs.ctype) + ['TIME']
    out_wcs.wcs.cunit = list(target_wcs.wcs.cunit) + ['s']

    pc = np.identity(4)
    pc[:3, :3] = target_wcs.wcs.pc

    out_wcs.wcs.pc = pc

    return NDCube(memmap, out_wcs)
