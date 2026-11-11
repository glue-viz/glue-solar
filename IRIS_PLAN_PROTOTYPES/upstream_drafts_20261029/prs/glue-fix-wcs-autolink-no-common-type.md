# Skip pairs with no physical type in common in wcs_autolink instead of raising ValueError

- Upstream: glue-viz/glue
- Fork branch: `fix-wcs-autolink-no-common-type` at 7b60370273b92187b377bd9956819228520fc4ae (one commit on upstream/main a34a5011)
- Needs: nothing
- Label: bug

## Body

~~~~~
`wcs_autolink` raises for two datasets whose WCSes have no physical type in common, such as an image
and a 1-D spectrum:

    ValueError: Cannot slice WCS: the resulting WCS should have at least one pixel and one world dimension.

`WCSLink`'s general case finds no axis to keep and slices every axis away. `wcs_autolink` skips only
`IncompatibleWCS`, so the error comes out of `find_possible_links` and no link is suggested for any
dataset in the collection.

This raises `IncompatibleWCS` when there is no axis to keep (two lines), so the pair is skipped like
any other that cannot be linked. `test_wcs_autolink_no_common_physical_type` (a FITS image and a 1-D
FITS spectrum) fails on main with the error above.
~~~~~

## Notes for the owner (not to paste)

- Commit subject (69 characters): "Fix ValueError in wcs_autolink for WCSes with no common physical type". The
  tracker's title is 88 characters, so it is the PR title only.
- Diff against upstream/main: 2 files, 29 insertions. Source: 3 lines (the two-line guard and a blank) after the
  two `sorted(slicing_axes...)` lines of the upstream general case. Test: beside the two `emptywcs` tests, before
  `test_wcs_autolink_spectral_cube`, not at the end of the file.
- Fails without the fix: the test file alone on upstream/main gives `1 failed, 20 passed, 1 xfailed, 1 xpassed`,
  the failure being the ValueError quoted in the body. On the branch: `21 passed, 1 xfailed, 1 xpassed`.
- The reviewer's `exp_nomatch.py`: all three pairs raise on main (image + 1-D spectrum, image + 2-D
  frequency/time, 1-D spectrum + 1-D time series); all three give 0 links on the branch.
- Merges cleanly with `origin/perf-g5-lazy-scipy-optimize`, and with the other five branches.
- Lint: ruff 0.16.1 passes (upstream pins 0.17.3, which is not in the scratch tools).
