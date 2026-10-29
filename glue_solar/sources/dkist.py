"""
DKIST Level 1 datasets, read with dkist from their ASDF file by File → Open Data Set (D102).
"""

import atexit
import contextlib
import contextvars
import copy
import hashlib
import inspect
import os
import threading
import warnings
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from functools import cached_property
from pathlib import Path

import numpy as np
from glue.config import autolinker, data_factory
from glue.core import fixed_resolution_buffer
from glue.core.component import Component, DaskComponent
from glue.core.component_link import ComponentLink
from glue.core.coordinates import Coordinates
from glue.core.data import Data
from glue.core.exceptions import IncompatibleAttribute
from glue.core.hub import HubListener
from glue.core.message import ApplicationClosedMessage, DataCollectionDeleteMessage
from glue.core.state import GlueSerializeError, _load_data_5, _save_data_5
from glue.plugins.wcs_autolinking import wcs_autolinking
from glue.plugins.wcs_autolinking.wcs_autolinking import IncompatibleWCS, WCSLink
from glue.utils.array import compute_statistic, unbroadcast

import astropy.units as u
from astropy.coordinates import SpectralCoord, StokesCoord
from astropy.io import fits
from astropy.stats import mad_std
from astropy.time import Time
from astropy.wcs.utils import fit_wcs_from_points
from astropy.wcs.wcsapi import (
    BaseHighLevelWCS,
    BaseLowLevelWCS,
    HighLevelWCSMixin,
    HighLevelWCSWrapper,
    SlicedLowLevelWCS,
)

from glue_solar.sources.loaders.iris import _HPC, _add_exposure, _add_time, _off_frames, _ScanAt

__all__ = ["dkist_data", "is_dkist_asdf"]

# Color limits sample values of up to this many whole frames whose files are present
SAMPLE_FRAMES = 16
# The header columns of a DKIST frame's quality, by FITS keyword, and their units (`_frame_quality`, D110); glue's Profile
# viewer shows the first present: the seeing, else the light level, as the AO lock is shaded (`_FrameCurves`)
QUALITY = {"ATMOS_R0": "m", "LIGHTLVL": "adu", "AO_LOCK": "", "XPOSURE": "ms", "ELEV_ANG": "deg"}
# Set while glue-solar's WCS link tests its transforms (`glue_patches.wcs_link_init`): `GlueWCS`'s inverse raises outside
# a dataset's times there, as dkist's does, rather than giving NaN (D103)
STRICT_INVERSE = contextvars.ContextVar("strict_inverse", default=False)
# `GlueWCS.pixel_to_world_values`'s last 64 distinct inputs and its results (D103)
_WORLD, _WORLD_LOCK = OrderedDict(), threading.Lock()


