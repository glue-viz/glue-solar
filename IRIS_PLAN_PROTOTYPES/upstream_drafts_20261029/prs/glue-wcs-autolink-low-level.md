# Autolink datasets whose coords are low-level-only APE 14 WCSes

- Upstream: glue-viz/glue
- Fork branch: `wcs-autolink-low-level` at fe857590716d7617888f711b2e6e80c715da4b78 (one commit on `ape14-wcs-link` f10ef60f)
- Needs: `ape14-wcs-link` (tracker row 13)
- Label: enhancement

## Body

~~~~~
Builds on #NNNN (WCSLink for APE 14 WCSes other than astropy.wcs.WCS); only the last commit is new.

`wcs_autolink` only looks at datasets whose `coords` are a `BaseHighLevelWCS`. A dataset whose WCS
has just the low-level APE 14 API, such as a `SlicedLowLevelWCS`, never gets a suggested link,
although `WCSLink` links it (with #NNNN).

`wcs_autolink` now takes a `BaseLowLevelWCS` too: one import and one condition.

glue's own `Coordinates` classes are `BaseLowLevelWCS` as well. They give no physical types, so
`WCSLink` refuses them at its first check and they still get no link. `wcs_autolink` over 100
datasets with `IdentityCoordinates` takes 1.6 ms.

Test: two images with `SlicedLowLevelWCS` coords get a link; without the change none is suggested.
~~~~~

## Notes for the owner (not to paste)

- Commit subject (62 characters): "Autolink datasets whose coords are low-level-only APE 14 WCSes".
- Diff against its parent: 2 files, 30 insertions, 2 deletions (against upstream/main: 166 and 7).
- From #2595: only the filter in `wcs_autolink` and its import. The fixture is none at all: the test uses
  astropy's own `SlicedLowLevelWCS(wcs, Ellipsis)`, which has the low-level API only, in place of #2595's
  50-line `SimpleLowLevelWCS`. The test sits after `test_wcs_autolink_image_and_spectral_cube`, away from the end
  of the file where the other branches append and from row 4's test.
- Fails without the fix: with the source of `ape14-wcs-link`, `1 failed, 22 passed`: `assert 0 == 1` (no link
  suggested). On upstream/main's source the same test fails the same way. On the branch: `23 passed, 1 xfailed,
  1 xpassed`.
- Checked: a `Data` made without coords has `coords` None, so only datasets given glue `Coordinates` on purpose
  are newly looked at, and they cost about 0.3 us a pair (`glue-wcs/probe_coords.py`).
- Merge with `origin/perf-g5-lazy-scipy-optimize`: TWO conflicts. (1) The test file, as for its parent (both
  append at the end; keep both). (2) The module's imports: this branch adds `BaseLowLevelWCS` to the
  `astropy.wcs.wcsapi` import line and perf-g5 deletes the next line, `from scipy.optimize import leastsq`.
  Resolution: this branch's import line, without the scipy line. With both resolved, the six branches plus
  perf-g5 give `35 passed, 1 xfailed, 1 xpassed`.
- Lint: ruff 0.16.1 passes.
