"""
'Regrid on time': an IRIS dataset resampled at a regular time step, as a new dataset; and 'North up': a slit-jaw image
shown north up, on a new dataset's helioprojective grid.
"""

import numpy as np
from glue.config import layer_action
from glue.core import Data
from glue.core.link_helpers import LinkSame
from glue.utils import unbroadcast
from glue_qt.utils.decorators import messagebox_on_error
from glue_qt.viewers.image import ImageViewer
from qtpy import QtWidgets
from scipy.interpolate import make_interp_spline

from astropy.wcs import WCS
from astropy.wcs.wcsapi.wrappers import BaseWCSWrapper

from glue_solar.quicklook import _cadence, _placeable, _role, _time_axis, _timed, _times, nearest
from glue_solar.sources.loaders.iris import (
    _SJI_POINTING,
    _add_exposure,
    _dataset,
    _GlueWCS,
    _per_frame,
    keep_hpc_linked,
)
from glue_solar.sources.loaders.lazy import RawComponent, RawStack

__all__ = ["north_up", "north_up_iris", "regrid_iris", "regrid_on_time"]

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
    those of ``data``, and so are the pointing offset and the coordinates, along this axis those at each pixel's time
    (at the last time for a last pixel past it), so that a slit-jaw image's time coordinate is regular.
    ``meta['time_step']`` is the step in seconds. Data stored as int16 are read from their file as they are viewed, as
    ``data`` is.

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
    regridded.coords.pointing_offset = data.coords.pointing_offset
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


class _NorthUp(BaseWCSWrapper):
    """
    ``wcs``, a slit-jaw image's in arcsec and seconds, with its longitude and latitude those of ``tan``, a 2-D WCS in
    degrees, and its time ``times[t]`` at pixel ``t`` along its last pixel axis, linearly in between.
    """

    pixel_shape = pixel_bounds = None  # the wrapped WCS's are the image's

    def __init__(self, wcs, tan, times):
        super().__init__(wcs)
        self._tan, self._times, self._frames = tan, times, np.arange(len(times))

    @property
    def axis_correlation_matrix(self):
        return np.array([[True, True, False], [True, True, False], [False, False, True]])

    def pixel_to_world_values(self, x, y, t):
        x, y, t = np.broadcast_arrays(x, y, t)
        lon, lat = self._tan.pixel_to_world_values(x, y)
        time = np.interp(unbroadcast(t), self._frames, self._times, left=np.nan, right=np.nan)
        return ((np.asarray(lon) + 180) % 360 - 180) * 3600, np.asarray(lat) * 3600, np.broadcast_to(time, t.shape)

    def world_to_pixel_values(self, lon, lat, time):
        lon, lat, time = np.broadcast_arrays(lon, lat, time)
        x, y = self._tan.world_to_pixel_values(lon / 3600, lat / 3600)
        t = np.interp(unbroadcast(time), self._times, self._frames, left=np.nan, right=np.nan)
        return x, y, np.broadcast_to(t, time.shape)


def north_up(data):
    """
    A north-up helioprojective grid for ``data``, a slit-jaw image or aligned AIA cutout, as a new dataset
    ``<label> north up`` with no values, its ``empty`` NaN, and ``data``'s ``Time``: square pixels of ``data``'s
    ``CDELT1`` on a gnomonic (TAN) projection with latitude up its y axis, covering every frame as its own pointing
    places it, and along its first axis ``data``'s frames and times. Glue shows ``data`` on it through the links
    `north_up_iris` adds.

    Raises
    ------
    ValueError
        For data without a helioprojective longitude and latitude and a time for each frame, such as a raster.
    """
    if data.ndim != 3 or not _placeable(data):
        raise ValueError(f"{data.label} is not a slit-jaw image or aligned AIA cutout, whose frames have a pointing.")
    nt, ny, nx = data.shape
    # the corners of every frame: its edges are great circles, which a gnomonic projection keeps straight
    lon, lat, _ = data.coords.pixel_to_world_values(*np.meshgrid([-0.5, nx - 0.5], [-0.5, ny - 0.5], np.arange(nt)))
    tan = WCS(naxis=2)
    tan.wcs.ctype = ["HPLN-TAN", "HPLT-TAN"]
    tan.wcs.cdelt = [abs(data.meta["CDELT1"]) / 3600] * 2
    tan.wcs.crval = [np.mean(lon) / 3600, np.mean(lat) / 3600]
    tan.wcs.crpix = [1, 1]
    x, y = tan.world_to_pixel_values(lon / 3600, lat / 3600)
    first = np.round([x.min(), y.min()])
    tan.wcs.crpix = 1 - first
    grid = Data(label=f"{data.label} north up")
    grid.coords = _GlueWCS(_NorthUp(data.coords, tan, data.coords.pixel_to_world_values(0, 0, np.arange(nt))[2]))
    grid.meta["DSUN_OBS"] = data.meta.get("DSUN_OBS")  # for Measure's km
    shape = (nt, *(np.round([y.max(), x.max()]) - first[::-1] + 1).astype(int))
    grid.add_component(np.broadcast_to(np.float32(np.nan), shape), "empty")  # for glue's layer: a time cannot show
    grid.add_component(_per_frame(data[data.id["Time"], (slice(None), 0, 0)], shape), "Time")
    return grid


@layer_action(
    "North up", single=True, data=True, tooltip="Show this slit-jaw image or AIA cutout north up, in a new Image viewer"
)
@messagebox_on_error("Could not show north up")
def north_up_iris(data, data_collection):
    """
    Add the `north_up` grid of ``data`` to the data collection, its helioprojective coordinates linked with the others'
    and its time and frames with ``data``'s, and open an Image viewer of it showing ``data``, its own layer hidden;
    glue shows why for data that has no grid.
    """
    grid = north_up(data)
    data_collection.append(grid)
    keep_hpc_linked(data_collection)
    # glue places each frame with its own pointing at its time; the frames save it inverting data's at each step
    data_collection.add_link(
        [
            LinkSame(grid.world_component_ids[0], data.world_component_ids[0]),
            LinkSame(grid.pixel_component_ids[0], data.pixel_component_ids[0]),
        ]
    )
    windows = QtWidgets.QApplication.topLevelWidgets()
    app = next((window for window in windows if getattr(window, "data_collection", None) is data_collection), None)
    if app is not None:
        viewer = app.new_data_viewer(ImageViewer, data=grid)
        viewer.add_data(data)
        viewer.state.layers[0].visible = False
