"""
'Regrid on time': an IRIS dataset resampled at a regular time step, as a new dataset; 'North up': a slit-jaw image
shown north up, on a new dataset's helioprojective grid; and 'Rebin…': an IRIS dataset binned, as a new dataset.
"""

import gc
import math
import warnings

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
from astropy.wcs.wcsapi.wrappers import BaseWCSWrapper, SlicedLowLevelWCS

from glue_solar.quicklook import _cadence, _placeable, _role, _spectral_axes, _time_axis, _timed, _times, nearest
from glue_solar.sources.loaders.iris import (
    _SJI_POINTING,
    WCS_LOCK,
    _add_exposure,
    _dataset,
    _GlueWCS,
    _per_frame,
    keep_hpc_linked,
)
from glue_solar.sources.loaders.lazy import RawComponent, RawStack
from glue_solar.sources.moments import SLAB, _accepted, _start

__all__ = ["north_up", "north_up_iris", "rebin", "rebin_iris", "regrid_iris", "regrid_on_time"]

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
        self._positions = positions  # for a session
        pixels = np.arange(len(positions))
        self._to_source = make_interp_spline(pixels, positions, k=1)
        self._from_source = make_interp_spline(positions, pixels, k=1)

    def pixel_to_world_values(self, *pixel_arrays):
        *pixel, position = pixel_arrays
        return self._wcs.pixel_to_world_values(*pixel, self._to_source(position))

    def world_to_pixel_values(self, *world_arrays):
        *pixel, position = self._wcs.world_to_pixel_values(*world_arrays)
        return (*pixel, self._from_source(position))


class _Broadcast(BaseWCSWrapper):
    """``wcs`` given its pixel arrays broadcast to one shape: ndcube's ``ResampledLowLevelWCS`` takes no others."""

    def pixel_to_world_values(self, *pixel_arrays):
        return self._wcs.pixel_to_world_values(*np.broadcast_arrays(*pixel_arrays))

    def world_to_pixel_values(self, *world_arrays):
        return self._wcs.world_to_pixel_values(*world_arrays)


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
        return np.asarray(lon) * 3600, np.asarray(lat) * 3600, np.broadcast_to(time, t.shape)

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
        For data without a helioprojective longitude and latitude and a time for each frame, such as a raster, or
        without a pixel scale, such as a north-up grid.
    """
    if data.ndim != 3 or not _placeable(data) or "CDELT1" not in data.meta:
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


def _check(data):
    """Raise why ``data`` is not an IRIS dataset, which can be rebinned."""
    if not _timed(data) or not isinstance(data.coords, _GlueWCS):
        raise ValueError(f"{data.label} is not an IRIS raster window, slit-jaw image or AIA cutout.")


def _rebinned(data, view, values, bins, operation=np.nanmean):
    """``values``, of ``data`` at ``view``, binned by ndcube's ``NDCube.rebin`` with ``operation``."""
    from ndcube import NDCube

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)  # a bin with every value missing: NaN
        binned = NDCube(values, SlicedLowLevelWCS(data.coords, view)).rebin(bins, operation=operation).data
    gc.collect(0)  # ndcube's cubes are reference cycles, which hold ``values`` until Python's collector runs
    return binned


