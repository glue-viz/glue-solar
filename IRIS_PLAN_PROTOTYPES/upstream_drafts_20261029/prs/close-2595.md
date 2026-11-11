# Closing comment for glue-viz/glue#2595 (`ape14-wcs-autolink`)

- Upstream: glue-viz/glue, draft PR #2595
- When: #2595 was closed on 2026-11-12 without a comment; post this once the four PRs below are open
- Fill in: the PR numbers marked #AAAA to #FFFF below

## Comment

~~~~~
Closing in favour of smaller PRs that each do one thing: #AAAA (WCSLink for APE 14 WCSes other than
astropy.wcs.WCS), #BBBB (wcs_autolink for low-level-only WCSes), #CCCC (world axes of one class matched
by physical type) and #DDDD (no ValueError for pairs with no physical type in common). With those
applied, ten of this PR's eleven tests pass unchanged. The eleventh, `test_wcs_autolink_ndim_mismatch`,
is about a dataset whose array has a different number of dimensions than its WCS, which none of them
handles; I can open that separately if it is wanted. The axis permutation here was switched on by
whether both WCSes were high-level, which was the wrong test: #CCCC goes by the classes of the world
objects instead, and also fixes the same swap for pairs of astropy.wcs.WCS on main.
~~~~~

Numbers: #AAAA `ape14-wcs-link`, #BBBB `wcs-autolink-low-level`, #CCCC `wcs-link-match-world-axes`,
#DDDD `fix-wcs-autolink-no-common-type`. The two others (`wcs-link-trial-pixels`, `wcs-link-refuse-nan`)
replace nothing in #2595, so the comment does not name them.

## Notes for the owner (not to paste)

#2595's eleven tests, run unchanged from a file of their own (`glue-wcs/pr2595_tests.py`) against three trees:

| Tree | Passed |
|---|---|
| upstream/main a34a5011 | 0 of 11 |
| the stack's tip, `wcs-link-match-world-axes` (rows 13, 14, 16, 17) | 3 of 11 |
| all six branches merged (the tip plus rows 4 and 15) | 10 of 11 |

- On the stack's tip alone the 3 that pass are `test_wcs_autolink_low_level_disjoint`,
  `test_wcs_autolink_low_level_transform_failure` and `test_wcs_autolink_low_level_disjoint_same_ndim`. The other
  8 fail with `assert 0 == 1`: they call `wcs_autolink` on low-level-only WCSes, and the filter change is on the
  side branch `wcs-autolink-low-level` (row 15), which is not in the linear stack.
- With all six merged, these 10 pass: `test_wcs_autolink_low_level`, `_low_level_and_fits_wcs`,
  `_low_level_disjoint`, `_low_level_transform_failure`, `_correlated_axes`, `_low_level_disjoint_same_ndim`,
  `_low_level_world_order_permutation`, `_low_level_11d`, `_all_axes_coupled`, `_iris_like`.
- The one that fails: `test_wcs_autolink_ndim_mismatch`, `assert 3 == 1`. #2595 raised `IncompatibleWCS` when
  `data.ndim != wcs.pixel_n_dim`; none of the six branches has that check, so the mismatched dataset is linked
  (through whichever pixel components `data.ndim - 1 - i` lands on; a negative index wraps round). glue's
  `Data` itself raises `IndexError` for a FITS WCS with more axes than
  the array, so the state is reachable only with a WCS like the test's hand-written one. Two lines in `WCSLink`
  would cover it.

Behaviour of #2595 that the six branches do not cover:

1. The dimension check above.
2. #2595 skipped the `SlicedLowLevelWCS` wrapper when no axis is sliced away, because before astropy 7.2 that
   wrapper cannot invert a 1-D WCS. Row 13 always wraps. Here (astropy 8.0.2) `_low_level_and_fits_wcs`, which
   links two 1-D WCSes, passes; on CI's py310 jobs (astropy 6.1) such a pair would get no link. Not verified:
   no older astropy is installed.
3. Nothing else that I found. `kept_numpy_axes` is replaced by row 13's `matched_pixel_axes`
   (`_correlated_axes`, `_all_axes_coupled` and `_iris_like` pass); the permutation by row 17; the guard for
   pairs with nothing in common by rows 13 and 4. "Time axes out of wcs_autolink" was never in #2595.
