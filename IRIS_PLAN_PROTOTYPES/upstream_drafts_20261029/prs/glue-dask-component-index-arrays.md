# Read a DaskComponent at several index arrays

- Upstream: glue-viz/glue
- Fork branch: `nabobalis:dask-component-index-arrays`, commit 1aafe967 (pushed 2026-11-12)
- Needs: `fix-unbroadcast-empty` (commit a5da831d, its parent)
- Label: bug

## Body

~~~~~markdown
Reading a `DaskComponent` at two or more index arrays raises `NotImplementedError: Don't yet support nd fancy indexing`, and at one index array with several dimensions a `TypeError`, because dask takes one 1-d index array at a time. Every other component takes such a view:

```python
data = Data(v=da.from_array(np.arange(12.).reshape(3, 4), chunks=2))
data.get_data(data.id['v'], view=(np.array([0, 2]), np.array([1, 3])))
```

`DaskComponent.__getitem__` now handles a key made only of integer arrays and integers itself. It takes the distinct indices along each axis in turn, the axis with the fewest first, which reads only the chunks they fall in, and then picks the pixels from the result as numpy would. Any other key goes to dask as before.

Known limit: the values it reads are the product of the distinct indices along each axis. Index arrays that vary together, as along a diagonal path, read their whole bounding box.

`test_view_dask_index_arrays` compares seven keys with numpy. Six fail on main; the seventh, an array with a slice, checks that such keys still go to dask.

Stacked on #NNNN, which the empty index arrays need. Only the last commit is new here.
~~~~~

## Notes for the owner (not to paste)

- Replace #NNNN with the number of the `fix-unbroadcast-empty` PR. Until that merges, this PR shows two commits.
- Against the fork's `fix-frb-dask-index-arrays`: the `vindex` fallback and `import math` are gone, and `test_view_dask_index_arrays_along_path`, which tested the fallback, with them.
- The shape fix: the result is indexed with each axis's positions broadcast to `np.broadcast(*key).shape`, so an axis along which every index array is broadcast is kept. I wrote it from the review's description, as the reviewer's diff was not in the files I could read.
- The condition is `sum(np.ndim(k) for k in key) > 1`, not "two or more arrays", so that one index array with several dimensions is handled too. That is the review's "1-D dask dataset in a 2-D frame" case.
- "Fewest first" is kept because it measures: for a row over 40 of 400 frames, the peak is 1.0 MiB against 32.5 MiB in axis order.
- The reviewer's two shape cases are the last two parameters of the test. With the fork's original `__getitem__` they fail: `shapes (1, 2, 3, 5), (4, 2, 3, 5) mismatch` and `TypeError`.
- The reviewer's fuzz script (136 keys against numpy) gives 7 mismatches, all for keys this PR does not claim: slices, `None`, `Ellipsis`, booleans or floats mixed with arrays (dask raises, as on main), and index arrays of shapes that do not broadcast (`ValueError` here, `IndexError` in numpy).
- Tests: `test_component.py` and `test_array.py`, 191 passed, 1 xfailed. On upstream/main six cases fail: five with `NotImplementedError: Don't yet support nd fancy indexing`, one with `TypeError: '>=' not supported between instances of 'list' and 'int'`. Without the `unbroadcast` change the empty case fails: `IndexError: Index is out of bounds for axis 0 with size 3`.
- Label: `bug` because any other component takes these views; `enhancement` would also be fair.
