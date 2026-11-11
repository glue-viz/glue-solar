# Refuse NaN links between non-astropy WCSes in WCSLink's general case

- Upstream: glue-viz/glue
- Fork branch: `wcs-link-refuse-nan` at f833d73207deff5141d791089e61f5bf2f3816a5 (one commit on `wcs-link-trial-pixels` a95c3005; pushed 2026-11-12)
- Needs: `wcs-link-trial-pixels` (tracker row 14), which needs `ape14-wcs-link` (row 13)
- Label: enhancement

## Body

~~~~~
Builds on #NNNN (link trial at three pixels); only the last commit is new.

`WCSLink`'s general case for APE 14 WCSes other than `astropy.wcs.WCS` (#MMMM) links datasets that
cannot be linked pixel for pixel, such as a cube and an image. Such a WCS may give NaN, not an error,
for world coordinates outside its data, as gWCS does outside its bounding box, so two datasets that
do not overlap get a link there that gives NaN for every pixel.

Refused with this (`IncompatibleWCS`, and no suggestion from `wcs_autolink`): a pair in that general
case, neither WCS an `astropy.wcs.WCS`, for which none of the middle, first and last pixel of either
dataset transforms to the other and back to finite values. That includes a pair that overlaps only
away from those six pixels.

Not refused, so nothing that links on main today stops linking: datasets that can be linked pixel for
pixel (linked whatever their pixels transform to, overlapping or not), and any pair with an
`astropy.wcs.WCS`. On main the refused pairs raise `AttributeError`.

Tests: a cube and an image that do not overlap are refused (fails without the change); two images
that share only a corner, and a pair with one `astropy.wcs.WCS`, link as they do on main.
~~~~~

## Notes for the owner (not to paste)

- #NNNN is the PR of `wcs-link-trial-pixels`, #MMMM that of `ape14-wcs-link`.
- Commit subject (68 characters): "Refuse NaN links between non-astropy WCSes in WCSLink's general case". The
  tracker's row 16 title ("Refuse a WCS link that gives NaN pixels for WCSes other than astropy.wcs.WCS") no
  longer says what the PR does; this title replaces it. The "pairs that stop linking" list is gone: it is
  empty.
- Diff against its parent: 2 files, 75 insertions, 16 deletions (source: 14 and 6).
- What changed from b2f5b09d: the pixel-for-pixel path no longer passes `finite`, and `astropy_pair` is gone
  from `WCSLink.__init__` (it is as in `wcs-link-trial-pixels`). Only `get_ape14_cids_and_functions` passes
  `finite`.
- ONE THING BEYOND YOUR INSTRUCTION. You said: refuse on the new path, which no caller reaches on main. Some
  callers do reach main's general case with a non-astropy WCS and get a link: when the FIRST dataset's WCS is
  an `astropy.wcs.WCS` without celestial axes, `wcs1.has_celestial and wcs2.has_celestial` stops at the first
  term and never touches the other WCS. A spectrum (astropy) plus a cube (other WCS) links on main that way,
  and since `ape14-wcs-link` it takes the new path. With the refusal for every pair on the new path, one such
  pair stopped linking in my checks: an astropy spectrum with `pixel_bounds` set (astropy 8 gives NaN outside
  them) and a cube whose WCS gives NaN outside its data, not overlapping. So the refusal is for pairs with NO
  `astropy.wcs.WCS` only (`finite = not (isinstance(wcs1, WCS) or isinstance(wcs2, WCS))`, one line and a
  comment). What that gives up, measured on the matrix below: the two variants differ in 12 of 840 pair types,
  all an `astropy.wcs.WCS` WITH `pixel_bounds` beside a WCS that gives NaN outside its data. Two of the 12 link
  on main (the ones your rule protects); the other 10 raise on main and now get a link that gives NaN where
  the datasets do not overlap. With a plain FITS WCS (no `pixel_bounds`) the two variants agree everywhere: a
  pixel of the other dataset always transforms there and back to finite values, so such a pair is never
  refused either way. `test_wcs_link_nan_pixels_one_astropy_wcs` holds the condition: it fails if it is
  replaced by `True`. If you would rather have the simpler rule and accept the two pair types, it is that one
  line.
- Tests and their proof:
  - On the branch: `28 passed, 1 xfailed, 1 xpassed`.
  - `test_wcs_link_ape14_no_overlap` (the proving test, now a cube and an image so that it takes the general
    case): with the parent's source, `1 failed, 27 passed`, `Failed: DID NOT RAISE IncompatibleWCS`.
  - `test_wcs_link_nan_pixels_same_axes` (your 11 x 11 images sharing a 3 x 3 corner): passes on
    upstream/main's source and on the parent; with b2f5b09d's source it fails with `IncompatibleWCS: Can't
    create WCS link between Data 1 and Data 2`.
  - `test_wcs_link_nan_pixels_one_astropy_wcs`: passes on upstream/main's source and on the parent; fails with
    b2f5b09d's source and with the refusal for every pair on the new path. It can only fail on an astropy that
    gives NaN outside `pixel_bounds` (8.0.2 here does); on an older one it passes either way.
  - Dropped: the `nan` cases of `test_wcs_link_ape14_partial_overlap` and `no_overlap[raise]`, which passed
    without the change and guard nothing about the limit.
  - The fixture gained an `outside` mode (`'raise'` by default, so the parent's tests are untouched but for the
    helper's new name `bounded_data`: it now also makes a cube).
- Checked against main with a matrix of 840 pair types (`glue-wcs/matrix.py`, outcomes in `glue-wcs/matrix/`):
  361 link on upstream/main, and all 361 link on this branch with the same axes and the same pixels at three
  sample points. Against its parent this branch refuses 6, all pairs of NaN-outside WCSes in the general case
  (a cube and an image without overlap or sharing only a corner, in either order; a spectrum or a time series
  of spectra and a cube without overlap); each raises `AttributeError` on main.
- Still true, and in the body: in the general case a pair of such WCSes that overlaps only away from the six
  trial pixels is refused although it overlaps. On main it raises, so nothing is lost against main; against
  `wcs-link-trial-pixels` alone it is.
- The guarantee rests on main's general case raising `AttributeError` for a first WCS that is not an
  `astropy.wcs.WCS`. A WCS class of another kind that happens to have `has_celestial`, `celestial` and
  `wcs.lng` would be an exception; I know of none.
- Not verified: astropy older than 8.0.2 (CI's py310 jobs install 6.1). None of the new tests uses a 1-D WCS.
- Merge with `origin/perf-g5-lazy-scipy-optimize`: the same single test-file conflict as row 13 (both append at
  the end of the file; keep both).
- Lint: ruff 0.16.1 passes.
