"""
DKIST Level 1 datasets, read with dkist from their ASDF file by File → Open Data Set (D102).
"""

import warnings
from pathlib import Path

import numpy as np
from glue.config import autolinker, data_factory
from glue.core.component import DaskComponent
from glue.core.data import Data
from glue.core.exceptions import IncompatibleAttribute
from glue.plugins.wcs_autolinking import wcs_autolinking
from glue.plugins.wcs_autolinking.wcs_autolinking import IncompatibleWCS, WCSLink
from glue.utils.array import compute_statistic

import astropy.units as u
from astropy.time import Time
from astropy.wcs.wcsapi import BaseHighLevelWCS, BaseLowLevelWCS, HighLevelWCSMixin

from glue_solar.sources.loaders.iris import _HPC

__all__ = ["dkist_data", "is_dkist_asdf"]

# Color limits sample values of up to this many whole frames whose files are present
SAMPLE_FRAMES = 16


def _wrapped(wcs, world):
    """The values ``world`` of the world axes of ``wcs``, helioprojective longitude in [-180°, 180°), as SkyCoord's."""
    world = list(world)
    for k, kind in enumerate(wcs.world_axis_physical_types):
        if kind == _HPC[0]:
            half = (180 * u.deg).to_value(wcs.world_axis_units[k])
            world[k] = (np.asarray(world[k]) + half) % (2 * half) - half
    return world


