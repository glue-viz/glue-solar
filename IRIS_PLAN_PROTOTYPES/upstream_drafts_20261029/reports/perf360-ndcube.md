# ndcube: slicing deep-copies the whole NDMeta (perf360 c2)

- **Where:** a new issue on sunpy/ndcube, "Performance Suggestions" template (sunpy/.github `PERFORMANCE.yaml`: Describe
  the performance issue, To Reproduce, Proposed fix). No existing issue or PR found (`gh search` for "deepcopy meta",
  "NDMeta slice slow", "meta slicing performance", "deepcopy", "slicing slow", "NDMeta copy"; no open PR on meta).
  Related, both open: #815 (copy or deepcopy of the meta in `rebin`; Cadair proposes `copy`) and your #989 (deep copies
  through `_ndcube`; #996 merged). An issue, not a PR: sharing the values not axis-aware is the same open choice as
  #815. The body offers the PR.
- **Review row:** perf360 REPORT (c) c2 (and its irispy alternative, an `SGMeta.__deepcopy__` sharing `_fits_header`).
- **Reproducer:** `scripts/perf360_ndcube.py` (synthetic 412-card header with the value types of an IRIS primary
  header); output `out/perf360_ndcube_rel.txt`; peak 312 MB. Release: ndcube 2.4.3 in iris-plan-latest-1028,
  `python -I -B`, 24G cap.
- **Tests with the prototype:** `scripts/perf360_ndcube_plugin.py` applies the same shallow copy in the slicer;
  `pytest -n 4 --pyargs ndcube` gives 610 passed, 29 skipped, 10 xfailed with and without it
  (`out/perf360_ndcube_tests_{stock,proto}.txt`; peaks 1.4 and 1.2 GB).
- **Main (f4d58976) not run:** the permission classifier refused to run the clone's code ("Code from External").
  From the source: `ndcube/meta.py`, `mixins/ndslicing.py` and `ndcube.py` are identical to v2.4.3, and the
  deepcopy is still `meta.py:370`. The sketch is against main.

## Title

Slicing an NDCube deep-copies its whole NDMeta, a FITS header included

## Body (paste)

**Describe the performance issue**

`_NDMetaSlicer.__getitem__` starts with `new_meta = copy.deepcopy(self.meta)` (`ndcube/meta.py:370`), then replaces
the axis-aware values. So every slice of a cube with an `NDMeta` copies every value in it, and also `_original_meta`.
Neither needs copying for the slice: the slicer only changes the axis-aware values, `_axes`, `_key_comments` and
`_data_shape`. A plain dict meta, by contrast, is shared by the slice, as NDData shares it.

With an `NDMeta` made from a 412-card FITS header and one axis-aware value, `cube[0]` takes 0.72 ms, against 0.016 ms
with the same header as a dict meta. Almost all of it is the deepcopy (0.65 ms). irispy keeps each file's header in
its `NDMeta` subclass. glue-solar slices 11,070 such cubes to load one IRIS observation, and there the deepcopy was
1.3 of the 2.3 ms each slice took: 13.5% of the load.

**To Reproduce**