def _open_files():
    """
    How many FITS files DKIST data keep open: up to 4096, half the process's open-file soft limit, which this raises
    toward its hard limit, as macOS's is 256 (user, 2026-10-23: 128 files reopened a ViSP map's 510 at each move).
    """
    try:
        import resource
    except ImportError:  # Windows, whose C runtime allows 8192
        return 4096
    soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
    for wanted in (8192, 4096, 2048):
        wanted = wanted if hard == resource.RLIM_INFINITY else min(wanted, hard)
        if wanted <= soft:
            break
        with contextlib.suppress(ValueError, OSError):  # above macOS's kern.maxfilesperproc
            resource.setrlimit(resource.RLIMIT_NOFILE, (wanted, hard))
            soft = wanted
            break
    return min(4096, soft // 2)


# DKIST data's FITS files kept open, the least recently read first, at most `OPEN_FILES`; and the threads that read
# them, as astropy's RICE decoding releases the GIL (`_Files`, D103)
OPEN_FILES, _OPEN, _OPEN_LOCK = _open_files(), OrderedDict(), threading.Lock()
_READERS = ThreadPoolExecutor(8)
atexit.register(lambda: [file.close() for file in list(_OPEN.values())])  # as glue quits, not left to the collector
# FITS files a download is writing, read as missing until they are whole: Globus may write them in place, and a file
# opened part-written stays unreadable once kept open (D110, `_section`)
_ARRIVING = set()
# Set while glue computes an Image buffer of a DKIST dataset's values (`DKISTData.compute_fixed_resolution_buffer`)
_EXACT = contextvars.ContextVar("exact", default=False)


def _wrapped(wcs, world):
    """
    The values ``world`` of the world axes of ``wcs``, helioprojective longitude and latitude in [-180°, 180°), as
    SkyCoord's: dkist gives longitude 0° to 360°, and its small ViSP test raster a zero or negative latitude as 360°
    plus it.
    """
    world = list(world)
    for k, kind in enumerate(wcs.world_axis_physical_types):
        if kind in _HPC:
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
    world axes go in ``order`` (`_glue_order`), those of no pixel axis of their own first; helioprojective longitude and
    latitude in [-180°, 180°) (`_wrapped`); and a pixel axis of no world axis of its own, such as one of a Cryo-NIRSP
    context imager's two axes of time, its index, named by ``names``.
    """

    serialized_classes = False

    def __init__(self, wcs, order, names):
        self._wcs, self._order, self._names = wcs, order, names
        # dkist's VaryingCelestialTransform sets one model's parameters at each pointing index, then evaluates it, and
        # glue-qt's profile worker evaluates beside the GUI thread (report candidate)
        self._lock = threading.Lock()
        self._extra = len(order) - wcs.pixel_n_dim
        # the pixel axes dkist ravels into one index of its times (its Ravel), a raster's steps and repeats or a
        # Cryo-NIRSP dataset's steps and measurements: those its time varies along, and their lengths
        self._raveled = ()
        model = getattr(wcs, "forward_transform", None)
        if hasattr(model, "traverse_postorder"):  # a gWCS's compound model
            from dkist.wcs.models import Ravel

            ravel = next((leaf for leaf in model.traverse_postorder() if isinstance(leaf, Ravel)), None)
            if ravel is not None:
                time = np.asarray(wcs.axis_correlation_matrix)[wcs.world_axis_physical_types.index("time")]
                self._raveled = tuple(zip(np.flatnonzero(time), ravel.array_shape))

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
        # its last 64 distinct inputs of up to 10,000 values kept (D103): WCSAxes asks the same at each draw, 2601 at
        # most, and at each dkist builds a model per raster step, 3 s a ViSP map
        key = None
        if pixel[0].size <= 10_000:
            key = id(self), pixel[0].shape, hashlib.blake2b(np.asarray(pixel, float).tobytes()).digest()
            with _WORLD_LOCK:
                if key in _WORLD:
                    _WORLD.move_to_end(key)
                    return copy.deepcopy(_WORLD[key][1])
        world = self._world(pixel)
        if key is not None:
            with _WORLD_LOCK:
                _WORLD[key] = self, copy.deepcopy(world)  # kept alive, so that no other takes its id
                while len(_WORLD) > 64:
                    _WORLD.popitem(last=False)
        return world

    def _world(self, pixel):
        # dkist 1.18.1's Ravel gives a NaN time off either end of a raveled axis, where WCSAxes' frame asks, and WCSAxes
        # raises for a time range all NaN. Taken there at its nearest end, of that end's time, so WCSAxes finds a time
        # range, and no longitude or latitude, as dkist gives off its pointing table (D103)
        inputs, past = list(pixel), np.zeros(pixel[0].shape, bool)
        for p, size in self._raveled:
            off = (np.rint(pixel[p]) < 0) | (np.rint(pixel[p]) > size - 1)  # as Ravel rounds
            inputs[p], past = np.where(off, np.clip(pixel[p], 0, size - 1), pixel[p]), past | off
        with self._lock:
            world = _wrapped(self._wcs, self._wcs.pixel_to_world_values(*inputs))
        if past.any():
            types = self._wcs.world_axis_physical_types
            world = [np.where(past, np.nan, values) if kind in _HPC else values for values, kind in zip(world, types)]
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
        # inverted at finite values only, raveled: NaN pixels where a world value is NaN, as a regridded IRIS dataset's
        # time in its gaps, where dkist's inverse raises (`_off_frames`); and dkist's Unravel inverse, of a Cryo-NIRSP
        # context image of repeated measurements, raises TypeError on arrays of more than one dimension (report
        # candidate)
        world = np.broadcast_arrays(*(np.asarray(values, dtype=float) for values in world))
        finite = np.all(np.isfinite(world), axis=0)
        # the link test (`STRICT_INVERSE`) refusing a NaN world value, as of off-limb data of other dates, which sunpy
        # places at no longitude or latitude in the other's frame (D103)
        if STRICT_INVERSE.get() and not finite.all():
            raise ValueError("no pixel")
        pixel = [np.full(finite.shape, np.nan) for _ in range(self.pixel_n_dim)]
        if finite.any():
            inside = [w[finite] for w in world]
            try:
                with self._lock:
                    found = self._wcs.world_to_pixel_values(*inside)
            # a time off its frames (`_off_frames`): dkist #765, unreleased; and raveled, Unravel's ValueError on its
            # inverse's NaN time (dkist/wcs/models.py:815, report candidate) (D103)
            except (NotImplementedError, ValueError):
                if STRICT_INVERSE.get():
                    raise
                with self._lock:
                    found = _off_frames(self._wcs, inside)
            for values, at in zip(pixel, found, strict=True):
                values[finite] = at
        for i, k in enumerate(self._order):
            if k is None:
                pixel[i - self._extra] = np.broadcast_to(world_arrays[i], pixel[0].shape) * 1.0
        return tuple(pixel)


class _Open:
    """
    A FITS file of DKIST data, open while among the `OPEN_FILES` last read (`_section`), and its lock: an astropy file
    is not safe across threads, and glue-qt's profile worker reads beside the viewers (D103).
    """

    def __init__(self, path):
        self.path, self.lock, self.hdus, self.kept = path, threading.Lock(), None, True

    def read(self, target, key):
        """``key`` of its HDU ``target``, only the tiles it touches decompressed (astropy's section)."""
        with self.lock:
            if self.hdus is None:  # as dkist opens it
                self.hdus = fits.open(self.path, memmap=False, do_not_scale_image_data=True, mode="denywrite")
            values = self.hdus[target].section[key]
            if not self.kept:  # out of the last read while this read
                self.close()
            return values

    def close(self):
        if self.hdus is not None:
            self.hdus.close()
            self.hdus = None


def _section(path, target, key, files):
    """
    ``key`` of HDU ``target`` of the FITS file at ``path``, of ``files`` (`_Files`), kept open (`_Open`) while they are
    kept; None where it is missing.
    """
    if path in _ARRIVING or not os.path.exists(path):  # NaN, as dkist reads it
        return None
    with _OPEN_LOCK:
        if files.kept:
            file = _OPEN.pop(path, None) or _Open(path)
            _OPEN[path] = file
        else:  # its dataset gone from glue, for a profile still computing: closed once read (`_close`)
            file = _Open(path)
            file.kept = False
        closed = [_OPEN.popitem(last=False)[1] for _ in range(len(_OPEN) - OPEN_FILES)]
    _shut(closed)
    return file.read(target, key)


def _close(files):
    """Close ``files`` (`_Files`) and keep them open no more, as their dataset leaves glue (`_Recenter`)."""
    with _OPEN_LOCK:
        files.kept = False
        closed = [_OPEN.pop(path) for path in set(files.paths.flat) if path in _OPEN]
    _shut(closed)


def _shut(files):
    for old in files:
        with old.lock:
            old.kept = False
            old.close()


class _Files:
    """
    A DKIST dataset's values in its FITS files, ``paths`` over its first array axes, each the HDU ``target`` of a frame
    of ``shape`` and ``dtype``, read as they are viewed (D103): from each file only the tiles a view touches
    decompressed, on 8 threads (`_READERS`), where dkist's dask array decompresses each file whole, 4.5 s for a ViSP map;
    a missing file NaN, as dkist reads it.
    """

    def __init__(self, paths, target, shape, dtype):
        self.paths, self.target = paths if paths.size > 1 else paths.reshape(()), target
        self.lead = (0,) if shape[0] == 1 else ()  # a frame's leading axis of one, which dkist drops
        self.shape = self.paths.shape + tuple(shape[len(self.lead) :])
        self.dtype = np.result_type(dtype, np.float16)  # holding NaN
        self.kept = True  # its files kept open (`_section`) until its dataset leaves glue (`_close`)

    def read(self, view):
        """The values at ``view``, as NumPy indexes an array; None for a view of other kinds."""
        view, n = view if isinstance(view, tuple) else (view,), len(self.shape)
        if len(view) == n and all(isinstance(v, np.ndarray) and v.dtype.kind in "iu" for v in view):
            # the pixels glue's Image buffer samples (`_EXACT`): the distinct ones read, then picked
            picks = [np.arange(size)[unbroadcast(v)] for v, size in zip(view, self.shape)]
            axes = [np.unique(pick) for pick in picks]
            values = self._outer(axes)[tuple(np.searchsorted(a, pick) for a, pick in zip(axes, picks))]
            return np.broadcast_to(values, np.broadcast_shapes(*(v.shape for v in view)))
        if len(view) <= n and all(isinstance(v, (slice, np.integer)) or type(v) is int for v in view):
            view += (slice(None),) * (n - len(view))
            values = self._outer([np.atleast_1d(np.arange(size)[v]) for v, size in zip(view, self.shape)])
            return values[tuple(slice(None) if isinstance(v, slice) else 0 for v in view)]
        return None

    def _outer(self, axes):
        """The values at each combination of the indices ``axes``, an array of them per array axis."""
        if any(len(a) == 0 for a in axes):
            return np.empty([len(a) for a in axes], self.dtype)
        k = self.paths.ndim
        paths, frame = (self.paths[np.ix_(*axes[:k])] if k else self.paths), axes[k:]
        low = [int(a.min()) for a in frame]
        key = self.lead + tuple(slice(start, int(a.max()) + 1) for start, a in zip(low, frame))
        pick = np.ix_(*(a - start for a, start in zip(frame, low)))
        flat = paths.ravel()
        values = np.full((flat.size, *(len(a) for a in frame)), np.nan, self.dtype)

        def read(i):
            part = _section(flat[i], self.target, key, self)
            if part is not None:
                values[i] = part[pick]

        if flat.size > 1:
            list(_READERS.map(read, range(flat.size)))
        else:
            read(0)
        return values.reshape(paths.shape + values.shape[1:])


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
    _frames = None  # each frame's DATE-AVG and XPOSURE in seconds, over the frame axes
    _quality = None  # each frame's header columns of `QUALITY`, by keyword, over the frame axes
    _files = None  # its values' files (`_Files`), None where dask reads them
    _observed = None  # its instrument and observing program execution (`_context_imager`)
    _dataset = None  # its dkist Dataset, whose FITS files 'Download these frames…' fetches (D110)

    def get_data(self, cid, view=None):
        # its values' views read from their files (`_Files`, D103)
        if self._files is not None and view is not None and cid is self.main_components[0]:
            values = self._files.read(view)
            if values is not None:
                return values
        return super().get_data(cid, view=view)

    def compute_fixed_resolution_buffer(self, *args, **kwargs):
        # an Image buffer of its values reads only the pixels glue samples (`get_data`), where glue reads their bounding
        # box of a DaskComponent (glue-core 1.28.0's fixed_resolution_buffer.py:286-296): 500 files of a ViSP map whose
        # view samples 34 (D103)
        exact = self._files is not None and kwargs.get("subset_state") is None
        token = _EXACT.set(exact and kwargs.get("target_cid") is self.main_components[0])
        try:
            return super().compute_fixed_resolution_buffer(*args, **kwargs)
        finally:
            _EXACT.reset(token)

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

    @cached_property
    def _noise(self):
        """
        The noise level of Stokes Q, U and V, by index, by an SST cube's rule (`~glue_solar.sources.sst._Cube._noise`,
        D107): the standard deviation of each at the quieter end of its wavelengths, as an artifact or a line at one end
        only raises it, as at AIOMGG's first, from the median absolute deviation of about 10,000 values there, evenly
        spaced along the other axes of up to 4 frames, whose files the GUI thread opens (16 took 0.28 s on TXIPCV,
        D109), NaN, such as all of DL-NIRSP's first wavelength, left out; 0 if all are NaN at both ends.
        """
        types = self.coords.world_axis_physical_types
        s, w = (self.coords.world_n_dim - 1 - types.index(kind) for kind in ("phys.polarization.stokes", "em.wl"))
        lead, other = self._present.ndim, [a for a in range(self.ndim) if a not in (s, w)]  # its frames' axes first
        view = [0] * self.ndim
        for a in other:
            along = [b for b in other if (b < lead) == (a < lead)]
            step = max(1, round(self.shape[a] / (4 if a < lead else 2500) ** (1 / len(along))))
            view[a] = slice(step // 2, None, step)
        cid, ends = self.main_components[0], []
        for view[w] in (0, self.shape[w] - 1):
            with warnings.catch_warnings(action="ignore", category=RuntimeWarning):  # 'All-NaN slice encountered'
                noise = {
                    k: float(np.nan_to_num(mad_std(self[cid, (*view[:s], k, *view[s + 1 :])], ignore_nan=True)))
                    for k in (1, 2, 3)
                }
            ends.append(noise)
        return {k: min((end[k] for end in ends if end[k]), default=0.0) for k in (1, 2, 3)}

    def register_to_hub(self, hub):
        # each frame's Time and Exposure time, as IRIS data's, which the Point window and readouts give (D103): added
        # here, not as it loads, where glue's load log would number a mosaic's components apart from older sessions',
        # and before the hub, which would hear of each
        if self._frames is not None and self.find_component_id("Exposure time") is None:
            _add_time(self, self._frames[0])
            _add_exposure(self, self._frames[1])
        super().register_to_hub(hub)
        self._recenter = _Recenter(self, hub)  # the hub holds its listeners weakly

    # A session saves a dataset as glue saves a Data, but for its coordinates, a gWCS, which glue cannot save: it
    # restores as this class with the coordinates, frames, sample and center tile of the dataset its load log reads
    # again from the ASDF file, as `LazyData` does for IRIS data (D102)
    def __gluestate__(self, context):
        log, meta = getattr(self, "_load_log", None), {}
        if log is None:  # made by `dkist_data` in glue's terminal, not opened: glue's own error, as `LazyData` gives
            return _save_data_5(self, context)
        for key, value in self.meta.items():
            try:
                context.do(value)
            except GlueSerializeError:  # left out, as glue leaves it out
                continue
            meta[key] = value
        return {
            "components": [(context.id(cid), context.id(self.get_component(cid))) for cid in self._components],
            "subsets": [context.id(subset) for subset in self.subsets],
            "label": self.label,
            "style": context.do(self.style),
            "_key_joins": [
                [context.id(key), [context.id(cid) for cid in cids], [context.id(cid) for cid in other]]
                for key, (cids, other) in self._key_joins.items()
            ],
            "uuid": self.uuid,
            "primary_owner": [context.id(cid) for cid in self.components if cid.parent is self],
            "meta": context.do(meta),
            "log": context.id(log),
            "log_item": log.data.index(self),
            "center": log.data.index(self._center),  # the first tile left once the center tile is removed (`_Recenter`)
        }

    @classmethod
    def __setgluestate__(cls, rec, context):
        log = context.object(rec["log"])
        source = log.data[rec["log_item"]]
        context.register_object(f"{rec['uuid']} coords", source.coords)
        restored = _load_data_5({**rec, "coords": f"{rec['uuid']} coords"}, context)
        data = next(restored)
        data.__class__, data._load_log = cls, log  # glue's loader makes a Data
        data._mosaic, data._samples, data._present = source._mosaic, source._samples, source._present
        data._mosaic[data._mosaic.index(source)] = data  # the tiles shared, restored in place of their sources (D105)
        data._files = source._files
        data._frames = source._frames  # for a session saved without its Time and Exposure time (`register_to_hub`)
        data._quality = source._quality
        data._observed = source._observed
        data._dataset = source._dataset
        data._center = log.data[rec["center"]] if "center" in rec else source._center  # #374's sessions saved none
        log.data[rec["log_item"]] = data  # for a session saved from this one
        for tile in log.data:  # its mosaic's tiles, restored or not, link to it if it is the center (`wcs_autolink`)
            if tile._center is source:
                tile._center = data
        yield data
        yield from restored


def _frame_times(data):
    """
    The array axes of ``data``, a DKIST dataset, along which its time varies, in order, and its times along them as
    `numpy.datetime64`, at the middle of its other axes; None where it has none.
    """
    wcs = data.coords
    if "time" not in wcs.world_axis_physical_types:
        return None
    axes = np.flatnonzero(np.asarray(wcs.axis_correlation_matrix)[wcs.world_axis_physical_types.index("time")])
    if not len(axes):
        return None
    axes = sorted(int(data.ndim - 1 - p) for p in axes)
    grid = np.indices([data.shape[axis] for axis in axes])
    pixel = [grid[axes.index(a)] if a in axes else n // 2 for a, n in enumerate(data.shape)]
    [time] = [world for world in wcs.pixel_to_world(*pixel[::-1]) if isinstance(world, Time)]
    return axes, time.datetime64


def _slit(data, step, at=None):
    """
    The array axis along the slit of ``data``, a DKIST raster stepping along array axis ``step``, and at each step the
    helioprojective longitude and latitude (arcsec) of the slit's first pixel and their change over one pixel along it,
    at the middle of the other axes, or at ``at``, indices by axis of those they vary along too, such as a Cryo-NIRSP
    raster's measurement (D105), or a column of them for a table per index (`link_hpc`); None where they vary along
    other axes too.
    """
    wcs, at = data.coords, at or {}
    types = list(wcs.world_axis_physical_types)
    if not set(_HPC) <= set(types):
        return None
    matrix = np.asarray(wcs.axis_correlation_matrix)[[types.index(kind) for kind in _HPC]]
    axes = {data.ndim - 1 - p for p in np.flatnonzero(matrix.any(axis=0))} - {step, *at}
    if len(axes) != 1:
        return None
    [slit] = axes
    ends = []
    for end in (0, data.shape[slit] - 1):
        pixel = [
            np.arange(n) if a == step else end if a == slit else at.get(a, n // 2) for a, n in enumerate(data.shape)
        ]
        world = wcs.pixel_to_world_values(*pixel[::-1])
        ends.append(np.stack([world[types.index(kind)] for kind in _HPC], axis=-1))
    return slit, ends[0], (ends[1] - ends[0]) / (data.shape[slit] - 1)


class _SlitAt:
    """
    A DKIST raster's step, or with ``slit`` its slit pixel, at helioprojective longitude and latitude ``lon, lat``
    (arcsec) of IRIS data, and on a sit-and-stare raster at its frame ``index`` (`link_hpc`, D102): glue inverts the
    raster's coordinates from one world value per array axis, never its time, from which dkist's gWCS takes the step.
    The step is that whose slit passes nearest, as the quicklook places a point on a scanning IRIS raster, NaN past half
    a step beyond either end, as the quicklook's no match (D7), or on a sit-and-stare raster that nearest the frame's
    time however far, ``steps`` by frame, as `_ScanAt` gives a stack's scan; the slit pixel is that level with the place
    along that step's slit, from its first pixel, ``starts``, and one pixel along it, ``pixels``, per step (`_slit`).
    A scanning raster with repeats or measurements has them per repeat or measurement, and at its frame ``index`` IRIS
    data take that ``repeats`` gives by frame, the one nearest its time (D102). Saved in sessions.
    """

    def __init__(self, starts, pixels, slit, steps=None, repeats=None):
        self.starts, self.pixels = np.asarray(starts, dtype=float), np.asarray(pixels, dtype=float)
        self.slit, self.steps, self.repeats = slit, steps, repeats
        self.__name__ = "slit_pixel" if slit else "nearest_step"  # glue's name of a link function, as its helpers set
        # its inputs to glue and its link editor, not self too
        inputs = (lambda lon, lat: None) if steps is None and repeats is None else (lambda lon, lat, index: None)
        self.__signature__ = inspect.signature(inputs)
        if repeats is not None:
            self._frames = _ScanAt(repeats)
            self._tables = [_SlitAt(*table, slit) for table in zip(self.starts, self.pixels, strict=True)]
            return
        if steps is not None:
            self._frames = _ScanAt(steps)
            return
        # the slits' offsets across them, in order, and half a step past each end, beyond which a point is no match (D7)
        along = self.pixels.mean(axis=0)
        self._across = np.array([-along[1], along[0]])
        offsets = self.starts @ self._across
        order = np.argsort(offsets)
        self._offsets, self._steps = (
            np.r_[1.5 * x[0] - 0.5 * x[1], x, 1.5 * x[-1] - 0.5 * x[-2]] for x in (offsets[order], order * 1.0)
        )

    def __call__(self, lon, lat, index=None):
        if self.repeats is not None:
            lon, lat, repeat = np.broadcast_arrays(lon, lat, self._frames(index))
            found = np.full(repeat.shape, np.nan)  # none for a frame of no time
            for k, table in enumerate(self._tables):
                found[repeat == k] = table(lon[repeat == k], lat[repeat == k])
            return found
        place = np.stack(np.broadcast_arrays(lon, lat), axis=-1)
        if self.steps is None:
            step = np.interp(place @ self._across, self._offsets, self._steps, left=np.nan, right=np.nan)
        else:
            step = self._frames(index)
        if not self.slit:
            return step
        at = np.clip(np.round(np.nan_to_num(step)), 0, len(self.starts) - 1).astype(int)
        pixel = self.pixels[at]
        along = np.sum((place - self.starts[at]) * pixel, axis=-1) / np.sum(pixel**2, axis=-1)
        return np.where(np.isnan(step), np.nan, along)

    def __gluestate__(self, context):
        steps = None if self.steps is None else np.asarray(self.steps, dtype=float).tolist()
        repeats = None if self.repeats is None else np.asarray(self.repeats, dtype=float).tolist()
        return {
            "starts": self.starts.tolist(),
            "pixels": self.pixels.tolist(),
            "slit": self.slit,
            "steps": steps,
            "repeats": repeats,
        }

    @classmethod
    def __setgluestate__(cls, rec, context):
        return cls(rec["starts"], rec["pixels"], rec["slit"], rec["steps"], rec.get("repeats"))  # none saved before


class _SlitPlace:
    """
    The helioprojective longitude, or latitude with ``kind`` 1, (arcsec) of a DKIST raster at its ``step`` and
    ``slit`` pixel, ``starts`` and ``pixels`` as `_SlitAt` takes them (`link_hpc`, D102): where glue gives it none, as
    a sit-and-stare raster's step axis has its time (`GlueWCS`), so that IRIS data are placed on it. Saved in sessions.
    """

    __name__ = "slit_place"  # glue's name of a link function, as its own link helpers set it
    __signature__ = inspect.signature(lambda step, slit: None)  # its inputs to glue and its link editor, not self too

    def __init__(self, starts, pixels, kind):
        self.starts, self.pixels = np.asarray(starts, dtype=float), np.asarray(pixels, dtype=float)
        self.kind = kind

    def __call__(self, step, slit):
        at = np.clip(np.round(np.nan_to_num(step)), 0, len(self.starts) - 1).astype(int)
        place = self.starts[at, self.kind] + np.asarray(slit, dtype=float) * self.pixels[at, self.kind]
        return np.where(np.isnan(step), np.nan, place)

    def __gluestate__(self, context):
        return {"starts": self.starts.tolist(), "pixels": self.pixels.tolist(), "kind": self.kind}

    @classmethod
    def __setgluestate__(cls, rec, context):
        return cls(rec["starts"], rec["pixels"], rec["kind"])


class _At:
    """
    ``value`` at every pixel: a DKIST tile's time, or index along its axis, at the slice its mosaic's image shows
    (`_mosaic_links`, D108). Saved in sessions.
    """

    __name__ = "at_slice"  # glue's name of a link function, as its own link helpers set it
    __signature__ = inspect.signature(lambda pixel: None)  # one input to glue and its link editor, not self too

    def __init__(self, value):
        self.value = float(value)

    def __call__(self, pixel):
        return np.full(np.shape(pixel), self.value)

    def __gluestate__(self, context):
        return {"value": self.value}

    @classmethod
    def __setgluestate__(cls, rec, context):
        return cls(rec["value"])


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
    inventory = dataset.meta["inventory"]
    data._observed = inventory["instrumentName"], inventory.get("observingProgramExecutionId")
    data._dataset = dataset
    # its first frame's band, line (nm) and whether its wavelengths are in air or vacuum, for its lines (D107)
    for key, kind in (("WAVEBAND", str), ("LINEWAV", float), ("WAVEREF", str)):
        if key in headers.colnames:
            data.meta[key] = kind(headers[key][0])
    files = dataset.files
    data._present = np.vectorize(lambda name: (Path(files.basepath) / name).exists(), otypes=[bool])(
        files.fileuri_array
    )
    if data._present.size == 1:  # one frame, as a VBI single-shot tile's, whose file axis dkist drops (D102)
        data._present = data._present.reshape(())
    # its values read from its files as they are viewed (`_Files`, D103); by dask where it is cut within its files'
    # frames, as ``dataset[0, :, 400]``, or dkist gives no HDU of its files, of no public API in dkist 1.18.1
    try:
        target = files._fm._striped_external_array.target
    except AttributeError:
        target = None
    if target is not None and dataset.data.shape == files.output_shape:
        paths = np.vectorize(lambda name: str(Path(files.basepath) / name), otypes=[object])(files.fileuri_array)
        data._files = _Files(paths, target, files.shape, dataset.data.dtype)
    # each file's DATE-AVG, its gWCS's time to 0.5 ms, not the gWCS's, 0.8 s for CZKPML's 4000 frames, and XPOSURE (ms);
    # none without its headers table, as dkist's visp_no_headers
    if {"DATE-AVG", "XPOSURE"} <= set(headers.colnames):
        times = np.array(headers["DATE-AVG"], dtype="datetime64[ns]").reshape(data._present.shape)
        data._frames = times, (np.array(headers["XPOSURE"]) * u.ms).to_value(u.s).reshape(data._present.shape)
        # and its columns of `QUALITY`, NaN where masked, as ATMOS_R0 is at some frames (D110)
        data._quality = {
            key: np.ma.filled(np.ma.asarray(headers[key], dtype=float), np.nan).reshape(data._present.shape)
            for key in QUALITY
            if key in headers.colnames
        }
    return data


class _FrameTimes(Coordinates):
    """
    A DKIST dataset's frames' times, ``seconds`` since its first frame, at ``start``, by row of its frame quality and
    linear between them: its world axis (`_frame_quality`, D110). Saved in sessions.
    """

    def __init__(self, seconds, start):
        super().__init__(n_dim=1)
        self.seconds, self.start = np.asarray(seconds, dtype=float), start

    world_axis_units = property(lambda self: ["s"])
    world_axis_names = property(lambda self: [f"time since {self.start}"])
    axis_correlation_matrix = property(lambda self: np.ones((1, 1), bool))

    def pixel_to_world_values(self, pixel):
        return np.interp(pixel, np.arange(len(self.seconds)), self.seconds)

    def world_to_pixel_values(self, world):
        return np.interp(world, self.seconds, np.arange(len(self.seconds)))

    def __gluestate__(self, context):
        return {"seconds": self.seconds.tolist(), "start": self.start}

    @classmethod
    def __setgluestate__(cls, rec, context):
        return cls(rec["seconds"], rec["start"])


def _frame_quality(data):
    """
    The frame quality of ``data``, a DKIST dataset, from its headers alone (D110): a dataset of a row per FITS file in
    time order, its columns of `QUALITY` (`_data`), ``AO_LOCK`` 1 while locked, and its ``Time``, against its time in s
    since its first frame (`_FrameTimes`).
    """
    times = data._frames[0].ravel()
    order = np.argsort(times, kind="stable")
    times = times[order]
    seconds = (times - times[0]) / np.timedelta64(1, "s")
    frames = Data(label=f"{data.label} frame quality", coords=_FrameTimes(seconds, str(times[0])[:19]))
    for key, values in data._quality.items():
        frames.add_component(Component(values.ravel()[order], units=QUALITY[key]), key)
    frames.add_component(times, "Time")  # last: glue's Profile viewer shows the first, and cannot show a time
    return frames


def _held_axes(data):
    """
    The array axes of ``data``, a DKIST dataset, that a point takes at its viewer's sliders, as the quicklook's spectra
    do (D103): its Stokes axis, a repeat axis and a Cryo-NIRSP measurement axis, by their pixel axis names and
    physical types; none for other data.
    """
    wcs = getattr(data, "coords", None)
    if not isinstance(wcs, GlueWCS):
        return set()
    names = wcs._names
    held = {p for p, name in enumerate(names) if "measurement" in name or "repeat" in name}
    stokes = [k for k, kind in enumerate(wcs.world_axis_physical_types) if kind == "phys.polarization.stokes"]
    held.update(np.flatnonzero(np.asarray(wcs.axis_correlation_matrix)[stokes].any(axis=0)))
    return {data.ndim - 1 - int(p) for p in held}


def _held_names(data):
    """`_held_axes` of ``data`` by their pixel axis names (``DPNAMEn``), such as 'measurement number'."""
    return {data.coords._names[data.ndim - 1 - axis]: axis for axis in _held_axes(data)}


def _frame_axis(data):
    """
    The array axis of ``data``, a DKIST dataset, of its frames or raster steps: the first its time varies along, but
    those a point takes at its viewer's sliders (`_held_axes`); None for none.
    """
    return min(_time_axes(data) - _held_axes(data), default=None)


def _time_axes(data):
    """The array axes of ``data``, a DKIST dataset, along which its time varies."""
    wcs = data.coords
    types = list(wcs.world_axis_physical_types)
    if "time" not in types:
        return set()
    time = np.asarray(wcs.axis_correlation_matrix)[types.index("time")]
    return {data.ndim - 1 - int(p) for p in np.flatnonzero(time)}


# The context imager observed with each spectrograph (D105)
_CONTEXT = {"VISP": "VBI", "CRYO-NIRSP": "CRYO-NIRSP"}


def _context_imager(raster, datasets):
    """
    Of ``datasets``, the first context imager observed with ``raster``, a ViSP or Cryo-NIRSP spectrograph dataset:
    VBI with ViSP, Cryo-NIRSP's context imager with its spectrograph, of the same observing program execution, with
    frames whose times overlap (D105); a mosaic's center tile; else None.
    """

    def spectral(data):
        return "em.wl" in data.coords.world_axis_physical_types

    instrument, program = getattr(raster, "_observed", None) or (None, None)
    if instrument not in _CONTEXT or program is None or raster._frames is None or not spectral(raster):
        return None
    times = raster._frames[0]
    for data in datasets:
        if not isinstance(data, DKISTData) or data._observed != (_CONTEXT[instrument], program) or spectral(data):
            continue
        if _frame_axis(data) is None:  # a single shot, as a one-file VBI tile, has no frames to follow the raster
            continue
        if data._frames is not None and data._frames[0].min() <= times.max() and times.min() <= data._frames[0].max():
            return data._center if data._center in datasets else data
    return None


def _mosaic_image(tiles, at):
    """
    ``tiles``, a DKIST mosaic's, at the indices ``at`` of their axes but the last two, such as a frame, or a Stokes
    parameter, repeat and wavelength, stitched into one image by reproject (D108): on ``find_optimal_celestial_wcs``'s
    grid, at their finest pixel, their mean where they overlap (``reproject_and_coadd``, with ``reproject_interp``:
    ``reproject_exact`` took 4 times as long on DL-NIRSP's tiles), NaN where none is; only that slice of each read.
    Labeled by, and its meta holding, its time, the tiles' mean (``DATE-AVG``), wavelength (``WAVELNTH``, nm) and
    Stokes parameter (``STOKES``), those the tiles have.
    """
    from reproject import reproject_interp  # with the first mosaic rather than at glue's launch
    from reproject.mosaicking import find_optimal_celestial_wcs, reproject_and_coadd

    view = (*at, slice(None), slice(None))
    images = [np.asarray(tile[tile.main_components[0], view], dtype=np.float32) for tile in tiles]
    sliced = [HighLevelWCSWrapper(SlicedLowLevelWCS(tile.coords, view)) for tile in tiles]
    wcs, shape = find_optimal_celestial_wcs(list(zip(images, sliced)), negative_lon_cdelt="auto")
    # each tile's coordinates there as a FITS WCS fitted at 3 by 3 pixels, in the mosaic's frame, the first tile's:
    # reproject would evaluate the tile's gWCS at every pixel, holding `GlueWCS`'s lock against the viewers, and
    # transform it from its own frame, of its dataset's mean time: 55 s for LOQEPP's 9 tiles, 27 s so
    # ponytail: the observer's move between the tiles' times left out, at most 0.5 pixel on LOQEPP and 1.6 on CARJML's
    # 4 minutes, less than the Sun turns meanwhile; fit each tile in its own frame if it matters
    fitted = []
    for image, tile_wcs in zip(images, sliced):
        y, x = (grid.ravel() for grid in np.mgrid[0 : image.shape[0] - 1 : 3j, 0 : image.shape[1] - 1 : 3j])
        fitted.append(fit_wcs_from_points((x, y), tile_wcs.pixel_to_world(x, y), projection=wcs))
    values = np.zeros(shape, np.float32)
    reproject_and_coadd(
        list(zip(images, fitted)),
        wcs,
        shape_out=shape,
        reproject_function=reproject_interp,
        output_array=values,
        blank_pixel_value=np.nan,
        roundtrip_coords=False,
    )
    world = [
        tile.coords.pixel_to_world((image.shape[1] - 1) / 2, (image.shape[0] - 1) / 2, *at[::-1])
        for tile, image in zip(tiles, images)
    ]
    times = Time([value for values in world for value in values if isinstance(value, Time)])
    meta, named = {"DATE-AVG": times.mean().isot}, []
    for value in world[0]:
        if isinstance(value, StokesCoord):
            meta["STOKES"] = str(value.symbol)
            named.append(meta["STOKES"])
        elif isinstance(value, SpectralCoord):
            meta["WAVELNTH"] = float(value.to_value(u.nm))
            named.append(f"{meta['WAVELNTH']:.3f} nm")
    label = " ".join([f"{tiles[0].label.rsplit(' (', 1)[0]} mosaic", *named, meta["DATE-AVG"][:19]])
    image = Data(label=label, coords=wcs)
    cid = tiles[0].main_components[0]
    image.add_component(Component(values, units=tiles[0].get_component(cid).units), cid.label)
    image.meta.update(meta)
    return image


def _mosaic_links(image, tiles, at):
    """
    The links that give each of ``tiles``, at every pixel of ``image``, their mosaic at their indices ``at``
    (`_mosaic_image`), its time there and its index along that time's axis (`_At`, D108): glue reaches a tile's pixel
    from every world value its place varies with, so a point on the mosaic reaches it through 'Link helioprojective
    coordinates' only with its time; and the index, as glue otherwise takes the tile's frame as soon from another
    tile's link to it (`wcs_autolink`), the frame nearest that tile's time, seconds apart.
    """
    pixels, links = [image.pixel_component_ids[0]], []
    for tile in tiles:
        wcs, (ny, nx) = tile.coords, tile.shape[-2:]
        world = wcs.pixel_to_world_values((nx - 1) / 2, (ny - 1) / 2, *at[::-1])
        for axis in range(tile.ndim - 2):
            k = wcs.world_n_dim - 1 - axis  # glue's world axis of array axis ``axis`` (`GlueWCS`)
            if wcs.world_axis_physical_types[k] == "time":
                links.append(ComponentLink(pixels, tile.world_component_ids[axis], using=_At(world[k])))
                links.append(ComponentLink(pixels, tile.pixel_component_ids[axis], using=_At(at[axis])))
    return links


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

    path = os.path.abspath(path)  # a session's is relative to it, which glue leaves before dkist reads the files
    dataset = dkist.load_dataset(path)
    if not isinstance(dataset, (dkist.Dataset, dkist.TiledDataset)):  # a Level 2 inversion, an NDCollection (D102)
        raise ValueError(f"{Path(path).name} is a DKIST Level 2 inversion: glue-solar opens Level 1 datasets only.")
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
    _note_missing(datasets, label, Path(path).parent)
    return datasets if len(datasets) > 1 else datasets[0]


def _note_missing(datasets, label, folder):
    """Warn, in glue's Error Console, how many FITS files of ``datasets``, a DKIST dataset's, are in ``folder``."""
    present = sum(int(data._present.sum()) for data in datasets)
    expected = sum(data._present.size for data in datasets)
    if present < expected:
        warnings.warn(
            f"{label}: {present} of {expected} files are in {folder}; dkist reads the others as NaN.", stacklevel=3
        )


def _transfer(parts, folder):
    """
    Start one Globus transfer, from the DKIST data center into ``folder``, of the FITS files of ``parts``, each a
    dkist Dataset sliced to them and their names, and return (D110): by dkist's own helper given those files alone, as
    ``FileManager.download`` adds the ASDF file, browse movie and quality report to every transfer, from the dataset's
    place, as dkist finds it again; by ``FileManager.download`` of each sliced dataset if that private API moved.
    """
    try:
        from dkist.net import conf
        from dkist.net.globus.transfer import _orchestrate_transfer_task as transfer

        source = Path(conf.dataset_path.format(**parts[0][0].files._inventory))  # as dkist 1.18.1's file_manager.py:271
        inspect.signature(transfer).bind([], recursive=False, destination_path=folder, wait=False)
    except (ImportError, AttributeError, TypeError):
        for dataset, _ in parts:
            dataset.files.download(path=folder, wait=False)
        return
    files = [source / name for _, names in parts for name in names]
    transfer(files, recursive=False, destination_path=folder, wait=False)


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


class _Recenter(HubListener):
    """
    Once ``tile``, a DKIST mosaic's center tile, is removed from its data collection, the first of the mosaic's tiles
    left there becomes their center, and those linked to ``tile`` are linked to it at once (D102, user 2026-10-22):
    glue drops a removed dataset's links, and `wcs_autolink` links tiles to their center only.
    """

    def __init__(self, tile, hub):
        self.tile = tile
        # ahead of glue's link manager, of priority 10, which drops the links
        hub.subscribe(self, DataCollectionDeleteMessage, handler=self._removed, priority=11)
        # Reset Session, Open Session and 'Restore last session' close the window, removing no data
        hub.subscribe(self, ApplicationClosedMessage, handler=self._release)

    def _release(self, message=None):
        if self.tile._files is not None:  # its kept files closed, not held until glue quits (user, 2026-10-23)
            _close(self.tile._files)

    def _removed(self, message):
        if message.data is not self.tile:
            return
        self._release()
        collection = message.sender
        tiles = [data for data in collection if getattr(data, "_center", None) is self.tile]
        ends = [(link.data1, link.data2) for link in collection.external_links if isinstance(link, WCSLink)]
        linked = {data for pair in ends if self.tile in pair for data in pair}
        links = []
        for tile in tiles:
            tile._center = tiles[0]
            if tile is not tiles[0] and tile in linked:
                with contextlib.suppress(IncompatibleWCS):
                    links.append(WCSLink(tiles[0], tile))
        if links:  # glue rediscovers every dataset's links on each add_link, even an empty one
            collection.add_link(links)


class _BoxRead(type):
    """
    glue's test of a DaskComponent in an Image buffer, whose pixels glue reads as their bounding box, false while
    `_EXACT`, for a DKIST dataset's values (D103).
    """

    def __instancecheck__(cls, component):
        return isinstance(component, DaskComponent) and not _EXACT.get()


fixed_resolution_buffer.DaskComponent = _BoxRead("DaskComponent", (), {})

autolinker.members[:] = [
    (label, wcs_autolink if function is wcs_autolinking.wcs_autolink else function) for label, function in autolinker
]
