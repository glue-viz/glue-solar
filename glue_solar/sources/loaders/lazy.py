"""
IRIS data held as the file's raw 16-bit integers, scaled only where glue reads them, with the missing-data codes as NaN
and IRIS data's Level 2 ceiling as +Inf.
"""

from uuid import uuid4

import dask.array as da
import numpy as np
from glue.core.component import DaskComponent, DerivedComponent
from glue.core.data import Data
from glue.core.state import GlueSerializeError, _load_data_5, _save_data_5
from glue.core.subset import SliceSubsetState
from glue.utils import random_indices_for_array

__all__ = ["LazyData", "RawComponent", "RawStack", "allow_open_files", "fill_mask"]

# Colour limits count every raw value of a window up to this many bytes, else of evenly spaced planes (raster
# steps or slit-jaw frames) up to it: exact on the acceptance windows, at most 0.6 s for the first Image layer
SAMPLE_BYTES = 512 * 2**20
# Steps or frames per dask chunk, for the reads glue makes of a whole component
CHUNK_STEPS = 32
# The open-file limit lazy loading asks for: macOS's OPEN_MAX
OPEN_FILES = 10240


def allow_open_files():
    """
    Raise this process's soft limit on open files to `OPEN_FILES` (never above the hard limit, never lower).

    Each memory-mapped raster file stays open, once per read of its windows (a ``raster_data`` call, or the windows
    of an observation ticked in the browser): the 99 scans of 3602506433 pass the 256 files macOS gives GUI
    applications by their third read.
    """
    try:
        import resource
    except ImportError:  # Windows has no such limit
        return
    soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
    wanted = OPEN_FILES if hard == resource.RLIM_INFINITY else min(OPEN_FILES, hard)
    if soft != resource.RLIM_INFINITY and soft < wanted:
        resource.setrlimit(resource.RLIMIT_NOFILE, (wanted, hard))


def fill_mask(values):
    """1 where ``values`` are NaN (missing), else 0: one byte per sample, as glue stores a bool component as int64."""
    return np.isnan(values).view(np.uint8)


class _Scaled:
    """
    What glue and dask read: ``raw[key]`` as float32 ``raw * bscale + bzero``, scaled as astropy scales, with the
    ``fill`` codes NaN and the codes from ``top`` up, if any, +Inf. It has no ``copy`` method, which dask would call
    and so read the whole file.
    """

    def __init__(self, raw, bscale, bzero, fill, top=None):
        # ponytail: raw is irispy's memory map, whose pages stay resident once viewed and which a file cut short or a
        # lost drive turns into SIGBUS; a reader of whole planes (os.pread) in its place bounds both
        self.raw = raw
        self.shape, self.ndim, self.dtype = raw.shape, raw.ndim, np.dtype(np.float32)
        self.bscale, self.bzero, self.fill = np.float32(bscale), np.float32(bzero), np.asarray(fill, np.int16)
        self.top = top

    def __getitem__(self, key):
        raw = np.asarray(self.raw[key])
        values = raw.astype(np.float32)
        values *= self.bscale
        values += self.bzero
        values[np.isin(raw, self.fill)] = np.nan
        if self.top is not None:
            values[raw >= self.top] = np.inf
        return values