```python
"""Slicing an NDCube whose NDMeta holds a FITS header: the slicer deep-copies the whole NDMeta every time.

The header has 412 cards with the value types of an IRIS level 2 primary header (211 float, 138 int, 61 str, 2 bool).
The script times a slice with NDMeta, with the same header as a plain dict meta (which slicing shares, as NDData does),
and with a prototype slicer that shallow-copies the NDMeta and replaces only the sliced axis-aware values.
"""

import copy
import resource
import sys
import timeit

import numpy as np

import astropy
import astropy.wcs
import ndcube
import ndcube.meta
from astropy.io import fits
from ndcube import NDCube, NDMeta


def header():
    cards = []
    for i in range(412):
        if i < 211:
            value = 0.1 * i
        elif i < 349:
            value = i
        elif i < 410:
            value = f"text {i}" if i % 2 else f"t{i}"  # short strings are padded with spaces, as in a FITS file
        else:
            value = bool(i % 2)
        cards.append((f"KEY{i:04d}", value, f"comment {i}"))
    return fits.Header.fromstring(fits.Header(cards).tostring())  # parsed from a card string, as from a file


def make_cube(meta):
    wcs = astropy.wcs.WCS(naxis=3)
    wcs.wcs.ctype = ["WAVE", "HPLT-TAN", "HPLN-TAN"]
    wcs.wcs.cunit = ["Angstrom", "deg", "deg"]
    wcs.wcs.cdelt = [0.025, 0.0001, 0.0001]
    wcs.wcs.crval = [1400, 0, 0]
    return NDCube(np.zeros((8, 100, 40)), wcs=wcs, meta=meta)


def make_ndmeta():
    meta = NDMeta(header(), data_shape=(8, 100, 40))
    meta.add("exposure time", np.linspace(8, 8.5, 8), "seconds, one per step", axes=0)
    return meta


def per_call(fn, number=300):
    return min(timeit.repeat(fn, number=number, repeat=7)) / number


def shallow_copy(meta, memo=None):
    """Prototype for _NDMetaSlicer.__getitem__: share the values, copy only what the slicer changes."""
    new = type(meta).__new__(type(meta))
    new.__dict__.update(meta.__dict__)
    dict.update(new, meta)
    new._axes = dict(meta._axes)
    new._key_comments = dict(meta._key_comments)
    new._data_shape = meta._data_shape.copy()
    return new


def same(a, b):
    return (
        a.keys() == b.keys()
        and all(np.array_equal(a[k], b[k]) if isinstance(a[k], np.ndarray) else a[k] == b[k] for k in a)
        and {k: tuple(v) for k, v in a.axes.items()} == {k: tuple(v) for k, v in b.axes.items()}
        and dict(a.key_comments) == dict(b.key_comments)
        and np.array_equal(a.data_shape, b.data_shape)
    )


print(f"Python {sys.version.split()[0]}, numpy {np.__version__}, astropy {astropy.__version__}")
print(f"ndcube {ndcube.__version__} from {ndcube.__file__}")
meta = make_ndmeta()
cube = make_cube(meta)
plain = make_cube(dict(header()))
print(f"NDMeta: {len(meta)} keys, original_meta a {type(meta._original_meta).__name__} of {len(meta._original_meta)} cards")
items = {"cube[0]": 0, "cube[2:5]": slice(2, 5)}
stock = {}
for label, item in items.items():
    stock[label] = cube[item].meta
    t_cube = per_call(lambda: cube[item])
    t_plain = per_call(lambda: plain[item])
    t_slice = per_call(lambda: meta.slice[item])
    print(f"{label}: {t_cube * 1e3:.3f} ms with NDMeta, {t_plain * 1e3:.3f} ms with a dict meta; "
          f"meta.slice[...] alone {t_slice * 1e3:.3f} ms")
t_deep = per_call(lambda: copy.deepcopy(meta))
print(f"copy.deepcopy(meta) alone: {t_deep * 1e3:.3f} ms")
print("a dict meta is shared by the slice:", plain[0].meta is plain.meta)

ndcube.meta.copy = type(sys)("copy")  # the slicer's copy.deepcopy becomes the prototype's shallow copy
ndcube.meta.copy.deepcopy = shallow_copy
before = (dict(meta.axes), meta.data_shape.copy(), dict(meta.key_comments), len(meta))
for label, item in items.items():
    sliced = cube[item].meta
    t_cube = per_call(lambda: cube[item])
    t_slice = per_call(lambda: meta.slice[item])
    print(f"prototype, {label}: {t_cube * 1e3:.3f} ms with NDMeta; meta.slice[...] alone {t_slice * 1e3:.3f} ms; "
          f"meta equal to stock: {same(sliced, stock[label])}; exposure time {sliced['exposure time']}")
after = (dict(meta.axes), meta.data_shape.copy(), dict(meta.key_comments), len(meta))
print("prototype leaves the original NDMeta unchanged:",
      before[0].keys() == after[0].keys() and np.array_equal(before[1], after[1]) and before[2:] == after[2:])
print(f"peak RSS: {resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024:.0f} MB")
```

Output with ndcube 2.4.3 (main, f4d58976, has the same `meta.py`), paths shortened:

