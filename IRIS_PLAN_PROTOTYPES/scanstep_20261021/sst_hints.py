"""
The glue-solar change this prototype proposes for wp10-l-sst-scan-step, written as a patch of `_Cube`
(glue_solar/sources/sst.py) so it can be measured without touching glue-solar: before glue reads an SST cube's values
from its memory map, tell the kernel every page the read will touch (MADV_WILLNEED on the cube's own mapping), so the
pages come from the disk in parallel instead of one page fault at a time. The values still come from the map.

    import sst_hints; sst_hints.patch()        # in a process, before reading
    python sst_hints.py CUBE.fits              # self-check: same values, and a cold slit read with and without
"""

import mmap

import numpy as np
from glue.core.component import Component
from glue.core.subset import SliceSubsetState
from glue.utils import unbroadcast

from glue_solar.sources.sst import _Cube

_PAGE = mmap.PAGESIZE
_CHUNK = (128 << 10) // _PAGE  # pages a call


def _ranges(starts, length):
    """
    The page ranges, ``(first page, pages)``, covering ``length`` bytes at each of ``starts``, byte offsets into a map:
    ranges a page or less apart as one (a dense sample's pages, all of them), split in calls of at most 128 KB, as
    the kernel reads no more of one call than its readahead window (4 MB here, 128 KB by default).
    """
    starts = np.sort(np.asarray(starts, np.int64).ravel())
    lo, hi = starts // _PAGE, (starts + length - 1) // _PAGE
    cut = np.flatnonzero(lo[1:] > hi[:-1] + 2) + 1
    return [(page, min(_CHUNK, int(hi[b - 1]) + 1 - page))
            for a, b in zip(np.r_[0, cut].tolist(), np.r_[cut, len(lo)].tolist())
            for page in range(int(lo[a]), int(hi[b - 1]) + 1, _CHUNK)]


def _will_need(array, starts, length):
    """
    MADV_WILLNEED on `_ranges`, ``starts`` byte offsets from the first value of ``array``, a view of a file's memory
    map; nothing for an array in memory or without madvise (Windows).
    """
    root = array
    while isinstance(root.base, np.ndarray):
        root = root.base
    if not isinstance(root.base, mmap.mmap) or not hasattr(root.base, "madvise") or not len(starts):
        return
    origin = array.__array_interface__["data"][0] - np.frombuffer(root.base, np.uint8).__array_interface__["data"][0]
    for page, pages in _ranges(np.asarray(starts, np.int64) + origin, length):
        root.base.madvise(mmap.MADV_WILLNEED, page * _PAGE, pages * _PAGE)


def hint_view(cube, cid, view):
    """
    `_will_need` on the values of ``cube[cid, view]`` for a fancy index, as glue's image buffers and samples read: for
    glue's buffers, broadcasts of an index per axis, each row's span between the columns read, else each value, for
    100,000 values or fewer. The byte offsets and length asked for, or None.
    """
    component = cube._components.get(cid)
    if type(component) is not Component or not isinstance(view, tuple) or len(view) != cube.ndim:
        return
    if not all(isinstance(index, np.ndarray) and index.dtype.kind in "iu" for index in view):
        return
    array = component.data
    small = [unbroadcast(index) for index in view]
    along = [[k for k, n in enumerate(index.shape) if n > 1] for index in small]
    if all(len(axes) <= 1 for axes in along) and len({axis for axes in along for axis in axes}) == sum(map(len, along)):
        *outer, columns = (np.unique(index).astype(np.int64) for index in small)
        starts = sum(index * stride for index, stride in zip(np.ix_(*outer), array.strides))
        hint = starts + columns[0] * array.strides[-1], (columns[-1] - columns[0]) * array.strides[-1] + array.itemsize
    elif view[0].size <= 100_000:
        hint = np.unique(sum(index.astype(np.int64) * s for index, s in zip(view, array.strides))), array.itemsize
    else:
        return None
    _will_need(array, *hint)
    return hint


def hint_subset(cube, cid, subset_state):
    """`_will_need` on the rows of a slice subset of ``cube``: a per-frame limit's frame, a spectrum's pixel."""
    component = cube._components.get(cid)
    if type(component) is Component and isinstance(subset_state, SliceSubsetState):
        *outer, columns = (np.arange(*s.indices(n)) if isinstance(s, slice) else np.array([s])
                           for s, n in zip(subset_state.slices, cube.shape))
        if len(columns) and np.prod([len(index) for index in outer]) <= 100_000:
            array = component.data
            grid = np.ix_(*outer)
            starts = sum(index * stride for index, stride in zip(grid, array.strides)) + columns[0] * array.strides[-1]
            _will_need(array, starts, (columns[-1] - columns[0]) * array.strides[-1] + array.itemsize)


def get_data(self, cid, view=None, _original=_Cube.get_data):
    """glue's, after `hint_view`."""
    hint_view(self, cid, view)
    return _original(self, cid, view=view)


def compute_statistic(self, statistic, cid, subset_state=None, _original=_Cube.compute_statistic, **kwargs):
    """`_Cube`'s, after `hint_subset`."""
    hint_subset(self, cid, subset_state)
    return _original(self, statistic, cid, subset_state=subset_state, **kwargs)


def patch():
    _Cube.get_data, _Cube.compute_statistic = get_data, compute_statistic


if __name__ == "__main__":  # self-check on a real cube: identical values, and the cold read with and without
    import os
    import sys
    import time

    from glue_solar.sources.sst import sst_data

    path = sys.argv[1]
    cube = sst_data(path)
    cid = cube.main_components[0]
    *_, tunings, rows, columns = cube.shape
    lead = (np.array([[[1]]]),) * (cube.ndim - 3)  # scan 1, Stokes I
    y = np.round(np.linspace(0, rows - 1, 88)).astype(int)[None, :, None]
    view = (*lead, np.arange(tunings)[:, None, None], y, np.array([[[columns // 2]]]))  # the slit at panel size
    frame = SliceSubsetState(cube, [slice(2, 3)] + [slice(0, 1)] * (cube.ndim - 4) + [slice(None)] * 2)

    def evict():
        fd = os.open(path, os.O_RDONLY)
        os.posix_fadvise(fd, 0, 0, os.POSIX_FADV_DONTNEED)  # pages this process mapped stay: those read are not reread
        os.close(fd)

    def cold(label, read):
        evict()
        start = time.perf_counter()
        value = read()
        print(f"{label}: {(time.perf_counter() - start) * 1e3:.1f} ms")
        return value

    before = cold("slit, glue's read", lambda: np.array(cube.get_data(cid, view)))
    del cube
    cube = sst_data(path)  # a fresh map, unread
    cid = cube.main_components[0]
    frame = SliceSubsetState(cube, frame.slices)
    limit = cube.compute_statistic("percentile", cid, subset_state=frame, percentile=99.5, random_subset=10_000)
    patch()
    shifted = (*lead, np.arange(tunings)[:, None, None], np.minimum(y + 1, rows - 1), np.array([[[columns // 2]]]))
    after = cold("slit, with the hints", lambda: np.array(cube.get_data(cid, shifted)))  # rows not yet mapped
    raw = cube.get_component(cid).data  # the memory map itself, no glue
    assert np.array_equal(after, raw[shifted], equal_nan=True)
    assert np.array_equal(np.array(cube.get_data(cid, view)), before, equal_nan=True)
    # glue's 10,000 random values are drawn once per dataset: the same with the hints as without
    assert cube.compute_statistic("percentile", cid, subset_state=frame, percentile=99.5, random_subset=10_000) == limit
    print("same values with the hints")
