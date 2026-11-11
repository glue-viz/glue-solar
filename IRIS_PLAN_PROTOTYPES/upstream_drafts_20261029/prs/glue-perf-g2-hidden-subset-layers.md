# Skip updating and redrawing hidden image subset layers

- Upstream: glue-viz/glue
- Fork branch: `nabobalis:perf-g2-hidden-subset-layers`, commit 9deb45f5 (pushed 2026-11-12)
- Label: enhancement

## Body

~~~~~markdown
Every subset change calls `update()` on each layer artist of that subset, and `ImageSubsetLayerArtist.update` recomputes the layer and redraws the canvas even when the layer is hidden. With several image viewers that hide a subset layer, each subset edit redraws all of them for nothing.

`update()` now only drops the cached arrays of a hidden layer, and `_update_image` does a full update when the layer is shown again.

Measured with five tiled image viewers, four of which hide the subset layer: each subset change draws one canvas instead of five and takes 44 ms instead of 158 ms.

`test_hidden_subset_layer` checks that a subset change does not draw the canvas of a viewer whose subset layer is hidden, and that the layer is up to date when it is shown again. On main the canvas is drawn twice.
~~~~~

## Notes for the owner (not to paste)

- The only change to the fork branch: the test no longer adds `from numpy.testing import assert_equal`; its one use is `np.testing.assert_array_equal(...)`. Commit message unchanged.
- I fetched upstream PR #2604's head and checked: the branch now merges cleanly with it, where the fork branch conflicts.
- The 44 and 158 ms are the commit message's numbers (44.3 and 157.6), not measured again.
- Tests: `glue/viewers/image/tests/test_viewer.py` 11 passed, 5 skipped (the visual tests). On upstream/main: `AssertionError: assert 2 == 0` (`draw.call_count`).