```
Python 3.13.16, numpy 2.5.4, astropy 8.0.2
ndcube 2.4.3 from .../site-packages/ndcube/__init__.py
NDMeta: 413 keys, original_meta a Header of 412 cards
cube[0]: 0.722 ms with NDMeta, 0.016 ms with a dict meta; meta.slice[...] alone 0.678 ms
cube[2:5]: 0.757 ms with NDMeta, 0.015 ms with a dict meta; meta.slice[...] alone 0.713 ms
copy.deepcopy(meta) alone: 0.646 ms
a dict meta is shared by the slice: True
prototype, cube[0]: 0.046 ms with NDMeta; meta.slice[...] alone 0.024 ms; meta equal to stock: True; exposure time 8.0
prototype, cube[2:5]: 0.070 ms with NDMeta; meta.slice[...] alone 0.039 ms; meta equal to stock: True; exposure time [8.14285714 8.21428571 8.28571429]
prototype leaves the original NDMeta unchanged: True
peak RSS: 312 MB
```

The prototype gives the same sliced meta (values, axes, comments, data shape), leaves the original unchanged, and
takes a slice from 0.72 to 0.05 ms. With it, ndcube's tests pass as before (`pytest --pyargs ndcube`: 610 passed,
29 skipped, 10 xfailed, on 2.4.3).

**Proposed fix**

Copy the `NDMeta` shallowly in the slicer, with fresh copies of only what the slicer changes in place. A `__copy__` on
`NDMeta` keeps that in one place (today `copy.copy(meta)` shares `_axes`, `_key_comments` and `_data_shape` with the
original, so an `add` on the copy changes the original's axes). A sketch against main:

```diff
--- a/ndcube/meta.py
+++ b/ndcube/meta.py
@@ -312,6 +312,16 @@
     def original_meta(self):
         return MappingProxyType(self._original_meta)
 
+    def __copy__(self):
+        # Share the values, but not the axes, comments and data shape, which add, del and slicing change in place.
+        new_meta = type(self).__new__(type(self))
+        new_meta.__dict__.update(self.__dict__)
+        dict.update(new_meta, self)
+        new_meta._axes = dict(self._axes)
+        new_meta._key_comments = dict(self._key_comments)
+        new_meta._data_shape = self._data_shape.copy()
+        return new_meta
+
     @property
     def slice(self):
         # Docstring in ABC.
@@ -367,7 +377,9 @@
         if len(data_shape) == 0:
             raise TypeError("NDMeta object does not have a shape and so cannot be sliced.")
 
-        new_meta = copy.deepcopy(self.meta)
+        # The values that are not axis-aware are shared with the unsliced meta, as NDData shares a meta that is
+        # not an NDMeta. A deepcopy here copied all of them (a large FITS header, say) on every slice.
+        new_meta = copy.copy(self.meta)
         naxes = len(data_shape)
         if isinstance(item, (numbers.Integral, slice)):
             item = [item]
```

The change in behavior: a value that is not axis-aware, such as a header object, is then the same object in the cube
and in its slices, as it is for a dict meta. That is the copy-or-deepcopy question of #815 for `rebin`; if a deepcopy
is the wanted default, a `copy=False` option on the slice would do for us. I am happy to open a PR either way.

Python 3.13.16 on Fedora Linux 44, ndcube 2.4.3 from pip, astropy 8.0.2, numpy 2.5.4.

## Notes for the user (not to paste)

- The irispy and glue-solar figures (11,070 slices, 1.3 of 2.3 ms, 13.5%) are the perf360 REPORT's, from stock #360
  with follow-irispy-main; not re-run. In that profile filelock's audit hook also ran inside the deepcopy, which the
  2.3 ms includes.
- The prototype tested is the function in the reproducer, used for the slicer's `copy.deepcopy` only. The sketch
  puts the same code in `NDMeta.__copy__` and calls `copy.copy`, so `copy.copy(meta)` elsewhere changes too (it
  stops sharing the bookkeeping dicts). ndcube calls `copy.copy` on a meta nowhere in its source. ruff 0.16.1 with
  ndcube's config passes on the edited `meta.py`.
- irispy note: with a shallow slice, `_combine_raster_metas` writing DATE_END into its header copy must stay a copy
  (REPORT c2), or the write reaches the shared header.
