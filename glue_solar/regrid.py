"""
'Regrid on time': an IRIS dataset resampled at a regular time step, as a new dataset.
"""

import numpy as np
from glue.config import layer_action
from glue_qt.utils.decorators import messagebox_on_error
from scipy.interpolate import make_interp_spline

from astropy.wcs.wcsapi.wrappers import BaseWCSWrapper

from glue_solar.quicklook import _cadence, _role, _time_axis, _timed, _times, nearest
from glue_solar.sources.loaders.iris import _SJI_POINTING, _add_exposure, _dataset, _per_frame, keep_hpc_linked
from glue_solar.sources.loaders.lazy import RawComponent, RawStack

__all__ = ["regrid_iris", "regrid_on_time"]

# A pixel takes the exposure, frame or scan nearest its time within this many time steps, else it is a gap
REACH = 0.75


class _Regridded(BaseWCSWrapper):
    """
    ``wcs`` with its last pixel axis, numpy's first, resampled: pixel ``i`` along it is pixel ``positions[i]`` of
    ``wcs``, and in between and beyond the ends linearly so.
    """

    pixel_shape = pixel_bounds = None  # the wrapped WCS's are the source's

    def __init__(self, wcs, positions):
        super().__init__(wcs)
        pixels = np.arange(len(positions))
        self._to_source = make_interp_spline(pixels, positions, k=1)
        self._from_source = make_interp_spline(positions, pixels, k=1)

    def pixel_to_world_values(self, *pixel_arrays):
        *pixel, position = pixel_arrays
        return self._wcs.pixel_to_world_values(*pixel, self._to_source(position))

    def world_to_pixel_values(self, *world_arrays):
        *pixel, position = self._wcs.world_to_pixel_values(*world_arrays)
        return (*pixel, self._from_source(position))


def _gather(values, index, gap):
    """``values`` at ``index`` along their first axis, and ``gap`` where it is -1."""
    taken = values[index]
    return np.where(_per_frame(index < 0, taken.shape), gap, taken)


def regrid_on_time(data):
    """
    A sit-and-stare raster, slit-jaw image, aligned AIA cutout or stack of raster scans resampled along its exposures,
    frames or scans at the median step between their times.

    Pixel ``i`` along that axis is ``i`` steps after the first time, up to the first pixel at or past the last, and
    holds the exposure, frame or scan nearest its time (the earlier of two as near) within 0.75 steps, else NaN, as
    do its ``Time`` (NaT then) and ``Exposure time``; a scan is timed by its middle raster step. The other axes are
    those of ``data``, and so are the coordinates, along this axis those at each pixel's time (at the last time for
    a last pixel past it), so that a slit-jaw image's time coordinate is regular. ``meta['time_step']`` is the step
    in seconds. Data stored as int16 are read from their file as they are viewed, as ``data`` is.

    Raises
    ------
    ValueError
        For a scanning raster, whose steps are places on the Sun, and for other data than an IRIS sit-and-stare
        raster, slit-jaw image, AIA cutout or stack, or one with fewer than two different times.
    """
    if not _timed(data) or _time_axis(data) is None:  # which is the first axis of the others
        if _role(data) == "raster":
            raise ValueError(f"{data.label} cannot be regridded on time: the steps of a scanning raster are places "
                             "on the Sun, not times. Its scans can be, stacked with 'Stack sequential raster scans' in "
                             "the observation browser.")
        raise ValueError(f"{data.label} is not an IRIS sit-and-stare raster, slit-jaw image or stack of scans.")
    times = _times(data, data.shape[1] // 2)  # a stack's scans by their middle step, as the quicklook times them
    step = _cadence(times)
    if not step:
        raise ValueError(f"{data.label} needs two different times to be regridded on time.")
    valid = ~np.isnat(times)
    start = times[valid].min()
    grid = start + np.arange(int(np.ceil((times[valid].max() - start) / step)) + 1) * step
    index, offset = nearest(grid, times)
    index[np.abs(offset) > REACH * step] = -1
    # the source's pixel position at each pixel's time, and its last for a last pixel past its last time
    positions = np.interp((grid - start).view("int64"), (times[valid] - start).view("int64"), np.flatnonzero(valid))
    component = data.get_component(data.main_components[0])
    if isinstance(component, RawComponent):  # its planes, still in the file, with a missing-data code in the gaps
        scaled = component._source
        gap = np.broadcast_to(np.array(scaled.fill[0], scaled.raw.dtype), scaled.raw.shape[1:])
        values, scaling = RawStack([scaled.raw[i] if i >= 0 else gap for i in index]), (scaled.bscale, scaled.bzero)
    else:
        values, scaling = _gather(np.asarray(component.data), index, np.nan), None
    meta = dict(data.meta)
    for name in set(_SJI_POINTING) & set(meta):
        meta[name] = _gather(np.asarray(meta[name], float), index, np.nan)
    meta["time_step"] = step / np.timedelta64(1, "s")
    regridded = _dataset(_Regridded(data.coords._wcs, positions), meta, component.units, values,
                         f"{data.label} regridded", color=data.style.color, cmap=data.style.preferred_cmap,
                         scaling=scaling)
    lead = (slice(None),) * (data.ndim - 2) + (0, 0)  # one value per exposure, frame, or scan and step
    regridded.add_component(_per_frame(_gather(data[data.id["Time"], lead], index, np.datetime64("NaT", "ns")),
                                       regridded.shape), "Time")
    exposure = data.find_component_id("Exposure time")
    if exposure is not None:
        _add_exposure(regridded, _gather(data[exposure, lead], index, np.nan))
    return regridded


@layer_action("Regrid on time", single=True, data=True,
              tooltip="Add the dataset resampled at the median step between its times, with NaN where none is near")
@messagebox_on_error("Could not regrid on time")
def regrid_iris(data, data_collection):
    """
    Add ``data`` regridded on time (`regrid_on_time`) to the data collection, with its helioprojective coordinates
    linked, and no viewer; glue shows why for data that cannot be.
    """
    data_collection.append(regrid_on_time(data))
    keep_hpc_linked(data_collection)
