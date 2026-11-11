# Apply a restored image layer's cmap_bad

- Upstream: glue-viz/glue
- Fork branch: `nabobalis:fix-restored-cmap-bad`, commit 35d2e2e6 (on the fork, not rebuilt)
- Label: bug

## Body

~~~~~markdown
`ImageLayerArtist` passes the layer state's `cmap_bad` to the viewer's `CompositeArray` only from its `cmap_bad` callback. A layer artist made from a state that already has a `cmap_bad`, as when a session is restored, leaves the composite's at `None`, so NaN values are drawn opaque again after a restore.

The artist now sets the composite's `cmap_bad` from its state when it is created, if the state has one (3 lines). A state with `cmap_bad=None` leaves the composite alone, so adding a layer does not reset another layer's bad colour.

`test_restored_layer_cmap_bad` saves and restores an application with an image viewer whose layer has a transparent `cmap_bad`. It fails on main, where the restored composite's `cmap_bad` is `None`.
~~~~~

## Notes for the owner (not to paste)

- Not rebuilt and not run by me: the text comes from the commit message, the drafted body (`prs/glue-fix-restored-cmap-bad.md`, shortened from 56 lines) and the review, which found the test fails without the fix once glue-solar is stubbed.
- The drafted body's reproducer and its last line about a downstream workaround are left out.
- Its test is added to `glue/viewers/image/tests/test_viewer.py`, like those of `perf-g1a-wcs-labels` and `perf-g2-hidden-subset-layers`. The rebuilt `perf-g2-hidden-subset-layers` merges cleanly with this branch.
