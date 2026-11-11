# Match world axes by physical type when WCSLink cannot tell them apart by class

- Upstream: glue-viz/glue
- Fork branch: `wcs-link-match-world-axes` at 49bf2cba4c10c4850b2781d92341d65f5bffe842 (one commit on `wcs-link-refuse-nan` f833d732; pushed 2026-11-12)
- Needs: `wcs-link-refuse-nan` (tracker row 16), which needs rows 14 and 13
- Label: bug

## Body

~~~~~
Builds on #NNNN (NaN refusal); only the last commit is new.

On main, two images with the FITS axes `SOLX, SOLY` and `SOLY, SOLX` are linked x to x:
`WCSLink(data1, data2).forwards(1, 2)` gives `(1, 2)`, not `(2, 1)`.

astropy's `pixel_to_pixel` matches the world objects of two WCSes by class, and several objects of
one class by position. Both axes here are `Quantity`, so they are swapped and nothing is raised. Any
pair with two or more world axes of one class in different orders is affected (`HPLN`/`HPLT` too
when sunpy is not imported), pixel for pixel and in the general case for other APE 14 WCSes.

`WCSLink` now puts such world objects in the other WCS's order by the physical types of their axes.
It does so only if a class occurs more than once and both WCSes have the same physical types, each
once, in different orders. Every other pair goes through `pixel_to_pixel` as before.

Cost: the check adds 27 us to a call (221 to 248 us for one pixel of an RA/Dec pair). A link matched
this way does not use `pixel_to_pixel`'s shortcut for broadcast arrays: 13 ms for a 1000 x 1000 grid.

Tests: the pair above, which fails on main, and a cube and an image with other APE 14 WCSes.
~~~~~

## Notes for the owner (not to paste)

- Commit subject (57 characters): "Match world axes of one class by physical type in WCSLink"; the tracker's
  title is 78 characters, so it is the PR title only.
- Diff against its parent: 2 files, 85 insertions, 2 deletions (87 changed lines; against upstream/main: 345
  and 15). Rebased onto the rebuilt `wcs-link-refuse-nan`: the commit adds and removes exactly the lines the
  earlier f1268c1d did, and its message is unchanged. The one conflict was at the end of the test file, where
  both branches append; its two tests now follow the parent's three.
- A rewrite, not a cherry-pick. What differs from #2595's `permuted_values_functions`:
  - The gate is on `world_axis_object_classes`: it applies when some class of one WCS does not occur exactly
    once among the other's, which is when astropy falls back to position. `both_high_level` is gone.
  - It lives in the one function all three link paths call (`get_cids_and_functions`, through a new
    `pixel_to_pixel_by_type`), so the pixel-for-pixel path, the APE 14 path and the upstream general case all
    get it from 35 source lines.
  - It reorders the world OBJECTS and still lets astropy convert them, where #2595 went through world values
    and did its own unit conversion. Units, frames and time scales are therefore handled as before (checked:
    km against m; a SkyCoord beside two Quantity axes; two Quantity axes beside a SpectralCoord).
  - Duplicate physical types, or sets that differ, are left to `pixel_to_pixel` as before; #2595 raised
    `IncompatibleWCS` for duplicates.
- Fails without the fix: with the source of `wcs-link-refuse-nan`, both new tests fail on values, e.g.
  `ACTUAL: array([1., 2.])  DESIRED: array([2, 1])`. `test_wcs_link_world_axes_of_one_class` alone on
  upstream/main fails the same way: this is the reproducer that fails on main, with plain `astropy.wcs.WCS`
  and no fixture. On the branch: `30 passed, 1 xfailed, 1 xpassed` (`2 failed, 28 passed` with the parent's
  source).
- The reviewer's `exp_order.py` on the six branches together: all 8 cases right (on main: 1 right, 1 transposed,
  6 errors). The six together: `32 passed, 1 xfailed, 1 xpassed`.
- Against main, in the matrix of 840 pair types (`glue-wcs/matrix.py`): all 361 that link on main still link
  on this branch. 342 give the same pixels; the other 19 are the one geometry this fixes (SOLX, SOLY against
  SOLY, SOLX, in every mix of WCS kinds), where main gives the swapped pixels.
- Can it stand on upstream/main alone? With its source change and its FIRST test: yes, 60 changed lines (33
  insertions and 2 deletions of source, 25 lines of test). Checked without building a branch: main plus only
  the source change passes that test and main's own (`21 passed`). With BOTH tests: no. The second links a cube
  and an image whose WCSes are not `astropy.wcs.WCS`, which needs the general case that row 13 adds, not only
  its `APE14WCS` test class: on main plus this source change, with that class copied in, it fails with
  `AttributeError: 'APE14WCS' object has no attribute 'has_celestial'`. I stacked it as instructed.
- Left alone on purpose: two WCSes whose world axes are of one class but of DIFFERENT physical types (SOLX,
  SOLY against SOLX, DIST; HPLN, HPLT against HGLN, HGLT without sunpy) are still linked by position, as on
  main. Refusing those is a second behaviour change and would be its own PR.
- The upstream general case for two `astropy.wcs.WCS` of different dimensions has other faults with such axes
  (a cube SOLX, FREQ, SOLY and an image SOLY, SOLX raise `IndexError` on main, from `slicing_axes1 =
  slicing_axes2 = []` naming one list). Not touched.
- The 13 ms: a type-matched link computes the full grid, where `pixel_to_pixel` computes separable axes once
  (0.2 ms, but transposed). Only pairs that were wrong before pay this.
- Merge with `origin/perf-g5-lazy-scipy-optimize`: the same single test-file conflict as row 13 (keep both).
- Lint: ruff 0.16.1 passes.
