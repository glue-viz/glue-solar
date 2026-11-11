# Profile viewer: small slice subsets of large data skip the worker

- Upstream: glue-viz/glue-qt
- Fork branch: `nabobalis:perf-q2-slice-profile-sync` at `0b5b4ea118` (pushed 2026-11-12)
- Needs: `perf-q1-worker-block` merged first (not stacked on it: the numbers are stated with it)
- Label: enhancement

## Body

~~~~~markdown
The profile layer sends a layer to its worker thread when `state.layer.size > 1e7`. For a subset that is the size of the parent dataset, so the profile of one pixel of a large cube (a slice subset from a pixel selection tool, say) goes through the worker too, although `Data.compute_statistic` only reads the slice. The profile is drawn once the worker has handed it back to the main thread, so every move of the pixel waits for that round trip.

For a `SliceSubsetState` defined on the layer's own `Data`, the size of the slice now decides. Datasets, other subset states, slice subsets defined on another dataset, and data classes other than `Data` are unchanged. A layer whose worker is still computing keeps using the worker, so that an older result cannot replace a newer one.

Measured on top of #WORKER-PR (ComputeWorker blocks on its work queue): for a one-pixel slice subset of an 11x1000x1000 cube, the median time from changing the subset to its first profile is 12 ms with #WORKER-PR alone and 1.3 ms with this as well (15 changes, PyQt6, Linux). On main, where the worker polls, it is 72 ms.

Tests in `glue_qt/viewers/profile/tests/test_data_viewer.py`: `test_large_data_slice_subset` fails without the change. `test_large_data_slice_subset_worker_busy` guards the `is_computing` clause: it fails when only that clause is removed, and passes on main, where every subset of a large dataset goes to the worker.
~~~~~

## Notes for the owner (not to paste)

- Replace `#WORKER-PR` with the number of the `perf-q1-worker-block` PR; open this one after that merges.
- Existing fork branch, to force-push. Same tree as the fork's (checked); one commit on main. Only the message changed: new subject (the tracker's title), wording and numbers stated with the blocking worker, and a paragraph on the two tests.
- The numbers in the message are the reviewer's (12.1 ms, 1.3 ms, 72.3 ms). My own run of the same probe today, niced on a shared CPU: 15.0 ms with the blocking worker, 1.3 ms with both, 73.6 ms on main, and 1.7 ms with this change alone on main.
- Checked: on main with the tests added, `test_large_data_slice_subset` fails (`assert Subset: s1 (data: large) in []`) and `..._worker_busy` passes; with `or self.is_computing` removed, `..._worker_busy` fails (`assert 1 == 0`).
- Tests on the branch: `test_data_viewer.py` of the profile viewer, 48 passed, 1 skipped.
- ruff: passes.
