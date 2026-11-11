# Try a WCS link at the middle, first and last pixel of both datasets

- Upstream: glue-viz/glue
- Fork branch: `wcs-link-trial-pixels` at a95c30057f2105992e1bf33bf8293d3621424f6e (one commit on `ape14-wcs-link` f10ef60f)
- Needs: `ape14-wcs-link` (tracker row 13)
- Label: enhancement

## Body

~~~~~
Builds on #NNNN (WCSLink for APE 14 WCSes other than astropy.wcs.WCS); only the last commit is new.

`WCSLink` decides whether two WCSes can be linked by transforming pixel 0 of each dataset to the
other. A WCS may raise for world coordinates outside its range, as a tabular lookup can, and two
datasets that overlap in part need not overlap at pixel 0. Such a pair is refused with
`IncompatibleWCS` although the datasets can be linked.

`get_cids_and_functions` now transforms the middle, first and last pixel of the first dataset to the
second and back, then those of the second, and accepts the pair at the first that raises nothing.

Cost: a pair that links still takes two `pixel_to_pixel` calls. A pair that does not takes six failed
calls where it took one: 0.7 ms against 0.09 ms for a FITS image and a 2-D frequency/time WCS.

Tests: three partial overlaps (the last pixel only, the middle only, the second dataset inside the
first) with a WCS that raises outside its pixel bounds. Each fails without the change.
~~~~~

## Notes for the owner (not to paste)

- Commit subject (67 characters): "Try a WCS link at the middle, first and last pixel of both datasets".
- Diff against its parent: 2 files, 66 insertions, 9 deletions (against upstream/main: 199 and 11).
- From the fork's second commit 20d91e3e: the three-pixel round trip, without the `finite` keyword and its test
  of finite values. Tests: `outside='raise'` only, so the fixture here has no mode at all (it always raises
  outside its bounds); no `first` case. The `nan` mode arrives with `wcs-link-refuse-nan`.
- Fails without the fix: with the source of `ape14-wcs-link`, `3 failed, 22 passed`, each
  `IncompatibleWCS: Can't create WCS link between Data 1 and Data 2`
  (`test_wcs_link_ape14_partial_overlap[last]`, `[middle]`, `[second]`). On the branch: `25 passed, 1 xfailed,
  1 xpassed`.
- The 0.7 against 0.09 ms is measured here (`glue-wcs/time_trial.py`, best of 5 x 200 calls). For a collection
  of many unrelated same-dimension datasets this multiplies: about 0.6 ms more per pair that does not link.
  A maintainer may ask for it to be cheaper; a failure to match world classes does not depend on the pixel,
  but I found no small way to tell it from an out-of-range error.
- The tests use a same-dimension pair, so they do not need the new APE 14 path of row 13; the branch is on it
  because both change `get_cids_and_functions` and the tests use its `APE14WCS` class.
- Merge with `origin/perf-g5-lazy-scipy-optimize`: the same single test-file conflict as its parent (both
  append at the end of the file; keep both).
- Lint: ruff 0.16.1 passes.
