# Sample only the pixels a buffer needs from a DaskComponent

- Upstream: glue-viz/glue
- Fork branch: `nabobalis:frb-sample-dask-pixels`, commit 75ce0655 (pushed 2026-11-12)
- Needs: `dask-component-index-arrays` (commit 1aafe967, its parent), which needs `fix-unbroadcast-empty`
- Label: enhancement

## Body

~~~~~markdown
`compute_fixed_resolution_buffer` reads a `DaskComponent` as the bounding box of the pixels it samples (`slice(min, max + 1)` along each axis) and picks the pixels from that box, because dask could not take them directly. A zoomed-out view of a cube with a chunk per frame, such as a file per frame, therefore reads every frame between the first and the last one it samples.

With #NNNN a `DaskComponent` takes the sampled pixels directly, so the buffer now passes them to it as to any other component. It keeps the bounding box only for subset masks over dask data.

`compute_fixed_resolution_buffer` on in-memory dask arrays, median of 9 calls, main → this PR, with the tracemalloc peak:

| Case | Time | Peak memory |
| --- | --- | --- |
| (4096, 4096) in chunks of 1024, whole image at 1000 x 1000 | 22.2 → 11.3 ms | 193 → 44 MiB |
| same image, a 500-pixel corner at 800 x 800 | 3.7 → 4.6 ms | 17 → 8 MiB |
| (100, 512, 512) with a chunk per frame, frame 50 at 800 x 800 | 4.1 → 3.8 ms | 22 → 8 MiB |
| same cube, row 256 over all 100 frames | 11.9 → 15.0 ms | 3 → 1 MiB |
| (400, 512, 512), row 256 over 40 of the 400 frames | 37.4 → 8.6 ms | 4 → 1 MiB |
| (4096, 4096), a 500-pixel region rotated by 45 degrees at 800 x 800 | 10.1 → 31.5 ms | 30 → 37 MiB |

Where each chunk costs a file read, the gain is in the chunks not read: 40 frames instead of 400 in the fifth row.

Known slowdown: in a view that is rotated against the data, the sampled pixels are not a grid, so the read still covers their bounding box and the work per pixel comes on top. In the last row the whole call is 3 times slower, and the read alone 5 times (5 → 27 ms).

`test_dask_reads_sampled_chunks` checks that a cube with a chunk per frame reads only the 6 frames it samples; without this change it reads every frame from the first to the last. `test_dask_unlinked_target_axis` checks the buffer's shape when an axis of the target data is not linked to the dask data.

Stacked on #NNNN. Only the last commit is new here.
~~~~~

## Notes for the owner (not to paste)

- Replace both #NNNN with the number of the `dask-component-index-arrays` PR.
- The source change is the fork branch's, with a smaller comment diff: the paragraph that said fancy indexing "doesn't work at all for dask arrays" is deleted, and the paragraph about subset masks is left as upstream wrote it.
- The table is my own measurement of this build on this machine (shared CPU, niced, so times vary by about 20% between runs; the peaks do not). Scripts: `bench.py` and, for the read alone, `bench2.py`, kept with the local reproducers (OPERATIONS.md).
- The review gives the rotated slowdown as 3.5 to 5.5 times. I measured 4.9 times for the read alone (5.4 → 26.6 ms) and about 3 times for the whole call, which includes the coordinate transform. A whole image rotated at 1000 x 1000 is 1.4 times slower for the whole call (48 → 69 ms), with a lower peak (209 → 89 MiB); it is left out of the table to keep it short.
- Two rows are slightly slower (the corner, and the row over all 100 frames, which reads every chunk either way). They are in the table on purpose.
- `test_dask_unlinked_target_axis` passes on main and without this PR's source change. It guards the regression the review found: with the fork's original `__getitem__` it fails with `shapes (1, 5, 4), (3, 5, 4) mismatch`.
- Tests: `test_fixed_resolution_buffer.py`, `test_component.py` and `test_array.py`, 202 passed, 1 xfailed; `test_data.py` also passes. Without the `fixed_resolution_buffer.py` change: `assert {0, 1, 2, 3, 4, 5, ...} == {0, 9, 18, 27, 36, 45}`.
- Compared with main and equal: a 1-D dask dataset in a 2-D frame, a 3-D buffer, bounds outside the data, and a subset mask over dask data.
- Row 28 (the `vindex` fallback) is not built, as asked.