def _glue_order(wcs, shape):
    """
    The world axes of ``wcs``, a DKIST dataset's gWCS of pixel axes of lengths ``shape``, as `GlueWCS` orders them:
    those of no pixel axis of their own, then that of each pixel axis, None where it has none. Longitude and latitude
    go to the two pixel axes the pointing moves most along, those along which time does not change first, so an
    imager's frames keep their time; a slit raster's step only if the pointing moves a pixel along the slit or more,
    else it is sit-and-stare and its time goes there (D102). Each other world axis goes to the pixel axis it changes
    most along, of those left.
    """
    types, matrix = wcs.world_axis_physical_types, np.asarray(wcs.axis_correlation_matrix)
    pixel = np.repeat([[size // 2 for size in shape]], 2 * len(shape), axis=0)
    for p, size in enumerate(shape):  # the two ends of each pixel axis, at the middle of the others
        pixel[2 * p + 1, p], pixel[2 * p, p] = size - 1, 0
    world = np.array(_wrapped(wcs, wcs.pixel_to_world_values(*pixel.T)), float)
    span = np.nan_to_num(abs(world[:, 1::2] - world[:, ::2])) * matrix
    order = {}  # pixel axis: world axis
    if set(_HPC) <= set(types):
        lon, lat = map(types.index, _HPC)
        pointing = np.hypot(span[lon], span[lat])
        timed = matrix[types.index("time")] if "time" in types else np.zeros(len(shape), bool)
        first, *moving = sorted(map(int, np.flatnonzero(pointing)), key=lambda p: (timed[p], -pointing[p]))
        step = pointing[first] / max(shape[first] - 1, 1)  # a pixel along the slit
        if moving and pointing[moving[0]] >= step:
            a, b = first, moving[0]
            if span[lon, a] + span[lat, b] < span[lon, b] + span[lat, a]:
                a, b = b, a
            order[a], order[b] = lon, lat
        else:
            order[first] = lon if span[lon, first] >= span[lat, first] else lat
    hpc = [types.index(kind) for kind in _HPC if kind in types]
    for k in sorted(set(range(len(types))) - set(order.values()), key=lambda k: (k in hpc, matrix[k].sum(), k)):
        free = [p for p in np.flatnonzero(matrix[k]) if p not in order]
        if free:
            order[max(free, key=lambda p: span[k, p])] = k
    extra = [k for k in range(len(types)) if k not in order.values()]
    return [*extra, *(order.get(p) for p in range(len(shape)))]


class GlueWCS(BaseLowLevelWCS, HighLevelWCSMixin):
    """
    A DKIST dataset's gWCS, ``wcs``, as glue reads it (D102): glue gives array axis i world axis ``world_n_dim - 1 -
    i`` (glue's ``CoordinateComponent``, Image viewer and its state), assuming one world axis per pixel axis, so the
    world axes go in ``order`` (`_glue_order`), those of no pixel axis of their own first; helioprojective longitude in
    [-180°, 180°), as SkyCoord gives it, where dkist gives 0° to 360°; and a pixel axis of no world axis of its own,
    such as one of a Cryo-NIRSP context imager's two axes of time, its index, named by ``names``.
    """

    serialized_classes = False

    def __init__(self, wcs, order, names):
        self._wcs, self._order, self._names = wcs, order, names
        self._extra = len(order) - wcs.pixel_n_dim

    pixel_n_dim = property(lambda self: self._wcs.pixel_n_dim)
    world_n_dim = property(lambda self: len(self._order))
    pixel_shape = property(lambda self: self._wcs.pixel_shape)
    pixel_bounds = property(lambda self: self._wcs.pixel_bounds)

    def _pick(self, values, index):
        """Of ``values``, one per world axis of ``wcs``, those of this one's, ``index(pixel axis)`` for an index."""
        return tuple(index(i - self._extra) if k is None else values[k] for i, k in enumerate(self._order))

    @property
    def world_axis_physical_types(self):
        return self._pick(self._wcs.world_axis_physical_types, lambda p: None)

    @property
    def world_axis_units(self):
        return self._pick(self._wcs.world_axis_units, lambda p: "")

    @property
    def world_axis_names(self):
        return self._pick(self._wcs.world_axis_names, self._names.__getitem__)

    @property
    def world_axis_object_components(self):
        return list(self._pick(self._wcs.world_axis_object_components, lambda p: (f"index {p}", 0, "value")))

    @property
    def world_axis_object_classes(self):
        index = {f"index {p}": (u.Quantity, (), {"unit": u.one}) for p in range(self.pixel_n_dim)}
        return {**self._wcs.world_axis_object_classes, **index}

    @property
    def axis_correlation_matrix(self):
        return np.array(self._pick(self._wcs.axis_correlation_matrix, lambda p: np.arange(self.pixel_n_dim) == p))

    def pixel_to_world_values(self, *pixel_arrays):
        pixel = np.broadcast_arrays(*pixel_arrays)
        world = _wrapped(self._wcs, self._wcs.pixel_to_world_values(*pixel))
        return self._pick(world, lambda p: pixel[p] * 1.0)

    def world_to_pixel_values(self, *world_arrays):
        # glue's coordinate links give the values of glue's world components only, one per pixel axis (D102): none
        # of a world axis of no pixel axis of its own, so no pixel
        if len(world_arrays) < self.world_n_dim:
            raise IncompatibleAttribute()
        world = [None] * self._wcs.world_n_dim
        for values, k in zip(world_arrays, self._order):
            if k is not None:
                world[k] = values
        pixel = list(np.broadcast_arrays(*self._wcs.world_to_pixel_values(*world)))
        for i, k in enumerate(self._order):
            if k is None:
                pixel[i - self._extra] = np.broadcast_to(world_arrays[i], pixel[0].shape) * 1.0
        return tuple(pixel)


class DKISTData(Data):
    """
    A DKIST dataset, whose sampled statistics of its values, the color limits of an Image layer, its style editor and
    a Histogram's range, are those of as many values as glue samples, at random from up to `SAMPLE_FRAMES` evenly spaced
    whole frames whose files are present, one sample for all the tiles of a VBI mosaic, so their limits match (D102):
    glue samples a dask array at a corner of ten chunks, 0 to 2 % of a frame, and dkist reads a missing file as NaN.
    """

    _mosaic = ()  # the datasets, this one among them, whose frames the sample takes
    _samples = None  # {size: values}, shared by them
    _present = None  # whether each frame's file is present, over the frame axes

    def compute_statistic(
        self,
        statistic,
        cid,
        subset_state=None,
        axis=None,
        finite=True,
        positive=False,
        percentile=None,
        view=None,
        random_subset=None,
        **kwargs,
    ):
        if random_subset and subset_state is None and axis is None and view is None and cid is self.main_components[0]:
            return compute_statistic(
                statistic, self._sample(random_subset), finite=finite, positive=positive, percentile=percentile
            )
        return super().compute_statistic(
            statistic,
            cid,
            subset_state=subset_state,
            axis=axis,
            finite=finite,
            positive=positive,
            percentile=percentile,
            view=view,
            random_subset=random_subset,
            **kwargs,
        )

    def _sample(self, size):
        """At least ``size`` values of the frames, as `DKISTData` samples them."""
        if size not in self._samples:
            frames = [(data, tuple(frame)) for data in self._mosaic for frame in np.argwhere(data._present)]
            picks = np.unique(np.linspace(0, len(frames) - 1, SAMPLE_FRAMES).round().astype(int)) if frames else []
            rng, values = np.random.default_rng(0), [np.empty(0)]
            for k in picks:
                data, frame = frames[k]
                frame = np.asarray(data.get_component(data.main_components[0]).data[frame]).ravel()
                values.append(frame[rng.integers(0, frame.size, -(-size // len(picks)))])
            self._samples[size] = np.concatenate(values)
        return self._samples[size]


def _frame_times(data):
    """
    The array axis of ``data``, a DKIST dataset, along which its time varies, and its times there as `numpy.datetime64`,
    at the middle of its other axes; None where its time varies along several or it has none.
    """
    wcs = data.coords
    if "time" not in wcs.world_axis_physical_types:
        return None
    axes = np.flatnonzero(np.asarray(wcs.axis_correlation_matrix)[wcs.world_axis_physical_types.index("time")])
    if len(axes) != 1:
        return None
    axis = data.ndim - 1 - axes[0]
    pixel = [np.arange(data.shape[axis]) if p == axes[0] else n // 2 for p, n in enumerate(data.shape[::-1])]
    [time] = [world for world in wcs.pixel_to_world(*pixel) if isinstance(world, Time)]
    return axis, time.datetime64


def is_dkist_asdf(filename, **_kwargs):
    """An ASDF file that dkist wrote or reads, as the DKIST data center's dataset files are."""
    if not str(filename).endswith(".asdf"):
        return False
    try:
        with open(filename, "rb") as file:
            return b"dkist" in file.read(4096)
    except OSError:
        return False


def _data(dataset, label):
    """``dataset`` as a `DKISTData`, its values left in its files."""
    wcs, headers = dataset.wcs.low_level_wcs, dataset.headers
    names = [
        str(headers[f"DPNAME{p + 1}"][0]) if f"DPNAME{p + 1}" in headers.colnames else f"pixel {p}"
        for p in range(wcs.pixel_n_dim)
    ]
    data = DKISTData(label=label, coords=GlueWCS(wcs, _glue_order(wcs, dataset.data.shape[::-1]), names))
    data.add_component(DaskComponent(dataset.data, units=str(dataset.unit or "")), "data")
    files = dataset.files
    data._present = np.vectorize(lambda name: (Path(files.basepath) / name).exists(), otypes=[bool])(
        files.fileuri_array
    )
    return data


@data_factory("DKIST Level 1 dataset (ASDF)", is_dkist_asdf, priority=200)
def dkist_data(path):
    """
    Load a DKIST Level 1 dataset from its ASDF file with dkist, as one dataset, or a VBI mosaic as one per tile,
    labeled by instrument, dataset ID and tile, such as ``VBI YCDRFH (1, 1)``.

    The values stay in the dataset's FITS files, read as they are viewed; dkist reads a frame whose file is missing as
    NaN, and a warning gives how many are present. The coordinates are the dataset's gWCS, with one world axis per
    array axis, as glue shows them (`GlueWCS`).

    Returns
    -------
    `~glue.core.data.Data` or list of `~glue.core.data.Data`
    """
    import dkist  # with the first DKIST dataset rather than at glue's launch

    dataset = dkist.load_dataset(path)
    inventory = dataset.meta["inventory"]
    label = f"{inventory['instrumentName']} {inventory['datasetId']}"
    if isinstance(dataset, dkist.TiledDataset):
        mask = np.broadcast_to(dataset.mask, dataset.shape)
        tiles = [index for index in np.ndindex(dataset.shape) if not mask[index]]
        datasets = [_data(dataset[index], f"{label} {index}") for index in tiles]
        # the tile nearest the middle, which the others link to (`wcs_autolink`)
        center = datasets[np.argmin(np.linalg.norm(np.subtract(tiles, (np.array(dataset.shape) - 1) / 2), axis=1))]
    else:
        datasets = [_data(dataset, label)]
        center = datasets[0]
    samples = {}
    for data in datasets:
        data._mosaic, data._samples, data._center = datasets, samples, center
    present = sum(int(data._present.sum()) for data in datasets)
    expected = sum(data._present.size for data in datasets)
    if present < expected:
        warnings.warn(
            f"{label}: {present} of {expected} files are in {Path(path).parent}; dkist reads the others as NaN.",
            stacklevel=2,
        )
    return datasets if len(datasets) > 1 else datasets[0]


def wcs_autolink(data_collection):
    """
    glue's WCS autolinker, the tiles of a DKIST mosaic linked to its center tile only, and other data to that tile only
    (D102): glue links every pair, 5778 links for DL-NIRSP's 108 tiles, and finds every link again at each change.
    """
    datasets = [data for data in data_collection if isinstance(getattr(data, "coords", None), BaseHighLevelWCS)]
    existing = {(link.data1, link.data2) for link in data_collection.external_links if isinstance(link, WCSLink)}
    links = []
    for i, data1 in enumerate(datasets):
        for data2 in datasets[i + 1 :]:
            pair = data1, data2
            # each the center tile of its mosaic, or of the other's
            if pair in existing or not all(getattr(data, "_center", data) in pair for data in pair):
                continue
            try:
                links.append(WCSLink(data1, data2))
            except IncompatibleWCS:
                pass
    return links


autolinker.members[:] = [
    (label, wcs_autolink if function is wcs_autolinking.wcs_autolink else function) for label, function in autolinker
]