class RawComponent(DaskComponent):
    """
    A glue component over the raw int16 of an IRIS window, slit-jaw or AIA cube: a memory map, or an array in memory
    for a ``.fits.gz`` file.

    A read with a view, as every image, profile and cursor readout asks, scales only what the view selects, index
    arrays included; a read of the whole component goes through dask, a chunk at a time. Values at or above
    ``ceiling``, if given, are +Inf, as irispy's scaled reads of IRIS data give its Level 2 ceiling (D57).
    """

    def __init__(self, raw, bscale, bzero, missing, ceiling=None, units=None):
        # the raw codes of the missing values (D12): exact integers only, as only those can be stored
        codes = [(value - bzero) / bscale for value in missing]
        fill = [int(code) for code in codes if float(code).is_integer() and -32768 <= code <= 32767]
        top = None if ceiling is None else int(np.ceil((ceiling - bzero) / bscale))
        self._source = _Scaled(raw, bscale, bzero, fill, top if top is not None and top <= 32767 else None)
        self._counts = None
        values = da.from_array(
            self._source,
            chunks=(1,) * (raw.ndim - 3) + (CHUNK_STEPS, *raw.shape[-2:]),
            name=f"iris-raw-{uuid4().hex}",  # dask would otherwise hash, so read, the whole file
            meta=np.empty((0,) * raw.ndim, np.float32),
            asarray=False,
        )
        super().__init__(values, units=units)

    def __getitem__(self, key):
        return self._source[key]

    def _count(self, key):
        """How often each raw code occurs in ``raw[key]``, the fill codes and +Inf left out, as glue leaves them out."""
        counts = np.bincount(np.asarray(self._source.raw[key]).ravel().astype(np.int32) + 32768, minlength=65536)
        counts[self._source.fill.astype(np.int32) + 32768] = 0
        if self._source.top is not None:
            counts[self._source.top + 32768 :] = 0
        return counts

    def _sample(self):
        """How often each raw code occurs in the colour-limit sample (`SAMPLE_BYTES`), as `_count` counts them."""
        if self._counts is None:
            raw = self._source.raw
            planes = int(np.prod(raw.shape[:-2]))
            wanted = max(1, min(planes, SAMPLE_BYTES // (raw.shape[-2] * raw.shape[-1] * raw.dtype.itemsize)))
            counts = np.zeros(65536, np.int64)
            for plane in np.unique(np.linspace(0, planes - 1, wanted).round().astype(int)):
                counts += self._count(np.unravel_index(plane, raw.shape[:-2]))
            self._counts = counts
        return self._counts

    def sampled_statistic(self, statistic, percentile=None, positive=False, view=None):
        """
        'minimum', 'maximum' or 'percentile' of the sample, or of every value ``view`` selects, as NumPy's linear
        percentile of the scaled values.
        """
        # ponytail: a view's codes are counted at once, 14 bytes a value; a Collapse range across a whole window
        # would want them plane by plane, as the sample is
        counts = self._sample() if view is None else self._count(view)
        values = np.arange(-32768, 32768, dtype=np.float32) * self._source.bscale + self._source.bzero
        if positive:
            counts = np.where(values > 0, counts, 0)
        cumulative = np.cumsum(counts)
        total = int(cumulative[-1])
        if total == 0:
            return np.nan
        position = {"minimum": 0.0, "maximum": total - 1.0}.get(statistic)
        if position is None:
            position = (total - 1) * (percentile / 100)
        below = np.floor(position)
        low, high = values[np.searchsorted(cumulative, [below, np.ceil(position)], side="right")]
        # NumPy's interpolation, in float32 as for float32 values
        fraction = position - below
        if fraction < 0.5:
            return float(low + (high - low) * np.float32(fraction))
        return float(high - (high - low) * np.float32(1 - fraction))


class RawStack:
    """
    Equal-shaped raw arrays as one array with a leading axis: one per raster scan of a stack, or per pixel along the
    time axis of data regridded on time. A read touches only the arrays it selects.
    """

    def __init__(self, scans):
        if any(scan.shape != scans[0].shape for scan in scans):
            raise ValueError("All raster scans must have the same shape to be stacked")
        self.scans = scans
        self.shape = (len(scans), *scans[0].shape)
        self.ndim, self.dtype = len(self.shape), scans[0].dtype

    def __getitem__(self, key):
        key = key if isinstance(key, tuple) else (key,)
        if key[0] is Ellipsis:  # as glue reads a value subset's mask
            key = (slice(None), *key)
        first, rest = key[0], key[1:]
        if isinstance(first, (int, np.integer)):
            return np.asarray(self.scans[first][rest])
        if isinstance(first, slice):
            return np.stack([np.asarray(self.scans[i][rest]) for i in range(*first.indices(len(self.scans)))])
        if not any(np.ndim(index) for index in rest):
            # an index array of scans with basic indices, such as a spectrum's slice: each scan selected read once,
            # its axis first, as NumPy places it
            scans, inverse = np.unique(first, return_inverse=True)
            return np.stack([np.asarray(self.scans[i][rest]) for i in scans])[inverse.reshape(np.shape(first))]
        # one index array per axis, as glue's fixed-resolution buffer asks: one read per array of its samples, sorted
        # together, so that a 600 by 400 image across the 1645 pixels of a regridded window takes 6 ms, not 90 ms
        shape = np.broadcast(*key).shape
        first, *rest = (array.ravel() for array in np.broadcast_arrays(*key))
        order = np.argsort(first, kind="stable")
        values = np.empty(first.shape, self.dtype)
        for group in np.split(order, np.flatnonzero(np.diff(first[order])) + 1):
            if group.size:  # an empty read has one, empty, group
                values[group] = self.scans[first[group[0]]][tuple(array[group] for array in rest)]
        return values.reshape(shape)


class LazyData(Data):
    """
    A glue dataset whose `RawComponent` answers glue's sampled statistics, the colour limits of an Image layer, its
    style editor and a Histogram's range, from the counts of its raw codes (`SAMPLE_BYTES`), and those of a view or
    a slice, such as an Image layer's per-frame limits, from the counts of every raw code it selects.

    glue samples a dask array at a corner of ten chunks, mostly fill in IRIS windows, which gives limits of 0 to 1, and
    10,000 random values of a slice; a derived attribute, such as one made with glue's arithmetic attribute editor, is
    sampled at random points instead, as glue samples NumPy data.
    """

    def compute_statistic(self, statistic, cid, subset_state=None, axis=None, finite=True, positive=False,
                          percentile=None, view=None, random_subset=None, **kwargs):
        sampled = random_subset and finite and statistic in ("minimum", "maximum", "percentile")
        if isinstance(subset_state, SliceSubsetState) and subset_state.reference_data is self and view is None:
            subset_state, view = None, tuple(subset_state.slices)  # the view glue reads it as
        if sampled and subset_state is None and axis is None:
            component = self.get_component(cid)
            if isinstance(component, RawComponent):
                return component.sampled_statistic(statistic, percentile, positive, view)
            if view is None and isinstance(component, DerivedComponent) and self.size > random_subset:
                view, random_subset = random_indices_for_array(self, random_subset), None
        if subset_state is not None and not isinstance(subset_state, SliceSubsetState):
            # glue picks its sample of a subset's values from a mask that can be dask, which refuses index arrays;
            # the mask has read every value already
            random_subset = None
        return super().compute_statistic(statistic, cid, subset_state=subset_state, axis=axis, finite=finite,
                                          positive=positive, percentile=percentile, view=view,
                                          random_subset=random_subset, **kwargs)

    # A session saves a dataset read from its files (``_load_log``) as glue saves a Data, but for the coordinates and
    # metadata its files give, which its load log reads again, so that it restores with them, irispy's metadata class
    # and this class: only the pointing offset and the metadata added since are saved
    def __gluestate__(self, context):
        log = getattr(self, "_load_log", None)
        if context.include_data or log is None:
            return _save_data_5(self, context)
        meta = {}
        for key, value in self.meta.items():
            if key not in self._loaded_meta:
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
            "pointing_offset": list(self.coords.pointing_offset),
        }

    @classmethod
    def __setgluestate__(cls, rec, context):
        if "log" not in rec:
            yield from _load_data_5(rec, context)
            return
        log = context.object(rec["log"])
        source = log.data[rec["log_item"]]
        source.coords.pointing_offset = tuple(rec["pointing_offset"])
        context.register_object(f"{rec['uuid']} coords", source.coords)
        restored = _load_data_5({**rec, "coords": f"{rec['uuid']} coords"}, context)
        data = next(restored)
        data.__class__ = cls  # glue's loader makes a Data
        data.meta, data._load_log, data._loaded_meta = source.meta, log, source._loaded_meta
        log.data[rec["log_item"]] = data  # for a session saved from this one
        yield data
        yield from restored
