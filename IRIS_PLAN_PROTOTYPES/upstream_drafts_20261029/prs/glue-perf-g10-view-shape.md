# Compute view_shape for integer index arrays without building the view

- Upstream: glue-viz/glue
- Fork branch: `nabobalis:perf-g10-view-shape`, commit 22c22760 (on the fork, not rebuilt)
- Label: enhancement

## Body

~~~~~markdown
`view_shape` returns `np.broadcast_to(1, shape)[view].shape`. For a tuple of integer index arrays, such as the pixel coordinates that `compute_fixed_resolution_buffer` passes to `Data.get_mask`, the fancy indexing allocates and fills an int64 array of the full view shape only to read its shape. For a 333x196x100 buffer that takes 21 to 34 ms and 52 MB per call, about half of the subset mask gather on each redraw of an image viewer that shows a subset over an aggregated slice.

The shape of such a view is the broadcast shape of the index arrays followed by the dimensions they do not index, so it is now computed with `np.broadcast` (which, unlike `np.broadcast_shapes`, exists in every supported numpy). The call takes about a microsecond and allocates nothing.

Other views, and index arrays that `np.broadcast` rejects (shapes that do not broadcast, or more arrays than it accepts), still take the old path and give the same result or error as before. Index values are not checked against the shape on the new path.

Tests: `test_view_shape_index_arrays`, `test_view_shape_index_arrays_large` and `test_view_shape_index_arrays_invalid`.
~~~~~

## Notes for the owner (not to paste)

- Not rebuilt and not run by me: the text is the commit message, shortened. The review marks the branch ready as it is.
- It touches `glue/utils/array.py` and its tests, like `fix-unbroadcast-empty`. The two merge cleanly.
