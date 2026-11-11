# Return an empty array unchanged from unbroadcast

- Upstream: glue-viz/glue
- Fork branch: `nabobalis:fix-unbroadcast-empty`, commit a5da831d (pushed 2026-11-12)
- Label: bug

## Body

~~~~~markdown
`glue.utils.unbroadcast` takes an axis with a stride of 0 for a broadcast axis and shrinks it to length 1. numpy also gives every axis of an empty array a stride of 0, so an empty array came back as a view of length 1 along each axis, over memory the array does not own:

```python
>>> unbroadcast(np.array([], dtype=int))
array([140183257475840])
>>> unbroadcast(np.zeros((0, 3))).shape
(1, 1)
```

An empty array is now returned as it is. `test_unbroadcast_empty` fails on main with `assert (1, 1) == (0, 3)`.
~~~~~

## Notes for the owner (not to paste)

- One changed source line (`or array.size == 0`), taken from `origin/fix-frb-dask-index-arrays`, and a new direct test in `glue/utils/tests/test_array.py`.
- The two outputs in the body are from a run on upstream/main; the first value is whatever is in memory, so it differs from run to run.
- Tests: `glue/utils/tests/test_array.py` 119 passed. On upstream/main: `assert (1, 1) == (0, 3)`.
- `dask-component-index-arrays` is stacked on this branch.
- It merges cleanly with `perf-g10-view-shape`, which touches the same two files.