def rebin(data, bins):
    """
    ``data``, an IRIS dataset, binned by ``bins`` pixels along each axis, as a new dataset ``<label> rebinned <bins>``.

    Each pixel is the nanmean of the values in its bin, by ndcube's ``NDCube.rebin``, NaN where every one is missing,
    in float32 in memory; ``data`` is read a slab at a time, a stack a bin of scans at a time, and pixels past its last
    whole bin along an axis are left out. Its coordinates are ndcube's ``ResampledLowLevelWCS`` of those of ``data``,
    so a pixel is at its bin's centre; its ``Time`` is the mean of its bin's times, and its ``Exposure time`` the mean
    of its bin's exposure times, NaN where one is 0 s, so that ``<label> DN/s`` is its mean DN over it. The units,
    colormap, pointing offset and metadata are those of ``data``, without a slit-jaw image's per-frame pointing,
    ``meta['rebinned']`` adding ``bins``, and the ``meta['time_step']`` of data regridded on time multiplied by the bin
    along time.

    Raises
    ------
    ValueError
        For other data than an IRIS dataset, or ``bins`` that are not a whole number of pixels from 1 to the length
        of each axis.
    """
    from ndcube.wcs.wrappers import ResampledLowLevelWCS

    _check(data)
    bins = tuple(int(n) for n in bins)
    if len(bins) != data.ndim or not all(1 <= n <= length for n, length in zip(bins, data.shape)):
        raise ValueError(f"{data.label}, of {data.shape} pixels, cannot be binned by {bins}.")
    covered = tuple(slice(0, length // n * n) for n, length in zip(bins, data.shape))
    # slabs of whole bins along the first axis, or a stack's raster steps, a bin of scans at a time
    axis, cid = data.ndim - 3, data.main_components[0]
    end = covered[axis].stop
    rows = bins[axis] * max(1, SLAB // (math.prod(bins[: axis + 1]) * math.prod(p.stop for p in covered[axis + 1 :])))
    groups = [(slice(scan, scan + bins[0]),) for scan in range(0, covered[0].stop, bins[0])] if axis else [()]
    values = []
    for group in groups:
        views = ((*group, slice(start, min(start + rows, end)), *covered[axis + 1 :]) for start in range(0, end, rows))
        values.append(np.concatenate([_rebinned(data, view, data[cid, view], bins) for view in views], axis=axis))
    with WCS_LOCK:
        wcs = _Broadcast(ResampledLowLevelWCS(SlicedLowLevelWCS(data.coords._wcs, covered), bins[::-1]))
    meta = {key: value for key, value in data.meta.items() if key not in _SJI_POINTING}
    meta["rebinned"] = bins
    if "time_step" in meta:  # 'Regrid on time': along the first axis
        meta["time_step"] *= bins[0]
    rebinned = _dataset(
        wcs,
        meta,
        data.get_component(cid).units,
        np.concatenate(values),
        f"{data.label} rebinned {'x'.join(map(str, bins))}",
        color=data.style.color,
        cmap=data.style.preferred_cmap,
        missing=(),
    )
    rebinned.coords.pointing_offset = data.coords.pointing_offset
    lead, along = (*covered[:-2], 0, 0), bins[:-2]  # one value per exposure, frame, or scan and step
    times = data[data.id["Time"], lead]
    offsets = _rebinned(data, lead, (times - times.flat[0]) / np.timedelta64(1, "ns"), along)
    rebinned.add_component(_per_frame(times.flat[0] + offsets.astype("timedelta64[ns]"), rebinned.shape), "Time")
    exposure = data.find_component_id("Exposure time")
    if exposure is not None:
        seconds = data[exposure, lead]
        _add_exposure(rebinned, _rebinned(data, lead, np.where(seconds > 0, seconds, np.nan), along, np.mean))
    return rebinned


def _ask(data):
    """
    The pixels per bin typed for each axis of ``data``, at first 2 along its last two axes but wavelength, the map or
    image, and 1 along the others; or None for Cancel.
    """
    dialog = QtWidgets.QDialog(QtWidgets.QApplication.activeWindow())
    dialog.setWindowTitle(f"Rebin {data.label}")
    form = QtWidgets.QFormLayout(dialog)
    image = sorted(set(range(data.ndim)) - _spectral_axes(data))[-2:]
    boxes = []
    for axis, (cid, length) in enumerate(zip(data.world_component_ids, data.shape)):
        box = QtWidgets.QSpinBox(objectName=f"axis {axis}", minimum=1, maximum=length)
        box.setValue(2 if axis in image else 1)
        form.addRow(f"{cid.label} ({length} pixels):", box)
        boxes.append(box)
    return tuple(box.value() for box in boxes) if _accepted(dialog, form) else None


@messagebox_on_error("Could not rebin")
def _failed(exc_info):
    raise exc_info[1]


@layer_action(
    "Rebin…",
    single=True,
    data=True,
    tooltip="Add the dataset binned: the mean of so many pixels along each axis, missing data left out",
)
@messagebox_on_error("Could not rebin")
def rebin_iris(data, data_collection):
    """
    Add ``data`` binned by the pixels typed for each axis (`rebin`) to the data collection, with its helioprojective
    coordinates linked, and no viewer; glue shows why for other data. It is binned in the background, while glue's
    status bar says so.
    """
    _check(data)  # before asking
    bins = _ask(data)
    if bins is not None:
        _start(data_collection, f"Rebinning {data.label}…", _failed, rebin, data, bins)
