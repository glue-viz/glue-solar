# Fix WCSLink between datasets with APE 14 WCSes other than astropy.wcs.WCS

- Upstream: glue-viz/glue
- Fork branch: `ape14-wcs-link` at f10ef60f47cdd45494152e9f48c85ca6009bad98 (one commit on upstream/main a34a5011; pushed 2026-11-12)
- Needs: nothing
- Label: bug

## Body

~~~~~
`WCSLink` handles any APE 14 WCS only when two datasets can be linked pixel for pixel. Otherwise (a
cube and an image, say) its general case reads `has_celestial`, `celestial` and `wcs.lng`, which only
`astropy.wcs.WCS` has: for a gWCS or any other APE 14 WCS it raises `AttributeError`, and so does
`wcs_autolink`. It also takes world axis i to belong to pixel axis i, which APE 14 does not promise.

This adds a path for pairs in which either WCS is not an `astropy.wcs.WCS`. It keeps the pixel axes
along which only world axes of the physical types both WCSes have vary (from
`axis_correlation_matrix`), slices the others at 0 and links the sliced WCSes with `pixel_to_pixel`,
as the existing code does. Pairs of `astropy.wcs.WCS` go through the existing code unchanged.

Tests, both failing on main with the `AttributeError`: a cube and an image; a slit spectrum with
three world axes on two pixel axes and an image.

Known limit, shared with the pixel-for-pixel path on main: `pixel_to_pixel` matches several world
objects of one class (two `Quantity` axes, say) by position, so two WCSes that have such axes in
different orders get a transposed link. That needs its own fix, in both paths.
~~~~~

## Notes for the owner (not to paste)

- Commit subject (70 characters): "Fix WCSLink's general case for APE 14 WCSes other than astropy.wcs.WCS", with a
  body. The tree is identical to the fork's first commit 6f6e8d73 (`git diff 6f6e8d73 f10ef60f` is empty); only
  the message changed.
- Diff against upstream/main: 2 files, 136 insertions, 5 deletions.
- The reviewer's optional six-line world-order guard is NOT in it, as instructed: the body's last paragraph
  states the limit instead. `wcs-link-match-world-axes` is the fix; once that has a number, the last sentence
  can point at it.
- Fails without the fix: the test file alone on upstream/main gives `2 failed, 20 passed`, both
  `AttributeError: 'APE14WCS' object has no attribute 'has_celestial'`. On the branch: `22 passed, 1 xfailed,
  1 xpassed`.
- Merge with `origin/perf-g5-lazy-scipy-optimize`: one conflict, in the test file only. Both append at the end
  of `test_wcs_autolinking.py` (this branch's `APE14WCS` block, perf-g5's
  `test_import_does_not_import_scipy_optimize`). Keep both blocks. The module merges cleanly.
- Not verified: astropy older than 8.0.2 (CI's py310 jobs install 6.1). The new path wraps every WCS in
  `SlicedLowLevelWCS`, which before astropy 7.2 cannot invert a 1-D WCS; such a pair would get no link there
  (not an error). No test here uses a 1-D WCS. #2595 avoided the no-op slice for that reason.
- Not in it, from #2595: a check that a dataset's array has as many dimensions as its WCS. The new path indexes
  `pixel_component_ids[data.ndim - 1 - i]`, which for such a dataset lands on a component that means nothing
  (a negative index wraps round) and links it, where #2595 skipped it. glue's own `Data`
  already raises `IndexError` when given a FITS WCS with more axes than the array, so I could only reach this
  with #2595's hand-written test WCS.
- Lint: ruff 0.16.1 passes.
