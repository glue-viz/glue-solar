# Read SliceSubsetState values directly in Data.compute_histogram

- Upstream: glue-viz/glue
- Fork branch: `nabobalis:perf-g8-slice-histogram`, commit 1d5d8f76 (pushed 2026-11-12)
- Label: enhancement

## Body

~~~~~markdown
`Data.compute_histogram` builds a boolean mask the size of the whole dataset for every subset state and indexes the data with it, even for a `SliceSubsetState` (such as the `PixelSubsetState` of the image viewer's pixel tool), which selects a small block of the array.

For a 1-D histogram without weights, of the data the slices are defined on or of data that is pixel-aligned with it, it now reads the sliced values with `to_array`, as `compute_statistic` already does. Every other case builds the mask as before, so the counts are the same, including the empty histogram for data that is not pixel-aligned with the slices' data.

For a 300x400x400 float32 cube and a pixel subset that selects one spectrum, a histogram goes from about 11 ms and a 48 MB temporary mask to under 0.1 ms, with identical counts.

One behaviour change: for dask data, `random_subset` is now applied to a slice subset too, as it is to the whole dataset. Before, it was skipped for any subset, because indexing a dask array with a mask gives an array of unknown size.

`test_compute_histogram_slice_subset` compares the counts with those of the equivalent mask, checks that no mask is built, and covers data that is not pixel-aligned.
~~~~~

## Notes for the owner (not to paste)

- Added to the fork branch: the condition `subset_state.reference_data is self or subset_state.reference_data in self.pixel_aligned_data`, two comment lines that say why, and four test lines for a slice subset defined on other data (zeros, as on main).
- The commit message lost its paragraph about `IncompatibleAttribute`, and its first paragraph now names the two cases the fast path covers. The dask `random_subset` paragraph is kept, as it is still a behaviour change.
- The reviewer's probe (`glue-small/bin/g8_probe.py`) now prints the same eight results on upstream/main and on the branch.
- I measured the speed again here: 7.7 ms and a 48.0 MB peak on upstream/main, 0.009 ms on the branch, same counts. The body keeps the commit message's "about 11 ms".
- Not tested: the pixel-aligned case of the fast path (reordered slices). It uses `SliceSubsetState.to_array`, which `compute_statistic` already relies on.
- Tests: `glue/core/tests/test_data.py` 98 passed, 1 xfailed. On upstream/main: `AssertionError: assert 1 == 0` (`get_mask.call_count`). With the fork branch's source as it was: `glue.core.exceptions.IncompatibleAttribute` at the new lines.
