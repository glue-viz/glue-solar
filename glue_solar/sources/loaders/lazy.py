"""
IRIS data held as the file's raw 16-bit integers, scaled only where glue reads them, with the missing-data codes as NaN.
"""

from uuid import uuid4

import dask.array as da
import numpy as np
from glue.core.component import DaskComponent, DerivedComponent
from glue.core.data import Data
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

    Each memory-mapped raster file stays open, once per window read from it: the 99 scans of 3602506433
    pass the 256 files macOS gives GUI applications by its third window.
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
    ``fill`` codes NaN. It has no ``copy`` method, which dask would call and so read the whole file.
    """

    def __init__(self, raw, bscale, bzero, fill):
        # ponytail: raw is irispy's memory map, whose pages stay resident once viewed and which a file cut short or a
        # lost drive turns into SIGBUS; a reader of whole planes (os.pread) in its place bounds both
        self.raw = raw
        self.shape, self.ndim, self.dtype = raw.shape, raw.ndim, np.dtype(np.float32)
        self.bscale, self.bzero, self.fill = np.float32(bscale), np.float32(bzero), np.asarray(fill, np.int16)

    def __getitem__(self, key):
        raw = np.asarray(self.raw[key])
        values = raw.astype(np.float32)
        values *= self.bscale
        values += self.bzero
        values[np.isin(raw, self.fill)] = np.nan
        return values


class RawComponent(DaskComponent):
    """
    A glue component over the raw int16 of an IRIS window, slit-jaw or AIA cube: a memory map, or an array in memory
    for a ``.fits.gz`` file.

    A read with a view, as every image, profile and cursor readout asks, scales only what the view selects, index
    arrays included; a read of the whole component goes through dask, a chunk at a time.
    """

    def __init__(self, raw, bscale, bzero, missing, units=None):
        # the raw codes of the missing values (D12): exact integers only, as only those can be stored
        codes = [(value - bzero) / bscale for value in missing]
        fill = [int(code) for code in codes if float(code).is_integer() and -32768 <= code <= 32767]
        self._source = _Scaled(raw, bscale, bzero, fill)
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

    def _sample(self):
        """How often each raw code occurs in the colour-limit sample (`SAMPLE_BYTES`), the fill codes left out."""
        if self._counts is None:
            raw = self._source.raw
            planes = int(np.prod(raw.shape[:-2]))
            wanted = max(1, min(planes, SAMPLE_BYTES // (raw.shape[-2] * raw.shape[-1] * raw.dtype.itemsize)))
            counts = np.zeros(65536, np.int64)
            for plane in np.unique(np.linspace(0, planes - 1, wanted).round().astype(int)):
                values = np.asarray(raw[np.unravel_index(plane, raw.shape[:-2])])
                counts += np.bincount(values.ravel().astype(np.int32) + 32768, minlength=65536)
            counts[self._source.fill.astype(np.int32) + 32768] = 0
            self._counts = counts
        return self._counts

    def sampled_statistic(self, statistic, percentile=None, positive=False):
        """'minimum', 'maximum' or 'percentile' of the sample, as NumPy's linear percentile of the scaled values."""
        counts = self._sample()
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
    Equal-shaped raw arrays, one per raster scan, as one array with a leading scan axis; a read touches only the
    scans it selects.
    """

    def __init__(self, scans):
        if any(scan.shape != scans[0].shape for scan in scans):
            raise ValueError("All raster scans must have the same shape to be stacked")
        self.scans = scans
        self.shape = (len(scans), *scans[0].shape)
        self.ndim, self.dtype = len(self.shape), scans[0].dtype

    def __getitem__(self, key):
        key = key if isinstance(key, tuple) else (key,)
        first, rest = key[0], key[1:]
        if isinstance(first, (int, np.integer)):
            return np.asarray(self.scans[first][rest])
        if isinstance(first, slice):
            return np.stack([np.asarray(self.scans[i][rest]) for i in range(*first.indices(len(self.scans)))])
        # one index array per axis, as glue's fixed-resolution buffer asks
        arrays = np.broadcast_arrays(*key)
        values = np.empty(arrays[0].shape, self.dtype)
        for scan in np.unique(arrays[0]):
            where = arrays[0] == scan
            values[where] = self.scans[scan][tuple(array[where] for array in arrays[1:])]
        return values


class LazyData(Data):
    """
    A glue dataset whose `RawComponent` answers glue's sampled statistics, the colour limits of an Image layer, its
    style editor and a Histogram's range, from the counts of its raw codes (`SAMPLE_BYTES`).

    glue samples a dask array at a corner of ten chunks, mostly fill in IRIS windows, which gives limits of 0 to 1; a
    derived attribute, such as one made with glue's arithmetic attribute editor, is sampled at random points instead,
    as glue samples NumPy data.
    """

    def compute_statistic(self, statistic, cid, subset_state=None, axis=None, finite=True, positive=False,
                          percentile=None, view=None, random_subset=None, **kwargs):
        sampled = random_subset and finite and statistic in ("minimum", "maximum", "percentile")
        if sampled and subset_state is None and axis is None and view is None:
            component = self.get_component(cid)
            if isinstance(component, RawComponent):
                return component.sampled_statistic(statistic, percentile, positive)
            if isinstance(component, DerivedComponent) and self.size > random_subset:
                view, random_subset = random_indices_for_array(self, random_subset), None
        return super().compute_statistic(statistic, cid, subset_state=subset_state, axis=axis, finite=finite,
                                          positive=positive, percentile=percentile, view=view,
                                          random_subset=random_subset, **kwargs)
