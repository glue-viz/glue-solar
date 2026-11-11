# dkist: whole-file reads (comment on dkist #226)

- **Where:** a comment on DKISTDC/dkist#226 ("Reading real data into the Dask array is *slow*", open since 2023-02-23,
  last updated 2025-07-15; listed in #256). Its loader task ("use the new `.section` api if available to load one
  section ... make the dask array with chunk size equal to the tile size") is ticked, but the graph still reads whole
  files. Draft #738 (remote file URIs) edits `loaders.py`, `striped_array.py` and `file_manager.py`, so a fix should
  follow it.
- **Review row:** dkist row 7 (REPORT). Replaces the draft `scratchpad/fix13/wp13-dkist-read-path/dkist-whole-files.md`.
  Its suggested fix is changed: dask does not pass a view through `stack` to a `from_array` loader (tried), so the
  chunks must be the files' tiles.
- **Reproducer:** `scripts/dkist_whole_files.py`, run by `run.sh rel|main dkist_whole_files.py`, and
  `run.sh main dkist_whole_files.py --tile-chunks` for the prototype; outputs
  `out/dkist_whole_files_{rel,main,prototype}.txt`.

## Comment (paste)

The task "use the new `.section` api if available to load one section" is ticked, but dkist 1.18.1 and main
(2a4b15ba) still decompress every file a view touches whole. One value, or two values from each file, asks each
loader for `slice(None)`. With dkist's own test data:

```python
import warnings
from pathlib import Path

import dkist
from dkist.data.test import rootdir
from dkist.io.dask.loaders import AstropyFITSLoader

warnings.filterwarnings("ignore", message="ERFA function")  # the test files' dates
asked = []
getitem = AstropyFITSLoader.__getitem__


def recorded(self, slc):
    asked.append((Path(self.fileuri).name, slc))
    return getitem(self, slc)


AstropyFITSLoader.__getitem__ = recorded
ds = dkist.load_dataset(Path(rootdir) / "small_visp" / "test_visp.asdf")  # 3 FITS files of (1, 10, 25)
print("dkist from", dkist.__file__, "| array", ds.data.shape, "chunks", ds.data.chunks)
print("one value:", float(ds.data[1, 2, 3].compute()), "| the loaders were asked for", asked)
asked.clear()
ds.data[:, 0, :2].compute()
print("two values from each file | the loaders were asked for", sorted(asked))
```

The output is the same on 1.18.1 and main (path shortened):

```
dkist from .../site-packages/dkist/__init__.py | array (3, 10, 25) chunks ((1, 1, 1), (10,), (25,))
one value: 0.28217638603112705 | the loaders were asked for [('1.fits', slice(None, None, None))]
two values from each file | the loaders were asked for [('0.fits', slice(None, None, None)), ('1.fits', slice(None, None, None)), ('2.fits', slice(None, None, None))]
```

`stack_loader_array` makes one task per file, `(_call_loader, loader)` (`dkist/io/dask/utils.py:40-45` on main).
`_call_loader` reads `loader.data` (`:66-67`), which is `self[:]` (`loaders.py:64-65`). Dask slices that whole array
afterwards, so `hdu.section[slc]` (`loaders.py:102`) never sees the view. The `chunksize` rechunk (`utils.py:56-62`)
runs after the whole-file reads, so it cannot help either.

On complete Level 1 data this is most of a view's cost. For a ViSP map at one wavelength (510 RICE-compressed files of
916 x 2555 per Stokes parameter, 256 x 256 tiles), we measured 4.5-5 s of an 8 s draw reading 500 files whole, where
the tiles the view touches take 0.7 s on 8 threads.

A fix that worked in a quick prototype, checked only for what the loaders are asked, is to give each file its own
dask array, chunked by the file's compression tiles, and stack those. Dask then asks each loader for the tiles a view
touches, and `hdu.section` decompresses only those:

```python
import uuid

import dask.array as da
import numpy as np


def stack_loader_array(loader_array, output_shape, chunksize=None):
    tile = (1, 5, 5)  # for the test files; the files' own ZTILEn in general
    arrays = [da.from_array(loader, chunks=tile, name=f"load-{uuid.uuid4().hex}", asarray=False,
                            meta=np.empty((0,) * len(tile), dtype=loader.dtype)) for loader in loader_array.flat]
    return da.stack(arrays).reshape(output_shape)
```

Patched in for `dkist.io.dask.striped_array.stack_loader_array`, the script above gives, on main:

```
dkist from .../dkist-main/dkist/__init__.py | array (3, 10, 25) chunks ((1, 1, 1), (5, 5), (5, 5, 5, 5, 5))
one value: 0.28217638603112705 | the loaders were asked for [('1.fits', (slice(0, 1, None), slice(0, 5, None), slice(0, 5, None)))]
two values from each file | the loaders were asked for [('0.fits', (slice(0, 1, None), slice(0, 5, None), slice(0, 5, None))), ('1.fits', (slice(0, 1, None), slice(0, 5, None), slice(0, 5, None))), ('2.fits', (slice(0, 1, None), slice(0, 5, None), slice(0, 5, None)))]
```

Chunks of a whole file are not enough: dask does not pass a later slice through `stack` to the loader, so it still
asks for the whole file. The tile shape could come from the file manager's `chunksize` (in the schema since 1.0.0)
or the files' `ZTILEn`.

Two things must go with it. The missing-file branch of `AstropyFITSLoader.__getitem__` returns NaN in the whole
file's shape and ignores the slice (`loaders.py:89-93`). With tile chunks, and 2.fits removed from a copy of
small_visp, a view that touches it raises `ValueError: cannot reshape array of size 250 into shape (1,5,5)` instead of
giving NaN; applying `slc` there too fixes that. And `__getitem__` opens the file at each call (`:95-102`), so tile
chunks make views cheap but cost one open and one task per tile on a whole-file read: counting `fits.open` calls,
`ds.data.compute()` on small_visp makes 30 instead of 3, and a 916 x 2555 ViSP file in 256 x 256 tiles would take 40
instead of 1 (20,400 for a whole read of the 510-file map, at about 4-5 ms an open on that data). So chunks of several tiles, or keeping recently used files open, should come with it. Keeping files open
needs care with the open-file limit and a lock per file for threaded schedulers.

## Notes for the user (not to paste)

- The ViSP figures (TXIPCV: 4.5-5 s of 8 s, 0.7 s for the tiles, 4-5 ms of opening per file) are glue-solar's
  profiling of 2026-10-23 (`scratchpad/dkist-profile/REPORT.md`), not re-run here.
- The prototype was checked only for what the loaders are asked (on small_visp, whose test files are tiny); it was not
  timed on compressed data or run through dkist's tests.
- The missing-file and file-open figures are `scripts/dkist_missing_file_probe.py` on main
  (`out/dkist_missing_file_probe_main.txt`): small_visp copied, 2.fits moved away. dkist as is gives NaN for 2.fits
  and 3 opens for a whole read; the prototype raises the ValueError and makes 30 opens; the prototype with the branch
  returning `np.broadcast_to(np.nan, self.shape)[slc]` gives NaN again. 40 is ceil(916/256) x ceil(2555/256) = 4 x 10.
- The draft's suggestion ("dask's getitem optimization fuses a view into `loader[slc]`") does not hold on dask
  2026.8.0. A single `from_array` array passes `(0, 2, 3)` to its loader, but through `stack` or `concatenate` dask
  asks for the whole chunk (`tmp/fuse_probe.py`).
